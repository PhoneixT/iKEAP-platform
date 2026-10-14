from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.security import current_user, writer
from app.infrastructure.database import get_db
from app.modules.platform.models.entities import Resource, FileAsset
from app.modules.blisk_cam.models.entities import CamProject
from app.modules.blisk_cam.schemas.contracts import (
    CamProjectInput,
    SimulationInput,
    MachiningFeedback,
    AlgorithmInput,
)
from app.modules.blisk_cam.services.metaalgorithm import (
    optimize_parameters,
    generate_toolpath,
)
from app.modules.blisk_cam.services.workflow import (
    plan_project,
    simulate_project,
    approve_project,
    dispatch_project,
)
from app.shared.services import listing, require, save, audit

router = APIRouter(prefix="/blisk-cam", tags=["叶盘CAM"])


@router.get("/projects")
def projects(db: Session = Depends(get_db), user=Depends(current_user)):
    return listing(db, CamProject)


@router.post("/projects", status_code=201)
def create_project(
    body: CamProjectInput, db: Session = Depends(get_db), user=Depends(writer)
):
    if body.resource_id:
        require(db, Resource, body.resource_id)
    if body.geometry_file_id:
        asset = require(db, FileAsset, body.geometry_file_id)
        if not asset.name.lower().endswith((".step", ".stp", ".stl")):
            raise HTTPException(422, "几何文件应为STEP、STP或STL")
    return save(db, CamProject(**body.model_dump()), user, "cam.project.create")


@router.get("/projects/{identifier}")
def project(identifier: str, db: Session = Depends(get_db), user=Depends(current_user)):
    return require(db, CamProject, identifier).as_dict()


def commit_result(db, user, identifier, operation, result):
    audit(db, user, "cam." + operation, identifier)
    db.commit()
    return result


@router.post("/projects/{identifier}/plan")
def plan(identifier: str, db: Session = Depends(get_db), user=Depends(writer)):
    return commit_result(db, user, identifier, "plan", plan_project(db, identifier))


@router.post("/projects/{identifier}/simulate")
def simulate(
    identifier: str,
    body: SimulationInput,
    db: Session = Depends(get_db),
    user=Depends(writer),
):
    return commit_result(
        db, user, identifier, "simulate", simulate_project(db, identifier, body.mode)
    )


@router.post("/projects/{identifier}/algorithm")
def algorithm(
    identifier: str,
    body: AlgorithmInput,
    db: Session = Depends(get_db),
    user=Depends(writer),
):
    return commit_result(
        db,
        user,
        identifier,
        "algorithm",
        optimize_parameters(db, identifier, **body.model_dump()),
    )


@router.post("/projects/{identifier}/toolpath")
def toolpath(identifier: str, db: Session = Depends(get_db), user=Depends(writer)):
    return commit_result(
        db, user, identifier, "toolpath", generate_toolpath(db, identifier)
    )


@router.post("/projects/{identifier}/approve")
def approve(identifier: str, db: Session = Depends(get_db), user=Depends(writer)):
    return commit_result(
        db, user, identifier, "approve", approve_project(db, identifier, user.username)
    )


@router.post("/projects/{identifier}/dispatch")
def dispatch(identifier: str, db: Session = Depends(get_db), user=Depends(writer)):
    return commit_result(
        db, user, identifier, "dispatch", dispatch_project(db, identifier)
    )


@router.post("/projects/{identifier}/feedback")
def feedback(
    identifier: str,
    body: MachiningFeedback,
    db: Session = Depends(get_db),
    user=Depends(writer),
):
    record = require(db, CamProject, identifier)
    if record.status != "dispatched":
        raise HTTPException(409, "仅已分发项目可以提交执行反馈")
    record.execution = {**record.execution, "feedback": body.model_dump()}
    record.status = "completed" if body.accepted else "needs_review"
    return save(db, record, user, "cam.feedback")
