#!/usr/bin/env python3
# main.py
"""
CSI Indoor Localization – Entry Point

Commands
--------
  collect   – capture CSI data from ESP32 over serial
  parse     – convert raw CSVs to processed numpy arrays
  train     – run full training pipeline
  predict   – batch prediction from a CSV file
  live      – real-time prediction from ESP32 serial stream
  plot      – regenerate all result plots from saved models
"""

import argparse
import sys
from pathlib import Path


# ─────────────────────────────────────────────────────────────────────────────
def cmd_collect(args):
    from src.data_collection.csi_capture import capture
    capture(
        port     = args.port,
        baud     = args.baud,
        duration = args.duration,
        label    = args.label,
        x        = args.x,
        y        = args.y,
        out_path = Path(args.out),
    )


def cmd_collect_multi(args):
    """Collect from multiple ESP32s in parallel."""
    from src.data_collection.multi_device import collect_multi
    
    # Parse locations from "x1,y1 x2,y2" format
    locations = []
    for loc_str in args.locations:
        x, y = map(float, loc_str.split(','))
        locations.append((x, y))
    
    results = collect_multi(
        ports=args.ports,
        labels=args.labels,
        locations=locations,
        duration=args.duration,
        baud=args.baud,
        parse=args.parse,
    )
    
    print(f"\n{'='*60}")
    print(f"Multi-Device Collection Complete")
    print(f"{'='*60}")
    print(f"Collected from: {len(results['files'])} devices")
    print(f"Total samples: {results['combined_samples']}")
    if results['merged_file']:
        print(f"Merged file: {results['merged_file']}")
    if results['numpy_data']:
        print(f"Numpy arrays: {results['numpy_data']['output_dir']}")
    print(f"{'='*60}\n")


def cmd_parse(args):
    from src.data_collection.parser import parse_directory
    parse_directory(
        raw_dir = Path(args.raw_dir) if args.raw_dir else None,
        out_dir = Path(args.out_dir) if args.out_dir else None,
    )


def cmd_train(args):
    from src.localization.train import train_pipeline
    results = train_pipeline(use_pca=not args.no_pca)

    if not args.no_plots:
        from src.visualization.plot_results import generate_all_plots
        generate_all_plots(results)
        print("\nPlots saved to results/graphs/")

    print(f"\n{'='*55}")
    print(f"  Room classification accuracy : {results['accuracy']*100:.2f}%")
    print(f"  Mean Euclidean error          : {results['mean_euclidean_error']:.3f} m")
    print(f"  90th-percentile error         : {results['p90_error']:.3f} m")
    print(f"  MAE x                         : {results['mae_x']:.3f} m")
    print(f"  MAE y                         : {results['mae_y']:.3f} m")
    print(f"{'='*55}\n")


def cmd_predict(args):
    from src.localization.predict import Artefacts, predict_from_file
    art = Artefacts().load_all()
    df  = predict_from_file(Path(args.csv), art)
    print(df.to_string(index=False))
    if args.out:
        df.to_csv(args.out, index=False)
        print(f"\nSaved predictions → {args.out}")


def cmd_live(args):
    from src.localization.predict import Artefacts, predict_live
    from src.utils.config import SERIAL_PORT, BAUD_RATE

    art = Artefacts().load_all()

    display = None
    if not args.no_display:
        try:
            from src.visualization.realtime_display import RealtimeDisplay
            from src.utils.config import ROOM_LABELS
            display = RealtimeDisplay(room_labels=ROOM_LABELS)
            display.start()
        except Exception as e:
            print(f"[WARN] Could not start GUI display: {e}. Running headless.")

    def on_pred(pred: dict):
        print(
            f"[LIVE] Room: {pred['room_name']:15s} | "
            f"({pred['x_pred']:.2f} m, {pred['y_pred']:.2f} m) | "
            f"conf: {pred['confidence']:.2%}"
        )
        if display:
            display.update(
                x         = pred["x_pred"],
                y         = pred["y_pred"],
                room_name = pred["room_name"],
            )

    try:
        predict_live(port=args.port or SERIAL_PORT, art=art, on_prediction=on_pred)
    finally:
        if display:
            display.stop()


def cmd_plot(args):
    """Reload saved results and regenerate plots (requires saved models)."""
    import numpy as np
    from src.utils.config import PROC_DIR
    from src.localization.predict import Artefacts

    art = Artefacts().load_all()
    print("Loading processed data for subcarrier plot …")
    try:
        amplitude = np.load(PROC_DIR / "amplitude_db.npy")
        import pandas as pd
        meta   = pd.read_csv(PROC_DIR / "metadata.csv")
        labels = meta["label"].to_numpy()
    except FileNotFoundError:
        amplitude = labels = None
        print("[WARN] Processed data not found – skipping subcarrier plot.")

    # We need results dict — re-run a quick test pass
    print("Re-running test predictions …")
    from src.localization.train import (
        load_processed_data, run_preprocessing,
        run_feature_extraction, run_anomaly_detection,
    )
    import joblib, numpy as np
    from sklearn.model_selection import train_test_split
    from src.utils.config import TEST_SPLIT, RANDOM_STATE, ENCODER_FILE, SCALER_FILE, PCA_FILE
    from src.preprocessing.normalization import transform
    from src.feature_engineering.pca import apply_pca
    from src.visualization.plot_results import generate_all_plots
    from src.localization.model import LocalizationModel

    data  = run_preprocessing(load_processed_data())
    feat  = run_feature_extraction(data)
    le    = joblib.load(ENCODER_FILE)
    feat["y_label"] = le.transform(feat["y_label"])
    feat  = run_anomaly_detection(feat)
    idx   = np.arange(len(feat["X"]))
    tr, te = train_test_split(idx, test_size=TEST_SPLIT,
                               stratify=feat["y_label"], random_state=RANDOM_STATE)
    X_te  = apply_pca(transform(feat["X"][te]))
    preds_label = art.classifier.predict(X_te)
    preds_x     = art.reg_x.predict(X_te)
    preds_y     = art.reg_y.predict(X_te)

    # Minimal results dict
    class _M:
        feature_importances = lambda self: {}
    results = dict(
        model            = _M(),
        accuracy         = 0,
        mae_x=0, mae_y=0,
        mean_euclidean_error=0, p90_error=0,
        classification_report="",
        predictions      = dict(room_label=preds_label, x_pred=preds_x,
                                y_pred=preds_y,
                                xy_pred=np.stack([preds_x, preds_y], axis=1)),
        y_label_test     = feat["y_label"][te],
        y_x_test         = feat["y_x"][te],
        y_y_test         = feat["y_y"][te],
    )
    generate_all_plots(results, amplitude=amplitude, labels=labels)
    print(f"Plots saved to results/graphs/")


# ─────────────────────────────────────────────────────────────────────────────
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="csi-loc",
        description="CSI Indoor Localization – ESP32 + Random Forest / XGBoost",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # collect
    p_col = sub.add_parser("collect", help="Capture CSI from ESP32 serial")
    p_col.add_argument("--port",     default=None)
    p_col.add_argument("--baud",     default=115200, type=int)
    p_col.add_argument("--duration", default=60,     type=float)
    p_col.add_argument("--label",    default=0,      type=int)
    p_col.add_argument("--x",        default=0.0,    type=float)
    p_col.add_argument("--y",        default=0.0,    type=float)
    p_col.add_argument("--out",      required=True,  help="Output CSV path")

    # collect-multi (new)
    p_col_multi = sub.add_parser("collect-multi", help="Parallel collection from 2+ ESP32s")
    p_col_multi.add_argument("--ports",     nargs='+', required=True, 
                            help="Serial ports (e.g., /dev/ttyUSB0 /dev/ttyUSB1)")
    p_col_multi.add_argument("--labels",    nargs='+', type=int, required=True,
                            help="Room labels (e.g., 0 0)")
    p_col_multi.add_argument("--locations", nargs='+', required=True,
                            help="Coordinates (e.g., 0,0 10,0)")
    p_col_multi.add_argument("--duration",  default=60, type=float, help="Seconds per device")
    p_col_multi.add_argument("--baud",      default=115200, type=int)
    p_col_multi.add_argument("--parse",     action='store_true', help="Parse to numpy arrays")

    # parse
    p_par = sub.add_parser("parse", help="Parse raw CSVs → processed arrays")
    p_par.add_argument("--raw_dir", default=None)
    p_par.add_argument("--out_dir", default=None)

    # train
    p_tr = sub.add_parser("train", help="Run full training pipeline")
    p_tr.add_argument("--no_pca",    action="store_true", help="Skip PCA step")
    p_tr.add_argument("--no_plots",  action="store_true", help="Skip plot generation")

    # predict
    p_pr = sub.add_parser("predict", help="Batch predict from CSV file")
    p_pr.add_argument("csv",        help="Path to raw CSI CSV")
    p_pr.add_argument("--out",      default=None, help="Save predictions to CSV")

    # live
    p_lv = sub.add_parser("live", help="Real-time prediction from ESP32")
    p_lv.add_argument("--port",       default=None)
    p_lv.add_argument("--no_display", action="store_true", help="Headless mode (no GUI)")

    # plot
    sub.add_parser("plot", help="Regenerate all result plots")

    return parser


if __name__ == "__main__":
    parser = build_parser()
    args   = parser.parse_args()

    dispatch = {
        "collect": cmd_collect,
        "collect-multi": cmd_collect_multi,
        "parse":   cmd_parse,
        "train":   cmd_train,
        "predict": cmd_predict,
        "live":    cmd_live,
        "plot":    cmd_plot,
    }
    dispatch[args.command](args)
