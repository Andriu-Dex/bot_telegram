import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock
import httpx
import pytest
from sqlalchemy import select
from telegram.error import TelegramError
from app.config import settings
from app.models import Lead, Message
from app.main import app
from app import stt, telegram_worker as worker


def voice_update(text_bytes=b'OggS-test', duration=20, file_size=10, chat_type='private', update_id=1):
    async def download(*, out):
        out.write(text_bytes)
    file = SimpleNamespace(download_to_memory=AsyncMock(side_effect=download))
    voice = SimpleNamespace(duration=duration, file_size=file_size, get_file=AsyncMock(return_value=file))
    message = SimpleNamespace(voice=voice, text=None, reply_text=AsyncMock())
    return SimpleNamespace(effective_message=message, effective_user=SimpleNamespace(full_name='Prueba de voz'), effective_chat=SimpleNamespace(id=123, type=chat_type), update_id=update_id)


def stt_provider(monkeypatch, handler):
    cfg = settings()
    monkeypatch.setattr(cfg, 'groq_api_key', 'test-stt-secret')
    monkeypatch.setattr(cfg, 'groq_base_url', 'https://stt.example/v1/')
    original = httpx.AsyncClient
    def create(**kwargs):
        assert kwargs['timeout'] == 45
        return original(transport=httpx.MockTransport(handler), **kwargs)
    monkeypatch.setattr(stt.httpx, 'AsyncClient', create)


def test_stt_multipart_contract_and_file_last(monkeypatch):
    calls = []
    def handler(request):
        calls.append(request)
        assert str(request.url) == 'https://stt.example/v1/audio/transcriptions'
        assert request.headers['Authorization'] == 'Bearer test-stt-secret'
        body = request.content
        names = [body.index(f'name="{name}"'.encode()) for name in ('model', 'language', 'response_format', 'temperature', 'prompt', 'file')]
        assert names == sorted(names)
        assert b'whisper-large-v3-turbo' in body
        assert b'\r\n\r\nes\r\n' in body and b'\r\n\r\njson\r\n' in body
        assert b'name="format"' not in body and b'name="keyterm"' not in body
        assert b'CTT FISEI Python Arduino Linux GitHub CCNA' in body
        assert b'filename="voice.ogg"' in body and b'Content-Type: audio/ogg' in body
        assert b'OggS-test' in body
        return httpx.Response(200, json={'text': '  Me interesa Python.  '})
    stt_provider(monkeypatch, handler)
    assert asyncio.run(stt.transcribe(b'OggS-test')) == 'Me interesa Python.'
    assert len(calls) == 1


@pytest.mark.parametrize('status', [401, 429, 503])
def test_stt_http_failure_is_clear_and_does_not_retry(monkeypatch, status):
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(status, json={'error': 'unavailable'})
    stt_provider(monkeypatch, handler)
    with pytest.raises(stt.TranscriptionError, match=f'HTTP {status}') as error:
        asyncio.run(stt.transcribe(b'audio'))
    assert len(calls) == 1 and 'test-stt-secret' not in str(error.value)


@pytest.mark.parametrize('body', [{}, {'text': ''}, {'text': '  '}, {'text': None}, {'text': 123}, []])
def test_stt_rejects_unusable_transcription(monkeypatch, body):
    stt_provider(monkeypatch, lambda request: httpx.Response(200, json=body))
    with pytest.raises(stt.TranscriptionError, match='usable'):
        asyncio.run(stt.transcribe(b'audio'))


def test_stt_timeout(monkeypatch):
    def timeout(request):
        raise httpx.ReadTimeout('private provider details', request=request)
    stt_provider(monkeypatch, timeout)
    with pytest.raises(stt.TranscriptionError, match='conectar'):
        asyncio.run(stt.transcribe(b'audio'))


def test_stt_invalid_json(monkeypatch):
    stt_provider(monkeypatch, lambda request: httpx.Response(200, text='not-json'))
    with pytest.raises(stt.TranscriptionError, match='respuesta inválida'):
        asyncio.run(stt.transcribe(b'audio'))


@pytest.mark.parametrize('audio', [b'', b'a' * 2_000_001])
def test_stt_rejects_size_before_any_network(monkeypatch, audio):
    def never(**kwargs):
        raise AssertionError('No debe contactar al proveedor')
    monkeypatch.setattr(stt.httpx, 'AsyncClient', never)
    with pytest.raises(stt.TranscriptionError):
        asyncio.run(stt.transcribe(audio))


def test_stt_missing_key_no_network(monkeypatch):
    monkeypatch.setattr(settings(), 'groq_api_key', '')
    monkeypatch.setattr(settings(), 'openai_api_key', 'legacy-key-must-not-be-used')
    with pytest.raises(stt.TranscriptionError, match='AI_GROQ_API_KEY'):
        asyncio.run(stt.transcribe(b'audio'))


def test_groq_environment_names(monkeypatch):
    from app.config import Settings
    monkeypatch.setenv('AI_GROQ_API_KEY', 'test-key')
    monkeypatch.setenv('AI_GROQ_BASE_URL', 'https://api.groq.com/openai/v1')
    monkeypatch.setenv('AI_GROQ_MODEL', 'whisper-large-v3-turbo')
    cfg = Settings(_env_file=None)
    assert cfg.groq_api_key == 'test-key'
    assert cfg.groq_base_url == 'https://api.groq.com/openai/v1'
    assert cfg.stt_model == 'whisper-large-v3-turbo'


def test_standard_groq_environment_aliases(monkeypatch):
    from app.config import Settings
    for name in ('AI_GROQ_API_KEY', 'AI_GROQ_BASE_URL', 'AI_GROQ_MODEL'):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv('GROQ_API_KEY', 'test-key')
    monkeypatch.setenv('GROQ_BASE_URL', 'https://api.groq.com/openai/v1')
    monkeypatch.setenv('GROQ_MODEL', 'whisper-large-v3')
    cfg = Settings(_env_file=None)
    assert cfg.groq_api_key == 'test-key' and cfg.stt_model == 'whisper-large-v3'


def test_stt_rejects_chat_model_before_network(monkeypatch):
    monkeypatch.setattr(settings(), 'groq_api_key', 'test')
    monkeypatch.setattr(settings(), 'stt_model', 'openai/gpt-oss-120b')
    def never(**kwargs):
        raise AssertionError('No debe enviar audio a un modelo de conversación')
    monkeypatch.setattr(stt.httpx, 'AsyncClient', never)
    with pytest.raises(stt.TranscriptionError, match='AI_GROQ_MODEL'):
        asyncio.run(stt.transcribe(b'audio'))


@pytest.mark.parametrize('options,expected_reply', [({'chat_type':'group'}, False), ({'duration':61}, True), ({'file_size':2_000_001}, True)])
def test_voice_rejected_before_download(monkeypatch, options, expected_reply):
    update = voice_update(**options)
    transcribe = AsyncMock()
    forward = AsyncMock()
    monkeypatch.setattr(worker, 'transcribe', transcribe)
    monkeypatch.setattr(worker, 'forward_text', forward)
    asyncio.run(worker.incoming_voice(update, None))
    update.effective_message.voice.get_file.assert_not_awaited()
    transcribe.assert_not_awaited(); forward.assert_not_awaited()
    assert update.effective_message.reply_text.await_count == int(expected_reply)


def test_voice_checks_actual_downloaded_size(monkeypatch):
    update = voice_update(text_bytes=b'a' * 2_000_001, file_size=None)
    transcribe = AsyncMock(); forward = AsyncMock()
    monkeypatch.setattr(worker, 'transcribe', transcribe)
    monkeypatch.setattr(worker, 'forward_text', forward)
    asyncio.run(worker.incoming_voice(update, None))
    transcribe.assert_not_awaited(); forward.assert_not_awaited()
    assert '2 MB' in update.effective_message.reply_text.await_args.args[0]


@pytest.mark.parametrize('result', [stt.TranscriptionError('HTTP 401'), '', '   '])
def test_voice_stt_failure_stays_local(monkeypatch, result):
    update = voice_update()
    transcribe = AsyncMock(side_effect=result) if isinstance(result, Exception) else AsyncMock(return_value=result)
    forward = AsyncMock()
    monkeypatch.setattr(worker, 'transcribe', transcribe)
    monkeypatch.setattr(worker, 'forward_text', forward)
    asyncio.run(worker.incoming_voice(update, None))
    forward.assert_not_awaited()
    assert 'No pude entender' in update.effective_message.reply_text.await_args.args[0]


def test_voice_telegram_download_failure_stays_local(monkeypatch):
    update = voice_update()
    update.effective_message.voice.get_file.side_effect = TelegramError('Download unavailable')
    forward = AsyncMock()
    monkeypatch.setattr(worker, 'forward_text', forward)
    asyncio.run(worker.incoming_voice(update, None))
    forward.assert_not_awaited()
    assert update.effective_message.reply_text.await_count == 1


def test_voice_truncates_prefix_and_transcript(monkeypatch):
    update = voice_update()
    monkeypatch.setattr(worker, 'transcribe', AsyncMock(return_value='x' * 5000))
    forward = AsyncMock()
    monkeypatch.setattr(worker, 'forward_text', forward)
    asyncio.run(worker.incoming_voice(update, None))
    text = forward.await_args.args[1]
    assert text.startswith('🎤 ') and len(text) == 4000


def test_voice_accepts_exact_duration_and_size_limits(monkeypatch):
    update = voice_update(duration=60, file_size=2_000_000, text_bytes=b'a' * 2_000_000)
    monkeypatch.setattr(worker, 'transcribe', AsyncMock(return_value='Consulta válida'))
    forward = AsyncMock()
    monkeypatch.setattr(worker, 'forward_text', forward)
    asyncio.run(worker.incoming_voice(update, None))
    assert forward.await_args.args[1] == '🎤 Consulta válida'
    update.effective_message.reply_text.assert_not_awaited()


def test_voice_backend_failure_reports_registration_problem(monkeypatch):
    update = voice_update()
    monkeypatch.setattr(worker, 'transcribe', AsyncMock(return_value='Me interesa Python'))
    monkeypatch.setattr(worker, 'forward_text', AsyncMock(side_effect=httpx.ConnectError('offline')))
    asyncio.run(worker.incoming_voice(update, None))
    assert 'no pude registrar' in update.effective_message.reply_text.await_args.args[0]


def test_voice_uses_existing_ingest_and_respects_handover(session_factory, monkeypatch):
    original = httpx.AsyncClient
    monkeypatch.setattr(worker, 'client', lambda: original(transport=httpx.ASGITransport(app=app), base_url='http://test', headers={'Authorization':'Bearer ' + 'i'*40}))
    monkeypatch.setattr(worker, 'transcribe', AsyncMock(side_effect=['Quiero hablar con un asesor', 'Tengo otra consulta sobre Python']))
    updates = [voice_update(update_id=1), voice_update(update_id=2)]
    async def scenario():
        await worker.incoming_voice(updates[0], None)
        await worker.incoming_voice(updates[1], None)
    asyncio.run(scenario())
    with session_factory() as db:
        lead = db.scalar(select(Lead))
        assert lead.channel == 'telegram' and lead.external_id == '123' and lead.name == 'Prueba de voz'
        assert lead.handoff is True
        messages = db.scalars(select(Message).order_by(Message.id)).all()
        assert len(messages) == 3
        assert messages[0].text == '🎤 Quiero hablar con un asesor' and messages[0].external_id == '1'
        assert messages[1].role == 'assistant' and messages[1].delivery == 'handoff_pending'
        assert messages[2].text == '🎤 Tengo otra consulta sobre Python' and messages[2].role == 'user'
    updates[0].effective_message.reply_text.assert_not_awaited()
    assert 'se transcribió' in updates[1].effective_message.reply_text.await_args.args[0]
    assert 'IA está pausada' in updates[1].effective_message.reply_text.await_args.args[0]


@pytest.mark.parametrize('mode,duplicate,expected', [('human',False,1),('human',True,0),('llm',False,0),('fallback',False,0),('rules',False,0)])
def test_handoff_receipt_is_local_and_not_a_second_bot_answer(monkeypatch, mode, duplicate, expected):
    update=voice_update()
    monkeypatch.setattr(worker,'transcribe',AsyncMock(return_value='Pregunta sobre el curso'))
    monkeypatch.setattr(worker,'forward_text',AsyncMock(return_value={'mode':mode,'duplicate':duplicate}))
    asyncio.run(worker.incoming_voice(update,None))
    assert update.effective_message.reply_text.await_count==expected


def test_text_in_handoff_also_receives_receipt(monkeypatch):
    update=voice_update();update.effective_message.text='Hola'
    monkeypatch.setattr(worker,'forward_text',AsyncMock(return_value={'mode':'human','duplicate':False}))
    asyncio.run(worker.incoming(update,None))
    assert 'Recibí tu mensaje' in update.effective_message.reply_text.await_args.args[0]


def test_unexpected_private_update_error_notifies_user():
    update=voice_update()
    asyncio.run(worker.on_error(update,SimpleNamespace(error=RuntimeError('private details'))))
    assert 'Ocurrió un problema' in update.effective_message.reply_text.await_args.args[0]
    assert 'private details' not in update.effective_message.reply_text.await_args.args[0]


def test_group_errors_do_not_send_private_support_notice():
    update=voice_update(chat_type='group')
    asyncio.run(worker.on_error(update,SimpleNamespace(error=RuntimeError())))
    update.effective_message.reply_text.assert_not_awaited()


@pytest.mark.parametrize('text,expected', [('Hola', 'Hola'), ('/start', 'Ver cursos'), ('/asesor', 'Quiero hablar con un asesor')])
def test_text_handler_preserves_existing_behavior(monkeypatch, text, expected):
    update = voice_update(); update.effective_message.text = text
    forward = AsyncMock()
    monkeypatch.setattr(worker, 'forward_text', forward)
    asyncio.run(worker.incoming(update, None))
    assert forward.await_args.args == (update, expected)
