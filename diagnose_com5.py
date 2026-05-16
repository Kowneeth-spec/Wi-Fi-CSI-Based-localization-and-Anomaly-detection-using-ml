#!/usr/bin/env python3
"""
Diagnose what's coming from ESP32 on COM5
"""
import serial
import time

print("=" * 70)
print("ESP32 SERIAL DIAGNOSTICS - COM5")
print("=" * 70)

try:
    ser = serial.Serial("COM5", 115200, timeout=2)
    print(f"\n✓ Connected to COM5 @ 115200 baud\n")
    
    # Reset ESP32
    print("[*] Resetting ESP32...")
    ser.dtr = False
    time.sleep(0.5)
    ser.dtr = True
    time.sleep(2)
    
    # Read boot output
    print("[*] Capturing boot output (5 seconds)...\n")
    print("=" * 70)
    
    boot_output = b""
    start_time = time.time()
    while time.time() - start_time < 5:
        if ser.in_waiting:
            data = ser.read(ser.in_waiting)
            boot_output += data
            try:
                print(data.decode('utf-8', errors='replace'), end='', flush=True)
            except:
                print(f"[Binary: {len(data)} bytes]")
    
    print("\n" + "=" * 70)
    
    # Analyze output
    if b"CSI" in boot_output:
        print("\n✓ CSI firmware detected!")
    else:
        print("\n⚠ No CSI mentions found")
    
    if b"passive" in boot_output.lower():
        print("✓ Passive mode active")
    
    # Check for errors
    if b"error" in boot_output.lower():
        print("⚠ Errors detected in boot output")
    
    ser.close()
    
except Exception as e:
    print(f"✗ Error: {e}")
