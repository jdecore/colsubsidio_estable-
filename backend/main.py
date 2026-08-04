"""Colsus Vision Voice - FastAPI backend."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

# Load .env from backend directory
_env_path = Path(__file__).parent / ".env"
if _env_path.exists():
    load_dotenv(_env_path)

from ai_engine import analyze_image, health as ai_health
from voice_engine import sintetizar, transcribir, health as voice_health

FRONTEND_URL = os.environ.get("FRONTEND_URL", "https://colsus.monokuko.com")

app = FastAPI(title="Colsus Vision Voice", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        FRONTEND_URL,
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "*",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Models ---

class AnalyzeRequest(BaseModel):
    image: str  # base64 encoded image (no data: prefix)


class SpeakRequest(BaseModel):
    text: str


# --- Endpoints ---

@app.get("/health")
def health():
    ai = ai_health()
    voice = voice_health()
    return {
        "ok": True,
        "gemini": ai.get("gemini", False),
        "openrouter": ai.get("openrouter", False),
        "elevenlabs": voice,
    }


@app.post("/analyze")
def analyze(req: AnalyzeRequest):
    """Analyze an image using Gemini (fallback OpenRouter)."""
    try:
        result = analyze_image(req.image)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/speak")
async def speak(req: SpeakRequest):
    """Text-to-speech using ElevenLabs."""
    try:
        audio = await sintetizar(req.text)
        return Response(content=audio, media_type="audio/mpeg")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"TTS error: {e}")


@app.post("/transcribe")
async def transcribe(file: UploadFile = File(...)):
    """Speech-to-text using ElevenLabs."""
    import logging
    log = logging.getLogger(__name__)
    try:
        audio = await file.read()
        log.info("Transcribe received: filename=%s, size=%d bytes", file.filename, len(audio))
        texto = await transcribir(audio, file.filename or "audio.webm")
        log.info("Transcribe result: %r", texto)
        return {"text": texto}
    except Exception as e:
        log.error("Transcribe error: %s", e)
        raise HTTPException(status_code=502, detail=f"STT error: {e}")


# Serve frontend
_frontend_dir = Path(__file__).parent.parent / "frontend"

@app.get("/")
async def serve_index():
    index = _frontend_dir / "index.html"
    if index.exists():
        return FileResponse(index)
    return {"message": "Backend running. Frontend not found."}


if __name__ == "__main__":
    import uvicorn

    host = os.environ.get("API_HOST", "0.0.0.0")
    port = int(os.environ.get("API_PORT", "8000"))
    uvicorn.run(app, host=host, port=port)
