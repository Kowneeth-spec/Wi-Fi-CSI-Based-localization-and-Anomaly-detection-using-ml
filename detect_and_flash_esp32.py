#!/usr/bin/env python3
"""
Detect ESP32 on any COM port and flash CSI firmware
"""
import serial
import subprocess
import sys
import os
import time

print("=" * 70)
print("DETECT ESP32 AND FLASH CSI FIRMWARE")
print("=" * 70)

# Step 1: Detect ESP32 on available COM ports
print("\n[1/4] Scanning for ESP32 devices...")

available_ports = []
for i in range(1, 20):
    port_name = f"COM{i}"
    try:
        ser = serial.Serial(port_name, 115200, timeout=0.5)
        ser.close()
        available_ports.append(port_name)
    except:
        pass

if not available_ports:
    print("  ✗ No COM ports found!")
    sys.exit(1)

print(f"  ✓ Found {len(available_ports)} COM port(s): {', '.join(available_ports)}")

# Step 2: Try to identify ESP32 specifically
esp32_port = None
print("\n[2/4] Identifying ESP32 (not ESP8266)...")

idf_python = r"C:\Users\kowne\.espressif\python_env\idf6.1_py3.14_env\Scripts\python.exe"

for port in available_ports:
    result = subprocess.run(
        [idf_python, "-m", "esptool", "--chip", "auto", "-p", port, "chip_id"],
        capture_output=True,
        text=True,
        timeout=5
    )
    
    if "ESP32" in result.stdout and "ESP8266" not in result.stdout:
        print(f"  ✓ Found ESP32 on {port}")
        esp32_port = port
        break
    elif "ESP8266" in result.stdout:
        print(f"  • {port}: ESP8266 (skipping)")

if not esp32_port:
    print("  ✗ No ESP32 found! Please check USB connection.")
    sys.exit(1)

# Step 3: Reset ESP32
print(f"\n[3/4] Resetting ESP32 on {esp32_port}...")
try:
    ser = serial.Serial(esp32_port, 115200, timeout=1)
    ser.dtr = False
    time.sleep(0.5)
    ser.dtr = True
    time.sleep(1)
    ser.close()
    print("  ✓ Reset complete")
except Exception as e:
    print(f"  ⚠ Reset warning: {e}")

time.sleep(1)

# Step 4: Flash firmware
print(f"\n[4/4] Flashing CSI firmware to {esp32_port}...")

build_dir = r"C:\ESP32-CSI-Tool\passive\build"

flash_cmd = [
    idf_python, "-m", "esptool",
    "--chip", "auto",
    "-p", esp32_port,
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

result = subprocess.run(flash_cmd, cwd=build_dir)

if result.returncode == 0:
    print("\n" + "=" * 70)
    print(f"✓ SUCCESS! ESP32 CSI firmware flashed to {esp32_port}")
    print("=" * 70)
    print("\nNext: Run 'python diagnose_esp32.py' to verify CSI packets")
    sys.exit(0)
else:
    print(f"\n✗ Flash failed with return code {result.returncode}")
    sys.exit(1)
