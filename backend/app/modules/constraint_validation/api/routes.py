from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.security import current_user, writer
from app.infrastructure.database import get_db
from app.shared.services import require, save, listing, audit
from app.modules.constraint_validation.models.entities import Rule, ValidationReport
from app.modules.constraint_validation.schemas.contracts import (
    RuleInput,
    ValidationInput,
)
from app.modules.constraint_validation.services.engine import evaluate

router = APIRouter(prefix="/constraint-validation", tags=["约束验证"])


@router.get("/rules")
def rules(db: Session = Depends(get_db), user=Depends(current_user)):
    return listing(db, Rule)


@router.post("/rules", status_code=201)
def create_rule(body: RuleInput, db: Session = Depends(get_db), user=Depends(writer)):
    return save(db, Rule(**body.model_dump()), user, "validation.rule.create")


@router.put("/rules/{identifier}")
def update_rule(
    identifier: str,
    body: RuleInput,
    db: Session = Depends(get_db),
    user=Depends(writer),
):
    rule = require(db, Rule, identifier)
    for key, value in body.model_dump().items():
        setattr(rule, key, value)
    rule.version += 1
    return save(db, rule, user, "validation.rule.update")


@router.post("/evaluate")
def validate(
    body: ValidationInput, db: Session = Depends(get_db), user=Depends(writer)
):
    report = evaluate(db, **body.model_dump())
    audit(db, user, "validation.evaluate", report["id"])
    db.commit()
    return report


@router.get("/reports")
def reports(db: Session = Depends(get_db), user=Depends(current_user)):
    return listing(db, ValidationReport)


@router.get("/reports/{identifier}")
def report(identifier: str, db: Session = Depends(get_db), user=Depends(current_user)):
    return require(db, ValidationReport, identifier).as_dict()
