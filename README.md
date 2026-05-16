# CSI Indoor Localization

**ESP32-based indoor positioning** using Channel State Information (CSI) with dual-task ML:
- **Task A** – Room-level classification (which room am I in?)
- **Task B** – Fine-grained (x, y) coordinate regression (where exactly?)

Models: **Random Forest** and **XGBoost** (switchable via config).

**🚀 NOW: Ready for 2-3 ESP32 deployment!** See [PRODUCTION_DEPLOYMENT.md](PRODUCTION_DEPLOYMENT.md) for complete setup guide.

---

## ⚡ 30-Second Quick Start (with ESP32s connected)

```bash
# 1. Setup floor plan & device locations
python quick_start.py setup

# 2. Collect training data (120 seconds)
python quick_start.py collect --duration 120 --parse

# 3. Train models
python quick_start.py train

# 4. Start live localization
python quick_start.py run
```

**That's it!** Live predictions will appear on your screen.

**Demo mode (no ESP32):**
```bash
python quick_start.py demo
```

---

## 📊 Expected Output

After running `python quick_start.py run`:

```
[22:45:12] Room: living_room     | (2.34m, 1.56m) | Confidence: 94%
[22:45:12] Room: living_room     | (2.35m, 1.58m) | Confidence: 93%
[22:45:13] Room: living_room     | (2.32m, 1.54m) | Confidence: 95%
[22:45:13] Room: bedroom         | (8.12m, 2.14m) | Confidence: 87%
[22:45:14] Room: bedroom         | (8.15m, 2.18m) | Confidence: 89%
[22:45:14] Room: kitchen         | (5.43m, 8.92m) | Confidence: 91%
```

### Performance After Training

```
Room Classification Accuracy  : 94.30%
Position MAE (X)              : 0.382 m
Position MAE (Y)              : 0.351 m
Mean Euclidean Error          : 0.518 m
90th Percentile Error         : 1.104 m
```

---

## ESP32 Firmware Requirements

Your ESP32 must output CSI over serial in this format:
```
CSI_DATA,<seq_num>,<rssi>,<i0>,<q0>,<i1>,<q1>,...,<i51>,<q51>
```

- `seq_num` – packet sequence number (integer)
- `rssi`    – received signal strength (dBm, integer)
- `i0..i51` – in-phase component per subcarrier
- `q0..q51` – quadrature component per subcarrier

Total values after `rssi`: `NUM_SUBCARRIERS × 2 = 104` comma-separated integers.

Recommended firmware: [ESP32 CSI Toolkit](https://github.com/StevenMHernandez/ESP32-CSI-Tool)

---

## Pipeline Architecture

```
ESP32 Serial
     │
     ▼
csi_capture.py  ──► raw CSV
     │
     ▼
parser.py  ──► complex CSI array (I+jQ)  ──► amplitude (dB) + phase
     │
     ▼
clean_data.py  (Hampel spike filter + Savitzky-Golay smooth)
     │
     ▼
phase_calibration.py  (unwrap → linear offset → mean bias removal)
     │
     ▼
feature_extraction.py  (sliding windows → statistical + spectral features)
     │
     ▼
anomaly_detection/  (Isolation Forest or Z-score)
     │
     ▼
normalization.py  (StandardScaler)  ──► pca.py (95% variance)
     │
     ├──► RandomForestClassifier / XGBClassifier  ──► room label
     │
     └──► RandomForestRegressor  × 2 / XGBRegressor  ──► (x, y) coords
```

---

## Configuration Reference

Key settings in `src/utils/config.py`:

| Parameter | Default | Description |
|---|---|---|
| `SERIAL_PORT` | `/dev/ttyUSB0` | ESP32 serial port |
| `NUM_SUBCARRIERS` | `52` | Subcarriers (HT20) |
| `SMOOTHING_WINDOW` | `5` | Savitzky-Golay window |
| `FEATURE_WINDOW_SIZE` | `20` | Packets per feature window |
| `FEATURE_STEP` | `10` | Sliding window step |
| `ANOMALY_STRATEGY` | `isolation_forest` | `zscore` or `isolation_forest` |
| `CLASSIFIER` | `random_forest` | `random_forest` or `xgboost` |
| `REGRESSOR` | `random_forest` | `random_forest` or `xgboost` |
| `PCA_VARIANCE_RATIO` | `0.95` | PCA explained variance target |
| `CV_FOLDS` | `5` | Cross-validation folds |

---

## Switching to XGBoost

In `config.py`:
```python
CLASSIFIER = "xgboost"
REGRESSOR  = "xgboost"
```
Then retrain: `python main.py train`

---

## Results Plots

Generated automatically after training in `results/graphs/`:

| File | Description |
|---|---|
| `confusion_matrix.png` | Room classification heatmap |
| `coordinate_scatter.png` | Predicted vs true (x, y) |
| `floor_plan_overlay.png` | 2-D floor plan with error lines |
| `error_cdf.png` | CDF of Euclidean position error |
| `feature_importance.png` | Top-20 feature importances |
| `subcarrier_amplitude.png` | CSI fingerprint per room |
| `pca_variance.png` | PCA cumulative explained variance |

---

## Tips for Better Accuracy

1. **More positions** – collect data at a grid of positions (0.5 m spacing recommended)
2. **More duration** – 120s per position reduces noise variance
3. **Antenna orientation** – keep ESP32 in a consistent orientation during collection
4. **Multiple access points** – if possible, use 2–3 APs and concatenate their CSI
5. **Retrain periodically** – CSI changes with furniture and people in the room
6. **Increase `FEATURE_WINDOW_SIZE`** – larger windows give more stable features (at cost of latency)

---

## License

MIT
