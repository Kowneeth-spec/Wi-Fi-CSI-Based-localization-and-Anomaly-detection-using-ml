#!/usr/bin/env python3
"""
ESP32 Diagnostic Tool - Check connection and firmware status
"""

import serial
import serial.tools.list_ports
import time
import sys

def find_all_ports():
    """List all available COM ports"""
    print("=" * 60)
    print("SCANNING FOR ESP32 DEVICES")
    print("=" * 60)
    
    ports = list(serial.tools.list_ports.comports())
    
    if not ports:
        print("❌ No COM ports detected!")
        return []
    
    print(f"✓ Found {len(ports)} COM port(s):\n")
    for port in ports:
        print(f"  🔌 {port.device:6} - {port.description}")
    
    return [p.device for p in ports if 'CP210x' in p.description or 'USB' in p.description]

def test_connection(port, baud=115200):
    """Test if we can connect to the ESP32 and read data"""
    print(f"\n{'='*60}")
    print(f"TESTING CONNECTION: {port} @ {baud} baud")
    print(f"{'='*60}")
    
    try:
        ser = serial.Serial(port, baud, timeout=2)
        print(f"✓ Connected to {port}")
        time.sleep(0.5)
        ser.reset_input_buffer()
        
        print(f"📡 Listening for data (5 seconds)...\n")
        start_time = time.time()
        csi_count = 0
        other_count = 0
        
        while time.time() - start_time < 5:
            try:
                line = ser.readline().decode('utf-8', errors='ignore').strip()
                if line:
                    if line.startswith("CSI_DATA"):
                        csi_count += 1
                        print(f"  ✓ CSI_DATA packet received")
                    else:
                        other_count += 1
                        print(f"  📝 Other: {line[:60]}")
            except:
                pass
        
        ser.close()
        
        print(f"\n{'='*60}")
        print("RESULTS:")
        print(f"{'='*60}")
        if csi_count > 0:
            print(f"✅ SUCCESS! Received {csi_count} CSI packets")
            print(f"   → ESP32 has proper CSI firmware ✓")
            return True
        else:
            print(f"❌ No CSI_DATA packets received")
            print(f"   → Other data: {other_count} packets")
            print(f"   → ESP32 may need CSI firmware flashing")
            return False
            
    except PermissionError:
        print(f"❌ PERMISSION DENIED - {port} is in use")
        print(f"   Possible causes:")
        print(f"   1. Arduino IDE, PuTTY, or Serial Monitor is open")
        print(f"   2. Another Python process has the port")
        print(f"   3. Driver issue - try unplugging/replugging ESP32")
        return False
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False

if __name__ == "__main__":
    esp32_ports = find_all_ports()
    
    if not esp32_ports:
        print("\n❌ No ESP32-like devices found. Check USB connection.")
        sys.exit(1)
    
    # Test each ESP32
    results = {}
    for port in esp32_ports:
        results[port] = test_connection(port)
    
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    for port, success in results.items():
        status = "✅ Ready" if success else "❌ Needs firmware"
        print(f"  {port}: {status}")
    
    if all(results.values()):
        print(f"\n✅ All ESP32s are ready to use!")
        sys.exit(0)
    else:
        print(f"\n⚠️  Some ESP32s need CSI firmware flashing.")
        sys.exit(1)
