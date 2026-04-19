# AI Assistive Communication System

A multimodal AI-based communication system designed for differently-abled users.

## 🔹 Features

- 🎤 Speech-to-Text (English + Hindi subtitles)
- 🔊 Text-to-Speech (Neural voices via edge-tts, fallback gTTS)
- 🌐 Real-time translation (English ↔ Hindi)
- ♿ Accessibility Mode (Touch UI for special users)
- 📳 Arduino Haptic Feedback (optional hardware)
- ⚡ Low-latency chunk-based audio processing

## 🔹 Tech Stack

- Python (Flask)
- SpeechRecognition
- pydub
- edge-tts
- gTTS
- deep-translator
- pyserial
- JavaScript (Vanilla)
## 🔹 How to Run

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python app.py
## 🔹 Project Structure
