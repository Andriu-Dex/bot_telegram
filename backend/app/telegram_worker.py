"""Run separately from API: python -m app.telegram_worker. One polling worker only."""
import logging
from io import BytesIO
import httpx
from telegram import ReplyKeyboardMarkup, Update
from telegram.error import TelegramError
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from .config import settings
from .stt import TranscriptionError, transcribe

log = logging.getLogger(__name__)

def client():
    cfg = settings()
    return httpx.AsyncClient(base_url=cfg.backend_url, headers={'Authorization': f'Bearer {cfg.internal_api_token}'}, timeout=180)

async def forward_text(update: Update, text: str):
    async with client() as api:
        response = await api.post('/api/channels/telegram/messages', json={'external_id': str(update.effective_chat.id), 'message_id': str(update.update_id), 'name': update.effective_user.full_name, 'text': text[:4000]})
        response.raise_for_status()
        return response.json()

async def acknowledge_handoff(message, result, *, voice=False):
    if isinstance(result, dict) and result.get('mode') == 'human' and not result.get('duplicate'):
        text = 'Tu nota de voz se transcribió y quedó en el hilo del asesor.' if voice else 'Recibí tu mensaje y quedó en el hilo del asesor.'
        await message.reply_text(text + ' Esta conversación está en atención humana; la IA está pausada. Un asesor continuará por aquí.')

async def incoming(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    user = update.effective_user
    if not message or not user or not message.text or update.effective_chat.type != 'private':
        return
    text = message.text
    if text == '/start':
        await message.reply_text('¡Bienvenido a CTT-FISEI! Soy un asistente automatizado. Guardamos tus mensajes para atender y dar seguimiento a tu consulta. No compartas documentos ni datos de pago.', reply_markup=ReplyKeyboardMarkup([['Ver cursos'], ['Quiero hablar con un asesor']], resize_keyboard=True))
        text = 'Ver cursos'
    elif text == '/asesor':
        text = 'Quiero hablar con un asesor'
    result = await forward_text(update, text)
    await acknowledge_handoff(message, result)

async def incoming_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    if not message or not user or not chat or chat.type != 'private' or not message.voice:
        return
    voice = message.voice
    duration = voice.duration.total_seconds() if hasattr(voice.duration, 'total_seconds') else voice.duration
    if duration > 60:
        await message.reply_text('Máximo un minuto; escribí el mensaje o acortalo.')
        return
    too_large = 'El audio supera los 2 MB. Escribí el mensaje o acortalo.'
    if voice.file_size and voice.file_size > 2_000_000:
        await message.reply_text(too_large)
        return
    try:
        telegram_file = await voice.get_file()
        with BytesIO() as buffer:
            await telegram_file.download_to_memory(out=buffer)
            audio = buffer.getvalue()
        if len(audio) > 2_000_000:
            await message.reply_text(too_large)
            return
        transcript = await transcribe(audio)
        if not isinstance(transcript, str) or not transcript.strip():
            raise TranscriptionError('Transcripción vacía.')
    except (TelegramError, TranscriptionError):
        log.warning('Voice transcription unavailable; user asked to send text')
        await message.reply_text('No pude entender el audio. Escribime o pedí un asesor.')
        return
    try:
        result = await forward_text(update, ('🎤 ' + transcript.strip())[:4000])
        await acknowledge_handoff(message, result, voice=True)
    except httpx.HTTPError:
        log.warning('Voice transcribed but backend unavailable')
        await message.reply_text('Entendí tu audio, pero no pude registrar la consulta. Intentá de nuevo en un momento.')

async def deliver(context: ContextTypes.DEFAULT_TYPE):
    # A persisted outbox survives worker restarts. Telegram has no idempotency key:
    # a crash between send and ack may result in a duplicate delivery.
    async with client() as api:
        response = await api.get('/api/channels/telegram/outbox')
        response.raise_for_status()
        for item in response.json():
            try:
                ack = await api.post(f"/api/channels/telegram/outbox/{item['id']}/dispatch")
                ack.raise_for_status()
            except Exception:
                log.warning('Delivery pending for message %s', item['id'])

async def post_init(app):
    async def outbox_loop():
        import asyncio
        while True:
            try:
                await deliver(type('DeliveryContext', (), {'bot': app.bot})())
            except Exception:
                log.warning('Backend unavailable; outbox will retry')
            await asyncio.sleep(3)
    import asyncio
    app.bot_data['outbox_task'] = asyncio.create_task(outbox_loop())

async def post_shutdown(app):
    task = app.bot_data.get('outbox_task')
    if task:
        task.cancel()

async def on_error(update, context):
    # Do not log exception strings: Telegram transport URLs can contain the bot token.
    log.warning('Update failed (type=%s)', type(context.error).__name__)
    message = getattr(update, 'effective_message', None)
    chat = getattr(update, 'effective_chat', None)
    if message and chat and chat.type == 'private':
        try:
            await message.reply_text('Ocurrió un problema al procesar tu mensaje. Inténtalo de nuevo o escribe tu consulta para que podamos atenderte.')
        except TelegramError:
            log.warning('Could not deliver processing error notice')

def main():
    cfg = settings()
    if not cfg.telegram_bot_token:
        raise SystemExit('Configura TELEGRAM_BOT_TOKEN en .env')
    app = Application.builder().token(cfg.telegram_bot_token).concurrent_updates(16).post_init(post_init).post_shutdown(post_shutdown).build()
    app.add_handler(CommandHandler(['start', 'asesor'], incoming))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, incoming))
    app.add_handler(MessageHandler(filters.VOICE, incoming_voice))
    app.add_error_handler(on_error)
    app.run_polling(drop_pending_updates=False)

if __name__ == '__main__':
    main()
