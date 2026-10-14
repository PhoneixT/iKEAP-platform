from sqlalchemy import Boolean, JSON, String
from sqlalchemy.orm import Mapped, mapped_column
from app.infrastructure.database import Record


class Rule(Record):
    __tablename__ = "validation_rules"
    name: Mapped[str] = mapped_column(String(120))
    scope: Mapped[str] = mapped_column(String(30))
    field: Mapped[str] = mapped_column(String(80))
    operator: Mapped[str] = mapped_column(String(20))
    expected: Mapped[dict] = mapped_column(JSON)
    unit: Mapped[str] = mapped_column(String(30), default="")
    severity: Mapped[str] = mapped_column(String(20), default="hard")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    version: Mapped[int] = mapped_column(default=1)


class ValidationReport(Record):
    __tablename__ = "validation_reports"
    name: Mapped[str] = mapped_column(String(160))
    scope: Mapped[str] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(String(30))
    input_data: Mapped[dict] = mapped_column(JSON)
    findings: Mapped[list] = mapped_column(JSON)
