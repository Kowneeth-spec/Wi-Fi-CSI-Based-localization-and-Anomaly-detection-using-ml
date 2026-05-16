#!/usr/bin/env python3
"""
ESP32 Board Configuration Discovery
Checks for web UI, Bluetooth, and other configuration interfaces
"""
import socket
import requests
import time
import subprocess

def check_http_ports(host_candidates):
    """Check common HTTP ports for web UI"""
    print("[*] Scanning for Web UI on ESP32...")
    common_ports = [80, 8080, 8888, 3000, 5000, 1880]
    
    for host in host_candidates:
        for port in common_ports:
            try:
                url = f"http://{host}:{port}"
                resp = requests.get(url, timeout=2)
                print(f"  ✓ Found: {url}")
                print(f"    Status: {resp.status_code}")
                print(f"    Content: {resp.text[:100]}")
                return url
            except:
                pass
    
    print("  ✗ No Web UI found on common ports")
    return None

def check_mdns():
    """Check for mDNS (Bonjour) services"""
    print("\n[*] Checking for mDNS (Bonjour) services...")
    try:
        # Try to find ESP32 via mDNS
        result = subprocess.run(
            ['powershell', '-Command', 
             'Get-ChildItem "HKLM:\\SYSTEM\\CurrentControlSet\\services\\mDNS" -ErrorAction SilentlyContinue'],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            print("  ✓ mDNS service detected")
            return True
    except:
        pass
    
    print("  ℹ mDNS check inconclusive")
    return False

def check_bluetooth():
    """Check for Bluetooth devices"""
    print("\n[*] Checking for Bluetooth connectivity...")
    try:
        result = subprocess.run(
            ['powershell', '-Command', 
             'Get-ChildItem "HKLM:\\SYSTEM\\CurrentControlSet\\services\\Bluetooth" -ErrorAction SilentlyContinue'],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            print("  ✓ Bluetooth service available")
            return True
    except:
        pass
    
    print("  ℹ Bluetooth check inconclusive")
    return False

def discover_esp32_info():
    """Try to get ESP32 network info"""
    print("\n[*] Attempting to discover ESP32 on network...")
    
    # Common ESP32 hostnames
    esp_hosts = [
        'esp32',
        'esp32.local',
        'esp-idf',
        'esp-idf.local',
        'esp32-webui',
        'esp32-webui.local',
        'espressif-esp32',
        'espressif-esp32.local',
    ]
    
    # Try to resolve each hostname
    for hostname in esp_hosts:
        try:
            ip = socket.gethostbyname(hostname)
            print(f"  ✓ Found {hostname} at {ip}")
            return ip
        except:
            pass
    
    print("  ℹ Could not resolve ESP32 hostname via DNS")
    return None

def check_serial_ports_for_csi():
    """Check what's accessible via serial"""
    print("\n[*] Checking Serial Port (COM7) for CSI status...")
    try:
        import serial
        ser = serial.Serial('COM7', 115200, timeout=1)
        time.sleep(0.5)
        
        # Clear buffer
        ser.reset_input_buffer()
        
        # Try info command
        ser.write(b'info\n')
        time.sleep(1)
        resp = ser.read(256)
        if resp and len(resp) > 10:
            print(f"  Response to 'info': {resp[:50]}")
        
        ser.close()
    except Exception as e:
        print(f"  Error: {e}")

def main():
    print("=" * 70)
    print("ESP32 BOARD CONFIGURATION DISCOVERY")
    print("=" * 70)
    
    # 1. Check network discovery
    esp_ip = discover_esp32_info()
    
    # 2. If IP found, check HTTP ports
    if esp_ip:
        check_http_ports([esp_ip, 'localhost', '127.0.0.1'])
    else:
        # Try common local IPs for ESP32
        print("\n[*] Trying common ESP32 IP addresses...")
        check_http_ports(['192.168.1.100', '192.168.4.1', '192.168.0.1', 'localhost'])
    
    # 3. Check Bluetooth
    check_bluetooth()
    
    # 4. Check mDNS
    check_mdns()
    
    # 5. Check serial for CSI
    check_serial_ports_for_csi()
    
    print("\n" + "=" * 70)
    print("NEXT STEPS:")
    print("=" * 70)
    print("""
Option A - Web UI Configuration:
  If found, open http://ESP32_IP in your browser and configure WiFi

Option B - Serial/AT Commands:
  Your ESP32 may accept AT commands. Try in serial terminal:
  - AT+CWSCAN=1
  - AT+CWJAP="ssid","password"
  - AT+CWJAP?

Option C - Buttons/Physical:
  Check your specific ESP32 board for:
  - BOOT/RESET buttons
  - Configuration mode combinations
  - LED indicators

Option D - Mobile App:
  Some ESP32 boards include companion mobile apps:
  - ESP BLE Config (for Bluetooth)
  - EspressIF apps (for official boards)
  - ESPTouch for SmartConfig

Option E - GPIO Pins:
  Check if pins have physical WiFi config switches
    """)

if __name__ == "__main__":
    main()
