"""Transport adapters implement outbound delivery, never admissions/business rules."""
import re
from typing import Protocol
import httpx
from .config import settings
from .network import tls_context

class Channel(Protocol):
    async def send(self, external_id: str, text: str) -> None: ...

def telegram_text(text: str) -> str:
    """Convert supported assistant Markdown to plain Telegram text."""
    text = re.sub(r'\*\*(?=\S)(.+?)\*\*', r'\1', text)
    return re.sub(r'(?m)^(\s*)\*\s+', r'\1• ', text)


class TelegramChannel:
    async def send(self, external_id, text):
        text = telegram_text(text)
        token = settings().telegram_bot_token
        if not token:
            raise RuntimeError('Telegram no está configurado')
        async with httpx.AsyncClient(timeout=20, verify=tls_context()) as client:
            for start in range(0, len(text), 4000):
                response = await client.post(f'https://api.telegram.org/bot{token}/sendMessage', json={'chat_id': external_id, 'text': text[start:start+4000]})
                response.raise_for_status()
                if not response.json().get('ok'):
                    raise RuntimeError('Telegram rechazó la entrega')

class SimulatorChannel:
    async def send(self, external_id, text):
        return None

def channel_for(name):
    if name == 'telegram':
        return TelegramChannel()
    if name == 'simulator':
        return SimulatorChannel()
    raise ValueError('Canal aún no implementado')
