#!/usr/bin/env python3
"""
Wait for ESP32 CSI build to complete, then flash automatically
"""

import time
import sys
from pathlib import Path

def find_firmware_binary():
    """Find the compiled firmware binary"""
    build_dir = Path("C:\\ESP32-CSI-Tool\\passive\\build")
    
    search_paths = [
        build_dir / "passive.bin",
        build_dir / "csi_receiver.bin",
        build_dir / "esp-idf" / "bootloader" / "bootloader.bin",
    ]
    
    # Most likely location
    for root in build_dir.glob("**/esp-idf/main"):
        for bin_file in root.glob("*.bin"):
            return bin_file
    
    return None

def wait_for_build_complete():
    """Poll for build completion"""
    print("⏳ Waiting for build to complete...")
    print("   Currently: step 97/1016")
    print("   Typical time: 5-10 minutes\n")
    
    timeout = 600  # 10 minutes
    start = time.time()
    
    while time.time() - start < timeout:
        firmware = find_firmware_binary()
        
        if firmware and firmware.stat().st_size > 100000:  # At least 100KB
            print(f"\n✅ BUILD COMPLETE!")
            print(f"   Binary: {firmware}")
            print(f"   Size: {firmware.stat().st_size} bytes")
            return firmware
        
        elapsed = int(time.time() - start)
        remaining = timeout - elapsed
        print(f"\r  [{elapsed}s/{timeout}s] Building... ({remaining}s remaining)", end="", flush=True)
        time.sleep(2)
    
    print(f"\n❌ Build timeout after {timeout}s")
    return None

def main():
    firmware = wait_for_build_complete()
    
    if not firmware:
        print("\nℹ️  Build is still running. Check the terminal for progress.")
        print("Once complete, run: idf.py flash monitor --port COM7")
        return False
    
    print(f"\n{'='*60}")
    print("BUILD SUCCESSFUL - Ready to Flash!")
    print(f"{'='*60}")
    print(f"\nNext command:")
    print(f"  idf.py flash monitor --port COM7")
    print(f"\nThis will:")
    print(f"  1. Flash the firmware to ESP32 on COM7")
    print(f"  2. Monitor serial output")
    print(f"  3. Show CSI_DATA packets")
    print(f"\nPress Ctrl+] to exit monitor\n")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
