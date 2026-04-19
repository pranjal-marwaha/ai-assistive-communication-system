import io
import base64
import asyncio

# ── Voice map: lang code → Microsoft Neural voice name ──
EDGE_VOICES = {
    "en":    "en-US-JennyNeural",
    "en-IN": "en-IN-NeerjaNeural",
    "en-US": "en-US-JennyNeural",
    "hi":    "hi-IN-SwaraNeural",
    "hi-IN": "hi-IN-SwaraNeural",
}

DEFAULT_VOICE = "en-US-JennyNeural"


def synthesize_speech(text: str, lang: str = "en") -> dict:
    """
    Convert text to speech. Tries edge-tts first (neural quality),
    falls back to gTTS if edge-tts is unavailable or fails.
    """
    if not text or not text.strip():
        return {"error": "Text is empty"}

    result = _synthesize_edge(text, lang)
    if "error" not in result:
        return result

    print(f"[tts] edge-tts failed ({result['error']}), falling back to gTTS")
    return _synthesize_gtts(text, lang)


# ── Primary: edge-tts ────────────────────────────────────

def _synthesize_edge(text: str, lang: str) -> dict:
    try:
        import edge_tts  # noqa: F401 — soft import check
    except ImportError:
        return {"error": "edge-tts not installed"}

    voice = EDGE_VOICES.get(lang, DEFAULT_VOICE)

    try:
        # Create a fresh event loop each call — safe inside Flask threads
        loop = asyncio.new_event_loop()
        try:
            mp3_bytes = loop.run_until_complete(_edge_tts_bytes(text, voice))
        finally:
            loop.close()

        return {
            "audio_b64": base64.b64encode(mp3_bytes).decode("utf-8"),
            "engine":    "edge-tts",
            "voice":     voice,
        }
    except Exception as e:
        return {"error": str(e)}


async def _edge_tts_bytes(text: str, voice: str) -> bytes:
    import edge_tts
    communicate = edge_tts.Communicate(text, voice)
    chunks = []
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            chunks.append(chunk["data"])
    if not chunks:
        raise RuntimeError("edge-tts returned no audio data")
    return b"".join(chunks)


# ── Fallback: gTTS ───────────────────────────────────────

def _synthesize_gtts(text: str, lang: str) -> dict:
    from gtts import gTTS
    from config.settings import TTS_SLOW

    gtts_lang = lang.split("-")[0] if "-" in lang else lang
    if gtts_lang not in ("en", "hi"):
        gtts_lang = "en"

    try:
        tts    = gTTS(text=text, lang=gtts_lang, slow=TTS_SLOW)
        buffer = io.BytesIO()
        tts.write_to_fp(buffer)
        buffer.seek(0)
        return {
            "audio_b64": base64.b64encode(buffer.read()).decode("utf-8"),
            "engine":    "gtts",
        }
    except Exception as e:
        return {"error": f"gTTS also failed: {e}"}