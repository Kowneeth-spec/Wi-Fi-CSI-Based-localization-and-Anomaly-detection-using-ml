#!/usr/bin/env python3
"""
Check what chip is actually on COM7 and attempt to detect it properly.
"""
import subprocess
import sys

print("=" * 70)
print("CHIP DETECTION ON COM7")
print("=" * 70)

# Try esptool chip detection
print("\n[*] Running esptool chip detection...")
result = subprocess.run(
    [sys.executable, "-m", "esptool", "--chip", "auto", "-p", "COM7", "chip_id"],
    capture_output=True,
    text=True
)

print("STDOUT:")
print(result.stdout)
print("\nSTDERR:")
print(result.stderr)
print(f"\nReturn code: {result.returncode}")

if "ESP32" in result.stdout:
    print("\n✓ Detected: ESP32")
elif "ESP8266" in result.stdout:
    print("\n✗ Detected: ESP8266 (WRONG DEVICE!)")
elif result.returncode != 0:
    print("\n⚠ Detection failed - device may need reset")
