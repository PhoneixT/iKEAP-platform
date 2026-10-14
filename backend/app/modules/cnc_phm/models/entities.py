from sqlalchemy import ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.infrastructure.database import Record


class Machine(Record):
    __tablename__ = "phm_machines"
    name: Mapped[str] = mapped_column(String(120))
    code: Mapped[str] = mapped_column(String(60), unique=True)
    component: Mapped[str] = mapped_column(String(80), default="主轴")
    thresholds: Mapped[dict] = mapped_column(JSON)
    telemetry: Mapped[list] = mapped_column(JSON, default=list)


class Anomaly(Record):
    __tablename__ = "phm_anomalies"
    machine_id: Mapped[str] = mapped_column(ForeignKey("phm_machines.id"), index=True)
    title: Mapped[str] = mapped_column(String(160))
    severity: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(30), default="open")
    measurements: Mapped[dict] = mapped_column(JSON)
    diagnosis: Mapped[dict] = mapped_column(JSON, default=dict)


class MaintenanceOrder(Record):
    __tablename__ = "phm_maintenance_orders"
    anomaly_id: Mapped[str] = mapped_column(ForeignKey("phm_anomalies.id"))
    title: Mapped[str] = mapped_column(String(160))
    assignee: Mapped[str] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(30), default="pending")
    actions: Mapped[list] = mapped_column(JSON)
    feedback: Mapped[str] = mapped_column(Text, default="")
