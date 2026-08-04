"""AI engine: Gemini -> fallback OpenRouter."""
from __future__ import annotations

import base64
import json
import os

import httpx

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.environ.get(
    "OPENROUTER_MODEL",
    "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free",
)

_GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "{model}:generateContent?key={key}"
)
_OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

_PROMPT = """Inventario: devuelve JSON con {"description":"breve","objects":[{"name":"","quantity":1,"confidence":0.9}],"confidence":0.9,"suggestion":""}. Sin productos: {"description":"...","objects":[],"confidence":0,"suggestion":""}. Solo JSON."""


def _analyze_gemini(image_b64: str) -> dict | None:
    """Intenta analizar con Gemini."""
    if not GEMINI_API_KEY:
        return None

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": _PROMPT},
                    {
                        "inline_data": {
                            "mime_type": "image/jpeg",
                            "data": image_b64,
                        }
                    },
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.3,
            "maxOutputTokens": 1024,
        },
    }

    try:
        resp = httpx.post(
            _GEMINI_URL.format(model=GEMINI_MODEL, key=GEMINI_API_KEY),
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        text = text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1]
        if text.endswith("```"):
            text = text.rsplit("```", 1)[0]
        return json.loads(text)
    except Exception:
        return None


def _analyze_openrouter(image_b64: str) -> dict | None:
    """Fallback: analiza con OpenRouter."""
    if not OPENROUTER_API_KEY:
        return None

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": _PROMPT},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_b64}"
                        },
                    },
                ],
            }
        ],
        "max_tokens": 1024,
        "temperature": 0.3,
    }

    try:
        resp = httpx.post(
            _OPENROUTER_URL,
            headers=headers,
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        text = data["choices"][0]["message"]["content"]
        text = text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1]
        if text.endswith("```"):
            text = text.rsplit("```", 1)[0]
        return json.loads(text)
    except Exception:
        return None


def analyze_image(image_b64: str) -> dict:
    """Analiza imagen con Gemini, fallback a OpenRouter."""
    result = _analyze_gemini(image_b64)
    if result:
        result["_provider"] = "gemini"
        return result

    result = _analyze_openrouter(image_b64)
    if result:
        result["_provider"] = "openrouter"
        return result

    return {
        "description": "No se pudo analizar la imagen. Verifica las API keys.",
        "objects": [],
        "confidence": 0.0,
        "suggestion": "Intenta de nuevo o verifica tu conexion.",
        "_provider": "none",
    }


def health() -> dict:
    return {
        "gemini": bool(GEMINI_API_KEY),
        "openrouter": bool(OPENROUTER_API_KEY),
    }
