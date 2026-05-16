#!/usr/bin/env python3
"""
Flash ESP32 CSI firmware - simple version
"""
import subprocess
import sys
import os
import time

print("=" * 70)
print("FLASH ESP32 CSI FIRMWARE")
print("=" * 70)

# Check which ports are available
ports_to_try = ["COM4", "COM5", "COM6", "COM3"]

idf_python = r"C:\Users\kowne\.espressif\python_env\idf6.1_py3.14_env\Scripts\python.exe"
build_dir = r"C:\ESP32-CSI-Tool\passive\build"

for port in ports_to_try:
    print(f"\n[*] Attempting to flash {port}...")
    
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
    
    if result.returncode == 0:
        print("\n" + "=" * 70)
        print(f"✓ SUCCESS! Firmware flashed to {port}")
        print("=" * 70)
        print(f"\nNow running: python main.py live --port {port} --no_display")
        
        # Test the live predictions
        time.sleep(2)
        os.system(f"python main.py live --port {port} --no_display")
        sys.exit(0)

print("\n✗ Failed to flash any port")
sys.exit(1)
