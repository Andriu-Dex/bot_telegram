"""Speech-to-text boundary shared by channel adapters. Audio never touches disk."""
import httpx
from .config import settings
from .network import tls_context


class TranscriptionError(RuntimeError):
    """The audio could not be transcribed safely into a usable text message."""


async def transcribe(audio: bytes, filename: str = 'voice.ogg') -> str:
    if len(audio) > 2_000_000:
        raise TranscriptionError('El audio supera el límite de 2 MB.')
    if not audio:
        raise TranscriptionError('El audio está vacío.')
    cfg = settings()
    if not cfg.groq_api_key:
        raise TranscriptionError('Configura AI_GROQ_API_KEY (o GROQ_API_KEY) para el servicio de transcripción.')
    if cfg.stt_model not in ('whisper-large-v3-turbo', 'whisper-large-v3'):
        raise TranscriptionError('AI_GROQ_MODEL debe ser whisper-large-v3-turbo o whisper-large-v3 para transcribir audio.')
    fields = [
        ('model', (None, cfg.stt_model)),
        ('language', (None, 'es')),
        ('response_format', (None, 'json')),
        ('temperature', (None, '0')),
        ('prompt', (None, 'CTT FISEI Python Arduino Linux GitHub CCNA')),
        ('file', (filename, audio, 'audio/ogg')),
    ]
    try:
        async with httpx.AsyncClient(timeout=45, verify=tls_context()) as client:
            response = await client.post(
                cfg.groq_base_url.rstrip('/') + '/audio/transcriptions',
                headers={'Authorization': f'Bearer {cfg.groq_api_key}'},
                files=fields,
            )
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise TranscriptionError(f'El servicio de transcripción devolvió HTTP {exc.response.status_code}.') from None
    except httpx.HTTPError:
        raise TranscriptionError('No se pudo conectar con el servicio de transcripción.') from None
    try:
        result = response.json()
    except ValueError:
        raise TranscriptionError('El servicio de transcripción devolvió una respuesta inválida.') from None
    text = result.get('text') if isinstance(result, dict) else None
    if not isinstance(text, str) or not text.strip():
        raise TranscriptionError('El servicio no devolvió una transcripción usable.')
    return text.strip()
