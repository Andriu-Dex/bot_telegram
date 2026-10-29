"""Run separately from API: python -m app.telegram_worker. One polling worker only."""
import logging
import httpx
from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from .config import settings

log = logging.getLogger(__name__)

def client():
    cfg = settings()
    return httpx.AsyncClient(base_url=cfg.backend_url, headers={'Authorization': f'Bearer {cfg.internal_api_token}'}, timeout=180)

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
    async with client() as api:
        response = await api.post('/api/channels/telegram/messages', json={'external_id': str(update.effective_chat.id), 'message_id': str(update.update_id), 'name': user.full_name, 'text': text[:4000]})
        response.raise_for_status()

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
    log.warning('Update failed; check backend availability')

def main():
    cfg = settings()
    if not cfg.telegram_bot_token:
        raise SystemExit('Configura TELEGRAM_BOT_TOKEN en .env')
    app = Application.builder().token(cfg.telegram_bot_token).post_init(post_init).post_shutdown(post_shutdown).build()
    app.add_handler(CommandHandler(['start', 'asesor'], incoming))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, incoming))
    app.add_error_handler(on_error)
    app.run_polling(drop_pending_updates=False)

if __name__ == '__main__':
    main()
