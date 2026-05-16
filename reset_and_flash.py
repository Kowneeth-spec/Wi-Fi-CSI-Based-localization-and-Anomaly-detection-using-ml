#!/usr/bin/env python3
"""
Reset ESP32 and flash with explicit auto-detection
"""
import serial
import time
import subprocess
import sys
import os

print("=" * 70)
print("ESP32 RESET AND FLASH PROCEDURE")
print("=" * 70)

# Step 1: Reset the device
print("\n[1/3] Resetting ESP32 on COM7...")
try:
    ser = serial.Serial("COM7", 115200, timeout=1)
    
    # Pull DTR low to reset
    print("  • Pulling DTR low (reset)...")
    ser.dtr = False
    time.sleep(0.5)
    ser.dtr = True
    time.sleep(1)
    
    ser.close()
    print("  ✓ Reset complete")
except Exception as e:
    print(f"  ✗ Error during reset: {e}")

# Step 2: Wait and check if device responds
print("\n[2/3] Waiting for device to stabilize...")
time.sleep(2)

# Step 3: Flash with esptool using the built-in Python from ESP-IDF
print("\n[3/3] Flashing firmware via esptool...")

idf_python = r"C:\Users\kowne\.espressif\python_env\idf6.1_py3.14_env\Scripts\python.exe"
build_dir = r"C:\ESP32-CSI-Tool\passive\build"

if not os.path.exists(idf_python):
    print(f"  ✗ ESP-IDF Python not found: {idf_python}")
    sys.exit(1)

# Flash command
flash_cmd = [
    idf_python, "-m", "esptool",
    "--chip", "auto",  # Auto-detect chip
    "-p", "COM7",
    "-b", "460800",
    "--before", "default-reset",
    "--after", "hard-reset",
    "write-flash",
    "--flash-mode", "dio",
    "--flash-freq", "40m",
    "--flash-size", "2MB",
    "0x1000", os.path.join(build_dir, "bootloader", "bootloader.bin"),
    "0x8000", os.path.join(build_dir, "partition_table", "partition-table.bin"),
    "0x10000", os.path.join(build_dir, "passive.bin"),
]

print(f"\n  Command: {' '.join(flash_cmd)}\n")

result = subprocess.run(flash_cmd, cwd=build_dir)

if result.returncode == 0:
    print("\n✓ Flash successful!")
else:
    print(f"\n✗ Flash failed with return code {result.returncode}")
    
print("\n" + "=" * 70)
