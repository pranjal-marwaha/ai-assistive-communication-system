"""
speech_to_text.py

Current mode : chunk-based transcription.
Future TODO  : Replace with Google Cloud Speech streaming API.
               See: https://cloud.google.com/speech-to-text/docs/streaming-recognize
"""

import os
import tempfile
import subprocess
import speech_recognition as sr


SUPPORTED_LANGS = {
    "en":    "en-IN",
    "hi":    "hi-IN",
    "en-IN": "en-IN",
    "hi-IN": "hi-IN",
    "en-US": "en-US",
}

CHUNK_SECONDS = 3


def transcribe_audio(audio_file, lang: str = "en-IN") -> dict:
    """
    Convert uploaded audio blob → WAV → transcribe in 3-second chunks.
    """
    tmp_input     = None
    tmp_wav       = None
    resolved_lang = SUPPORTED_LANGS.get(lang, lang)

    try:
        suffix = _get_suffix(audio_file.filename)
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as f:
            tmp_input = f.name
            audio_file.save(tmp_input)

        tmp_wav = tmp_input.replace(suffix, ".wav")
        result  = subprocess.run(
            ["ffmpeg", "-y", "-i", tmp_input,
             "-ac", "1", "-ar", "16000", "-f", "wav", tmp_wav],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if result.returncode != 0:
            return {"error": "Audio conversion failed — is ffmpeg installed?"}

        transcript = _transcribe_in_chunks(tmp_wav, resolved_lang)
        if transcript is None:
            return {"error": "Could not understand audio — please speak clearly"}

        return {"transcript": transcript, "lang_used": resolved_lang}

    except sr.RequestError as e:
        return {"error": f"STT service unavailable: {e}"}
    except FileNotFoundError:
        return {"error": "ffmpeg not found — run: winget install ffmpeg"}
    except Exception as e:
        return {"error": f"Audio processing failed: {e}"}
    finally:
        for path in (tmp_input, tmp_wav):
            if path and os.path.exists(path):
                os.remove(path)


def _transcribe_in_chunks(wav_path: str, lang: str):
    """
    Read WAV file and transcribe in CHUNK_SECONDS windows.
    record() advances the file pointer automatically — no manual offset needed.
    Returns joined transcript string, or None if nothing understood.
    """
    recognizer = sr.Recognizer()
    recognizer.pause_threshold = 0.5
    parts = []

    with sr.AudioFile(wav_path) as source:
        total_duration = source.DURATION   # sr.AudioFile exposes this correctly

        offset = 0.0
        while offset < total_duration:
            duration = min(CHUNK_SECONDS, total_duration - offset)
            if duration < 0.3:
                break

            # record() reads `duration` seconds from current pointer position
            # No offset argument needed — pointer advances automatically
            audio_chunk = recognizer.record(source, duration=duration)
            offset += duration

            try:
                text = recognizer.recognize_google(audio_chunk, language=lang)
                if text:
                    parts.append(text)
            except sr.UnknownValueError:
                pass   # silence or noise — skip chunk
            except sr.RequestError:
                raise  # real network error — propagate

    return " ".join(parts) if parts else None


def _get_suffix(filename: str) -> str:
    if filename and "." in filename:
        return "." + filename.rsplit(".", 1)[1].lower()
    return ".webm"