#!/usr/bin/env python3
"""
ESP32 CSI Serial Debug and WiFi Configuration
Resets ESP32, captures boot output, and sends WiFi config commands
"""
import serial
import time

def reset_and_debug_esp32(port="COM7", baud=115200):
    """Reset ESP32 and capture boot output"""
    try:
        print(f"[*] Opening connection to {port} @ {baud} baud...")
        ser = serial.Serial(port, baud, timeout=1)
        time.sleep(0.5)
        
        # Clear any existing data
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        time.sleep(0.5)
        
        print("[*] Sending ESP32 reset command...")
        # DTR high (hold reset)
        ser.dtr = False
        time.sleep(0.5)
        # DTR low (release reset)
        ser.dtr = True
        time.sleep(1)
        
        print("\n[*] Capturing ESP32 boot output (10 seconds)...")
        print("=" * 60)
        
        boot_output = []
        start_time = time.time()
        
        while time.time() - start_time < 10:
            if ser.in_waiting:
                chunk = ser.read(ser.in_waiting)
                try:
                    text = chunk.decode('utf-8', errors='replace')
                    print(text, end='', flush=True)
                    boot_output.append(text)
                except:
                    pass
            time.sleep(0.1)
        
        print("\n" + "=" * 60)
        
        boot_text = ''.join(boot_output)
        
        # Check boot output for key indicators
        print("\n[*] Analyzing boot output:")
        if 'wifi' in boot_text.lower():
            print("  ✓ WiFi-related output detected")
        if 'csi' in boot_text.lower():
            print("  ✓ CSI-related output detected")
        if 'ready' in boot_text.lower() or 'started' in boot_text.lower():
            print("  ✓ System ready indicator detected")
        if 'error' in boot_text.lower() or 'fail' in boot_text.lower():
            print("  ⚠ Error detected in boot output")
        
        # Try sending WiFi config commands
        print("\n[*] Sending WiFi configuration commands...")
        wifi_commands = [
            b'wifi_config iqoo neo 7 12345678\n',
            b'AT+CWJAP="iqoo neo 7","12345678"\n',
            b'WIFI_SET:iqoo neo 7:12345678\n',
        ]
        
        for cmd in wifi_commands:
            print(f"  → {cmd.decode()}", end='')
            ser.write(cmd)
            time.sleep(1)
            if ser.in_waiting:
                resp = ser.read(ser.in_waiting)
                print(f"    Response: {resp[:50]}")
            else:
                print("    (no response)")
        
        print("\n[✓] Debug completed! Check output above for WiFi connection status.")
        ser.close()
        
    except Exception as e:
        print(f"[✗] Error: {e}")

if __name__ == "__main__":
    reset_and_debug_esp32()
