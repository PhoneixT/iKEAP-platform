from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.core.security import current_user, writer
from app.infrastructure.database import get_db
from app.modules.cnc_phm.models.entities import Machine, Anomaly, MaintenanceOrder
from app.modules.cnc_phm.schemas.contracts import (
    MachineInput,
    TelemetryInput,
    DiagnosticInput,
    RulInput,
    MaintenanceInput,
    MaintenanceUpdate,
)
from app.modules.cnc_phm.services.diagnostics import ingest, diagnose, estimate_rul
from app.shared.services import listing, require, save, audit

router = APIRouter(prefix="/cnc-phm", tags=["机床PHM"])


@router.get("/machines")
def machines(db: Session = Depends(get_db), user=Depends(current_user)):
    return listing(db, Machine)


@router.post("/machines", status_code=201)
def create_machine(
    body: MachineInput, db: Session = Depends(get_db), user=Depends(writer)
):
    return save(db, Machine(**body.model_dump()), user, "phm.machine.create")


@router.post("/machines/{identifier}/telemetry")
def ingest_telemetry(
    identifier: str,
    body: TelemetryInput,
    db: Session = Depends(get_db),
    user=Depends(writer),
):
    result = ingest(db, identifier, body.samples)
    audit(db, user, "phm.telemetry", identifier, {"count": len(body.samples)})
    db.commit()
    return result


@router.post("/machines/{identifier}/rul")
def rul(
    identifier: str,
    body: RulInput,
    db: Session = Depends(get_db),
    user=Depends(current_user),
):
    return estimate_rul(db, identifier, body.failure_threshold)


@router.get("/anomalies")
def anomalies(db: Session = Depends(get_db), user=Depends(current_user)):
    return listing(db, Anomaly)


@router.post("/anomalies/{identifier}/diagnose")
def create_diagnosis(
    identifier: str,
    body: DiagnosticInput,
    db: Session = Depends(get_db),
    user=Depends(writer),
):
    result = diagnose(db, identifier, body.mode)
    audit(db, user, "phm.diagnose", identifier)
    db.commit()
    return result


@router.get("/maintenance")
def maintenance(db: Session = Depends(get_db), user=Depends(current_user)):
    return listing(db, MaintenanceOrder)


@router.post("/maintenance", status_code=201)
def create_order(
    body: MaintenanceInput, db: Session = Depends(get_db), user=Depends(writer)
):
    anomaly = require(db, Anomaly, body.anomaly_id)
    if anomaly.status != "diagnosed":
        raise HTTPException(409, "需要先完成候选故障分析")
    if db.scalar(
        select(MaintenanceOrder).where(
            MaintenanceOrder.anomaly_id == anomaly.id,
            MaintenanceOrder.status.in_(["pending", "in_progress"]),
        )
    ):
        raise HTTPException(409, "此异常已有未完成的维护工单")
    return save(
        db, MaintenanceOrder(**body.model_dump()), user, "phm.maintenance.create"
    )


@router.patch("/maintenance/{identifier}")
def update_order(
    identifier: str,
    body: MaintenanceUpdate,
    db: Session = Depends(get_db),
    user=Depends(writer),
):
    order = require(db, MaintenanceOrder, identifier)
    expected = {"pending": "in_progress", "in_progress": "completed"}
    if expected.get(order.status) != body.status:
        raise HTTPException(409, "工单状态转换不合法")
    order.status, order.feedback = body.status, body.feedback
    if body.status == "completed":
        require(db, Anomaly, order.anomaly_id).status = "closed"
    return save(db, order, user, "phm.maintenance.update")
