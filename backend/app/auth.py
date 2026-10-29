import base64
import hashlib
import hmac
import json
import time
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from .config import settings

bearer = HTTPBearer(auto_error=False)

def issue_token():
    cfg = settings()
    body = base64.urlsafe_b64encode(json.dumps({'sub': cfg.admin_username, 'exp': int(time.time()) + 28800}).encode()).decode()
    signature = hmac.new(cfg.session_secret.encode(), body.encode(), hashlib.sha256).hexdigest()
    return body + '.' + signature

def admin(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)):
    cfg = settings()
    if not cfg.session_secret or not credentials:
        raise HTTPException(401, 'Inicia sesión')
    try:
        body, signature = credentials.credentials.split('.')
        expected = hmac.new(cfg.session_secret.encode(), body.encode(), hashlib.sha256).hexdigest()
        payload = json.loads(base64.urlsafe_b64decode(body))
        if not hmac.compare_digest(signature, expected) or payload['exp'] < time.time() or payload['sub'] != cfg.admin_username:
            raise ValueError()
        return payload['sub']
    except (ValueError, KeyError, TypeError):
        raise HTTPException(401, 'Sesión inválida o vencida')

def internal(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)):
    token = settings().internal_api_token
    if not token or not credentials or not hmac.compare_digest(credentials.credentials, token):
        raise HTTPException(401, 'Canal no autorizado')
