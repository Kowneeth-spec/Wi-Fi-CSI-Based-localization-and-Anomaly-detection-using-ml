#!/usr/bin/env python3
"""
Test different baud rates to find the correct one for ESP32 boot output.
"""
import serial
import time

print("=" * 70)
print("ESP32 BAUD RATE DETECTION")
print("=" * 70)

BAUD_RATES = [115200, 230400, 460800, 921600, 74880, 9600]
PORT = "COM7"
READ_DURATION = 3

for baud in BAUD_RATES:
    print(f"\n[*] Attempting {baud} baud...", end=" ", flush=True)
    try:
        ser = serial.Serial(PORT, baud, timeout=1)
        time.sleep(0.5)
        
        # Send reset
        ser.dtr = False
        time.sleep(0.1)
        ser.dtr = True
        time.sleep(1)
        
        # Read boot output
        boot_output = b""
        start_time = time.time()
        while time.time() - start_time < READ_DURATION:
            if ser.in_waiting:
                boot_output += ser.read(ser.in_waiting)
        
        ser.close()
        
        # Check if output contains readable text
        try:
            readable = boot_output.decode('utf-8', errors='ignore')
            if len(readable) > 20 and any(c.isprintable() for c in readable):
                print(f"✓ FOUND READABLE OUTPUT!")
                print(f"\n{'='*70}")
                print(f"Baud Rate: {baud} - READOUT:")
                print(f"{'='*70}")
                print(readable[:500])  # First 500 chars
                print(f"\n{'='*70}\n")
            else:
                print("✗ No readable output")
        except:
            print("✗ Garbage data")
            
    except Exception as e:
        print(f"✗ Error: {e}")

print("\n[*] Baud rate detection complete")
