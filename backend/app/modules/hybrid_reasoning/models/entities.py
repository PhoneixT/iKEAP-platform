from sqlalchemy import JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.infrastructure.database import Record


class ReasoningRun(Record):
    __tablename__ = "reasoning_runs"
    title: Mapped[str] = mapped_column(String(160))
    task: Mapped[str] = mapped_column(Text)
    domain: Mapped[str] = mapped_column(String(30))
    mode: Mapped[str] = mapped_column(String(30))
    evidence: Mapped[dict] = mapped_column(JSON)
    candidates: Mapped[list] = mapped_column(JSON)
    service_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
