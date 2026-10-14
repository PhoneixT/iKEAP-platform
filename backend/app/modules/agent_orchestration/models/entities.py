from sqlalchemy import JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.infrastructure.database import Record


class Agent(Record):
    __tablename__ = "agents"
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text)
    capabilities: Mapped[list] = mapped_column(JSON)
    protocol: Mapped[str] = mapped_column(String(30), default="internal")
    endpoint: Mapped[str] = mapped_column(String(255), default="")
    version: Mapped[str] = mapped_column(String(30), default="1.0.0")


class Workflow(Record):
    __tablename__ = "workflows"
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text, default="")
    nodes: Mapped[list] = mapped_column(JSON)
    version: Mapped[int] = mapped_column(default=1)
