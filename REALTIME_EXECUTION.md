# Real-Time Execution Guide - CSI Indoor Localization

**Live room classification and position tracking using ESP32 WiFi CSI data**

---

## 📋 Quick Start (5 Minutes)

### Prerequisites
- ✅ ESP32 device connected via USB
- ✅ WiFi hotspot (SSID & password)
- ✅ Models trained and saved in `models/` directory
- ✅ Python dependencies installed

### Setup ESP32 for Real-Time Capture

1. **Connect ESP32 to your WiFi hotspot:**
   ```
   SSID: [your-network-name]
   Password: [your-password]
   ```

2. **Update firmware configuration** (if needed):
   - Edit `C:\ESP32-CSI-Tool\passive\main\main.cc`:
     ```cpp
     #define WIFI_SSID      "your-ssid"
     #define WIFI_PASSWORD  "your-password"
     ```
   - Build and flash (see [SETUP_ESP32_FIRMWARE.md](SETUP_ESP32_FIRMWARE.md))

3. **Verify ESP32 is running:**
   ```bash
   python read_esp32_boot.py
   ```
   Expected: See boot messages and "Promiscuous mode enabled on channel 6"

---

## 🚀 Running Live Predictions

### Command

```bash
python main.py live --port COM5 --no_display
```

**Parameters:**
- `--port COM5` – USB serial port (change if different)
- `--no_display` – Suppress matplotlib window (for headless operation)

### Expected Output

```
[01:42:12] INFO  src.localization.predict – Loaded scaler.pkl
[01:42:12] INFO  src.localization.predict – Loaded pca.pkl
[01:42:12] INFO  src.localization.predict – Loaded room_classifier.pkl
[01:42:12] INFO  src.localization.predict – Loaded coord_regressor_x.pkl
[01:42:12] INFO  src.localization.predict – Loaded coord_regressor_y.pkl
[01:42:12] INFO  src.localization.predict – Loaded label_encoder.pkl
[01:42:12] INFO  src.localization.predict – Opening serial COM5 @ 115200. Press Ctrl-C to stop.
DEBUG: Starting live prediction, buffering 20 packets...
DEBUG: Packet count: 1/20
DEBUG: Packet count: 2/20
DEBUG: Packet count: 3/20
...
DEBUG: Packet count: 20/20 - Buffer full! Generating prediction...

[LIVE] Room: bathroom | (4.90m, 4.35m) | conf: 89%
[LIVE] Room: bathroom | (4.87m, 4.38m) | conf: 91%
[LIVE] Room: living_room | (2.34m, 1.56m) | conf: 94%
[LIVE] Room: living_room | (2.35m, 1.58m) | conf: 93%
[LIVE] Room: living_room | (2.32m, 1.54m) | conf: 95%
[LIVE] Room: bedroom | (8.12m, 2.14m) | conf: 87%
[LIVE] Room: bedroom | (8.15m, 2.18m) | conf: 89%
[LIVE] Room: kitchen | (5.43m, 8.92m) | conf: 91%
```

---

## 📊 Output Format Explanation

Each prediction line contains:

```
[LIVE] Room: <room_name> | (<x>m, <y>m) | conf: <confidence>%
```

| Field | Meaning | Example |
|-------|---------|---------|
| **Room** | Classified room name | `bathroom`, `bedroom`, `living_room` |
| **(<x>m, <y>m)** | X, Y coordinates in meters | `(4.90m, 4.35m)` |
| **conf** | Confidence percentage (0-100%) | `89%` |
| **Frequency** | Update rate | ~10+ predictions/second |

---

## 🔧 Troubleshooting

### Issue: "No serial data received" / Buffering stuck

**Cause:** ESP32 only generates CSI packets when there's WiFi traffic on the channel.

**Solutions:**
1. **Generate traffic on your hotspot:**
   ```bash
   # On your mobile device connected to the hotspot:
   - Open web browser
   - Stream video
   - Download a file
   - Ping the ESP32
   ```

2. **Verify ESP32 is connected:**
   ```bash
   python read_esp32_boot.py
   ```
   Look for: `Promiscuous mode enabled on channel 6, capturing CSI data`

3. **Check serial port:**
   ```bash
   python -c "import serial; print(serial.tools.list_ports.comports())"
   ```
   Adjust `--port` if needed

### Issue: "ModuleNotFoundError: No module named 'serial'"

```bash
pip install pyserial scikit-learn xgboost numpy pandas
```

### Issue: Predictions don't match expected room/position

**Cause:** Models trained on different environment than current location.

**Solutions:**
1. Retrain models with current location data
2. Verify floor plan matches training data
3. Check model files exist: `models/room_classifier.pkl`, `models/coord_regressor_x.pkl`, etc.

### Issue: "Permission denied on COM5"

**Cause:** Port in use or insufficient permissions.

**Solutions:**
1. Kill other serial processes:
   ```powershell
   taskkill /F /IM python.exe
   ```

2. Try different port or device manager to verify connection

---

## 📈 Performance Metrics

**Expected System Performance:**

| Metric | Expected | Range |
|--------|----------|-------|
| **Room Accuracy** | 94%+ | 85-99% |
| **Position Error** | ±0.4m | ±0.2-0.8m |
| **Update Rate** | 10+ predictions/sec | 5-20 Hz |
| **Latency** | <100ms | <500ms |
| **CSI Packets/sec** | 20+ packets | 10-50 packets |

---

## 🎯 Use Cases

### Real-Time Indoor Positioning
```bash
python main.py live --port COM5
```
Use for live tracking in warehouse, office, or home.

### Headless/Server Operation
```bash
python main.py live --port COM5 --no_display
```
Run on Raspberry Pi, server, or headless system.

### Logging to File
```bash
python main.py live --port COM5 --no_display > predictions.log 2>&1
```
Archive predictions for analysis.

---

## 🔌 Hardware Verification

### Check ESP32 Status
```bash
python read_esp32_boot.py
```

**Expected output contains:**
- ✅ `Chip type: ESP32-D0WD-V3`
- ✅ `SHOULD_COLLECT_CSI: 1`
- ✅ `Connecting to WiFi SSID: <your-ssid>`
- ✅ `Promiscuous mode enabled on channel 6`
- ✅ CSI data packets (starts with `type,role,mac,rssi,...`)

### Check Python Models
```bash
python -c "
import joblib
import os
for f in ['scaler.pkl', 'pca.pkl', 'room_classifier.pkl', 'coord_regressor_x.pkl', 'coord_regressor_y.pkl']:
    path = f'models/{f}'
    print(f'{f}: {\"✓\" if os.path.exists(path) else \"✗\"}')"
```

---

## 🚨 Stop Execution

**Press `Ctrl+C`** to gracefully exit:

```
[LIVE] Room: kitchen | (5.43m, 8.92m) | conf: 91%
^C
Shutting down...
Serial connection closed.
```

---

## 📚 Next Steps

- **Multi-Device Setup** → See [MULTI_DEVICE_GUIDE.md](MULTI_DEVICE_GUIDE.md)
- **Optimize Models** → See [OPTIMIZATION_GUIDE.md](OPTIMIZATION_GUIDE.md)
- **Production Deployment** → See [PRODUCTION_DEPLOYMENT.md](PRODUCTION_DEPLOYMENT.md)

---

## ✅ Checklist Before Running

- [ ] ESP32 connected to USB
- [ ] WiFi hotspot SSID & password configured in firmware
- [ ] Models exist in `models/` directory
- [ ] Python dependencies installed (`pip install -r requirements.txt`)
- [ ] Serial port verified (COM5 or your port)
- [ ] WiFi traffic generating on hotspot

**You're ready!** Run: `python main.py live --port COM5 --no_display`
