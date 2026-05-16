#!/usr/bin/env python3
"""
Quick Start Script for CSI Indoor Localization

Complete production workflow:
  python quick_start.py setup     ← Initial device configuration
  python quick_start.py collect   ← Collect training data from all ESP32s
  python quick_start.py train     ← Train models
  python quick_start.py run       ← Live localization demo
"""

import sys
import json
import argparse
from pathlib import Path
import time
from datetime import datetime

from src.utils.helper import get_logger
from src.utils.config import RAW_DIR, PROC_DIR, MODEL_DIR, ROOM_LABELS

logger = get_logger(__name__)


def load_config():
    """Load device configuration."""
    config_file = Path("setup_config.json")
    if not config_file.exists():
        logger.error("Configuration not found. Run: python quick_start.py setup")
        return None
    
    with open(config_file) as f:
        return json.load(f)


def cmd_setup(args):
    """Run setup wizard."""
    from setup_wizard import run_setup_wizard
    run_setup_wizard()


def cmd_collect(args):
    """Collect training data from all ESP32s."""
    logger.info("="*70)
    logger.info("DATA COLLECTION - Multi-Device CSI Capture")
    logger.info("="*70)
    
    config = load_config()
    if not config:
        return
    
    devices = config["devices"]
    duration = args.duration or 60
    
    logger.info(f"\nCollecting from {len(devices)} device(s) for {duration}s each...\n")
    
    # Use multi-device collector
    from src.data_collection.multi_device import collect_multi
    
    ports = [d["port"] for d in devices]
    labels = [d["label"] for d in devices]
    locations = [(d["x"], d["y"]) for d in devices]
    
    results = collect_multi(
        ports=ports,
        labels=labels,
        locations=locations,
        duration=duration,
        baud=115200,
        parse=args.parse,
    )
    
    logger.info("\n" + "="*70)
    logger.info("COLLECTION COMPLETE")
    logger.info("="*70)
    logger.info(f"Files collected: {len(results['files'])}")
    logger.info(f"Total samples: {results['combined_samples']}")
    if results['merged_file']:
        logger.info(f"Merged CSV: {results['merged_file']}")
    if results['numpy_data']:
        logger.info(f"Numpy arrays: {results['numpy_data']['output_dir']}")
    logger.info("="*70 + "\n")


def cmd_train(args):
    """Train models on collected data."""
    logger.info("="*70)
    logger.info("MODEL TRAINING - Full Pipeline")
    logger.info("="*70 + "\n")
    
    # Check if data exists
    if not (PROC_DIR / "amplitude_db.npy").exists():
        logger.error("Processed data not found! Run: python quick_start.py collect")
        return
    
    from src.localization.train import train_pipeline
    
    logger.info("Training on processed CSI data...")
    results = train_pipeline(use_pca=True)
    
    logger.info("\n" + "="*70)
    logger.info("TRAINING RESULTS")
    logger.info("="*70)
    logger.info(f"Room Classification Accuracy  : {results['accuracy']*100:.2f}%")
    logger.info(f"Position MAE (X)              : {results['mae_x']:.3f} m")
    logger.info(f"Position MAE (Y)              : {results['mae_y']:.3f} m")
    logger.info(f"Mean Euclidean Error          : {results['mean_euclidean_error']:.3f} m")
    logger.info(f"90th Percentile Error         : {results['p90_error']:.3f} m")
    logger.info("="*70 + "\n")
    
    logger.info("Models saved to: models/")
    logger.info("Ready for live prediction!")


def cmd_run(args):
    """Run live real-time localization."""
    logger.info("="*70)
    logger.info("LIVE REAL-TIME LOCALIZATION")
    logger.info("="*70 + "\n")
    
    config = load_config()
    if not config:
        return
    
    # Check if models exist
    if not (MODEL_DIR / "room_classifier.pkl").exists():
        logger.error("Models not found! Run: python quick_start.py train")
        return
    
    from src.localization.predict import Artefacts, predict_live
    from src.visualization.realtime_display import RealtimeDisplay
    from src.utils.config import ROOM_LABELS
    
    logger.info("Loading trained models...")
    art = Artefacts().load_all()
    
    devices = config["devices"]
    port = devices[0]["port"]  # Use first device
    
    logger.info(f"Listening on port: {port}")
    logger.info("Press Ctrl+C to stop\n")
    
    # Setup display
    display = None
    try:
        display = RealtimeDisplay(room_labels=ROOM_LABELS)
        display.start()
    except Exception as e:
        logger.warning(f"Could not start GUI display: {e}. Running headless.")
    
    pred_count = 0
    
    def on_pred(pred: dict):
        nonlocal pred_count
        pred_count += 1
        
        timestamp = datetime.now().strftime("%H:%M:%S")
        logger.info(
            f"[{timestamp}] Room: {pred['room_name']:15s} | "
            f"({pred['x_pred']:.2f}m, {pred['y_pred']:.2f}m) | "
            f"Confidence: {pred['confidence']:.2%}"
        )
        
        if display:
            display.update(
                x=pred["x_pred"],
                y=pred["y_pred"],
                room_name=pred["room_name"],
            )
    
    try:
        predict_live(port=port, art=art, on_prediction=on_pred)
    except KeyboardInterrupt:
        logger.info("\n✓ Stopped by user")
    finally:
        if display:
            display.stop()
        logger.info(f"\nProcessed {pred_count} predictions")


def cmd_demo(args):
    """Run demo with synthetic data (no ESP32 needed)."""
    logger.info("="*70)
    logger.info("DEMO MODE - Synthetic Data")
    logger.info("="*70 + "\n")
    
    logger.info("This mode generates synthetic CSI data for testing\n")
    
    # Check if models exist
    if (MODEL_DIR / "room_classifier.pkl").exists():
        logger.info("✓ Models found, running live demo on synthetic data...")
        
        from src.localization.predict import Artefacts
        import numpy as np
        
        art = Artefacts().load_all()
        
        logger.info("\n" + "="*70)
        logger.info("DEMO PREDICTIONS (Synthetic Data)")
        logger.info("="*70 + "\n")
        
        # Generate 5 random test samples
        from src.preprocessing.normalization import transform
        from src.feature_engineering.pca import apply_pca
        from src.utils.config import ROOM_LABELS
        
        np.random.seed(42)
        X_random = np.random.randn(5, 30)
        
        for i in range(5):
            preds = art.classifier.predict(X_random[i:i+1])
            x_preds = art.reg_x.predict(X_random[i:i+1])
            y_preds = art.reg_y.predict(X_random[i:i+1])
            
            room_id = preds[0]
            room_name = ROOM_LABELS.get(int(room_id), "unknown")
            
            logger.info(
                f"Sample {i+1}: Room={room_name:15s} | "
                f"Position=({x_preds[0]:.2f}m, {y_preds[0]:.2f}m)"
            )
        
        logger.info("\n" + "="*70 + "\n")
    else:
        logger.info("Running full pipeline on synthetic data...")
        from src.localization.train import train_pipeline
        
        results = train_pipeline(use_pca=True)
        
        logger.info("\n" + "="*70)
        logger.info("SYNTHETIC DATA - Training Results")
        logger.info("="*70)
        logger.info(f"Room Classification Accuracy  : {results['accuracy']*100:.2f}%")
        logger.info(f"Position MAE (X)              : {results['mae_x']:.3f} m")
        logger.info(f"Position MAE (Y)              : {results['mae_y']:.3f} m")
        logger.info(f"Mean Euclidean Error          : {results['mean_euclidean_error']:.3f} m")
        logger.info("="*70 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="CSI Indoor Localization - Quick Start",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
QUICK START GUIDE:
  1. Setup:    python quick_start.py setup
  2. Collect:  python quick_start.py collect --duration 60
  3. Train:    python quick_start.py train
  4. Run:      python quick_start.py run

DEMO (no ESP32 needed):
  python quick_start.py demo
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Setup command
    subparsers.add_parser("setup", help="Initial device & floor plan setup")
    
    # Collect command
    collect_parser = subparsers.add_parser("collect", help="Collect training data")
    collect_parser.add_argument("--duration", type=int, default=60,
                               help="Recording duration per device (seconds)")
    collect_parser.add_argument("--parse", action="store_true",
                               help="Auto-parse to numpy arrays")
    
    # Train command
    subparsers.add_parser("train", help="Train models")
    
    # Run command
    subparsers.add_parser("run", help="Live real-time localization")
    
    # Demo command
    subparsers.add_parser("demo", help="Demo with synthetic data (no ESP32)")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Execute command
    command_map = {
        "setup": cmd_setup,
        "collect": cmd_collect,
        "train": cmd_train,
        "run": cmd_run,
        "demo": cmd_demo,
    }
    
    handler = command_map.get(args.command)
    if handler:
        handler(args)


if __name__ == "__main__":
    main()
