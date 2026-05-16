#!/usr/bin/env python3
"""
Quick WiFi Configuration Script for ESP32
"""
import serial
import time
import json

def configure_wifi_esp32(port, ssid, password):
    """Send WiFi configuration to ESP32"""
    try:
        ser = serial.Serial(port, 115200, timeout=2)
        time.sleep(1)
        
        print(f"[*] Connecting to ESP32 on {port}...")
        print(f"[*] Sending WiFi credentials...")
        print(f"    SSID: {ssid}")
        print(f"    Password: {password}")
        
        # Send configuration command
        config = f"WIFI_CONFIG:{ssid}:{password}\n"
        ser.write(config.encode())
        
        # Wait for response
        time.sleep(2)
        response = ser.read(1024).decode('utf-8', errors='ignore')
        
        if response:
            print(f"[✓] ESP32 Response:\n{response}")
        else:
            print("[*] No immediate response (this is normal)")
        
        print("[✓] WiFi config sent! ESP32 should now connect to your network.")
        print("[*] Restart the ESP32 or wait 10 seconds for changes to apply.")
        
        ser.close()
        return True
        
    except Exception as e:
        print(f"[✗] Error: {e}")
        return False

if __name__ == "__main__":
    SSID = "iqoo neo 7"
    PASSWORD = "12345678"
    PORT = "COM7"
    
    configure_wifi_esp32(PORT, SSID, PASSWORD)
