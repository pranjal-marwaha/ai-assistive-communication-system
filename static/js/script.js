/* ══════════════════════════════════════════════════════
   AI Assistive Communication — script.js
   ══════════════════════════════════════════════════════ */

const MAX_CHARS = 500;

// ── DOM refs ────────────────────────────────────────────
const btnRecord      = document.getElementById('btn-record');
const transcriptEl   = document.getElementById('transcript');        // EN box
const transcriptHiEl = document.getElementById('transcript-hi');     // HI box
const pulseRing      = document.getElementById('pulse-ring');
const statusDot      = document.getElementById('status-dot');
const statusText     = document.getElementById('status-text');
const ttsInput       = document.getElementById('tts-input');
const btnSpeak       = document.getElementById('btn-speak');
const ttsHistory     = document.getElementById('tts-history');
const charCount      = document.getElementById('char-count');
const toast          = document.getElementById('toast');
const btnClearStt    = document.getElementById('btn-clear-stt');
const btnClearTts    = document.getElementById('btn-clear-tts');

// ── State ───────────────────────────────────────────────
let mediaRecorder = null;
let audioChunks   = [];
let isRecording   = false;
let stream        = null;

// ════════════════════════════════════════════════════════
//  SECTION 1 — STT (Deaf users: hear → read)
// ════════════════════════════════════════════════════════

btnRecord.addEventListener('click', toggleRecording);

async function toggleRecording() {
  isRecording ? stopRecording() : await startRecording();
}

async function startRecording() {
  try {
    stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  } catch {
    showToast('Microphone access denied', 'error');
    return;
  }

  audioChunks = [];
  const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
    ? 'audio/webm;codecs=opus'
    : 'audio/webm';

  mediaRecorder = new MediaRecorder(stream, { mimeType });
  mediaRecorder.ondataavailable = e => audioChunks.push(e.data);
  mediaRecorder.onstop = sendAudioToServer;
  mediaRecorder.start(100);

  isRecording = true;
  btnRecord.classList.add('recording');
  btnRecord.textContent = '⏹ Stop Recording';
  pulseRing.classList.add('active');
  transcriptEl.classList.add('listening');
  setStatus('Listening…', 'active');
}

function stopRecording() {
  if (mediaRecorder && mediaRecorder.state !== 'inactive') mediaRecorder.stop();
  stream?.getTracks().forEach(t => t.stop());

  isRecording = false;
  btnRecord.classList.remove('recording');
  btnRecord.textContent = '🎙 Start Recording';
  pulseRing.classList.remove('active');
  transcriptEl.classList.remove('listening');
  setStatus('Processing…');
}

async function sendAudioToServer() {
  const lang = document.querySelector('input[name="lang"]:checked')?.value || 'en-IN';

  const blob = new Blob(audioChunks, { type: 'audio/webm' });
  const formData = new FormData();
  formData.append('audio', blob, 'recording.webm');
  formData.append('lang', lang);

  try {
    const res  = await fetch('/api/stt', { method: 'POST', body: formData });
    const data = await res.json();

    if (data.error) {
      showToast(data.error, 'error');
      setStatus('Ready');
      return;
    }

    appendSubtitle(transcriptEl,   data.transcript_en, 'en');
    appendSubtitle(transcriptHiEl, data.transcript_hi, 'hi');

    setStatus('Ready');
    showToast('Transcribed', 'success');
  } catch {
    showToast('Connection error', 'error');
    setStatus('Ready');
  }
}

function appendSubtitle(box, text, lang) {
  if (!text) return;

  const placeholder = box.querySelector('.placeholder');
  if (placeholder) placeholder.remove();

  const entry = document.createElement('div');
  entry.className = 'transcript-entry';
  entry.dataset.lang = lang;
  entry.innerHTML = `
    <div class="ts">${timestamp()}</div>
    <div class="text">${escapeHtml(text)}</div>
  `;
  box.appendChild(entry);
  box.scrollTop = box.scrollHeight;
}

btnClearStt.addEventListener('click', () => {
  transcriptEl.innerHTML   = '<p class="placeholder">English subtitles will appear here…</p>';
  transcriptHiEl.innerHTML = '<p class="placeholder">हिन्दी उपशीर्षक यहाँ दिखेगा…</p>';
});

// ════════════════════════════════════════════════════════
//  SECTION 2 — TTS (Mute users: type → speak)
// ════════════════════════════════════════════════════════

ttsInput.addEventListener('input', updateCharCount);
ttsInput.addEventListener('keyup', updateCharCount);
btnSpeak.addEventListener('click', speakText);

ttsInput.addEventListener('keydown', e => {
  if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') speakText();
});

function updateCharCount() {
  const len = ttsInput.value.length;
  charCount.textContent = `${len} / ${MAX_CHARS}`;
  charCount.classList.toggle('near-limit', len > MAX_CHARS * 0.85);
  btnSpeak.disabled = len === 0 || len > MAX_CHARS;
}

async function speakText() {
  const text = ttsInput.value.trim();
  if (!text) return;

  btnSpeak.disabled = true;
  btnSpeak.textContent = '⏳ Generating…';

  try {
    const res  = await fetch('/api/tts', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, lang: 'en' }), // ✅ ONLY ADDED LINE HERE
    });
    const data = await res.json();

    if (data.error) { showToast(data.error, 'error'); return; }

    playBase64Audio(data.audio_b64);
    addTtsHistoryEntry(text);
    showToast('Speaking', 'success');
  } catch {
    showToast('Connection error', 'error');
  } finally {
    btnSpeak.disabled = false;
    btnSpeak.textContent = '🔊 Speak Text';
  }
}

function playBase64Audio(b64) {
  const audio = new Audio(`data:audio/mp3;base64,${b64}`);
  audio.play().catch(() => showToast('Audio playback blocked by browser', 'error'));
}

function addTtsHistoryEntry(text) {
  const entry = document.createElement('div');
  entry.className = 'tts-entry';
  entry.textContent = text.length > 80 ? text.slice(0, 80) + '…' : text;
  entry.title = 'Click to re-speak';
  entry.addEventListener('click', () => {
    ttsInput.value = text;
    updateCharCount();
    speakText();
  });
  ttsHistory.prepend(entry);
}

btnClearTts.addEventListener('click', () => {
  ttsHistory.innerHTML = '';
  ttsInput.value = '';
  updateCharCount();
});

// ════════════════════════════════════════════════════════
//  SECTION 3 — UI helpers
// ════════════════════════════════════════════════════════

function setStatus(text, dotClass = '') {
  statusText.textContent = text;
  statusDot.className = 'status-dot' + (dotClass ? ' ' + dotClass : '');
}

let toastTimer = null;
function showToast(msg, type = '') {
  toast.textContent = msg;
  toast.className = 'show' + (type ? ' ' + type : '');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { toast.className = ''; }, 2800);
}

function timestamp() {
  return new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

function escapeHtml(str) {
  return str.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

// ── Init ─────────────────────────────────────────────────
updateCharCount();
setStatus('Ready');