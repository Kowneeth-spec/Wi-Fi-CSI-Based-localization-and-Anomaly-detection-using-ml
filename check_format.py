#!/usr/bin/env python3
"""
Quick check of CSI packet format from ESP32
"""
import serial
import time

ser = serial.Serial("COM5", 115200, timeout=2)
time.sleep(0.5)
ser.reset_input_buffer()

for i in range(5):
    raw = ser.readline().decode("utf-8", errors="ignore").strip()
    if raw.startswith("CSI_DATA"):
        tokens = raw.split(",")
        last_token = tokens[-1] if tokens else ""
        
        if "[" in last_token and "]" in last_token:
            start = last_token.find("[") + 1
            end = last_token.find("]")
            csi_str = last_token[start:end].strip()
            values = csi_str.split()
            print(f"Packet {i+1}: {len(values)} values")
            print(f"  First 10: {values[:10]}")
            print(f"  Last 10: {values[-10:]}")

ser.close()
