# AGENTS.md - Colsubsidio Vision Voice

## Qué es este proyecto

App de análisis de imágenes con voz para inventario. La app muestra la cámara en pantalla completa, analiza imágenes con IA (Gemini/OpenRouter), y habla los resultados. El usuario puede confirmar o corregir por voz.

## Paleta de Colores Colsubsidio

| Color | Hex | Uso |
|---|---|---|
| Amarillo Colsubsidio | `#FFD30F` | Botones principales, acentos, checkbox, spinner, speaking waves |
| Azul Colsubsidio | `#001F5B` | Botón captura, botón de voz (Hablar), headers |
| Grafito (Oscuro) | `#202124` | Fondo general, overlays, cards |
| Blanco | `#FFFFFF` | Texto principal |

## Arquitectura

```
colsubsidio_estable/
├── frontend/
│   └── index.html          ← App completa (1 archivo HTML, todo inline)
├── backend/
│   ├── main.py             ← FastAPI + CORS + 4 endpoints
│   ├── ai_engine.py        ← Gemini → fallback OpenRouter
│   ├── voice_engine.py     ← ElevenLabs STT + TTS
│   └── requirements.txt    ← fastapi, uvicorn, httpx, python-dotenv
└── .env.example
```

## Tech Stack

| Componente | Tecnología |
|---|---|
| Frontend | HTML + Tailwind CDN + JavaScript vanilla |
| Backend | Python 3.12 + FastAPI |
| Análisis IA | Google Gemini 2.5 Flash (gratis) |
| Fallback IA | OpenRouter - nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free |
| Speech-to-Text | ElevenLabs Scribe v1 |
| Text-to-Speech | ElevenLabs eleven_multilingual_v2 |
| Hosting Backend | Render (Web Service) |
| Hosting Frontend | https://colsus.monokuko.com (Caddy/traefik) |

## API Keys

| Servicio | Key | Modelo |
|---|---|---|
| Gemini | `TU_GEMINI_API_KEY` | gemini-2.5-flash |
| OpenRouter | `TU_OPENROUTER_API_KEY` | nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free |
| ElevenLabs | `TU_ELEVENLABS_API_KEY` | scribe_v1 + eleven_multilingual_v2 |

## Variables de Entorno (para Render)

```bash
GEMINI_API_KEY=tu_api_key_aqui
GEMINI_MODEL=gemini-2.5-flash
OPENROUTER_API_KEY=tu_api_key_aqui
OPENROUTER_MODEL=nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free
ELEVENLABS_API_KEY=tu_api_key_aqui
ELEVENLABS_VOICE_ID=EXAVITQu4vr4xnSDxMaL
ELEVENLABS_STT_MODEL=scribe_v1
ELEVENLABS_TTS_MODEL=eleven_multilingual_v2
API_HOST=0.0.0.0
API_PORT=8000
FRONTEND_URL=https://colsus.monokuko.com
```

## Endpoints del Backend

| Método | Ruta | Descripción | Body |
|---|---|---|---|
| GET | `/health` | Estado del sistema | — |
| POST | `/analyze` | Analiza imagen con IA | `{"image": "base64..."}` |
| POST | `/speak` | Text-to-speech | `{"text": "..."}` |
| POST | `/transcribe` | Speech-to-text | multipart/form-data (audio.webm) |
| GET | `/` | Sirve el frontend HTML | — |

### Respuesta de `/analyze`

```json
{
  "description": "Se ven 3 sacos de arroz y 2 cajas de fideos",
  "objects": [
    {"name": "arroz", "quantity": 3, "confidence": 0.95},
    {"name": "fideos", "quantity": 2, "confidence": 0.88}
  ],
  "confidence": 0.92,
  "suggestion": "Verificar conteo con inventario actual",
  "_provider": "gemini"
}
```

## Flujo de la App

1. **App abre** → Cámara activa en vivo
2. **Desktop** → Marco de teléfono centrado (390×844px, bordes redondeados 40px)
3. **Móvil** → Pantalla completa (100dvh)
4. **Usuario toca captura** → Se toma foto
5. **Spinner** → "Analizando imagen..."
6. **La app habla** → ElevenLabs TTS con el resultado
7. **Checklist editable** → Pantalla completa con checkbox + cantidad editable por producto
8. **Botones** → Confirmar / Reintentar / Hablar (STT) + "Agregar producto"
9. **Si toca Hablar** → Modal de grabación → STT → procesa comando
10. **Modo Auto** → Captura cada 5 segundos. Si detecta productos → para y muestra checklist

## Flujo de Voz

### Pantalla principal
- Botón "Hablar" (micrófono amarillo) → click para iniciar grabación
- Usuario dice inventario: "3 arroz, 2 leche"
- Se crea checklist directamente sin usar cámara

### En checklist
- Botón "Hablar" en resultados → agrega items por voz
- Usuario dice: "faltan 2 fideos" → se agrega al checklist
- También puede decir "confirmar" o "reintentar"

## Responsive Design

### Desktop (ratón + pantalla ≥1024px)
- Marco de teléfono: 390×844px, centrado
- Bordes redondeados: 40px
- Sombra: 0 25px 80px rgba(0,0,0,0.5)
- Detectado con: `@media (hover: hover) and (pointer: fine) and (min-width: 1024px)`

### Móvil/Tablet (táctil)
- Pantalla completa: 100vw × 100dvh
- Sin bordes redondeados
- Safe area insets para notch/home indicator
- Detectado con: `@media (hover: none) and (pointer: coarse)`

## Cómo replicar el proyecto

### Opción 1: Render (recomendado)

1. Subir la carpeta `colsubsidio_estable` a un repo de Git
2. En Render, crear un **Web Service**
3. Configurar:
   - **Runtime:** Python
   - **Build Command:** `pip install -r backend/requirements.txt`
   - **Start Command:** `cd backend && python main.py`
   - **Port:** 8000
4. Agregar las variables de entorno
5. Desplegar

### Opción 2: Local

```bash
cd colsubsidio_estable/backend
pip install -r requirements.txt
cp ../.env.example .env
# Editar .env con tus keys
python main.py
# Abrir http://localhost:8000
```

### Opción 3: Docker

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ .
COPY frontend/ ../frontend/
EXPOSE 8000
CMD ["python", "main.py"]
```

## Archivos clave y qué hacen

### `backend/main.py`
- FastAPI app con CORS
- sirve el frontend HTML en `/`
- 4 endpoints: health, analyze, speak, transcribe
- Variables: FRONTEND_URL para CORS

### `backend/ai_engine.py`
- `analyze_image(base64)` → intenta Gemini primero, fallback OpenRouter
- Prompt: describe qué ves, objetos detectados, confianza, sugerencia
- Retorna dict con description, objects, confidence, suggestion, _provider

### `backend/voice_engine.py`
- `transcribir(audio_bytes)` → ElevenLabs STT (scribe_v1, idioma spa)
- `sintetizar(texto)` → ElevenLabs TTS (eleven_multilingual_v2)
- `health()` → bool indica si la API key está configurada

### `frontend/index.html`
- App completa en 1 solo archivo HTML
- Tailwind CDN (sin build)
- JavaScript vanilla (sin framework)
- Cámara con `navigator.mediaDevices.getUserMedia`
- TTS: fetch a `/speak`, fallback a Web Speech API
- STT: MediaRecorder → blob → fetch a `/transcribe`

## APIs gratuitas usadas

### Gemini (Google)
- Gratis en https://aistudio.google.com/apikey
- 1500 requests/día, 10 RPM
- Soporte de imágenes incluido
- Modelo: gemini-2.5-flash

### OpenRouter
- Gratis con registro en https://openrouter.ai
- Modelo con visión: nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free
- 256K context, acepta imágenes
- Rate limit: más generoso que Gemini

### ElevenLabs
- Free tier disponible
- STT: scribe_v1
- TTS: eleven_multilingual_v2
- Voice ID default: EXAVITQu4vr4xnSDxMaL

## Notas importantes

- **HTTPS obligatorio** para micrófono en el navegador
- **CORS** debe incluir el dominio del frontend
- **La voz es secundaria** - si falla, el resto funciona
- **Fallback de TTS** - si ElevenLabs falla, usa Web Speech API del navegador
- **El backend sirve el frontend** - no necesita hosting separado
- **Safe area insets** - respeta el notch y barra del sistema en móviles

## Dependencias

### Backend (requirements.txt)
```
fastapi==0.115.0
uvicorn==0.30.0
httpx==0.27.0
python-dotenv==1.0.1
python-multipart==0.0.9
```

### Frontend (CDN, sin instalación)
- Tailwind CSS: `https://cdn.tailwindcss.com`
- Google Fonts: Inter
