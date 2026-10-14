from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.security import current_user, writer
from app.infrastructure.database import get_db
from app.shared.services import listing, require, audit
from app.modules.hybrid_reasoning.models.entities import ReasoningRun
from app.modules.hybrid_reasoning.schemas.contracts import ReasoningInput
from app.modules.hybrid_reasoning.services.reasoning import run_reasoning
from app.modules.hybrid_reasoning.services.task_parser import parse_task
from app.modules.knowledge_graph.services.retrieval import retrieve

router = APIRouter(prefix="/hybrid-reasoning", tags=["协同推理"])


@router.post("/parse")
def parse(body: ReasoningInput, user=Depends(current_user)):
    return parse_task(body.task, body.domain, body.parameters)


@router.post("/context")
def context(
    body: ReasoningInput, db: Session = Depends(get_db), user=Depends(current_user)
):
    return {
        "task_specification": parse_task(body.task, body.domain, body.parameters),
        "evidence": retrieve(db, body.task),
        "resource_id": body.resource_id,
    }


@router.get("/runs")
def runs(db: Session = Depends(get_db), user=Depends(current_user)):
    return listing(db, ReasoningRun)


@router.post("/runs", status_code=201)
def create_run(
    body: ReasoningInput, db: Session = Depends(get_db), user=Depends(writer)
):
    result = run_reasoning(db, **body.model_dump())
    audit(db, user, "reasoning.run", result["id"])
    db.commit()
    return result


@router.get("/runs/{identifier}")
def get_run(identifier: str, db: Session = Depends(get_db), user=Depends(current_user)):
    return require(db, ReasoningRun, identifier).as_dict()


@router.post("/runs/{identifier}/correct")
def correct_run(
    identifier: str,
    body: ReasoningInput,
    db: Session = Depends(get_db),
    user=Depends(writer),
):
    previous = require(db, ReasoningRun, identifier)
    result = run_reasoning(db, **body.model_dump())
    record = require(db, ReasoningRun, result["id"])
    record.service_metadata = {
        **record.service_metadata,
        "previous_run_id": previous.id,
    }
    audit(db, user, "reasoning.correct", record.id)
    db.commit()
    return record.as_dict()
