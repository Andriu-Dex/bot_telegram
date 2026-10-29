import asyncio
import httpx
from app.channels import TelegramChannel
from app.config import settings


def test_telegram_delivers_plain_text_without_markdown(monkeypatch):
    monkeypatch.setattr(settings(), 'telegram_bot_token', 'test-token')
    delivered = []
    async def post(self, url, **kwargs):
        delivered.append(kwargs['json'])
        return httpx.Response(200, json={'ok': True}, request=httpx.Request('POST', url))
    monkeypatch.setattr(httpx.AsyncClient, 'post', post)
    asyncio.run(TelegramChannel().send('123', '**GitHub**\n\n* **Estudiantes UTA:** $40\nhttps://example.org/a_b?q=1&n=2\n2 * 3 = 6'))
    assert delivered == [{'chat_id': '123', 'text': 'GitHub\n\n• Estudiantes UTA: $40\nhttps://example.org/a_b?q=1&n=2\n2 * 3 = 6'}]
