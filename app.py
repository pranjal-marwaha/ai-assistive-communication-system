import hashlib
from flask import Flask, render_template, request, jsonify
from modules.speech_to_text import transcribe_audio
from modules.text_to_speech import synthesize_speech
from modules.translation import translate_to_hindi, translate_to_english
from modules.hardware import trigger_vibration, is_connected

# Optional compression — install with: pip install flask-compress
try:
    from flask_compress import Compress
    _COMPRESS_AVAILABLE = True
except ImportError:
    _COMPRESS_AVAILABLE = False

app = Flask(__name__, static_folder='static', template_folder='templates')

# ── Compression ──────────────────────────────────────────
if _COMPRESS_AVAILABLE:
    app.config['COMPRESS_MIMETYPES'] = [
        'application/json',
        'text/html',
        'text/css',
        'application/javascript',
    ]
    app.config['COMPRESS_LEVEL'] = 6   # 1–9; 6 is CPU/ratio sweet spot
    Compress(app)

# ── TTS in-memory cache ──────────────────────────────────
# Key: sha256(text + lang) → Value: synthesize_speech() result dict
# Simple dict — survives the process lifetime, resets on restart.
# For production, swap with Redis or diskcache.
_tts_cache: dict[str, dict] = {}
TTS_CACHE_MAX = 100   # evict oldest when over this size


def _tts_cache_key(text: str, lang: str) -> str:
    return hashlib.sha256(f"{lang}:{text}".encode()).hexdigest()


def _tts_cached(text: str, lang: str) -> dict:
    """Return cached TTS result, or synthesize and cache it."""
    key = _tts_cache_key(text, lang)
    if key in _tts_cache:
        return {**_tts_cache[key], "cached": True}

    result = synthesize_speech(text, lang=lang)
    if "error" not in result:
        # Evict oldest entry if at capacity
        if len(_tts_cache) >= TTS_CACHE_MAX:
            oldest = next(iter(_tts_cache))
            del _tts_cache[oldest]
        _tts_cache[key] = result

    return result


# ── CORS helper ──────────────────────────────────────────
def _add_cors(response):
    """Allow requests from any origin (useful for local dev / mobile testing)."""
    response.headers['Access-Control-Allow-Origin']  = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    return response


@app.after_request
def after_request(response):
    return _add_cors(response)


@app.route('/', defaults={'path': ''}, methods=['OPTIONS'])
@app.route('/<path:path>', methods=['OPTIONS'])
def options_handler(path):
    """Handle CORS preflight requests."""
    return _add_cors(jsonify({}))


# ════════════════════════════════════════════════════════
#  Routes
# ════════════════════════════════════════════════════════

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/touch")
def touch():
    return render_template("touch.html")


@app.route("/api/haptic", methods=["POST"])
def haptic():
    """POST { signal } → trigger Arduino vibration pattern."""
    data   = request.get_json()
    signal = data.get("signal", "short") if data else "short"

    valid = {"short", "long", "double", "sos"}
    if signal not in valid:
        return jsonify({"error": f"Unknown signal '{signal}'. Use: {sorted(valid)}"}), 400

    sent = trigger_vibration(signal)
    return jsonify({"status": "sent" if sent else "no_hardware", "signal": signal})


@app.route("/api/stt", methods=["POST"])
def speech_to_text():
    """
    POST multipart/form-data with 'audio' file + optional 'lang'.
    Returns { transcript, transcript_en, transcript_hi, lang_used }.
    """
    if "audio" not in request.files:
        return jsonify({"error": "No audio file provided"}), 400

    audio_file = request.files["audio"]
    lang       = request.form.get("lang", "en-IN")

    stt_result = transcribe_audio(audio_file, lang=lang)
    if "error" in stt_result:
        return jsonify(stt_result), 500

    transcript = stt_result["transcript"]
    lang_used  = stt_result["lang_used"]

    if lang_used.startswith("hi"):
        transcript_hi = transcript
        transcript_en = translate_to_english(transcript).get("translated", transcript)
    else:
        transcript_en = transcript
        transcript_hi = translate_to_hindi(transcript).get("translated", "")

    return jsonify({
        "transcript":    transcript,
        "transcript_en": transcript_en,
        "transcript_hi": transcript_hi,
        "lang_used":     lang_used,
    })


@app.route("/api/tts", methods=["POST"])
def text_to_speech():
    """
    POST { text, lang } → { audio_b64, engine, cached? }.
    Repeated phrases are served from in-memory cache.
    """
    data = request.get_json()
    if not data or "text" not in data:
        return jsonify({"error": "No text provided"}), 400

    text = data["text"].strip()
    if not text:
        return jsonify({"error": "Text is empty"}), 400

    lang   = data.get("lang", "en")
    result = _tts_cached(text, lang)

    if "error" in result:
        return jsonify(result), 500

    trigger_vibration("short")
    return jsonify(result)


@app.route("/api/translate", methods=["POST"])
def translate():
    """POST { text, target: "hi"|"en" } → { translated }."""
    data = request.get_json()
    if not data or "text" not in data:
        return jsonify({"error": "No text provided"}), 400

    target = data.get("target", "hi")
    result = translate_to_hindi(data["text"]) if target == "hi" else translate_to_english(data["text"])

    if "error" in result:
        return jsonify(result), 500

    return jsonify(result)


@app.route("/api/status", methods=["GET"])
def status():
    """Health check — reports hardware state and cache stats."""
    return jsonify({
        "ok":            True,
        "hardware":      is_connected(),
        "tts_cache_size": len(_tts_cache),
        "compression":   _COMPRESS_AVAILABLE,
    })


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)