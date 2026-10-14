from sqlalchemy import Boolean, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.infrastructure.database import Record


class User(Record):
    __tablename__ = "sys_users"
    username: Mapped[str] = mapped_column(String(80), unique=True)
    display_name: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[str] = mapped_column(String(256))
    role: Mapped[str] = mapped_column(String(20), default="engineer")
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Resource(Record):
    __tablename__ = "platform_resources"
    name: Mapped[str] = mapped_column(String(120))
    kind: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(30), default="available")
    capabilities: Mapped[dict] = mapped_column(JSON, default=dict)
    description: Mapped[str] = mapped_column(Text, default="")


class AuditLog(Record):
    __tablename__ = "sys_audit_logs"
    actor: Mapped[str] = mapped_column(String(80))
    action: Mapped[str] = mapped_column(String(120))
    target: Mapped[str] = mapped_column(String(120), default="")
    detail: Mapped[dict] = mapped_column(JSON, default=dict)


class Job(Record):
    __tablename__ = "platform_jobs"
    name: Mapped[str] = mapped_column(String(160))
    module: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(30), default="submitted", index=True)
    owner_id: Mapped[str] = mapped_column(ForeignKey("sys_users.id"))
    input_data: Mapped[dict] = mapped_column(JSON, default=dict)
    result: Mapped[dict] = mapped_column(JSON, default=dict)
    error: Mapped[str] = mapped_column(Text, default="")
    progress: Mapped[int] = mapped_column(Integer, default=0)
    idempotency_key: Mapped[str | None] = mapped_column(
        String(160), unique=True, nullable=True
    )


class JobEvent(Record):
    __tablename__ = "platform_job_events"
    job_id: Mapped[str] = mapped_column(
        ForeignKey("platform_jobs.id", ondelete="CASCADE"), index=True
    )
    sequence: Mapped[int] = mapped_column(Integer)
    level: Mapped[str] = mapped_column(String(20), default="info")
    message: Mapped[str] = mapped_column(Text)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)


class FileAsset(Record):
    __tablename__ = "platform_files"
    name: Mapped[str] = mapped_column(String(255))
    storage_key: Mapped[str] = mapped_column(String(80), unique=True)
    content_type: Mapped[str] = mapped_column(String(120))
    sha256: Mapped[str] = mapped_column(String(64))
    size: Mapped[int] = mapped_column(Integer)
    owner_id: Mapped[str] = mapped_column(ForeignKey("sys_users.id"))
