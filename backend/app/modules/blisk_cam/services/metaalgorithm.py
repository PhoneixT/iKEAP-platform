import math
from fastapi import HTTPException
from app.modules.blisk_cam.models.entities import CamProject
from app.modules.blisk_cam.adapters.engineering_service import call_engineering
from app.modules.blisk_cam.services.workflow import digest
from app.modules.constraint_validation.services.engine import evaluate
from app.shared.services import require


def optimize_parameters(db, project_id, mode="local", engagement_width_mm=1):
    project = require(db, CamProject, project_id)
    if project.status not in {"planned", "demonstrated"}:
        raise HTTPException(409, "请在工艺规划后、真实工程验证前调用算法")
    if engagement_width_mm > project.parameters["tool_diameter"]:
        raise HTTPException(422, "径向切宽不能大于刀具直径")
    if mode == "external":
        result = call_engineering(
            "algorithm",
            {
                "project": project.as_dict(),
                "engagement_width_mm": engagement_width_mm,
                "input_digest": digest(project),
            },
        )
        if not result.get("algorithm_version") or not isinstance(
            result.get("candidates"), list
        ):
            raise HTTPException(502, "算法服务缺少版本或候选结果")
    else:
        candidates = []
        for feed_factor in (0.7, 1.0, 1.2):
            for depth_factor in (0.5, 1.0, 1.2):
                parameters = {
                    **project.parameters,
                    "feed_rate": round(
                        project.parameters["feed_rate"] * feed_factor, 4
                    ),
                    "cut_depth": round(
                        project.parameters["cut_depth"] * depth_factor, 4
                    ),
                }
                validation = evaluate(
                    db,
                    "cam",
                    parameters,
                    resource_id=project.resource_id,
                    persist=False,
                )
                if validation["status"] == "passed":
                    candidates.append(
                        {
                            "parameters": parameters,
                            "theoretical_removal_mm3_min": round(
                                parameters["feed_rate"]
                                * parameters["cut_depth"]
                                * engagement_width_mm,
                                4,
                            ),
                            "cutting_speed_m_min": round(
                                math.pi
                                * parameters["tool_diameter"]
                                * parameters["spindle_speed"]
                                / 1000,
                                4,
                            ),
                            "validation_status": "passed",
                        }
                    )
        candidates.sort(
            key=lambda item: item["theoretical_removal_mm3_min"], reverse=True
        )
        result = {
            "algorithm_version": "bounded-grid-v1",
            "mode": "local",
            "candidates": candidates,
            "engagement_width_mm": engagement_width_mm,
            "input_digest": digest(project),
            "description": "有界参数网格搜索；以理想几何去除率排序。未考虑切削力、颤振与几何可达性，结果用于参数比选，不自动修改项目参数。",
        }
    project.execution = {**project.execution, "algorithm": result}
    db.flush()
    return project.as_dict()


def generate_toolpath(db, project_id):
    project = require(db, CamProject, project_id)
    if (
        project.status not in {"planned", "demonstrated"}
        or not project.geometry_file_id
    ):
        raise HTTPException(409, "请先规划工艺并绑定几何文件")
    report = evaluate(db, "cam", project.parameters, resource_id=project.resource_id)
    if report["status"] != "passed":
        raise HTTPException(422, "参数与资源验证未通过")
    from app.modules.platform.models.entities import FileAsset

    asset = require(db, FileAsset, project.geometry_file_id)
    result = call_engineering(
        "toolpath",
        {
            "project": project.as_dict(),
            "geometry": {
                "file_id": asset.id,
                "sha256": asset.sha256,
                "download_url": "/api/v1/platform/files/" + asset.id + "/download",
            },
            "input_digest": digest(project),
        },
    )
    if not result.get("artifact_id") or not result.get("software_version"):
        raise HTTPException(502, "刀路服务缺少产物编号或软件版本")
    project.execution = {**project.execution, "toolpath": result}
    db.flush()
    return project.as_dict()
