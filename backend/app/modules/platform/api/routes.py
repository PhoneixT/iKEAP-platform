import os
from fastapi import APIRouter, Depends, HTTPException
from pydantic import Field
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.core.security import (
    current_user,
    writer,
    administrator,
    verify_password,
    hash_password,
    token_for,
)
from app.infrastructure.database import get_db
from app.infrastructure.models import (
    User,
    Resource,
    AuditLog,
    Job,
    Entity,
    Relation,
    Document,
    CamProject,
    Machine,
    Anomaly,
    ReasoningRun,
    ValidationReport,
    Workflow,
)
from app.shared.services import listing, save, audit
from app.modules.knowledge_graph.schemas.contracts import Contract

router = APIRouter(tags=["平台"])


class LoginInput(Contract):
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=128)


class UserInput(Contract):
    username: str = Field(min_length=2, max_length=80)
    display_name: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=12, max_length=128)
    role: str = Field(pattern="^(admin|engineer|viewer)$")


class ResourceInput(Contract):
    name: str = Field(min_length=1, max_length=120)
    kind: str = Field(min_length=1, max_length=40)
    description: str = Field(default="", max_length=10000)
    capabilities: dict = Field(default_factory=dict)
    status: str = Field(
        default="available", pattern="^(available|offline|maintenance)$"
    )


@router.post("/auth/login")
def login(body: LoginInput, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.username == body.username))
    if (
        not user
        or not user.active
        or not verify_password(body.password, user.password_hash)
    ):
        raise HTTPException(401, "用户名或密码错误")
    audit(db, user, "auth.login")
    db.commit()
    return {
        "access_token": token_for(user),
        "token_type": "bearer",
        "user": {
            key: val for key, val in user.as_dict().items() if key != "password_hash"
        },
    }


@router.get("/auth/me")
def me(user=Depends(current_user)):
    return {key: val for key, val in user.as_dict().items() if key != "password_hash"}


@router.get("/platform/users")
def users(db: Session = Depends(get_db), user=Depends(administrator)):
    return [
        {k: v for k, v in row.items() if k != "password_hash"}
        for row in listing(db, User)
    ]


@router.post("/platform/users", status_code=201)
def create_user(
    body: UserInput, db: Session = Depends(get_db), user=Depends(administrator)
):
    result = save(
        db,
        User(
            username=body.username,
            display_name=body.display_name,
            role=body.role,
            password_hash=hash_password(body.password),
        ),
        user,
        "platform.user.create",
    )
    result.pop("password_hash")
    return result


@router.get("/platform/resources")
def resources(db: Session = Depends(get_db), user=Depends(current_user)):
    return listing(db, Resource)


@router.post("/platform/resources", status_code=201)
def create_resource(
    body: ResourceInput, db: Session = Depends(get_db), user=Depends(writer)
):
    return save(db, Resource(**body.model_dump()), user, "platform.resource.create")


@router.get("/platform/audit")
def audits(db: Session = Depends(get_db), user=Depends(administrator)):
    return listing(db, AuditLog)


@router.get("/platform/services")
def services(user=Depends(current_user)):
    return [
        {
            "name": "知识检索",
            "kind": "internal",
            "configured": True,
            "version": "1.0",
            "description": "MySQL图数据与字符片段检索",
        },
        {
            "name": "约束验证",
            "kind": "internal",
            "configured": True,
            "version": "1.0",
            "description": "参数、单位与资源能力检查",
        },
        {
            "name": "大语言模型",
            "kind": "external",
            "configured": bool(os.getenv("MODEL_BASE_URL") and os.getenv("MODEL_NAME")),
            "version": os.getenv("MODEL_NAME") or "未配置",
            "description": "兼容chat-completions接口",
        },
        {
            "name": "CAM工程服务",
            "kind": "external",
            "configured": bool(os.getenv("CAM_SERVICE_URL")),
            "version": "HTTP adapter v1",
            "description": "刀路、仿真、程序分发接口",
        },
        {
            "name": "RUL趋势估计",
            "kind": "internal",
            "configured": True,
            "version": "linear-trend-v1",
            "description": "趋势外推示例，结果不能替代经验证的寿命模型",
        },
        {
            "name": "MCP工具端点",
            "kind": "protocol",
            "configured": True,
            "version": "2025-06-18",
            "description": "/mcp，stateless JSON HTTP",
        },
        {
            "name": "A2A任务端点",
            "kind": "protocol",
            "configured": True,
            "version": "0.3.0 subset",
            "description": "/a2a，JSON-RPC任务交换",
        },
    ]


@router.get("/platform/overview")
def overview(db: Session = Depends(get_db), user=Depends(current_user)):
    counts = {
        name: db.scalar(select(func.count()).select_from(model))
        for name, model in [
            ("entities", Entity),
            ("relations", Relation),
            ("documents", Document),
            ("cam_projects", CamProject),
            ("machines", Machine),
            ("anomalies", Anomaly),
            ("reasoning_runs", ReasoningRun),
            ("validation_reports", ValidationReport),
            ("workflows", Workflow),
        ]
    }
    counts["active_jobs"] = db.scalar(
        select(func.count())
        .select_from(Job)
        .where(Job.status.in_(["submitted", "running"]))
    )
    counts["open_anomalies"] = db.scalar(
        select(func.count()).select_from(Anomaly).where(Anomaly.status != "closed")
    )
    return {
        "counts": counts,
        "recent_jobs": listing(db, Job, 6),
        "recent_reports": listing(db, ValidationReport, 5),
        "recent_anomalies": listing(db, Anomaly, 5),
        "architecture": [
            {"name": "资源层", "description": "设备 · 软件 · 数据 · 算力"},
            {"name": "使能层", "description": "知识 · 检索 · 推理 · 验证"},
            {"name": "驱动层", "description": "Agent · 编排 · 调度 · 反馈"},
            {"name": "应用层", "description": "叶盘CAM · 机床PHM"},
        ],
    }
