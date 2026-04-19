from googletrans import Translator

_translator = Translator()


def translate_to_hindi(text: str) -> dict:
    return _translate(text, dest="hi")


def translate_to_english(text: str) -> dict:
    return _translate(text, dest="en")


def _translate(text: str, dest: str) -> dict:
    if not text or not text.strip():
        return {"error": "Empty text provided"}
    try:
        result = _translator.translate(text, dest=dest)

        # googletrans 4.0.0rc1 sometimes returns None on .text
        translated = getattr(result, "text", None)
        if not translated:
            raise ValueError("Empty translation result")

        return {
            "translated": translated,
            "src_lang":   getattr(result, "src", "unknown"),
            "dest_lang":  dest,
        }
    except Exception as e:
        return {"error": f"Translation failed: {e}"}