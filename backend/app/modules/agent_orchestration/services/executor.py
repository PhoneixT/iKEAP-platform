import hashlib
from fastapi import HTTPException
from sqlalchemy import select, func, update
from sqlalchemy.exc import IntegrityError
from app.infrastructure.database import SessionLocal
from app.modules.platform.models.entities import Job, JobEvent, Resource
from app.modules.agent_orchestration.models.entities import Workflow
from app.modules.knowledge_graph.schemas.contracts import SearchInput
from app.modules.knowledge_graph.services.retrieval import retrieve
from app.modules.hybrid_reasoning.schemas.contracts import ReasoningInput
from app.modules.hybrid_reasoning.services.reasoning import run_reasoning
from app.modules.constraint_validation.schemas.contracts import ValidationInput
from app.modules.constraint_validation.services.engine import evaluate
from app.modules.blisk_cam.services.workflow import plan_project
from app.modules.cnc_phm.services.diagnostics import diagnose
from app.shared.services import require, listing

ACTIONS = {
    "knowledge.search": "知识与证据检索",
    "reasoning.generate": "候选方案生成",
    "constraints.validate": "工业约束验证",
    "cam.plan": "叶盘工艺规划",
    "phm.diagnose": "故障候选分析",
    "resources.list": "资源查询",
}


def ordered_nodes(nodes):
    mapping = {n["id"]: n for n in nodes}
    if len(mapping) != len(nodes):
        raise HTTPException(422, "流程节点编号不能重复")
    for node in nodes:
        if node["action"] not in ACTIONS:
            raise HTTPException(422, "不支持的节点动作：" + node["action"])
        if not set(node["depends_on"]).issubset(mapping):
            raise HTTPException(422, "流程引用不存在的依赖节点")
    pending, done, result = list(nodes), set(), []
    while pending:
        ready = [node for node in pending if set(node["depends_on"]).issubset(done)]
        if not ready:
            raise HTTPException(422, "流程存在循环依赖")
        for node in ready:
            pending.remove(node)
            done.add(node["id"])
            result.append(node)
    return result


def resolve(value, context, outputs):
    if isinstance(value, dict):
        if set(value) == {"$ref"}:
            reference = value["$ref"]
            if not isinstance(reference, str) or len(reference) > 300:
                raise ValueError("无效输入引用")
            current = {"context": context, "nodes": outputs}
            for key in reference.split("."):
                if isinstance(current, dict) and key in current:
                    current = current[key]
                else:
                    raise ValueError("输入引用不存在：" + reference)
            return current
        return {k: resolve(v, context, outputs) for k, v in value.items()}
    if isinstance(value, list):
        return [resolve(v, context, outputs) for v in value]
    return value


def execute_action(db, action, data):
    if action == "knowledge.search":
        return retrieve(db, **SearchInput.model_validate(data).model_dump())
    if action == "reasoning.generate":
        return run_reasoning(db, **ReasoningInput.model_validate(data).model_dump())
    if action == "constraints.validate":
        return evaluate(db, **ValidationInput.model_validate(data).model_dump())
    if action == "cam.plan":
        return plan_project(db, data["project_id"])
    if action == "phm.diagnose":
        return diagnose(db, data["anomaly_id"], data.get("mode", "template"))
    if action == "resources.list":
        return {"resources": listing(db, Resource)}
    raise ValueError("节点动作未注册")


def append_event(db, job_id, message, payload=None, level="info"):
    sequence = (
        db.scalar(select(func.max(JobEvent.sequence)).where(JobEvent.job_id == job_id))
        or 0
    ) + 1
    db.add(
        JobEvent(
            job_id=job_id,
            sequence=sequence,
            message=message,
            payload=payload or {},
            level=level,
        )
    )


def submit(db, workflow_id, context, owner, idempotency_key=None):
    workflow = require(db, Workflow, workflow_id)
    ordered_nodes(workflow.nodes)
    job_input = {
        "workflow_id": workflow.id,
        "workflow_version": workflow.version,
        "nodes": workflow.nodes,
        "context": context,
    }
    key = (
        hashlib.sha256((owner.id + ":" + idempotency_key).encode()).hexdigest()
        if idempotency_key
        else None
    )
    if key:
        previous = db.scalar(select(Job).where(Job.idempotency_key == key))
        if previous:
            if previous.input_data != job_input:
                raise HTTPException(409, "幂等键已用于不同请求")
            return previous, False
    job = Job(
        name=workflow.name,
        module="agent_orchestration",
        owner_id=owner.id,
        input_data=job_input,
        idempotency_key=key,
    )
    db.add(job)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        if key:
            previous = db.scalar(select(Job).where(Job.idempotency_key == key))
            if previous and previous.input_data == job_input:
                return previous, False
        raise HTTPException(409, "任务提交冲突，请重新查询")
    append_event(db, job.id, "任务已提交", {"workflow_version": workflow.version})
    db.commit()
    return job, True


def run_job(job_id):
    with SessionLocal() as db:
        claimed = db.execute(
            update(Job)
            .where(Job.id == job_id, Job.status == "submitted")
            .values(status="running")
        ).rowcount
        if not claimed:
            db.rollback()
            return
        db.commit()
        job = require(db, Job, job_id)
        outputs = {}
        try:
            nodes = ordered_nodes(job.input_data["nodes"])
            for index, node in enumerate(nodes):
                db.refresh(job)
                if job.status == "cancelled":
                    append_event(db, job.id, "取消已在节点边界生效")
                    db.commit()
                    return
                append_event(
                    db, job.id, "节点开始：" + node["id"], {"action": node["action"]}
                )
                db.commit()
                data = resolve(node["input"], job.input_data["context"], outputs)
                outputs[node["id"]] = execute_action(db, node["action"], data)
                # 检查并保留其他请求写入的取消状态。
                db.refresh(job)
                job.result = {"outputs": outputs}
                job.progress = round((index + 1) / len(nodes) * 100)
                append_event(
                    db, job.id, "节点完成：" + node["id"], {"action": node["action"]}
                )
                db.commit()
                if (
                    node["action"] == "constraints.validate"
                    and outputs[node["id"]]["status"] != "passed"
                ):
                    raise HTTPException(422, "约束验证未通过，已停止后续节点")
            db.refresh(job)
            if job.status != "cancelled":
                job.status = "completed"
                append_event(db, job.id, "流程执行完成")
                db.commit()
        except Exception as error:
            db.rollback()
            db.refresh(job)
            if job.status != "cancelled":
                job.status = "failed"
                job.error = (
                    str(error.detail)
                    if isinstance(error, HTTPException)
                    else str(error)[:1000]
                )
                append_event(db, job.id, "流程执行失败", {"error": job.error}, "error")
                db.commit()
