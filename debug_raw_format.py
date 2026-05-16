#!/usr/bin/env python3
"""
Debug: Show actual packet format from ESP32
"""
import serial
import time

print("Capturing raw CSI packets from COM5...")
print("=" * 80)

try:
    ser = serial.Serial("COM5", 115200, timeout=2)
    time.sleep(0.5)
    ser.reset_input_buffer()
    
    for i in range(5):
        raw = ser.readline().decode("utf-8", errors="ignore").strip()
        if raw.startswith("CSI_DATA"):
            print(f"\nPacket {i+1}:")
            print(f"  Full line: {raw[:150]}...")
            print(f"  Length: {len(raw)}")
            
            # Split by comma
            tokens = raw.split(",")
            print(f"  Token count: {len(tokens)}")
            print(f"  Tokens[0:5]: {tokens[0:5]}")
            print(f"  Last token: {tokens[-1][:80] if len(tokens[-1]) > 80 else tokens[-1]}")
    
    ser.close()
    
except Exception as e:
    print(f"Error: {e}")
