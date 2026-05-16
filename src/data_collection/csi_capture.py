# src/data_collection/csi_capture.py
"""
Live CSI capture from ESP32 over USB-Serial.

Usage
-----
python -m src.data_collection.csi_capture \
    --port /dev/ttyUSB0 \
    --label 0 \           # room label (int)
    --x 2.5 --y 1.0 \    # ground-truth coordinates (metres)
    --duration 60 \       # seconds to record
    --out data/raw/living_room_01.csv
"""

import argparse
import csv
import time
from datetime import datetime
from pathlib import Path

import serial

from src.utils.config import SERIAL_PORT, BAUD_RATE, SERIAL_TIMEOUT
from src.utils.helper import get_logger

logger = get_logger(__name__)

# ── ESP32 line prefix emitted by custom firmware ─────────────────────────────
CSI_LINE_PREFIX = "CSI_DATA"


def open_serial(port: str, baud: int, timeout: float) -> serial.Serial:
    try:
        ser = serial.Serial(port, baud, timeout=timeout)
        logger.info(f"Opened serial port {port} @ {baud} baud")
        return ser
    except serial.SerialException as exc:
        logger.error(f"Cannot open {port}: {exc}")
        raise


def parse_line(line: str) -> list[str] | None:
    """
    Expect lines like:
        CSI_DATA,<seq>,<rssi>,<i0>,<q0>,<i1>,<q1>,...

    Returns a list of raw string tokens or None if the line is invalid.
    """
    line = line.strip()
    if not line.startswith(CSI_LINE_PREFIX):
        return None
    parts = line.split(",")
    if len(parts) < 4:
        return None
    return parts


def capture(
    port: str,
    baud: int,
    duration: float,
    label: int,
    x: float,
    y: float,
    out_path: Path,
) -> int:
    """
    Capture CSI packets for *duration* seconds and write to *out_path*.

    Returns the number of packets recorded.
    """
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    ser = open_serial(port, baud, SERIAL_TIMEOUT)
    time.sleep(0.5)            # let ESP32 stabilise
    ser.reset_input_buffer()

    packet_count = 0
    t_start = time.monotonic()

    with open(out_path, "w", newline="") as f:
        writer = csv.writer(f)
        # Header
        writer.writerow(["timestamp", "seq", "rssi", "label", "x_m", "y_m", "raw_tokens"])

        logger.info(f"Recording for {duration}s → {out_path}")
        try:
            while time.monotonic() - t_start < duration:
                try:
                    raw = ser.readline().decode("utf-8", errors="ignore")
                except serial.SerialException as exc:
                    logger.warning(f"Serial read error: {exc}")
                    continue

                tokens = parse_line(raw)
                if tokens is None:
                    continue

                _prefix = tokens[0]
                seq  = tokens[1] if len(tokens) > 1 else ""
                rssi = tokens[2] if len(tokens) > 2 else ""
                raw_payload = ",".join(tokens[3:])

                writer.writerow([
                    datetime.utcnow().isoformat(),
                    seq, rssi, label, x, y, raw_payload,
                ])
                packet_count += 1

                if packet_count % 100 == 0:
                    elapsed = time.monotonic() - t_start
                    logger.info(f"  {packet_count} packets in {elapsed:.1f}s")
        except KeyboardInterrupt:
            logger.info("Capture interrupted by user.")
        finally:
            ser.close()

    logger.info(f"Done. {packet_count} packets saved to {out_path}")
    return packet_count


# ── CLI ───────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="ESP32 CSI live capture")
    parser.add_argument("--port",     default=SERIAL_PORT)
    parser.add_argument("--baud",     default=BAUD_RATE,   type=int)
    parser.add_argument("--duration", default=60,          type=float, help="Recording time in seconds")
    parser.add_argument("--label",    default=0,           type=int,   help="Room label integer")
    parser.add_argument("--x",        default=0.0,         type=float, help="Ground-truth X coord (m)")
    parser.add_argument("--y",        default=0.0,         type=float, help="Ground-truth Y coord (m)")
    parser.add_argument("--out",      required=True,                   help="Output CSV path")
    args = parser.parse_args()

    capture(
        port=args.port,
        baud=args.baud,
        duration=args.duration,
        label=args.label,
        x=args.x,
        y=args.y,
        out_path=Path(args.out),
    )


if __name__ == "__main__":
    main()
