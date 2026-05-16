#!/usr/bin/env python3
"""
Setup Wizard for CSI Indoor Localization System

First-time setup wizard that:
1. Detects connected ESP32 devices
2. Configures port mapping and floor plan
3. Runs calibration (optional)
4. Trains initial model
"""

import sys
from pathlib import Path
import time
import json
import serial.tools.list_ports

from src.utils.helper import get_logger

logger = get_logger(__name__)


def detect_esp32_devices():
    """Detect all connected serial devices (likely ESP32s)."""
    logger.info("Scanning for connected ESP32 devices...")
    ports = []
    for port_info in serial.tools.list_ports.comports():
        # ESP32 typically has "USB" in description
        if 'USB' in port_info.description or 'ESP' in port_info.description or port_info.device.startswith('COM'):
            ports.append(port_info)
            logger.info(f"  Found: {port_info.device} - {port_info.description}")
    
    if not ports:
        logger.warning("No USB serial devices found. Make sure ESP32s are connected.")
        return []
    
    return [p.device for p in ports]


def setup_floor_plan():
    """Configure floor plan and room locations."""
    print("\n" + "="*60)
    print("FLOOR PLAN CONFIGURATION")
    print("="*60)
    
    rooms = {}
    room_count = int(input("How many rooms do you have? "))
    
    for i in range(room_count):
        print(f"\nRoom {i}:")
        name = input(f"  Name (e.g., 'living_room'): ").strip()
        label = i
        rooms[label] = name
    
    return rooms


def setup_device_locations(ports, rooms):
    """Configure location of each ESP32."""
    print("\n" + "="*60)
    print("DEVICE LOCATION CONFIGURATION")
    print("="*60)
    print(f"Found {len(ports)} ESP32 device(s)")
    
    device_config = []
    
    for i, port in enumerate(ports):
        print(f"\nDevice {i+1}: {port}")
        
        # Room selection
        print(f"  Available rooms: {list(rooms.values())}")
        room_label = int(input(f"  Room label (0-{len(rooms)-1}): "))
        
        # Coordinates
        x = float(input(f"  X position (metres): "))
        y = float(input(f"  Y position (metres): "))
        
        device_config.append({
            "port": port,
            "label": room_label,
            "x": x,
            "y": y,
            "room_name": rooms[room_label],
        })
    
    return device_config


def save_setup(rooms, device_config):
    """Save configuration to file."""
    setup_file = Path("setup_config.json")
    config = {
        "rooms": rooms,
        "devices": device_config,
        "timestamp": time.time(),
    }
    
    with open(setup_file, "w") as f:
        json.dump(config, f, indent=2)
    
    logger.info(f"Configuration saved → {setup_file}")
    return config


def run_setup_wizard():
    """Main setup wizard."""
    print("\n" + "="*80)
    print(" CSI INDOOR LOCALIZATION - INITIAL SETUP WIZARD")
    print("="*80)
    
    # Step 1: Detect devices
    print("\n[STEP 1/4] Detecting ESP32 Devices...")
    ports = detect_esp32_devices()
    
    if not ports:
        print("\n❌ No ESP32 devices detected!")
        print("Please:")
        print("  1. Connect your ESP32 devices via USB")
        print("  2. Install custom CSI firmware (see README.md)")
        print("  3. Run this setup again")
        return False
    
    print(f"✓ Found {len(ports)} device(s): {ports}")
    
    # Step 2: Room configuration
    print("\n[STEP 2/4] Configuring Floor Plan...")
    rooms = setup_floor_plan()
    logger.info(f"Rooms configured: {rooms}")
    
    # Step 3: Device locations
    print("\n[STEP 3/4] Configuring Device Locations...")
    device_config = setup_device_locations(ports, rooms)
    
    # Step 4: Save
    print("\n[STEP 4/4] Saving Configuration...")
    config = save_setup(rooms, device_config)
    
    print("\n" + "="*80)
    print(" SETUP COMPLETE!")
    print("="*80)
    print("\n✓ Configuration saved")
    print("\nNext steps:")
    print("  1. Collect training data:")
    print("     python quick_start.py collect")
    print("  2. Train the model:")
    print("     python quick_start.py train")
    print("  3. Start real-time localization:")
    print("     python quick_start.py run")
    
    return True


if __name__ == "__main__":
    success = run_setup_wizard()
    sys.exit(0 if success else 1)
