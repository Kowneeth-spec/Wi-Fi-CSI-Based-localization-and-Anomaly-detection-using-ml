# src/data_collection/parser.py
"""
Convert raw ESP32 CSI CSV files into a clean NumPy / Pandas format.

Expected raw CSV columns:
    timestamp, seq, rssi, label, x_m, y_m, raw_tokens

raw_tokens is a comma-separated list of alternating I/Q values:
    i0, q0, i1, q1, ..., i(N-1), q(N-1)

This parser:
1. Reads one or more raw CSVs.
2. Parses I/Q pairs → complex CSI matrix.
3. Validates packet length (drops malformed rows).
4. Saves processed amplitude + phase arrays alongside metadata.
"""

from __future__ import annotations

import glob
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from src.utils.config import NUM_SUBCARRIERS, PROC_DIR
from src.utils.helper import get_logger, amplitude_from_complex, phase_from_complex, to_db, save_dataframe

logger = get_logger(__name__)

EXPECTED_IQ_VALUES = NUM_SUBCARRIERS * 2    # I and Q per subcarrier


# ── Low-level row parser ──────────────────────────────────────────────────────
def parse_raw_tokens(raw_tokens: str) -> Optional[np.ndarray]:
    """
    Parse a comma-separated I/Q string into a complex array.

    Parameters
    ----------
    raw_tokens : str
        E.g. "3,-2,5,1,-4,7, ..."  (alternating I, Q values)

    Returns
    -------
    complex ndarray of shape (NUM_SUBCARRIERS,) or None on parse error.
    """
    try:
        values = list(map(float, raw_tokens.split(",")))
    except ValueError:
        return None

    if len(values) != EXPECTED_IQ_VALUES:
        return None

    iq = np.array(values).reshape(-1, 2)
    return iq[:, 0] + 1j * iq[:, 1]


# ── File-level parser ─────────────────────────────────────────────────────────
def parse_file(csv_path: Path) -> Optional[dict]:
    """
    Parse a single raw CSI CSV.

    Returns a dict with keys:
        timestamps  – list[str]
        seq         – ndarray int
        rssi        – ndarray float
        label       – ndarray int
        x_m         – ndarray float
        y_m         – ndarray float
        csi_complex – ndarray complex, shape (N, NUM_SUBCARRIERS)
        amplitude   – ndarray float,   shape (N, NUM_SUBCARRIERS)  [linear]
        amplitude_db– ndarray float,   shape (N, NUM_SUBCARRIERS)  [dB]
        phase       – ndarray float,   shape (N, NUM_SUBCARRIERS)  [-π, π]
    """
    csv_path = Path(csv_path)
    logger.info(f"Parsing {csv_path.name}")

    try:
        df = pd.read_csv(csv_path)
    except Exception as exc:
        logger.error(f"Cannot read {csv_path}: {exc}")
        return None

    required = {"timestamp", "seq", "rssi", "label", "x_m", "y_m", "raw_tokens"}
    if not required.issubset(df.columns):
        logger.error(f"Missing columns in {csv_path.name}: {required - set(df.columns)}")
        return None

    complex_rows, valid_mask = [], []
    for _, row in df.iterrows():
        csi = parse_raw_tokens(str(row["raw_tokens"]))
        if csi is None:
            valid_mask.append(False)
        else:
            complex_rows.append(csi)
            valid_mask.append(True)

    valid_mask = np.array(valid_mask, dtype=bool)
    df_valid   = df[valid_mask].reset_index(drop=True)
    n_dropped  = (~valid_mask).sum()

    if n_dropped:
        logger.warning(f"  Dropped {n_dropped} malformed packets ({n_dropped/len(df)*100:.1f}%)")

    if len(complex_rows) == 0:
        logger.error("No valid packets found.")
        return None

    csi_complex  = np.array(complex_rows)                    # (N, 52)
    amplitude    = amplitude_from_complex(csi_complex)
    amplitude_db = to_db(amplitude)
    phase        = phase_from_complex(csi_complex)

    logger.info(f"  → {len(complex_rows)} valid packets, shape {csi_complex.shape}")

    return dict(
        timestamps   = df_valid["timestamp"].tolist(),
        seq          = df_valid["seq"].to_numpy(dtype=int),
        rssi         = df_valid["rssi"].to_numpy(dtype=float),
        label        = df_valid["label"].to_numpy(dtype=int),
        x_m          = df_valid["x_m"].to_numpy(dtype=float),
        y_m          = df_valid["y_m"].to_numpy(dtype=float),
        csi_complex  = csi_complex,
        amplitude    = amplitude,
        amplitude_db = amplitude_db,
        phase        = phase,
    )


# ── Multi-file loader ─────────────────────────────────────────────────────────
def parse_directory(
    raw_dir: Path = None,
    pattern: str = "*.csv",
    save: bool = True,
    out_dir: Path = None,
) -> dict:
    """
    Parse all CSVs matching *pattern* in *raw_dir* and concatenate.

    Parameters
    ----------
    raw_dir  : directory with raw CSVs (default: config.RAW_DIR)
    pattern  : glob pattern
    save     : if True, save processed arrays to *out_dir*
    out_dir  : output directory (default: config.PROC_DIR)

    Returns
    -------
    Merged dict same structure as parse_file output.
    """
    from src.utils.config import RAW_DIR, PROC_DIR
    raw_dir = Path(raw_dir or RAW_DIR)
    out_dir = Path(out_dir or PROC_DIR)

    files = sorted(raw_dir.glob(pattern))
    if not files:
        raise FileNotFoundError(f"No files matching '{pattern}' in {raw_dir}")

    logger.info(f"Found {len(files)} raw files in {raw_dir}")

    parts: list[dict] = []
    for f in files:
        result = parse_file(f)
        if result:
            parts.append(result)

    if not parts:
        raise ValueError("No valid data parsed from any file.")

    # Concatenate all arrays
    merged = {
        "timestamps":   sum([p["timestamps"]       for p in parts], []),
        "seq":          np.concatenate([p["seq"]          for p in parts]),
        "rssi":         np.concatenate([p["rssi"]         for p in parts]),
        "label":        np.concatenate([p["label"]        for p in parts]),
        "x_m":          np.concatenate([p["x_m"]          for p in parts]),
        "y_m":          np.concatenate([p["y_m"]          for p in parts]),
        "csi_complex":  np.vstack([p["csi_complex"]       for p in parts]),
        "amplitude":    np.vstack([p["amplitude"]          for p in parts]),
        "amplitude_db": np.vstack([p["amplitude_db"]       for p in parts]),
        "phase":        np.vstack([p["phase"]              for p in parts]),
    }

    total = len(merged["label"])
    logger.info(f"Total parsed packets: {total}")

    if save:
        out_dir.mkdir(parents=True, exist_ok=True)
        np.save(out_dir / "csi_complex.npy",  merged["csi_complex"])
        np.save(out_dir / "amplitude.npy",     merged["amplitude"])
        np.save(out_dir / "amplitude_db.npy",  merged["amplitude_db"])
        np.save(out_dir / "phase.npy",         merged["phase"])

        meta = pd.DataFrame({
            "timestamp": merged["timestamps"],
            "seq":       merged["seq"],
            "rssi":      merged["rssi"],
            "label":     merged["label"],
            "x_m":       merged["x_m"],
            "y_m":       merged["y_m"],
        })
        save_dataframe(meta, out_dir / "metadata.csv")
        logger.info(f"Saved processed arrays to {out_dir}")

    return merged


# ── CLI ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="Parse raw ESP32 CSI files")
    p.add_argument("--raw_dir", default=None)
    p.add_argument("--out_dir", default=None)
    args = p.parse_args()
    parse_directory(raw_dir=args.raw_dir, out_dir=args.out_dir)
