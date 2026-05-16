#!/usr/bin/env python3
"""
Automatic firmware flasher - Waits for build to complete, then flashes to ESP32
"""

import os
import sys
import time
import subprocess
from pathlib import Path

def find_firmware_binary():
    """Find the compiled firmware binary"""
    build_dir = Path("C:\\ESP32-CSI-Tool\\passive\\build")
    
    # Common binary locations in ESP-IDF projects
    search_paths = [
        build_dir / "csi_receiver.bin",
        build_dir / "esp32" / "csi_receiver.bin",
        build_dir / "firmware.bin",
    ]
    
    for path in search_paths:
        if path.exists():
            return path
    
    return None

def wait_for_build(timeout=600):
    """Wait for build to complete (timeout in seconds)"""
    print("⏳ Waiting for firmware build to complete...")
    print(f"   Timeout: {timeout} seconds (~10 minutes)")
    print("   (Build typically takes 3-5 minutes)")
    
    start_time = time.time()
    last_size = 0
    no_change_count = 0
    
    while time.time() - start_time < timeout:
        firmware = find_firmware_binary()
        
        if firmware:
            print(f"\n✅ Build completed!")
            print(f"   Binary: {firmware}")
            print(f"   Size: {firmware.stat().st_size} bytes")
            return firmware
        
        # Check build directory for changes
        build_dir = Path("C:\\ESP32-CSI-Tool\\passive\\build")
        if build_dir.exists():
            current_size = sum(f.stat().st_size for f in build_dir.glob("**/*") if f.is_file())
            
            if current_size > last_size:
                print(f"  📝 Build in progress... ({current_size} bytes)")
                last_size = current_size
                no_change_count = 0
            else:
                no_change_count += 1
                if no_change_count % 10 == 0:
                    print(f"  ⏳ Still waiting... ({int(time.time() - start_time)}s elapsed)")
        
        time.sleep(2)
    
    print(f"❌ Build did not complete within {timeout} seconds")
    return None

def flash_firmware(firmware_path, port="COM7"):
    """Flash firmware to ESP32"""
    print(f"\n{'='*60}")
    print(f"FLASHING FIRMWARE")
    print(f"{'='*60}")
    print(f"Binary: {firmware_path}")
    print(f"Target: {port}")
    print(f"⚠️  DO NOT DISCONNECT THE ESP32!")
    
    cmd = [
        sys.executable, "-m", "esptool",
        "--port", port,
        "write_flash", "0x0", str(firmware_path)
    ]
    
    print(f"\nExecuting: {' '.join(cmd)}\n")
    
    try:
        result = subprocess.run(cmd, text=True)
        
        if result.returncode == 0:
            print(f"\n{'='*60}")
            print("✅ FLASHING SUCCESSFUL!")
            print(f"{'='*60}")
            print("\nNext steps:")
            print("1. Unplug ESP32 for 2 seconds")
            print("2. Replug it")
            print("3. Run: python diagnose_esp32.py (to verify)")
            print("4. Then: python main.py live --port COM7 --no_display")
            return True
        else:
            print(f"\n❌ Flashing failed with error code {result.returncode}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    print("="*60)
    print("ESP32 CSI Firmware Auto-Flasher")
    print("="*60)
    
    # Check if build is already done
    firmware = find_firmware_binary()
    
    if not firmware:
        print("Build not yet complete. Waiting...\n")
        firmware = wait_for_build()
    
    if not firmware:
        print("❌ Could not find compiled firmware")
        print("\nTroubleshooting:")
        print("1. Check that ESP-IDF build completed without errors")
        print("2. Look in: C:\\ESP32-CSI-Tool\\passive\\build")
        print("3. Check build output for errors")
        return False
    
    # Confirm before flashing
    response = input(f"\n✓ Found firmware: {firmware.name}\nReady to flash? (y/n): ").strip().lower()
    
    if response != 'y':
        print("Cancelled.")
        return False
    
    return flash_firmware(firmware)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
