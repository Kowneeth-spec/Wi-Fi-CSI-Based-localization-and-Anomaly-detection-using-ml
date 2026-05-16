#!/usr/bin/env python3
"""
Simplest possible serial reader - just print raw lines
"""
import serial
import time

ser = serial.Serial("COM5", 115200, timeout=1)
time.sleep(1)
ser.reset_input_buffer()

print("Reading from COM5...")
for i in range(30):
    line = ser.readline().decode("utf-8", errors="ignore")
    if line:
        print(f"Line {i}: {line[:100]}")

ser.close()
