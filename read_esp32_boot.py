#!/usr/bin/env python3
"""
Check what's coming from COM5
"""
import serial
import time

print("Reading ESP32 boot output from COM5...\n")

try:
    ser = serial.Serial("COM5", 115200, timeout=1)
    
    # Reset
    ser.dtr = False
    time.sleep(0.5)
    ser.dtr = True
    time.sleep(2)
    
    # Read 10 seconds
    start = time.time()
    while time.time() - start < 10:
        if ser.in_waiting:
            data = ser.read(ser.in_waiting)
            print(data.decode('utf-8', errors='replace'), end='', flush=True)
    
    ser.close()
    print("\n\nDone.")
    
except Exception as e:
    print(f"Error: {e}")
