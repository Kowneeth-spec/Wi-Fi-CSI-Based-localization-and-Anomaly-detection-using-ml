#!/usr/bin/env python3
"""
Debug CSI packet reception and parsing
"""
import serial
import sys
import time

sys.path.insert(0, 'src')
from data_collection.parser import parse_raw_tokens

print("Listening for CSI packets on COM5...")
print("=" * 70)

try:
    ser = serial.Serial("COM5", 115200, timeout=2)
    time.sleep(0.5)
    ser.reset_input_buffer()
    
    packet_count = 0
    valid_count = 0
    start_time = time.time()
    
    while time.time() - start_time < 15:  # 15 second window
        raw = ser.readline().decode("utf-8", errors="ignore").strip()
        
        if not raw.startswith("CSI_DATA"):
            continue
        
        packet_count += 1
        
        tokens = raw.split(",")
        if len(tokens) < 4:
            print(f"  ✗ Packet {packet_count}: Invalid token count ({len(tokens)})")
            continue
        
        raw_payload = ",".join(tokens[3:])
        csi = parse_raw_tokens(raw_payload)
        
        if csi is None:
            print(f"  ✗ Packet {packet_count}: Parse failed")
            continue
        
        valid_count += 1
        
        if valid_count % 5 == 0:
            print(f"  ✓ Received {valid_count} valid CSI packets (buffer: {valid_count}/20)")
    
    ser.close()
    
    print("\n" + "=" * 70)
    print(f"Total packets: {packet_count}")
    print(f"Valid packets: {valid_count}")
    if valid_count >= 20:
        print("✓ Enough CSI data for first prediction!")
    else:
        print(f"⚠ Need {20 - valid_count} more packets for first prediction")
    
except Exception as e:
    print(f"Error: {e}")
