import hashlib
import json
import math
from fastapi import HTTPException
from app.modules.blisk_cam.models.entities import CamProject
from app.modules.blisk_cam.adapters.engineering_service import call_engineering
from app.modules.hybrid_reasoning.services.reasoning import run_reasoning
from app.modules.constraint_validation.services.engine import evaluate
from app.shared.services import require


def digest(project):
    data = {
        "id": project.id,
        "material": project.material,
        "parameters": project.parameters,
        "resource_id": project.resource_id,
        "geometry_file_id": project.geometry_file_id,
    }
    return hashlib.sha256(
        json.dumps(data, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()


def plan_project(db, project_id):
    project = require(db, CamProject, project_id)
    if project.status in {"approved", "dispatched", "completed"}:
        raise HTTPException(409, "项目已进入执行阶段，请建立新版本项目")
    run = run_reasoning(
        db,
        f"{project.material}叶盘加工工艺规划，刀具与五轴加工策略",
        "cam",
        "template",
        project.parameters,
        project.resource_id,
    )
    p = project.parameters
    project.plan = {
        "reasoning_run_id": run["id"],
        "input_digest": digest(project),
        "validation": run["candidates"][0]["validation"],
        "cutting_speed_m_min": round(
            math.pi * p["tool_diameter"] * p["spindle_speed"] / 1000, 3
        ),
        "operations": [
            {"sequence": 1, "name": "装夹与几何检查", "strategy": "检查定位和干涉边界"},
            {"sequence": 2, "name": "叶间通道粗加工", "strategy": "分层粗加工"},
            {"sequence": 3, "name": "叶片半精加工", "strategy": "余量均匀化"},
            {"sequence": 4, "name": "叶片精加工", "strategy": "五轴侧铣"},
            {"sequence": 5, "name": "检测与结果归档", "strategy": "尺寸与表面质量检查"},
        ],
        "source": "演示工艺模板，需工程审核",
    }
    project.execution = {}
    project.status = "planned"
    db.flush()
    return project.as_dict()


def simulate_project(db, project_id, mode="demonstration"):
    project = require(db, CamProject, project_id)
    if (
        project.status not in {"planned", "demonstrated", "simulated"}
        or not project.plan
    ):
        raise HTTPException(409, "请先生成工艺方案")
    report = evaluate(
        db,
        "cam",
        project.parameters,
        resource_id=project.resource_id,
        name=project.name + "执行前检查",
    )
    if report["status"] != "passed":
        raise HTTPException(422, "约束验证未通过，不能进入仿真")
    if mode == "demonstration":
        result = {
            "mode": mode,
            "engineering_verified": False,
            "message": "仅展示接口流转和工序顺序；未生成制造刀路或数控程序，未执行碰撞与过切仿真。",
            "input_digest": digest(project),
            "operation_count": len(project.plan["operations"]),
        }
        project.status = "demonstrated"
    else:
        toolpath = project.execution.get("toolpath", {})
        if (
            not project.geometry_file_id
            or toolpath.get("input_digest") != digest(project)
            or not toolpath.get("artifact_id")
        ):
            raise HTTPException(409, "真实仿真需要绑定几何文件并先生成当前版本刀路")
        result = call_engineering(
            "simulate", {"project": project.as_dict(), "input_digest": digest(project)}
        )
        if (
            result.get("collision_free") is not True
            or result.get("constraint_passed") is not True
            or not isinstance(result.get("program"), str)
            or not result["program"].strip()
            or not result.get("software_version")
        ):
            raise HTTPException(502, "仿真未通过或缺少程序、软件版本")
        result = {**result, "mode": "external", "engineering_verified": True}
        project.status = "simulated"
    project.execution = {
        **project.execution,
        "simulation": result,
        "validation_report_id": report["id"],
    }
    db.flush()
    return project.as_dict()


def approve_project(db, project_id, reviewer):
    project = require(db, CamProject, project_id)
    simulation = project.execution.get("simulation", {})
    if (
        project.status != "simulated"
        or not simulation.get("engineering_verified")
        or simulation.get("input_digest") != digest(project)
    ):
        raise HTTPException(409, "仅当前版本的真实工程仿真通过后可审核放行")
    project.execution = {
        **project.execution,
        "approval": {"reviewer": reviewer, "input_digest": digest(project)},
    }
    project.status = "approved"
    db.flush()
    return project.as_dict()


def dispatch_project(db, project_id):
    project = require(db, CamProject, project_id)
    if project.status != "approved" or not project.resource_id:
        raise HTTPException(409, "需要审核通过并绑定目标资源")
    report = evaluate(db, "cam", project.parameters, resource_id=project.resource_id)
    if report["status"] != "passed":
        raise HTTPException(409, "当前资源或参数验证未通过")
    result = call_engineering(
        "dispatch",
        {
            "project_id": project.id,
            "target_resource_id": project.resource_id,
            "program": project.execution["simulation"]["program"],
            "idempotency_key": project.id + ":" + digest(project),
            "input_digest": digest(project),
        },
    )
    if result.get("accepted") is not True or not result.get("receipt_id"):
        raise HTTPException(502, "未取得有效的程序接收回执")
    project.execution = {**project.execution, "dispatch": result}
    project.status = "dispatched"
    db.flush()
    return project.as_dict()
