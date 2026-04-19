"""
hardware.py — Arduino vibration motor control via pyserial.

Arduino serial protocol (flash this logic to your board):
  Command format : "V<on_ms>,<off_ms>,<repeats>\n"
  Examples:
    "V200,0,1\n"    → buzz 200ms once         (short)
    "V800,0,1\n"    → buzz 800ms once         (long)
    "V250,200,2\n"  → buzz 250ms, pause 200ms, repeat 2x (double)
  SOS is sent as multiple sequential commands from Python.
"""

import time

# Optional import — app works without Arduino installed
try:
    import serial
    _SERIAL_AVAILABLE = True
except ImportError:
    _SERIAL_AVAILABLE = False

import config.settings as cfg


# ── Connection (attempted once at import time) ───────────

def _connect_arduino():
    """
    Try to open the serial port defined in settings.ARDUINO_PORT.
    Returns a serial.Serial instance, or None — never raises.
    """
    if not _SERIAL_AVAILABLE:
        print("[hardware] pyserial not installed — vibration disabled")
        return None

    if not cfg.ARDUINO_PORT:
        print("[hardware] ARDUINO_PORT is None — vibration disabled")
        return None

    try:
        conn = serial.Serial(cfg.ARDUINO_PORT, cfg.ARDUINO_BAUD, timeout=1)
        time.sleep(2)   # Arduino resets on serial open; wait for it
        print(f"[hardware] Arduino connected on {cfg.ARDUINO_PORT}")
        return conn
    except Exception as e:
        print(f"[hardware] Could not connect to {cfg.ARDUINO_PORT}: {e}")
        return None


_arduino = _connect_arduino()


# ── Public API ───────────────────────────────────────────

def trigger_vibration(pattern: str = "short") -> bool:
    """
    Send a vibration pattern to the Arduino.

    Args:
        pattern: "short" | "long" | "double" | "sos"

    Returns:
        True if command was sent, False if hardware unavailable.

    Always fails silently — never raises.
    """
    if _arduino is None:
        return False

    try:
        if pattern == "sos":
            _send_sos()
        else:
            _send_pattern(pattern)
        return True
    except Exception as e:
        print(f"[hardware] Vibration failed: {e}")
        return False


def is_connected() -> bool:
    """Return True if Arduino serial connection is live."""
    return _arduino is not None


# ── Internal helpers ─────────────────────────────────────

def _send_pattern(pattern: str):
    """
    Look up pattern in VIBRATION_PATTERNS and send one command.
    Falls back to a 300ms buzz if pattern is unknown.
    """
    params = cfg.VIBRATION_PATTERNS.get(pattern)

    if params is None:
        # Unknown pattern — use legacy duration as a short buzz
        on_ms, off_ms, repeats = cfg.VIBRATION_DURATION_MS, 0, 1
    else:
        on_ms, off_ms, repeats = params

    _write(on_ms, off_ms, repeats)


def _send_sos():
    """
    SOS: · · ·  — — —  · · ·
    3 short (100ms) · pause · 3 long (600ms) · pause · 3 short (100ms)
    Sent as three sequential serial commands with Python-side gaps.
    """
    # 3 short
    _write(100, 80, 3)
    time.sleep(0.6)

    # 3 long
    _write(600, 150, 3)
    time.sleep(0.6)

    # 3 short
    _write(100, 80, 3)


def _write(on_ms: int, off_ms: int, repeats: int):
    """
    Format and send one vibration command over serial.
    Protocol: "V<on_ms>,<off_ms>,<repeats>\n"
    """
    command = f"V{on_ms},{off_ms},{repeats}\n".encode("utf-8")
    _arduino.write(command)
    _arduino.flush()

    # Wait for the motor to finish before returning
    # Total duration = (on_ms + off_ms) * repeats  +  small buffer
    total_ms = (on_ms + off_ms) * repeats
    time.sleep((total_ms / 1000) + 0.05)