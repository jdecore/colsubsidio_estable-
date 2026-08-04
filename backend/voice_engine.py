"""ElevenLabs STT + TTS engine."""
from __future__ import annotations

import os

import httpx

ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID = os.environ.get("ELEVENLABS_VOICE_ID", "EXAVITQu4vr4xnSDxMaL")
ELEVENLABS_STT_MODEL = os.environ.get("ELEVENLABS_STT_MODEL", "scribe_v1")
ELEVENLABS_TTS_MODEL = os.environ.get("ELEVENLABS_TTS_MODEL", "eleven_multilingual_v2")

_STT_URL = "https://api.elevenlabs.io/v1/speech-to-text"
_TTS_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
_TIMEOUT = 60


def _has_key() -> bool:
    return bool(ELEVENLABS_API_KEY)


def transcribir(audio_bytes: bytes, filename: str = "audio.webm") -> str:
    """STT: audio bytes -> texto."""
    if not _has_key():
        raise RuntimeError("ELEVENLABS_API_KEY no configurada")
    resp = httpx.post(
        _STT_URL,
        headers={"xi-api-key": ELEVENLABS_API_KEY},
        data={
            "model_id": ELEVENLABS_STT_MODEL,
            "language_code": "spa",
        },
        files={"file": (filename, audio_bytes, "audio/webm")},
        timeout=_TIMEOUT,
    )
    resp.raise_for_status()
    return (resp.json().get("text") or "").strip()


def sintetizar(texto: str) -> bytes:
    """TTS: texto -> audio mpeg bytes."""
    if not _has_key():
        raise RuntimeError("ELEVENLABS_API_KEY no configurada")
    resp = httpx.post(
        _TTS_URL.format(voice_id=ELEVENLABS_VOICE_ID),
        headers={
            "xi-api-key": ELEVENLABS_API_KEY,
            "accept": "audio/mpeg",
        },
        json={
            "text": texto,
            "model_id": ELEVENLABS_TTS_MODEL,
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75,
            },
        },
        timeout=_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.content


def health() -> bool:
    return _has_key()
