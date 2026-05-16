#!/usr/bin/env python3
"""
Erase ESP32 flash and reflash CSI firmware
"""
import subprocess
import sys
import os
import time

print("=" * 70)
print("ESP32 ERASE AND REFLASH")
print("=" * 70)

idf_python = r"C:\Users\kowne\.espressif\python_env\idf6.1_py3.14_env\Scripts\python.exe"
build_dir = r"C:\ESP32-CSI-Tool\passive\build"
port = "COM5"

# Step 1: Erase flash
print("\n[1/3] Erasing ESP32 flash...")
erase_cmd = [
    idf_python, "-m", "esptool",
    "--chip", "auto",
    "-p", port,
    "-b", "460800",
    "erase_flash"
]

result = subprocess.run(erase_cmd, timeout=60)
if result.returncode != 0:
    print("✗ Erase failed!")
    sys.exit(1)

print("✓ Flash erased")

# Step 2: Wait
time.sleep(2)

# Step 3: Flash firmware
print("\n[2/3] Flashing clean firmware...")
flash_cmd = [
    idf_python, "-m", "esptool",
    "--chip", "auto",
    "-p", port,
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

result = subprocess.run(flash_cmd, cwd=build_dir, timeout=120)
if result.returncode != 0:
    print("✗ Flash failed!")
    sys.exit(1)

print("✓ Firmware flashed")

# Step 4: Wait for boot
print("\n[3/3] Waiting for ESP32 to boot (5 seconds)...")
time.sleep(5)

print("\n" + "=" * 70)
print("✓ SUCCESS! ESP32 is ready")
print("=" * 70)
print("\nNext: Run 'python main.py live --port COM5 --no_display'")
