import asyncio
from collections import defaultdict, deque
from contextlib import asynccontextmanager
import hmac
import time
import json
from typing import Literal
import httpx
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from .agent import respond
from .auth import admin, internal, issue_token
from .catalog import fetch_catalog, store_catalog
from .channels import channel_for
from .config import settings
from .db import get_db
from .models import Audit, Course, Lead, Message, now
from .triage import classify

@asynccontextmanager
async def lifespan(app):
    cfg = settings()
    if not cfg.admin_password or len(cfg.session_secret) < 32 or len(cfg.internal_api_token) < 32:
        raise RuntimeError('Configura ADMIN_PASSWORD, SESSION_SECRET e INTERNAL_API_TOKEN con scripts/setup.ps1')
    yield

app = FastAPI(title='CTT Connect', version='1.0.0', lifespan=lifespan)
locks = defaultdict(asyncio.Lock)
attempts = defaultdict(deque)
inference_tasks = {}
paused = set()
revision = 0

@app.middleware('http')
async def notify_changes(request: Request, call_next):
    global revision
    response = await call_next(request)
    if request.method in ('POST', 'PATCH') and response.status_code < 300:
        revision += 1
    return response

@app.get('/api/events', dependencies=[Depends(admin)])
async def events(request: Request):
    async def stream():
        last = -1
        ticks = 0
        while not await request.is_disconnected():
            if revision != last:
                last = revision
                yield f'data: {json.dumps({"revision": last})}\n\n'
            elif ticks % 30 == 0:
                yield ': heartbeat\n\n'
            ticks += 1
            await asyncio.sleep(0.5)
    return StreamingResponse(stream(), media_type='text/event-stream', headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})

def audit(db, actor, action, detail):
    db.add(Audit(actor=actor, action=action, detail=str(detail)))

def get_lead(db, lead_id):
    item = db.get(Lead, lead_id)
    if not item:
        raise HTTPException(404, 'Prospecto no encontrado')
    return item

class Login(BaseModel):
    username: str = Field(max_length=150)
    password: str = Field(max_length=300)

@app.post('/api/auth/login')
def login(body: Login, request: Request):
    key = request.client.host if request.client else 'unknown'
    recent = attempts[key]
    while recent and recent[0] < time.monotonic() - 60:
        recent.popleft()
    if len(recent) >= 10:
        raise HTTPException(429, 'Demasiados intentos. Espera un minuto.')
    recent.append(time.monotonic())
    cfg = settings()
    if not cfg.admin_password or not hmac.compare_digest(body.username.encode(), cfg.admin_username.encode()) or not hmac.compare_digest(body.password.encode(), cfg.admin_password.encode()):
        raise HTTPException(401, 'Credenciales incorrectas')
    return {'token': issue_token(), 'username': cfg.admin_username}

@app.get('/api/health')
def health():
    return {'status': 'ok'}

@app.get('/api/status', dependencies=[Depends(admin)])
def status():
    cfg = settings()
    return {'telegram_configured': bool(cfg.telegram_bot_token), 'llm_configured': bool(cfg.openai_api_key and cfg.openai_model), 'whatsapp': 'adapter_pending'}

@app.get('/api/courses', dependencies=[Depends(admin)])
def courses(db: Session = Depends(get_db)):
    return db.scalars(select(Course).order_by(Course.id.desc())).all()

@app.post('/api/courses/sync')
async def sync(actor=Depends(admin), db: Session = Depends(get_db)):
    try:
        items, errors = await fetch_catalog()
    except (httpx.HTTPError, ValueError):
        raise HTTPException(502, 'No se pudo importar el catálogo. Los datos publicados se conservaron.')
    count = store_catalog(db, items)
    audit(db, actor, 'catalog.sync', f'{count} cambios; {len(errors)} errores')
    db.commit()
    return {'fetched': len(items), 'changed': count, 'errors': errors}

class CoursePatch(BaseModel):
    approved: bool
    accept_pending: bool = False

@app.patch('/api/courses/{course_id}')
def update_course(course_id: int, body: CoursePatch, actor=Depends(admin), db: Session = Depends(get_db)):
    c = db.get(Course, course_id)
    if not c:
        raise HTTPException(404, 'Curso no encontrado')
    if body.accept_pending and c.pending:
        for key in ('title', 'status', 'hours', 'content', 'registration_url'):
            setattr(c, key, c.pending[key])
        c.pending = None
    c.approved = body.approved
    audit(db, actor, 'course.review', f'{course_id}: {body.model_dump()}')
    db.commit()
    return c

@app.get('/api/leads', dependencies=[Depends(admin)])
def leads(db: Session = Depends(get_db)):
    return db.scalars(select(Lead).order_by(Lead.priority.desc(), Lead.updated_at.desc()).limit(1000)).all()

@app.get('/api/leads/{lead_id}/messages', dependencies=[Depends(admin)])
def messages(lead_id: int, db: Session = Depends(get_db)):
    get_lead(db, lead_id)
    return db.scalars(select(Message).where(Message.lead_id == lead_id).order_by(Message.id).limit(1000)).all()

class LeadPatch(BaseModel):
    stage: Literal['nuevo', 'interesado', 'solicita_inscripcion', 'seguimiento', 'inscrito', 'cerrado']
    owner: str = Field(default='', max_length=150)
    notes: str = Field(default='', max_length=10000)
    next_action: str = Field(default='', max_length=500)
    handoff: bool = False

@app.patch('/api/leads/{lead_id}')
async def update_lead(lead_id: int, body: LeadPatch, actor=Depends(admin), db: Session = Depends(get_db)):
    get_lead(db, lead_id)
    if body.handoff:
        paused.add(lead_id)
        task = inference_tasks.get(lead_id)
        if task:
            task.cancel()
    async with locks[f'lead:{lead_id}']:
        db.expire_all()
        lead = get_lead(db, lead_id)
        for key, value in body.model_dump().items():
            setattr(lead, key, value)
        lead.updated_at = now()
        audit(db, actor, 'lead.update', f'{lead_id}: {body.stage}')
        db.commit()
        if not body.handoff:
            paused.discard(lead_id)
        return lead

class Incoming(BaseModel):
    external_id: str = Field(min_length=1, max_length=100)
    message_id: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=200)
    text: str = Field(min_length=1, max_length=4000)

async def ingest(channel, body, db):
    async with locks[f'in:{channel}:{body.external_id}']:
        lead = db.scalar(select(Lead).where(Lead.channel == channel, Lead.external_id == body.external_id))
        if not lead:
            lead = Lead(channel=channel, external_id=body.external_id, name=body.name, profile={})
            db.add(lead)
            db.flush()
        async with locks[f'lead:{lead.id}']:
            existing = db.scalar(select(Message).where(Message.lead_id == lead.id, Message.external_id == body.message_id))
            if existing:
                answer = db.scalar(select(Message).where(Message.lead_id == lead.id, Message.external_id == 'reply:' + body.message_id))
                return {'lead_id': lead.id, 'reply': answer.text if answer else None, 'message_id': answer.id if answer else None, 'duplicate': True, 'mode': 'cached'}
            db.add(Message(lead_id=lead.id, external_id=body.message_id, role='user', text=body.text))
            db.flush()
            lead.updated_at = now()
            db.commit()
            if lead.handoff or lead.id in paused:
                return {'lead_id': lead.id, 'reply': None, 'message_id': None, 'mode': 'human', 'duplicate': False}
            async def pipeline():
                await classify(db, lead, body.text)
                return await respond(db, lead, body.text)
            task = asyncio.create_task(pipeline())
            inference_tasks[lead.id] = task
            try:
                answer, mode = await task
            except asyncio.CancelledError:
                db.rollback()
                return {'lead_id': lead.id, 'reply': None, 'message_id': None, 'mode': 'human', 'duplicate': False}
            finally:
                inference_tasks.pop(lead.id, None)
            if lead.id in paused:
                db.rollback()
                return {'lead_id': lead.id, 'reply': None, 'message_id': None, 'mode': 'human', 'duplicate': False}
            msg = Message(lead_id=lead.id, external_id='reply:' + body.message_id, role='assistant', text=answer, delivery='pending' if channel != 'simulator' else 'delivered')
            db.add(msg)
            db.commit()
            return {'lead_id': lead.id, 'reply': answer, 'message_id': msg.id, 'mode': mode, 'duplicate': False}

@app.post('/api/simulator/messages', dependencies=[Depends(admin)])
async def simulator(body: Incoming, db: Session = Depends(get_db)):
    return await ingest('simulator', body, db)

@app.post('/api/channels/telegram/messages', dependencies=[Depends(internal)])
async def telegram(body: Incoming, db: Session = Depends(get_db)):
    return await ingest('telegram', body, db)

class Reply(BaseModel):
    text: str = Field(min_length=1, max_length=4000)

@app.post('/api/leads/{lead_id}/reply')
async def reply(lead_id: int, body: Reply, actor=Depends(admin), db: Session = Depends(get_db)):
    # Direct operator intervention also takes ownership and cancels inference.
    get_lead(db, lead_id)
    paused.add(lead_id)
    task = inference_tasks.get(lead_id)
    if task:
        task.cancel()
    async with locks[f'lead:{lead_id}']:
        db.expire_all()
        lead = get_lead(db, lead_id)
        lead.handoff = True
        lead.owner = lead.owner or actor
        msg = Message(lead_id=lead_id, role='advisor', text=body.text, delivery='pending')
        db.add(msg)
        lead.updated_at = now()
        db.commit()
        try:
            await channel_for(lead.channel).send(lead.external_id, body.text)
            msg.delivery = 'delivered'
        except (httpx.HTTPError, RuntimeError, ValueError):
            msg.delivery = 'failed'
        audit(db, actor, 'advisor.reply', f'{lead_id}: {msg.delivery}')
        db.commit()
        return msg

@app.get('/api/channels/telegram/outbox', dependencies=[Depends(internal)])
def outbox(db: Session = Depends(get_db)):
    rows = db.execute(select(Message, Lead).join(Lead, Message.lead_id == Lead.id).where(Lead.channel == 'telegram', Message.role == 'assistant', Message.delivery == 'pending').order_by(Message.id).limit(20)).all()
    return [{'id': m.id, 'external_id': l.external_id, 'text': m.text} for m, l in rows]

@app.post('/api/channels/telegram/outbox/{message_id}/dispatch', dependencies=[Depends(internal)])
async def dispatch(message_id: int, db: Session = Depends(get_db)):
    msg = db.get(Message, message_id)
    if not msg or msg.role != 'assistant':
        raise HTTPException(404, 'Mensaje no encontrado')
    async with locks[f'lead:{msg.lead_id}']:
        db.expire_all()
        lead = get_lead(db, msg.lead_id)
        if lead.channel != 'telegram':
            raise HTTPException(404, 'Canal incorrecto')
        if msg.delivery != 'pending':
            return {'delivery': msg.delivery}
        # The one handoff acknowledgement is allowed. Any earlier queued answer is suppressed.
        if lead.id in paused or (lead.handoff and lead.sentiment != 'frustrado' and 'He registrado tu solicitud' not in msg.text):
            msg.delivery = 'cancelled'
        else:
            try:
                await channel_for('telegram').send(lead.external_id, msg.text)
                msg.delivery = 'delivered'
            except (httpx.HTTPError, RuntimeError):
                raise HTTPException(502, 'Entrega pendiente; se reintentará')
        db.commit()
        return {'delivery': msg.delivery}

@app.post('/api/channels/telegram/outbox/{message_id}/ack', dependencies=[Depends(internal)])
def ack(message_id: int, db: Session = Depends(get_db)):
    msg = db.get(Message, message_id)
    if not msg or msg.role != 'assistant' or get_lead(db, msg.lead_id).channel != 'telegram':
        raise HTTPException(404, 'Mensaje no encontrado')
    msg.delivery = 'delivered'
    db.commit()
    return {'ok': True}

@app.get('/api/audit', dependencies=[Depends(admin)])
def audits(db: Session = Depends(get_db)):
    return db.scalars(select(Audit).order_by(Audit.id.desc()).limit(100)).all()
