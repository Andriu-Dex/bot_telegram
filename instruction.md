
Implementá reconocimiento de notas de voz en este repo de forma modular. Transcribí audio en el borde de Telegram y reutilizá el `ingest` de texto. No conviertas el agente ni el dashboard en un sistema multimodal.

## Objetivo

Una nota de voz en chat privado de Telegram se convierte en texto y entra por el mismo `POST /api/channels/telegram/messages` que ya existe. El asesor ve el mensaje con prefijo `🎤 `. El pipeline actual (`classify` → `respond` → outbox → handover) no se reescribe.

## Contrato

- Entrada: `message.voice` (OGG/Opus, chat privado).
- Salida: JSON `Incoming` actual: `external_id`, `message_id`, `name`, `text` (1–4000 chars).
- Si no hay transcripción usable, el worker responde en Telegram y **no** llama al backend.

## Qué no tocar

No modifiques salvo que sea estrictamente imprescindible: `agent.py`, `triage.py`, `catalog.py`, `channels.py`, `models.py`, migraciones, `ingest()`, el modelo `Incoming`, el frontend, outbox, SSE, auth. No agregues TTS, Whisper local, ffmpeg, `filters.AUDIO`, `video_note`, documentos, ni persistencia del `.ogg`. No mandes audio a `/responses`. No cambies el comportamiento del handler de texto más que extraer el POST a un helper si hace falta para no duplicar.

## Qué sí hacer

1. Crear `backend/app/stt.py`:

   - Función `async def transcribe(audio: bytes, filename: str = 'voice.ogg') -> str`.
   - No importar Telegram ni SQLAlchemy. Solo `httpx` + `settings`.
   - Rechazar si `len(audio) > 2_000_000`.
   - `POST {openai_base_url}/stt` con la misma `openai_api_key`.
   - Multipart: `model=grok-voice-transcribe-2.0` (o setting opcional `stt_model`), `language=es`, `format=true`, `keyterm` con `CTT FISEI Python Arduino Linux GitHub CCNA`. El campo `file` al final, content-type `audio/ogg`.
   - Devolver `text` strippeado. Si falta o hay error HTTP, lanzar excepción clara.
   - No escribir a disco.
   - Timeout ~45s. Un solo intento, sin retry loop.
2. Extender `backend/app/telegram_worker.py` lo mínimo:

   - Nuevo handler `incoming_voice` con `filters.VOICE`.
   - Solo chat privado + `effective_user` + `message.voice`.
   - Si `duration > 60`: reply local (“Máximo un minuto; escribí el mensaje o acortalo.”) y return.
   - `get_file` + `download_to_memory`.
   - Llamar `transcribe()`. Si falla o texto vacío: reply local (“No pude entender el audio. Escribime o pedí un asesor.”) y return.
   - `text = ("🎤 " + transcript)[:4000]`.
   - Mismo POST interno que el texto (`update.effective_chat.id`, `str(update.update_id)`, `user.full_name`).
   - Registrar el handler VOICE junto a los existentes, sin quitar `filters.TEXT`.
   - Opcional: extraer el POST a un helper `forward_text(...)` usado por texto y voz. No cambiar la URL ni el JSON.
3. Config (opcional y mínima):

   - Si agregás `stt_model`, default `grok-voice-transcribe-2.0` y una línea en `.env.example`.
   - Reutilizar `OPENAI_API_KEY` y `OPENAI_BASE_URL`. No inventar un segundo secreto.

## Criterio de modularidad

Borrar `stt.py` y el handler `VOICE` debe dejar el bot de texto idéntico. `stt.py` debe poder llamarse igual desde un adaptador WhatsApp futuro.

## Criterios de aceptación

- Una nota de voz corta en privado produce un lead/mensaje de usuario con texto transcrito y `🎤 `, y el bot responde por el outbox como con texto.
- Con handover activo, la transcripción llega al hilo y el LLM no responde (comportamiento actual de `ingest`).
- Voz larga, archivo grande, STT caído o 401: mensaje local, sin `ingest`, sin excepción no manejada que mate el worker.
- Grupos: ignorar.
- Diff acotado: un archivo nuevo + cambios puntuales en el worker (+ config opcional).

## Fuera de alcance

TTS, streaming STT, campo SQL `source`, filtros nuevos en el dashboard, procesar fotos/documentos, cambiar prompts del agente.

Implementá eso y listá los archivos tocados al final.
