import os
import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.update(ADMIN_PASSWORD='test-password', SESSION_SECRET='s'*40, INTERNAL_API_TOKEN='i'*40, OPENAI_API_KEY='', OPENAI_MODEL='', AI_PROVIDER_ID='openai', AI_PROVIDER_API_KEY='', AI_PROVIDER_MODEL='', AI_PROVIDER_BASE_URL='')
from app.config import settings
settings.cache_clear()
from app.db import Base, get_db
from app.main import app, attempts, locks, paused, inference_tasks
import app.main as main

@pytest.fixture
def session_factory(tmp_path, monkeypatch):
    engine = create_engine(f'sqlite:///{tmp_path / "test.db"}', connect_args={'check_same_thread':False})
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    monkeypatch.setattr(main, 'SessionLocal', factory)
    monkeypatch.setattr(main, 'seed_snapshot', lambda db: 0)
    def override():
        with factory() as db:
            yield db
    app.dependency_overrides[get_db] = override
    attempts.clear(); locks.clear(); paused.clear(); inference_tasks.clear()
    yield factory
    app.dependency_overrides.clear()
    engine.dispose()

@pytest.fixture
def client(session_factory):
    with TestClient(app) as client:
        response = client.post('/api/auth/login', json={'username':'admin','password':'test-password'})
        client.headers['Authorization'] = 'Bearer '+response.json()['token']
        yield client
