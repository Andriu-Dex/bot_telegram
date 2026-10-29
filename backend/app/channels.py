"""Transport adapters implement outbound delivery, never admissions/business rules."""
from typing import Protocol
import httpx
from .config import settings

class Channel(Protocol):
    async def send(self, external_id: str, text: str) -> None: ...

class TelegramChannel:
    async def send(self, external_id, text):
        token = settings().telegram_bot_token
        if not token:
            raise RuntimeError('Telegram no está configurado')
        async with httpx.AsyncClient(timeout=20) as client:
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
