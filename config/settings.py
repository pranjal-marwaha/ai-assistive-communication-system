import os

# --- Speech Recognition ---
STT_LANGUAGE    = "en-US"   # BCP-47 language tag for Google STT
STT_TIMEOUT     = 10        # Max seconds to wait for speech
STT_PHRASE_LIMIT = 15       # Max seconds per phrase

# --- Text to Speech ---
TTS_LANGUAGE = "en"         # gTTS fallback language code
TTS_SLOW     = False        # Slower speech for clarity

# --- Audio Processing ---
UPLOAD_FOLDER      = os.path.join(os.path.dirname(__file__), "..", "temp_audio")
ALLOWED_EXTENSIONS = {"webm", "wav", "ogg"}

# --- Hardware (Arduino) ---
# Set ARDUINO_PORT to your port string to enable vibration motor.
# Leave as None to disable hardware silently.
#   Windows example : ARDUINO_PORT = "COM3"
#   Linux example   : ARDUINO_PORT = "/dev/ttyUSB0"
#   Mac example     : ARDUINO_PORT = "/dev/cu.usbmodem14101"
ARDUINO_PORT = None         # ← set your COM port here
ARDUINO_BAUD = 9600

# Vibration patterns — each tuple is (on_ms, off_ms) repeated N times.
# The Arduino receives a command string: "V<on_ms>,<off_ms>,<repeats>\n"
VIBRATION_PATTERNS = {
    #          on_ms  off_ms  repeats
    "short":  (200,   0,      1),   # single short buzz
    "long":   (800,   0,      1),   # single long buzz
    "double": (250,   200,    2),   # two quick pulses
    "sos":    None,                 # handled specially — see hardware.py
}

# Legacy fallback (used if pattern not found)
VIBRATION_DURATION_MS = 300