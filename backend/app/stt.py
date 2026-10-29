"""Speech-to-text boundary shared by channel adapters. Audio never touches disk."""
import httpx
from .config import settings


class TranscriptionError(RuntimeError):
    """The audio could not be transcribed safely into a usable text message."""


async def transcribe(audio: bytes, filename: str = 'voice.ogg') -> str:
    if len(audio) > 2_000_000:
        raise TranscriptionError('El audio supera el límite de 2 MB.')
    if not audio:
        raise TranscriptionError('El audio está vacío.')
    cfg = settings()
    if not cfg.openai_api_key:
        raise TranscriptionError('Configura OPENAI_API_KEY y OPENAI_BASE_URL para el servicio de transcripción.')
    # xAI requires file to be the last multipart field. Do not route audio to Responses.
    fields = [
        ('model', (None, cfg.stt_model)),
        ('language', (None, 'es')),
        ('format', (None, 'true')),
        ('keyterm', (None, 'CTT FISEI Python Arduino Linux GitHub CCNA')),
        ('file', (filename, audio, 'audio/ogg')),
    ]
    try:
        async with httpx.AsyncClient(timeout=45) as client:
            response = await client.post(
                cfg.openai_base_url.rstrip('/') + '/stt',
                headers={'Authorization': f'Bearer {cfg.openai_api_key}'},
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
