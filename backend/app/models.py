from datetime import datetime, timezone
from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from .db import Base

def now():
    return datetime.now(timezone.utc)

class Course(Base):
    __tablename__ = 'courses'
    id: Mapped[int] = mapped_column(primary_key=True)
    source_url: Mapped[str] = mapped_column(String(500), unique=True)
    title: Mapped[str] = mapped_column(String(300))
    status: Mapped[str] = mapped_column(String(40), default='DESCONOCIDO')
    hours: Mapped[str] = mapped_column(String(100), default='')
    content: Mapped[str] = mapped_column(Text, default='')
    registration_url: Mapped[str] = mapped_column(String(1000), default='')
    approved: Mapped[bool] = mapped_column(Boolean, default=False)
    pending: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class Lead(Base):
    __tablename__ = 'leads'
    __table_args__ = (UniqueConstraint('channel', 'external_id'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    channel: Mapped[str] = mapped_column(String(30))
    external_id: Mapped[str] = mapped_column(String(100))
    name: Mapped[str] = mapped_column(String(200))
    stage: Mapped[str] = mapped_column(String(40), default='nuevo')
    course_id: Mapped[int | None] = mapped_column(ForeignKey('courses.id'), nullable=True)
    profile: Mapped[dict] = mapped_column(JSON, default=dict)
    priority: Mapped[int] = mapped_column(Integer, default=0)
    handoff: Mapped[bool] = mapped_column(Boolean, default=False)
    owner: Mapped[str] = mapped_column(String(150), default='')
    notes: Mapped[str] = mapped_column(Text, default='')
    next_action: Mapped[str] = mapped_column(String(500), default='')
    sentiment: Mapped[str] = mapped_column(String(30), default='interesado')
    sentiment_reason: Mapped[str] = mapped_column(String(500), default='Primera consulta')
    summary: Mapped[str] = mapped_column(Text, default='')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class Message(Base):
    __tablename__ = 'messages'
    __table_args__ = (UniqueConstraint('lead_id', 'external_id'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    lead_id: Mapped[int] = mapped_column(ForeignKey('leads.id'), index=True)
    external_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    role: Mapped[str] = mapped_column(String(30))
    text: Mapped[str] = mapped_column(Text)
    delivery: Mapped[str] = mapped_column(String(30), default='saved')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class Audit(Base):
    __tablename__ = 'audit'
    id: Mapped[int] = mapped_column(primary_key=True)
    actor: Mapped[str] = mapped_column(String(100))
    action: Mapped[str] = mapped_column(String(100))
    detail: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
