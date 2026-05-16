"""
Multi-ESP32 Dual Collector for Parallel CSI Data Capture

Collects from 2+ ESP32s simultaneously, merges data, and prepares for training.

Usage:
    python -c "from src.data_collection.multi_device import collect_multi; \
               collect_multi(['/dev/ttyUSB0', '/dev/ttyUSB1'], \
                           labels=[0, 0], \
                           locations=[(0, 0), (10, 0)], \
                           duration=60)"

Or use main.py:
    python main.py collect-multi --ports /dev/ttyUSB0 /dev/ttyUSB1 \
                                 --labels 0 0 \
                                 --locations 0,0 10,0 \
                                 --duration 60
"""

from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import List, Tuple
import pandas as pd
import numpy as np
from datetime import datetime

from src.utils.config import RAW_DIR, PROC_DIR
from src.utils.helper import get_logger
from src.data_collection.csi_capture import capture as single_capture

logger = get_logger(__name__)


class MultiDeviceCollector:
    """Manages parallel collection from multiple ESP32 devices."""
    
    def __init__(self, ports: List[str], labels: List[int], 
                 locations: List[Tuple[float, float]], 
                 baud: int = 115200, timeout: float = 2.0):
        """
        Initialize collector for multiple devices.
        
        Parameters
        ----------
        ports : list[str]
            Serial ports (e.g., ['/dev/ttyUSB0', '/dev/ttyUSB1'])
        labels : list[int]
            Room labels for each device
        locations : list[(x, y)]
            (x, y) coordinates in metres for each device location
        baud : int
            Baud rate (default: 115200)
        timeout : float
            Serial timeout in seconds
        """
        self.ports = ports
        self.labels = labels
        self.locations = locations
        self.baud = baud
        self.timeout = timeout
        self.threads = []
        self.output_files = []
        self.errors = {}
        
        if len(ports) != len(labels) or len(ports) != len(locations):
            raise ValueError("ports, labels, and locations must have same length")
        
        logger.info(f"MultiDeviceCollector initialized with {len(ports)} devices")
        for i, (port, label, loc) in enumerate(zip(ports, labels, locations)):
            logger.info(f"  Device {i+1}: {port} → Room {label}, Location {loc}")
    
    def _capture_worker(self, device_id: int, port: str, label: int, 
                       x: float, y: float, duration: int, out_path: Path):
        """Worker thread for capturing from a single device."""
        logger.info(f"[Device {device_id}] Starting capture on {port}")
        
        try:
            single_capture(
                port=port,
                baud=self.baud,
                duration=duration,
                label=label,
                x=x,
                y=y,
                out_path=out_path,
            )
            self.output_files.append(out_path)
            logger.info(f"[Device {device_id}] Capture complete → {out_path}")
        except Exception as e:
            error_msg = f"[Device {device_id}] Capture failed: {e}"
            logger.error(error_msg)
            self.errors[device_id] = str(e)
    
    def collect_parallel(self, duration: int = 60) -> dict:
        """
        Collect from all devices in parallel.
        
        Parameters
        ----------
        duration : int
            Collection duration per device (seconds)
            
        Returns
        -------
        dict with keys:
            files       – list of output CSV paths
            errors      – dict of device_id → error message
            merged_file – path to merged CSV (if successful)
            combined_samples – total samples collected
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"Starting parallel collection from {len(self.ports)} devices")
        logger.info(f"Duration: {duration}s per device")
        logger.info(f"{'='*60}\n")
        
        # Create timestamp for this batch
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Start collection threads
        self.threads = []
        self.output_files = []
        self.errors = {}
        
        for device_id, (port, label, (x, y)) in enumerate(
            zip(self.ports, self.labels, self.locations)
        ):
            out_file = RAW_DIR / f"esp32_{device_id}_{timestamp}_{port.replace('/', '_')}.csv"
            
            thread = threading.Thread(
                target=self._capture_worker,
                args=(device_id, port, label, x, y, duration, out_file),
                daemon=False
            )
            self.threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        logger.info("Waiting for all devices to finish collection...\n")
        for i, thread in enumerate(self.threads):
            thread.join()
            logger.info(f"Device {i+1} thread completed")
        
        # Merge collected files
        merged_file = None
        if self.output_files:
            merged_file = self.merge_files(self.output_files)
        
        # Summary
        logger.info(f"\n{'='*60}")
        logger.info(f"Collection Summary:")
        logger.info(f"  Devices started:    {len(self.ports)}")
        logger.info(f"  Successful:         {len(self.output_files)}")
        logger.info(f"  Errors:             {len(self.errors)}")
        
        if self.output_files:
            combined_samples = sum(
                len(pd.read_csv(f)) for f in self.output_files
            )
            logger.info(f"  Total samples:      {combined_samples}")
        
        if merged_file:
            logger.info(f"  Merged file:        {merged_file}")
        
        logger.info(f"{'='*60}\n")
        
        return {
            'files': self.output_files,
            'errors': self.errors,
            'merged_file': merged_file,
            'combined_samples': combined_samples if self.output_files else 0,
            'success': len(self.errors) == 0 and len(self.output_files) > 0,
        }
    
    @staticmethod
    def merge_files(csv_files: List[Path], output_path: Path = None) -> Path:
        """
        Merge multiple CSV files into one.
        
        Parameters
        ----------
        csv_files : list[Path]
            CSVs to merge
        output_path : Path, optional
            Output file path (default: data/raw/merged_*.csv)
            
        Returns
        -------
        Path to merged file
        """
        logger.info(f"\nMerging {len(csv_files)} CSV files...")
        
        dfs = []
        for csv_file in csv_files:
            try:
                df = pd.read_csv(csv_file)
                dfs.append(df)
                logger.info(f"  ✓ {csv_file.name}: {len(df)} rows")
            except Exception as e:
                logger.error(f"  ✗ {csv_file.name}: {e}")
        
        if not dfs:
            logger.error("No valid CSV files to merge")
            return None
        
        # Combine all dataframes
        merged_df = pd.concat(dfs, ignore_index=True)
        
        # Default output path
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = RAW_DIR / f"merged_{timestamp}.csv"
        
        # Save merged file
        merged_df.to_csv(output_path, index=False)
        
        logger.info(f"\n✓ Merged file saved: {output_path}")
        logger.info(f"  Total rows: {len(merged_df)}")
        logger.info(f"  Columns: {list(merged_df.columns)}")
        
        return output_path
    
    @staticmethod
    def merge_and_parse(csv_files: List[Path], output_dir: Path = None) -> dict:
        """
        Merge CSV files AND parse into numpy arrays (ready for training).
        
        Parameters
        ----------
        csv_files : list[Path]
        output_dir : Path, optional
            Directory for numpy outputs (default: PROC_DIR)
            
        Returns
        -------
        dict with keys: amplitude_db, phase, metadata
        """
        from src.data_collection.parser import parse_file
        
        output_dir = output_dir or PROC_DIR
        output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"\nParsing {len(csv_files)} files to numpy arrays...")
        
        all_csi = []
        all_metadata = []
        
        for csv_file in csv_files:
            parsed = parse_file(csv_file)
            if parsed:
                all_csi.append(parsed['csi_complex'])
                meta = pd.DataFrame({
                    'label': parsed['label'],
                    'x_m': parsed['x_m'],
                    'y_m': parsed['y_m'],
                    'rssi': parsed['rssi'],
                })
                all_metadata.append(meta)
        
        if not all_csi:
            logger.error("No valid CSI data parsed")
            return None
        
        # Combine CSI
        csi_combined = np.vstack(all_csi)
        amplitude = np.abs(csi_combined)
        amplitude_db = 20 * np.log10(amplitude + 1e-9)
        phase = np.angle(csi_combined)
        
        # Combine metadata
        metadata = pd.concat(all_metadata, ignore_index=True)
        
        # Save numpy arrays
        np.save(output_dir / "amplitude_db.npy", amplitude_db)
        np.save(output_dir / "phase.npy", phase)
        metadata.to_csv(output_dir / "metadata.csv", index=False)
        
        logger.info(f"✓ Parsed to numpy arrays:")
        logger.info(f"  Amplitude: {amplitude_db.shape}")
        logger.info(f"  Phase:     {phase.shape}")
        logger.info(f"  Metadata:  {len(metadata)} rows")
        
        return {
            'amplitude_db': amplitude_db,
            'phase': phase,
            'metadata': metadata,
            'output_dir': output_dir,
        }


def collect_multi(
    ports: List[str],
    labels: List[int],
    locations: List[Tuple[float, float]],
    duration: int = 60,
    baud: int = 115200,
    parse: bool = True,
) -> dict:
    """
    High-level function to collect from multiple ESP32s and merge data.
    
    Parameters
    ----------
    ports : list[str]
        Serial ports
    labels : list[int]
        Room labels
    locations : list[(x, y)]
        Device locations
    duration : int
        Seconds per device
    baud : int
        Baud rate
    parse : bool
        If True, also parse to numpy arrays
        
    Returns
    -------
    dict with collection results
    """
    collector = MultiDeviceCollector(ports, labels, locations, baud=baud)
    results = collector.collect_parallel(duration=duration)
    
    if parse and results['files']:
        parse_results = MultiDeviceCollector.merge_and_parse(results['files'])
        results['numpy_data'] = parse_results
    
    return results
