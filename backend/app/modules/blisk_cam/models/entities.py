from sqlalchemy import ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.infrastructure.database import Record


class CamProject(Record):
    __tablename__ = "cam_projects"
    name: Mapped[str] = mapped_column(String(160))
    material: Mapped[str] = mapped_column(String(80))
    description: Mapped[str] = mapped_column(Text, default="")
    resource_id: Mapped[str | None] = mapped_column(
        ForeignKey("platform_resources.id"), nullable=True
    )
    geometry_file_id: Mapped[str | None] = mapped_column(
        ForeignKey("platform_files.id"), nullable=True
    )
    parameters: Mapped[dict] = mapped_column(JSON)
    plan: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(30), default="draft")
    execution: Mapped[dict] = mapped_column(JSON, default=dict)
