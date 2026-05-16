#!/usr/bin/env python3
"""
Download pre-built CSI firmware and flash to ESP32
Uses GitHub raw content to download pre-built binaries
"""

import os
import sys
import subprocess
import urllib.request
from pathlib import Path

def download_file(url, destination):
    """Download file from URL"""
    print(f"📥 Downloading: {url}")
    print(f"💾 Saving to: {destination}")
    
    try:
        urllib.request.urlretrieve(url, destination)
        print(f"✓ Download complete!")
        return True
    except Exception as e:
        print(f"❌ Download failed: {e}")
        return False

def flash_firmware(port, firmware_path):
    """Flash firmware using esptool"""
    print(f"\n{'='*60}")
    print("FLASHING FIRMWARE")
    print(f"{'='*60}")
    print(f"Binary: {firmware_path}")
    print(f"Target: {port}")
    print(f"⚠️  DO NOT DISCONNECT THE ESP32!")
    print()
    
    cmd = [
        sys.executable, "-m", "esptool",
        "--port", port,
        "write_flash", "0x0", firmware_path
    ]
    
    print(f"Executing: {' '.join(cmd)}\n")
    
    try:
        result = subprocess.run(cmd)
        
        if result.returncode == 0:
            print(f"\n{'='*60}")
            print("✅ FLASHING SUCCESSFUL!")
            print(f"{'='*60}")
            return True
        else:
            print(f"\n❌ Flashing failed with error code {result.returncode}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def try_factory_reset(port):
    """Attempt factory reset of ESP32"""
    print(f"\nℹ️  Attempting to erase and reset {port}...")
    
    cmd = [
        sys.executable, "-m", "esptool",
        "--port", port,
        "erase_flash"
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✓ Flash erased successfully")
            return True
    except Exception as e:
        print(f"⚠️  Erase failed: {e}")
    
    return False

def main():
    print("="*60)
    print("ESP32 CSI Firmware - Pre-built Binary Flasher")
    print("="*60)
    
    port = "COM7"
    firmware_dir = Path("C:/ESP32-CSI-Firmware")
    firmware_dir.mkdir(parents=True, exist_ok=True)
    
    # Pre-built firmware URLs
    # These are common pre-compiled CSI firmware sources
    firmware_urls = [
        # Option 1: From Steven Hernandez's releases (if available)
        "https://github.com/StevenMHernandez/ESP32-CSI-Tool/releases/download/v1.0/csi_receiver.bin",
        # Option 2: Alternative mirror or build
        "https://raw.githubusercontent.com/StevenMHernandez/ESP32-CSI-Tool/main/build/csi_receiver.bin",
    ]
    
    print(f"\nℹ️  To complete firmware flashing, you need a pre-built CSI firmware binary.")
    print(f"\nOptions:")
    print(f"1. Manually download from:")
    print(f"   https://github.com/StevenMHernandez/ESP32-CSI-Tool/releases")
    print(f"   Look for: 'csi_receiver.bin' or similar")
    print(f"\n2. Place the file here: {firmware_dir}")
    print(f"\n3. Or provide the path to your firmware binary")
    
    firmware_path = input(f"\nEnter path to firmware binary (or press ENTER to skip): ").strip()
    
    if not firmware_path:
        print("\n⚠️  No firmware provided.")
        print("\nManual steps:")
        print("1. Download CSI firmware from releases page above")
        print("2. Save it to: C:\\ESP32-CSI-Firmware\\")
        print("3. Run: python -m esptool --port COM7 write_flash 0x0 /path/to/firmware.bin")
        return False
    
    firmware_path = Path(firmware_path)
    
    if not firmware_path.exists():
        print(f"❌ File not found: {firmware_path}")
        return False
    
    print(f"\n✓ Found firmware: {firmware_path.name} ({firmware_path.stat().st_size} bytes)")
    
    # Confirm before flashing
    response = input(f"\nReady to flash {port}? (y/n): ").strip().lower()
    
    if response != 'y':
        print("Cancelled.")
        return False
    
    # Flash the firmware
    return flash_firmware(port, str(firmware_path))

if __name__ == "__main__":
    success = main()
    
    print(f"\n{'='*60}")
    if success:
        print("✅ Flash completed successfully!")
        print("\nNext steps:")
        print("1. Unplug ESP32 for 2 seconds")
        print("2. Replug it")
        print("3. Test: python diagnose_esp32.py")
        print("4. Run: python main.py live --port COM7 --no_display")
    else:
        print("❌ Flashing incomplete")
        print("\nTroubleshooting:")
        print("• Check Device Manager for driver issues")
        print("• Try unplugging/replugging ESP32")
        print("• Make sure COM7 is not in use by another application")
    print(f"{'='*60}\n")
    
    sys.exit(0 if success else 1)
