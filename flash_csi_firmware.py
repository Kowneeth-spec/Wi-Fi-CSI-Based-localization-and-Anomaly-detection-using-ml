#!/usr/bin/env python3
"""
Download and flash pre-built ESP32 CSI firmware from GitHub releases
"""

import os
import sys
import json
import urllib.request
import subprocess
from pathlib import Path

def get_latest_release():
    """Fetch latest release info from GitHub"""
    print("📡 Fetching latest firmware from GitHub releases...")
    
    url = "https://api.github.com/repos/StevenMHernandez/ESP32-CSI-Tool/releases/latest"
    
    try:
        with urllib.request.urlopen(url) as response:
            data = json.loads(response.read().decode())
            return data
    except Exception as e:
        print(f"❌ Failed to fetch releases: {e}")
        return None

def download_firmware(download_url, output_path):
    """Download firmware binary"""
    print(f"📥 Downloading: {download_url}")
    print(f"💾 Saving to: {output_path}")
    
    try:
        urllib.request.urlretrieve(download_url, output_path, reporthook=report_download)
        print(f"\n✓ Download complete!")
        return True
    except Exception as e:
        print(f"❌ Download failed: {e}")
        return False

def report_download(block_num, block_size, total_size):
    """Show download progress"""
    downloaded = block_num * block_size
    percent = min(downloaded * 100 // total_size, 100)
    sys.stdout.write(f"\r  Progress: {percent}% ({downloaded}/{total_size} bytes)")
    sys.stdout.flush()

def flash_firmware(port, firmware_path):
    """Flash firmware to ESP32"""
    print(f"\n📡 Flashing firmware to {port}...")
    print(f"   Binary: {firmware_path}")
    print(f"   (This will take 30-60 seconds)")
    
    cmd = [
        sys.executable, "-m", "esptool",
        "--port", port,
        "write_flash", "0x0", firmware_path
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print("✓ Flashing successful!")
            return True
        else:
            print(f"❌ Flashing failed:\n{result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    port = "COM7"
    firmware_dir = Path("C:/ESP32-CSI-Firmware")
    firmware_path = firmware_dir / "csi_passive_receiver.bin"
    
    # Create firmware directory
    firmware_dir.mkdir(parents=True, exist_ok=True)
    
    print("="*60)
    print("ESP32 CSI Firmware Flasher")
    print("="*60)
    
    # Check if firmware already exists
    if firmware_path.exists():
        print(f"✓ Found existing firmware: {firmware_path}")
        use_existing = input("Use existing firmware? (y/n): ").strip().lower()
        if use_existing != 'y':
            firmware_path.unlink()
    
    # Download if needed
    if not firmware_path.exists():
        release = get_latest_release()
        if not release:
            print("❌ Could not fetch releases. Try manual download from:")
            print("   https://github.com/StevenMHernandez/ESP32-CSI-Tool/releases")
            return False
        
        print(f"\n✓ Latest release: {release.get('tag_name', 'unknown')}")
        
        # Look for firmware asset
        assets = release.get('assets', [])
        firmware_assets = [a for a in assets if 'passive' in a['name'].lower() or 'csi' in a['name'].lower()]
        
        if not firmware_assets:
            print("❌ No CSI firmware found in releases")
            print("Available assets:")
            for asset in assets:
                print(f"  - {asset['name']}")
            return False
        
        firmware_url = firmware_assets[0]['browser_download_url']
        print(f"Available: {firmware_assets[0]['name']} ({firmware_assets[0]['size']} bytes)")
        
        if not download_firmware(firmware_url, str(firmware_path)):
            return False
    
    # Flash the firmware
    print("\n" + "="*60)
    print("FLASHING FIRMWARE")
    print("="*60)
    print(f"Target: {port}")
    print(f"Firmware: {firmware_path.name}")
    print("\n⚠️  DO NOT DISCONNECT THE ESP32 DURING FLASHING!")
    input("Press ENTER to start flashing...")
    
    if flash_firmware(port, str(firmware_path)):
        print("\n" + "="*60)
        print("✅ SUCCESS!")
        print("="*60)
        print("Your ESP32 now has CSI firmware!")
        print("\nNext steps:")
        print("1. Unplug and replug the ESP32")
        print("2. Run: python main.py live --port COM7 --no_display")
        print("3. You should see CSI_DATA packets!")
        return True
    else:
        print("\n❌ Flashing failed. Try:")
        print("1. Unplug ESP32 for 3 seconds")
        print("2. Replug it in")
        print("3. Try again")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
