#!/usr/bin/env python3
"""
Generate WiFi traffic on a hotspot to stimulate CSI packet generation.

This script pings and makes HTTP requests to generate network traffic
that will cause the ESP32 to capture CSI packets.

Usage:
    python generate_wifi_traffic.py <hotspot_ip>  (e.g., 192.168.1.1)
"""

import sys
import subprocess
import time
from pathlib import Path

def ping_target(ip: str, count: int = 10):
    """Ping target IP address to generate traffic."""
    print(f"[TRAFFIC] Pinging {ip}...")
    try:
        if sys.platform == "win32":
            subprocess.run(
                ["ping", "-n", str(count), ip],
                capture_output=True,
                timeout=30
            )
        else:
            subprocess.run(
                ["ping", "-c", str(count), ip],
                capture_output=True,
                timeout=30
            )
        print(f"[TRAFFIC] ✓ Ping to {ip} complete")
    except Exception as e:
        print(f"[TRAFFIC] ✗ Ping failed: {e}")

def curl_traffic(url: str):
    """Make HTTP request to generate traffic."""
    print(f"[TRAFFIC] Downloading {url}...")
    try:
        import urllib.request
        urllib.request.urlopen(url, timeout=5)
        print(f"[TRAFFIC] ✓ Download complete")
    except Exception as e:
        print(f"[TRAFFIC] ✗ Download failed: {e}")

def main():
    print("""
╔═══════════════════════════════════════════════════════════════════╗
║     WiFi Traffic Generator for CSI Data Stimulation              ║
║     Run this while live predictions are buffering                 ║
╚═══════════════════════════════════════════════════════════════════╝
    """)
    
    if len(sys.argv) < 2:
        print("Usage: python generate_wifi_traffic.py <hotspot_ip>")
        print("Example: python generate_wifi_traffic.py 192.168.1.1")
        print()
        print("Default: Using gateway IP 192.168.1.1")
        hotspot_ip = "192.168.1.1"
    else:
        hotspot_ip = sys.argv[1]
    
    print(f"Target IP: {hotspot_ip}")
    print("Generating traffic for 2 minutes...")
    print()
    
    start_time = time.time()
    iteration = 0
    
    while time.time() - start_time < 120:  # 2 minutes
        iteration += 1
        print(f"\n--- Traffic Generation Round {iteration} ---")
        
        # Ping gateway
        ping_target(hotspot_ip, count=5)
        
        # Try downloading a small file to generate sustained traffic
        try:
            curl_traffic("http://www.google.com/images/branding/googlelogo/1x/googlelogo_color_272x92dp.png")
        except:
            pass  # Continue even if download fails
        
        time.sleep(5)
    
    print("""
    
╔═══════════════════════════════════════════════════════════════════╗
║            Traffic Generation Complete!                          ║
║                                                                   ║
║  CSI packets should now be buffering in the live predictions.     ║
║  You should see predictions appearing now.                        ║
╚═══════════════════════════════════════════════════════════════════╝
    """)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[TRAFFIC] Stopped by user")
