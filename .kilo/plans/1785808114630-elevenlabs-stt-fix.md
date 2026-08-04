# Plan: Reparar STT de ElevenLabs (la voz/TTS sí funciona)

## Contexto
El usuario confirma: **TTS funciona, pero STT no**. El TTS usa ElevenLabs y va bien, así que
la API key y la red están correctas. El fallo está aislado en el speech-to-text.

### Evidencia verificada (2026-08-03)
- `GET https://colsubsidio-estable.onrender.com/health` → `{"ok":true,"gemini":true,"openrouter":true,"elevenlabs":true}`.
  El backend está arriba y la key de ElevenLabs está presente (`elevenlabs: true`).
- `backend/requirements.txt` incluye `python-multipart==0.0.9` → no es falta de dependencia para `UploadFile`.
- TTS (`/speak` → `sintetizar`) funciona con la misma key → la key es válida y tiene TTS habilitado.

Con esto se **descartan** key ausente, dependencia faltante y backend caído. Quedan dos
hipótesis para el fallo de STT:
1. **Scribe de ElevenLabs no incluido en el plan** (feature de pago). El backend hace
   `resp.raise_for_status()` y devuelve 502 → el frontend muestra "No pude entender el audio".
   Si es 402/403, el error real se pierde en `main.py:91`.
2. El audio `audio/webm;codecs=opus` que produce `MediaRecorder` no es decodificado por
   ElevenLabs y devuelve texto vacío → el frontend muestra "No escuché nada".

El frontend **no tiene fallback de STT** (a diferencia de TTS, que sí cae a Web Speech API
en `index.html:714`). Por eso "no funciona" en seco.

## Objetivo
Que la transcripción por voz funcione de forma robusta, sin depender del plan de ElevenLabs,
mostrando el error real cuando falle el servicio externo.

## Tareas

### 1. Diagnosticar el error real (verify)
- En el navegador (HTTPS), abrir DevTools → Network, pulsar micrófono, hablar, soltar.
- Inspeccionar la respuesta de `POST /transcribe`:
  - **502** con body `STT error: ... 402/403/422` ⇒ es limitación del plan de ElevenLabs.
  - **200** con `{"text":""}` ⇒ es problema de formato de audio.
- También revisar `GET /health` → `elevenlabs: true` confirma que la key está presente
  (no que el plan incluya STT).

### 2. Exponer el error real en el backend
- `backend/voice_engine.py` (`transcribir`, ~línea 46): en vez de solo `raise_for_status()`,
  capturar y relanzar incluyendo `resp.status_code` y `resp.text[:500]`:
  ```python
  if resp.status_code >= 400:
      raise RuntimeError(f"ElevenLabs STT {resp.status_code}: {resp.text[:500]}")
  ```
- `backend/main.py` (`/transcribe`, línea 91): ya propaga `detail`, ahora con el código real.

### 3. Fallback de STT nativo del navegador (clave)
Añadir en `frontend/index.html` un reconocimiento por `webkitSpeechRecognition` /
`SpeechRecognition` (gratis, en Chrome, vía HTTPS, idioma `es-CO`/`es-ES`, **sin API key**):
- Nueva función `transcribeWithBrowser()` que:
  - crea `new (window.SpeechRecognition || window.webkitSpeechRecognition)()`,
  - setea `lang = 'es-CO'`, `interimResults = false`, `maxAlternatives = 1`,
  - en `onresult` llama `processVoiceCommand(event.results[0][0].transcript)`,
  - en `onerror`/`onend` sin resultado muestra el mensaje actual de reintento.
- En `sendAudio` (`index.html:793`): si `!res.ok` **o** `!data.text.trim()`, llamar a
  `transcribeWithBrowser()` en vez de solo decir "No pude entender". Así STT siempre funciona.

### 4. Robustez de captura de audio
- `startRecording` (`index.html:743`): elegir mimeType soportado de forma explícita:
  ```js
  const mime = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
    ? 'audio/webm;codecs=opus'
    : MediaRecorder.isTypeSupported('audio/mp4') ? 'audio/mp4' : '';
  mediaRecorder = mime ? new MediaRecorder(s, { mimeType: mime }) : new MediaRecorder(s);
  ```
- `sendAudio` (`index.html:790`): derivar la extensión del `blob.type` real
  (`webm`/`mp4`/`ogg`) para el `filename`, ya que el backend mapea content-type por extensión.
- Guarda mínima: ignorar grabaciones < ~300 ms para no enviar audio vacío.

### 5. Evitar capturar la propia voz de la app
- Al inicio de `startRecording` llamar `stopSpeaking()` (definida en `index.html:733`) para
  que el micrófono no grabe el audio TTS que sale por el altavoz.

## Archivos a modificar
- `backend/voice_engine.py` — mensaje de error con status code.
- `backend/main.py` — sin cambio real (ya propaga el detail).
- `frontend/index.html` — fallback `SpeechRecognition`, mimeType explícito, `stopSpeaking()`
  antes de grabar, derivar extensión del blob real.

## Riesgos
- `webkitSpeechRecognition` solo está en Chrome/Edge (no Firefox). Si falla, el usuario
  sigue sin STT en esos navegadores; se documenta como limitación.
- Reconocimiento del navegador puede diferir en exactitud del de ElevenLabs; el parseo de
  inventario (`parseInventoryText`, `index.html:853`) ya es tolerante.

## Validación
1. `GET /health` responde y `elevenlabs: true`.
2. En Chrome (HTTPS): pulsar micrófono, decir "3 arroz, 2 leche" → se crea/agrega checklist.
3. Confirmar en DevTools que, si `/transcribe` falla, el fallback del navegador transcribe.
4. TTS sigue hablando sin regresión (vía ElevenLabs como antes).
5. Probar en móvil (HTTPS) el mismo flujo de voz.
