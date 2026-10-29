from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')
    database_url: str = 'sqlite:///./ctt.db'
    admin_username: str = 'admin'
    admin_password: str = ''
    session_secret: str = ''
    internal_api_token: str = ''
    telegram_bot_token: str = ''
    openai_api_key: str = ''
    openai_model: str = ''
    openai_base_url: str = 'https://api.openai.com/v1'
    backend_url: str = 'http://127.0.0.1:8000'


@lru_cache
def settings():
    return Settings()
