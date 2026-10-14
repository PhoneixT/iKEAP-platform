from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import DateTime, String, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from app.core.config import DATABASE_URL


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Base(DeclarativeBase):
    pass


class Record(Base):
    __abstract__ = True
    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, onupdate=utcnow
    )

    def as_dict(self):
        result = {}
        for col in self.__table__.columns:
            value = getattr(self, col.name)
            result[col.name] = (
                value.isoformat() + "Z" if isinstance(value, datetime) else value
            )
        return result


engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    **(
        {"connect_args": {"check_same_thread": False}}
        if DATABASE_URL.startswith("sqlite")
        else {"pool_recycle": 1800}
    ),
)
if DATABASE_URL.startswith("sqlite"):

    @event.listens_for(engine, "connect")
    def sqlite_foreign_keys(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")


SessionLocal = sessionmaker(engine, expire_on_commit=False)


def get_db():
    with SessionLocal() as db:
        yield db
