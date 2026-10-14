import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from app.core.config import CORS_ORIGINS, SECRET_KEY
from app.infrastructure.database import SessionLocal
from app.infrastructure.models import Job
from app.modules.platform.api.routes import router as platform_router
from app.modules.platform.api.files import router as files_router
from app.modules.knowledge_graph.api.routes import router as knowledge_router
from app.modules.hybrid_reasoning.api.routes import router as reasoning_router
from app.modules.constraint_validation.api.routes import router as validation_router
from app.modules.agent_orchestration.api.routes import router as orchestration_router
from app.modules.agent_orchestration.adapters.protocols import (
    router as protocols_router,
)
from app.modules.agent_orchestration.services.executor import append_event
from app.modules.blisk_cam.api.routes import router as cam_router
from app.modules.cnc_phm.api.routes import router as phm_router


@asynccontextmanager
async def lifespan(app):
    if len(SECRET_KEY) < 32 or SECRET_KEY.startswith("REPLACE_"):
        raise RuntimeError("请在backend/.env中配置至少32位随机SECRET_KEY")
    with SessionLocal() as db:
        for job in db.scalars(
            select(Job).where(Job.status.in_(["submitted", "running"]))
        ):
            job.status = "failed"
            job.error = "服务重启中断了运行，请检查已完成节点后重新提交任务"
            append_event(db, job.id, job.error, level="error")
        db.commit()
    yield


app = FastAPI(
    title="iKEAP-platform",
    version="1.0.0",
    description="工业软件云平台接口",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "MCP-Protocol-Version", "Accept"],
)
for router in [
    platform_router,
    files_router,
    knowledge_router,
    reasoning_router,
    validation_router,
    orchestration_router,
    cam_router,
    phm_router,
]:
    app.include_router(router, prefix="/api/v1")
app.include_router(protocols_router)


@app.exception_handler(IntegrityError)
async def integrity_error(request: Request, error: IntegrityError):
    return JSONResponse(
        status_code=409, content={"detail": "数据重复或关联约束不满足，请检查输入"}
    )


@app.exception_handler(SQLAlchemyError)
async def database_error(request: Request, error: SQLAlchemyError):
    logging.getLogger("ikeap").error(
        "Database operation failed: %s", type(error).__name__
    )
    return JSONResponse(
        status_code=503, content={"detail": "数据库操作失败，请检查连接与迁移状态"}
    )


@app.get("/health")
def health():
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
        return {"status": "ok", "service": "iKEAP-platform", "database": "connected"}
    except SQLAlchemyError:
        return JSONResponse(
            status_code=503, content={"status": "degraded", "database": "unavailable"}
        )
