#!/usr/bin/env python3
"""
Debug CSI packet parsing from bracketed format
"""
import serial
import sys
import time
import numpy as np

sys.path.insert(0, 'src')

print("Testing CSI packet parsing from COM5...")
print("=" * 80)

try:
    ser = serial.Serial("COM5", 115200, timeout=2)
    time.sleep(0.5)
    ser.reset_input_buffer()
    
    packet_count = 0
    valid_count = 0
    buffer = []
    
    for i in range(500):  # Try up to 500 packets
        raw = ser.readline().decode("utf-8", errors="ignore").strip()
        
        if not raw.startswith("CSI_DATA"):
            continue
        
        packet_count += 1
        
        tokens = raw.split(",")
        if len(tokens) < 4:
            print(f"  ✗ Packet {packet_count}: Invalid token count ({len(tokens)})")
            continue
        
        # Extract CSI data from bracketed format
        last_token = tokens[-1] if tokens else ""
        if "[" not in last_token or "]" not in last_token:
            print(f"  ✗ Packet {packet_count}: No brackets found")
            continue
        
        start_idx = last_token.find("[")
        end_idx = last_token.find("]")
        if start_idx == -1 or end_idx == -1 or start_idx >= end_idx:
            print(f"  ✗ Packet {packet_count}: Bracket parsing failed")
            continue
        
        # Extract and parse values
        csi_str = last_token[start_idx+1:end_idx].strip()
        try:
            values = list(map(float, csi_str.split()))
        except ValueError as e:
            print(f"  ✗ Packet {packet_count}: Parse error: {e}")
            continue
        
        if len(values) != 104:
            print(f"  ✗ Packet {packet_count}: Wrong IQ count ({len(values)}, expected 104)")
            continue
        
        # Create complex array
        csi = np.array([values[i] + 1j * values[i+1] for i in range(0, len(values), 2)])
        
        valid_count += 1
        buffer.append(csi)
        
        if valid_count % 5 == 0:
            print(f"  ✓ Valid packet {valid_count}: {len(csi)} subcarriers")
        
        if valid_count == 20:
            print(f"\n✓ READY FOR FIRST PREDICTION! Got {valid_count} valid packets")
            break
    
    ser.close()
    
    print("\n" + "=" * 80)
    print(f"Total packets scanned: {packet_count}")
    print(f"Valid packets parsed: {valid_count}")
    
except KeyboardInterrupt:
    print("\nInterrupted")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
