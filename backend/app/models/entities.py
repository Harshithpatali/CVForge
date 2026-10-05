from datetime import datetime
from sqlalchemy import DateTime, Integer, String, Text, JSON, ForeignKey, Float, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from app.core.db import Base

def now(): return datetime.utcnow()

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    name: Mapped[str] = mapped_column(String(255), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)

class CandidateProfileRecord(Base):
    __tablename__ = "candidate_profiles"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(255), default="Untitled profile")
    profile_json: Mapped[dict] = mapped_column(JSON)
    source_text: Mapped[str] = mapped_column(Text, default="")
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)

class PromptVersion(Base):
    __tablename__ = "prompt_versions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    prompt_key: Mapped[str] = mapped_column(String(255), index=True)
    version: Mapped[int] = mapped_column(Integer)
    prompt_text: Mapped[str] = mapped_column(Text)
    role_family: Mapped[str] = mapped_column(String(80), default="general")
    seniority: Mapped[str] = mapped_column(String(80), default="entry")
    domain: Mapped[str] = mapped_column(String(80), default="general")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)

class Application(Base):
    __tablename__ = "applications"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    candidate_profile_id: Mapped[int | None] = mapped_column(ForeignKey("candidate_profiles.id"), nullable=True)
    job_title: Mapped[str] = mapped_column(String(255), default="")
    company: Mapped[str] = mapped_column(String(255), default="")
    job_json: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(40), default="draft", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)

class GenerationJob(Base):
    __tablename__ = "generation_jobs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id"), index=True)
    status: Mapped[str] = mapped_column(String(40), default="queued", index=True)
    error: Mapped[str | None] = mapped_column(Text)
    input_json: Mapped[dict | None] = mapped_column(JSON)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)

class ResumeArtifact(Base):
    __tablename__ = "resume_artifacts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id"), index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    resume_json: Mapped[dict] = mapped_column(JSON)
    ats_json: Mapped[dict] = mapped_column(JSON)
    prompt_version_id: Mapped[int | None] = mapped_column(ForeignKey("prompt_versions.id"))
    template_key: Mapped[str] = mapped_column(String(120), default="classic_ats")
    docx_path: Mapped[str | None] = mapped_column(Text)
    pdf_path: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)

class GenerationEvent(Base):
    __tablename__ = "generation_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    generation_job_id: Mapped[int] = mapped_column(ForeignKey("generation_jobs.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(80))
    payload: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
