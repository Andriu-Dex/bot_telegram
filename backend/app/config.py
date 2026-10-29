from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import AliasChoices, Field


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
    stt_model: str = 'grok-voice-transcribe-2.0'
    backend_url: str = 'http://127.0.0.1:8000'
    ai_provider_id: str = 'gemini'
    ai_provider_api_key: str = Field(default='', validation_alias=AliasChoices('AI_PROVIDER_API_KEY', 'GEMINI_API_KEY'))
    ai_provider_model: str = Field(default='', validation_alias=AliasChoices('AI_PROVIDER_MODEL', 'GEMINI_MODEL'))
    ai_provider_base_url: str = ''

    @property
    def llm_key(self):
        return self.ai_provider_api_key or (self.openai_api_key if self.ai_provider_id == 'openai' else '')

    @property
    def llm_model(self):
        return self.ai_provider_model or (self.openai_model if self.ai_provider_id == 'openai' else '')

    @property
    def llm_configured(self):
        return bool(self.llm_key and self.llm_model)


@lru_cache
def settings():
    return Settings()
