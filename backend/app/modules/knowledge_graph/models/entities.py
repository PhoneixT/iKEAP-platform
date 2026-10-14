from sqlalchemy import ForeignKey, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.infrastructure.database import Record


class Entity(Record):
    __tablename__ = "kg_entities"
    __table_args__ = (UniqueConstraint("name", "kind", name="uq_entity_name_kind"),)
    name: Mapped[str] = mapped_column(String(120), index=True)
    kind: Mapped[str] = mapped_column(String(60))
    aliases: Mapped[list] = mapped_column(JSON, default=list)
    properties: Mapped[dict] = mapped_column(JSON, default=dict)
    description: Mapped[str] = mapped_column(Text, default="")
    source: Mapped[str] = mapped_column(String(255))


class Relation(Record):
    __tablename__ = "kg_relations"
    source_id: Mapped[str] = mapped_column(
        ForeignKey("kg_entities.id", ondelete="CASCADE"), index=True
    )
    target_id: Mapped[str] = mapped_column(
        ForeignKey("kg_entities.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[str] = mapped_column(String(60))
    properties: Mapped[dict] = mapped_column(JSON, default=dict)
    source: Mapped[str] = mapped_column(String(255))


class Document(Record):
    __tablename__ = "kg_documents"
    title: Mapped[str] = mapped_column(String(160))
    content: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(255))
    entity_ids: Mapped[list] = mapped_column(JSON, default=list)
    version: Mapped[int] = mapped_column(default=1)
