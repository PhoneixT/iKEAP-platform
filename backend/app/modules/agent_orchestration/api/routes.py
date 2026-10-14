from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.security import current_user, writer
from app.infrastructure.database import get_db
from app.modules.agent_orchestration.models.entities import Agent, Workflow
from app.modules.agent_orchestration.schemas.contracts import (
    AgentInput,
    WorkflowInput,
    WorkflowRunInput,
)
from app.modules.agent_orchestration.services.executor import (
    ACTIONS,
    ordered_nodes,
    submit,
    run_job,
    append_event,
)
from app.modules.platform.models.entities import Job, JobEvent
from app.shared.services import listing, require, save, audit

router = APIRouter(prefix="/agent-orchestration", tags=["Agent与编排"])


@router.get("/actions")
def actions(user=Depends(current_user)):
    return [{"id": key, "name": value} for key, value in ACTIONS.items()]


@router.get("/agents")
def agents(
    capability: str | None = None,
    db: Session = Depends(get_db),
    user=Depends(current_user),
):
    rows = listing(db, Agent)
    return [row for row in rows if not capability or capability in row["capabilities"]]


@router.post("/agents", status_code=201)
def create_agent(body: AgentInput, db: Session = Depends(get_db), user=Depends(writer)):
    return save(db, Agent(**body.model_dump()), user, "agent.create")


@router.get("/workflows")
def workflows(db: Session = Depends(get_db), user=Depends(current_user)):
    return listing(db, Workflow)


@router.post("/workflows", status_code=201)
def create_workflow(
    body: WorkflowInput, db: Session = Depends(get_db), user=Depends(writer)
):
    data = body.model_dump()
    ordered_nodes(data["nodes"])
    return save(db, Workflow(**data), user, "workflow.create")


@router.post("/workflows/{identifier}/run", status_code=202)
def start_workflow(
    identifier: str,
    body: WorkflowRunInput,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
    user=Depends(writer),
):
    job, created = submit(db, identifier, body.context, user, body.idempotency_key)
    if created:
        background.add_task(run_job, job.id)
    return job.as_dict()


@router.get("/jobs")
def jobs(db: Session = Depends(get_db), user=Depends(current_user)):
    return listing(db, Job)


@router.get("/jobs/{identifier}")
def job(identifier: str, db: Session = Depends(get_db), user=Depends(current_user)):
    record = require(db, Job, identifier)
    events = [
        e.as_dict()
        for e in db.scalars(
            select(JobEvent)
            .where(JobEvent.job_id == identifier)
            .order_by(JobEvent.sequence)
        )
    ]
    return {**record.as_dict(), "events": events}


@router.post("/jobs/{identifier}/cancel")
def cancel(identifier: str, db: Session = Depends(get_db), user=Depends(writer)):
    record = require(db, Job, identifier)
    if record.owner_id != user.id and user.role != "admin":
        raise HTTPException(403, "仅任务提交人或管理员可以取消任务")
    if record.status not in {"submitted", "running"}:
        raise HTTPException(409, "当前任务不能取消")
    record.status = "cancelled"
    append_event(db, identifier, "请求取消；正在执行的外部调用会在节点边界停止后续步骤")
    audit(db, user, "workflow.cancel", identifier)
    db.commit()
    return record.as_dict()
