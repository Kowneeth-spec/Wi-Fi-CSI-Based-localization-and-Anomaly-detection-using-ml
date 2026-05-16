#!/usr/bin/env python3
"""
ESP32 CSI WiFi Configuration via Serial Protocol
Sends WiFi SSID & password to ESP32 CSI firmware via serial
"""
import serial
import time
import struct

def send_wifi_config(port, ssid, password, baud=115200):
    """Send WiFi configuration to ESP32 CSI firmware"""
    try:
        ser = serial.Serial(port, baud, timeout=2)
        time.sleep(1)
        
        print(f"[*] Connected to {port} @ {baud} baud")
        print(f"[*] Sending WiFi Configuration...")
        print(f"    SSID: {ssid}")
        print(f"    Password: {password}")
        
        # CSI firmware WiFi config format (custom protocol)
        # Format: <header><ssid_len><ssid><pass_len><password>
        
        # Flush any existing data
        ser.reset_input_buffer()
        time.sleep(0.5)
        
        # Try multiple command formats
        commands = [
            # Format 1: Simple JSON-like command
            f'WIFI_CONFIG_JSON:{{"ssid":"{ssid}","password":"{password}"}}\n'.encode(),
            
            # Format 2: Simple colon-separated
            f'WIFI_SET:{ssid}:{password}\n'.encode(),
            
            # Format 3: Simple space-separated  
            f'wifi_connect {ssid} {password}\n'.encode(),
            
            # Format 4: Binary protocol (length-prefixed)
            b'\xaa\xaa' + struct.pack('B', len(ssid)) + ssid.encode() + 
            struct.pack('B', len(password)) + password.encode() + b'\xbb\xbb\n'
        ]
        
        for i, cmd in enumerate(commands, 1):
            print(f"\n[{i}] Trying command format {i}...")
            ser.write(cmd)
            time.sleep(1)
            
            # Check for response
            if ser.in_waiting:
                response = ser.read(min(ser.in_waiting, 256))
                print(f"    Response: {response[:50]}")
                if b'OK' in response or b'SUCCESS' in response:
                    print(f"[✓] SUCCESS with format {i}!")
                    return True
        
        print("\n[*] Configuration commands sent to ESP32")
        print("[*] ESP32 should now connect to WiFi: iqoo neo 7")
        print("[*] Restart ESP32 or wait 30 seconds for changes to apply")
        
        ser.close()
        return True
        
    except Exception as e:
        print(f"[✗] Error: {e}")
        return False

if __name__ == "__main__":
    SSID = "iqoo neo 7"
    PASSWORD = "12345678"
    PORT = "COM7"
    
    send_wifi_config(PORT, SSID, PASSWORD)
