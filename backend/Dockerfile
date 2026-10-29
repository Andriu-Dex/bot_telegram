FROM python:3.12-slim
WORKDIR /workspace
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt
COPY backend backend
ENV PYTHONPATH=/workspace/backend
CMD ["sh", "-c", "alembic -c backend/alembic.ini upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
