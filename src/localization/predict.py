# src/localization/predict.py
"""
Inference module – load saved models and predict on new CSI data.

Two entry points
----------------
predict_from_file(csv_path)  – batch predict from a raw CSV file
predict_live(serial_port)    – real-time prediction from ESP32 serial stream
"""

from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from src.utils.config import (
    CLASSIFIER_FILE,
    ENCODER_FILE,
    PCA_FILE,
    REGRESSOR_X_FILE,
    REGRESSOR_Y_FILE,
    ROOM_LABELS,
    SCALER_FILE,
    SERIAL_PORT,
    BAUD_RATE,
)
from src.utils.helper import get_logger

logger = get_logger(__name__)


# ── Artefact loader ───────────────────────────────────────────────────────────
class Artefacts:
    """Lazy-loaded inference artefacts (scaler, PCA, models, encoder)."""

    def __init__(self):
        self._scaler     = None
        self._pca        = None
        self._classifier = None
        self._reg_x      = None
        self._reg_y      = None
        self._encoder    = None

    def load_all(self) -> "Artefacts":
        for path, attr in [
            (SCALER_FILE,      "_scaler"),
            (PCA_FILE,         "_pca"),
            (CLASSIFIER_FILE,  "_classifier"),
            (REGRESSOR_X_FILE, "_reg_x"),
            (REGRESSOR_Y_FILE, "_reg_y"),
            (ENCODER_FILE,     "_encoder"),
        ]:
            if not Path(path).exists():
                raise FileNotFoundError(
                    f"Missing artefact: {path}. Run train pipeline first."
                )
            setattr(self, attr, joblib.load(path))
            logger.info(f"Loaded {Path(path).name}")
        return self

    @property
    def scaler(self):     return self._scaler
    @property
    def pca(self):        return self._pca
    @property
    def classifier(self): return self._classifier
    @property
    def reg_x(self):      return self._reg_x
    @property
    def reg_y(self):      return self._reg_y
    @property
    def encoder(self):    return self._encoder


# ── Feature pipeline for a raw feature matrix ─────────────────────────────────
def _preprocess_features(X_raw: np.ndarray, art: Artefacts) -> np.ndarray:
    """Preprocess features with robust NaN/inf handling."""
    # Replace any NaN or inf values from feature extraction
    X_raw = np.nan_to_num(X_raw, nan=0.0, posinf=0.0, neginf=0.0)
    
    X_scaled = art.scaler.transform(X_raw)
    
    # Handle potential NaN from scaling
    X_scaled = np.nan_to_num(X_scaled, nan=0.0, posinf=0.0, neginf=0.0)
    
    X_pca = art.pca.transform(X_scaled)
    
    # Handle potential NaN from PCA
    X_pca = np.nan_to_num(X_pca, nan=0.0, posinf=0.0, neginf=0.0)
    
    return X_pca


# ── Single prediction from a feature vector ───────────────────────────────────
def predict_single(X_raw: np.ndarray, art: Artefacts) -> dict:
    """
    Predict for a single feature window (shape (1, F) or (F,)).

    Returns
    -------
    dict:
        room_label  – int
        room_name   – str
        x_pred      – float (metres)
        y_pred      – float (metres)
        confidence  – float (classifier max probability)
    """
    X = X_raw.reshape(1, -1)
    X_proc = _preprocess_features(X, art)

    label_enc  = int(art.classifier.predict(X_proc)[0])
    proba      = art.classifier.predict_proba(X_proc)[0]
    confidence = float(proba.max())
    room_name  = str(art.encoder.inverse_transform([label_enc])[0])

    x_pred = float(art.reg_x.predict(X_proc)[0])
    y_pred = float(art.reg_y.predict(X_proc)[0])

    return dict(
        room_label  = label_enc,
        room_name   = room_name,
        x_pred      = round(x_pred, 3),
        y_pred      = round(y_pred, 3),
        confidence  = round(confidence, 4),
    )


# ── Batch prediction from a raw CSV ──────────────────────────────────────────
def predict_from_file(csv_path: Path, art: Artefacts = None) -> pd.DataFrame:
    """
    Predict on a raw CSI CSV (same format as captured by csi_capture.py).

    Parameters
    ----------
    csv_path : path to raw CSV
    art      : pre-loaded Artefacts (loaded fresh if None)

    Returns
    -------
    DataFrame with columns: room_label, room_name, x_pred, y_pred, confidence
    """
    if art is None:
        art = Artefacts().load_all()

    from src.data_collection.parser import parse_file
    from src.preprocessing.clean_data import clean_csi
    from src.preprocessing.phase_calibration import calibrate_phase
    from src.feature_engineering.feature_extraction import extract_features

    parsed = parse_file(csv_path)
    if parsed is None:
        raise ValueError(f"Failed to parse {csv_path}")

    amp_c, ph_c = clean_csi(parsed["amplitude_db"], parsed["phase"])
    ph_cal      = calibrate_phase(ph_c)

    dummy = np.zeros(len(amp_c))
    feat  = extract_features(amp_c, ph_cal, dummy, dummy, dummy)
    X_raw = feat["X"]

    X_proc = _preprocess_features(X_raw, art)

    labels     = art.classifier.predict(X_proc)
    probas     = art.classifier.predict_proba(X_proc).max(axis=1)
    room_names = art.encoder.inverse_transform(labels)
    x_preds    = art.reg_x.predict(X_proc)
    y_preds    = art.reg_y.predict(X_proc)

    return pd.DataFrame({
        "room_label":  labels,
        "room_name":   room_names,
        "x_pred":      np.round(x_preds, 3),
        "y_pred":      np.round(y_preds, 3),
        "confidence":  np.round(probas, 4),
    })


# ── Real-time live prediction from ESP32 ─────────────────────────────────────
def predict_live(
    port: str = None,
    baud: int = None,
    art: Artefacts = None,
    on_prediction=None,
) -> None:
    """
    Stream CSI packets from ESP32 serial, predict in real-time.

    Parameters
    ----------
    port          : serial port (default: config.SERIAL_PORT)
    baud          : baud rate (default: config.BAUD_RATE)
    art           : pre-loaded Artefacts
    on_prediction : optional callback(dict) called after each prediction
                    (default: prints to stdout)
    """
    import time
    import serial
    from collections import deque

    from src.data_collection.parser import parse_raw_tokens
    from src.preprocessing.clean_data import clean_csi
    from src.preprocessing.phase_calibration import calibrate_phase
    from src.feature_engineering.feature_extraction import extract_window_features
    from src.utils.config import FEATURE_WINDOW_SIZE
    from src.utils.helper import amplitude_from_complex, phase_from_complex, to_db

    if art is None:
        art = Artefacts().load_all()

    port = port or SERIAL_PORT
    baud = baud or BAUD_RATE

    buffer: deque = deque(maxlen=FEATURE_WINDOW_SIZE)
    packet_count = 0
    valid_count = 0

    def _default_callback(pred: dict):
        print(
            f"[LIVE] Room: {pred['room_name']:15s} | "
            f"({pred['x_pred']:.2f} m, {pred['y_pred']:.2f} m) | "
            f"conf: {pred['confidence']:.2%}"
        )

    callback = on_prediction or _default_callback

    logger.info(f"Opening serial {port} @ {baud}. Press Ctrl-C to stop.")
    print(f"DEBUG: Starting live prediction, buffering {FEATURE_WINDOW_SIZE} packets...")
    try:
        ser = serial.Serial(port, baud, timeout=2)
        time.sleep(0.5)
        ser.reset_input_buffer()

        while True:
            raw = ser.readline().decode("utf-8", errors="ignore").strip()
            if not raw.startswith("CSI_DATA"):
                continue

            packet_count += 1
            
            if packet_count == 1 or packet_count % 10 == 0:
                print(f"DEBUG: Packet {packet_count} received")
            tokens = raw.split(",")
            if len(tokens) < 4:
                if packet_count % 50 == 0:
                    logger.debug(f"Packet {packet_count}: Invalid token count")
                continue

            # Extract CSI data from bracketed format: [...lots of values...]
            # Last token should contain the bracketed CSI values
            last_token = tokens[-1] if tokens else ""
            if "[" not in last_token or "]" not in last_token:
                if packet_count % 50 == 0:
                    logger.debug(f"Packet {packet_count}: No brackets")
                continue
            
            # Extract the values between brackets
            start_idx = last_token.find("[")
            end_idx = last_token.find("]")
            if start_idx == -1 or end_idx == -1 or start_idx >= end_idx:
                if packet_count % 50 == 0:
                    logger.debug(f"Packet {packet_count}: Bracket parse failed")
                continue
            
            # Remove brackets and parse space-separated values
            csi_str = last_token[start_idx+1:end_idx].strip()
            try:
                values = list(map(float, csi_str.split()))
            except ValueError:
                if packet_count % 50 == 0:
                    logger.debug(f"Packet {packet_count}: Float parse error")
                continue
            
            # Validate we have correct number of I/Q pairs (128 values = 64 subcarriers * 2)
            if len(values) not in [104, 128]:  # Allow both 52 and 64 subcarriers
                if packet_count % 50 == 0:
                    logger.debug(f"Packet {packet_count}: Wrong IQ count: {len(values)}")
                continue
            
            # Convert to complex array, taking only first 52 subcarriers if we have 64
            num_subcarriers = len(values) // 2
            csi_full = np.array([values[i] + 1j * values[i+1] for i in range(0, len(values), 2)])
            
            # Slice to 52 subcarriers if we have more (trained models expect 52)
            if num_subcarriers > 52:
                csi = csi_full[:52]
            else:
                csi = csi_full
            if csi is None or len(csi) == 0:
                continue

            valid_count += 1
            if valid_count % 5 == 0:
                print(f"DEBUG: [{valid_count}/20] CSI packets buffered")
            
            amp = to_db(amplitude_from_complex(csi.reshape(1, -1)))[0]
            ph  = phase_from_complex(csi.reshape(1, -1))[0]
            buffer.append((amp, ph))
            
            if valid_count % 5 == 0:
                logger.info(f"[{valid_count}/20] CSI packets buffered")

            if len(buffer) == FEATURE_WINDOW_SIZE:
                amp_win = np.array([row[0] for row in buffer])   # (W, N_sub)
                ph_win  = np.array([row[1] for row in buffer])

                fv     = extract_window_features(amp_win, ph_win).reshape(1, -1)
                X_proc = _preprocess_features(fv, art)
                pred   = predict_single(fv, art)
                callback(pred)

    except KeyboardInterrupt:
        logger.info("Live prediction stopped.")
    finally:
        if "ser" in dir() and ser.is_open:
            ser.close()


# ── CLI ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser(description="CSI localization inference")
    sub = p.add_subparsers(dest="mode")

    f_cmd = sub.add_parser("file",  help="Predict from CSV file")
    f_cmd.add_argument("csv_path")

    _     = sub.add_parser("live",  help="Real-time from ESP32 serial")

    args = p.parse_args()
    art  = Artefacts().load_all()

    if args.mode == "file":
        df = predict_from_file(args.csv_path, art)
        print(df.to_string(index=False))
    elif args.mode == "live":
        predict_live(art=art)
    else:
        p.print_help()
