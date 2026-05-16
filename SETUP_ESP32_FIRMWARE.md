# ESP32 CSI Firmware Setup Guide

Your ESP32 needs to be flashed with special CSI firmware to send wireless signal data.

## Quick Diagnosis
✅ Your ESP32 is detected on **COM7**  
❌ It needs **CSI firmware** (currently has generic firmware)

## Two Options to Flash

### **Option 1: Use Pre-built Binary (EASIEST)**
**Coming soon** - Check GitHub releases for pre-built firmware:
https://github.com/StevenMHernandez/ESP32-CSI-Tool/releases

Once you download `passive.bin` or `active_sta.bin`:
```bash
python -m esptool --port COM7 write_flash 0x0 /path/to/firmware.bin
```

### **Option 2: Build Firmware from Source (RECOMMENDED)**

**Step 1: Ensure ESP-IDF v4.3 is set up**
```bash
cd C:\esp-idf
. .\export.ps1  # Activate ESP-IDF environment
cd C:\ESP32-CSI-Tool\passive  # Choose receiver mode
```

**Step 2: Configure the firmware**
```bash
idf.py menuconfig
```
Set these options:
- Serial → Baud: 921600 (or 115200)
- WiFi → Enable CSI
- Other options as needed

**Step 3: Build**
```bash
idf.py build
```

**Step 4: Flash to ESP32**
```bash
idf.py flash monitor
```
This will:
- Flash the firmware
- Start monitoring output
- You should see `CSI_DATA,1,−30,5,3,...` packets

**Step 5: Return to your project**
Once flashing is done, test with:
```bash
cd "C:\Users\kowne\Downloads\Drive\Minor project\csi-indoor-localization"
python main.py live --port COM7 --no_display
```

## Still Having Issues?

If flashing fails, try:
1. Unplug ESP32 USB → wait 3 sec → replug
2. Run: `python -m esptool --port COM7 chip_id` (should show your chip ID)
3. Check Device Manager for driver issues
4. Download latest drivers for "Silicon Labs CP210x"

## Alternative: For Now

Run in **demo mode** while you set up firmware:
```bash
python quick_start.py demo
```

This shows predictions with synthetic data - proves everything works!
