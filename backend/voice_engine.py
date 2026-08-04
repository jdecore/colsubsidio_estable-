"""ElevenLabs STT + TTS engine + Qwen3/Cerebras correction."""
from __future__ import annotations

import logging
import os

import httpx

log = logging.getLogger(__name__)

ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID = os.environ.get("ELEVENLABS_VOICE_ID", "EXAVITQu4vr4xnSDxMaL")
ELEVENLABS_STT_MODEL = os.environ.get("ELEVENLABS_STT_MODEL", "scribe_v2")
ELEVENLABS_TTS_MODEL = os.environ.get("ELEVENLABS_TTS_MODEL", "eleven_flash_v2_5")

CEREBRAS_API_KEY = os.environ.get("CEREBRAS_API_KEY", "")
CEREBRAS_MODEL = os.environ.get("CEREBRAS_MODEL", "qwen3-235b-a22b-instruct-250")

_STT_URL = "https://api.elevenlabs.io/v1/speech-to-text"
_TTS_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
_CEREBRAS_URL = "https://api.cerebras.ai/v1/chat/completions"
_TIMEOUT = 60


def _has_key() -> bool:
    return bool(ELEVENLABS_API_KEY)


async def transcribir(audio_bytes: bytes, filename: str = "audio.webm") -> str:
    """STT: audio bytes -> texto."""
    if not _has_key():
        raise RuntimeError("ELEVENLABS_API_KEY no configurada")

    if len(audio_bytes) < 5000:
        log.warning("STT rechazado: audio muy pequeño (%d bytes)", len(audio_bytes))
        raise ValueError("Audio demasiado corto, por favor mantén presionado el botón al hablar.")

    content_type = "audio/webm"
    if filename.endswith(".ogg"):
        content_type = "audio/ogg"
    elif filename.endswith(".mp4") or filename.endswith(".m4a"):
        content_type = "audio/mp4"
    elif filename.endswith(".wav"):
        content_type = "audio/wav"

    log.info(
        "STT request: model=%s, lang=es, file=%s, content_type=%s, size=%d bytes",
        ELEVENLABS_STT_MODEL, filename, content_type, len(audio_bytes),
    )

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            _STT_URL,
            headers={"xi-api-key": ELEVENLABS_API_KEY},
            data={
                "model_id": ELEVENLABS_STT_MODEL,
                "language_code": "es",
            },
            files={"file": (filename, audio_bytes, content_type)},
            timeout=_TIMEOUT,
        )

    if resp.status_code >= 400:
        raise RuntimeError(f"ElevenLabs STT {resp.status_code}: {resp.text[:500]}")

    result = resp.json()
    text = (result.get("text") or "").strip()
    lang_detected = result.get("language_code", "?")
    log.info("STT result: lang=%s, text=%r", lang_detected, text)
    return text


async def sintetizar(texto: str) -> bytes:
    """TTS: texto -> audio mpeg bytes."""
    if not _has_key():
        raise RuntimeError("ELEVENLABS_API_KEY no configurada")
    async with httpx.AsyncClient() as client:
        resp = await client.post(
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


async def corregir_transcripcion(texto: str) -> str:
    """Corrige texto transcrito con Qwen3/Cerebras. Si falla, retorna el original."""
    if not CEREBRAS_API_KEY:
        return texto

    prompt = (
        "Eres un corrector de transcripciones de voz para inventario de supermercado. "
        "El usuario está hablando productos y cantidades. "
        "Corrige errores ortográficos, completas palabras cortadas, y normalizas números. "
        "Res SOLO el texto corregido, sin explicaciones ni comillas.\n\n"
        f"Transcripción: {texto}"
    )

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                _CEREBRAS_URL,
                headers={
                    "Authorization": f"Bearer {CEREBRAS_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": CEREBRAS_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 200,
                    "temperature": 0.1,
                },
                timeout=15,
            )

        if resp.status_code == 429:
            log.warning("Cerebras rate limit, usando texto original: %s", texto)
            return texto

        resp.raise_for_status()
        data = resp.json()
        corrected = data["choices"][0]["message"]["content"].strip().strip('"').strip("'")
        log.info("Qwen3 correction: %r -> %r", texto, corrected)
        return corrected if corrected else texto

    except Exception as e:
        log.warning("Cerebras error (%s), usando texto original: %s", e, texto)
        return texto


def health() -> dict:
    return {
        "elevenlabs": _has_key(),
        "cerebras": bool(CEREBRAS_API_KEY),
    }
