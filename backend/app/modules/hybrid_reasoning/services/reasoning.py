from fastapi import HTTPException
from app.modules.knowledge_graph.services.retrieval import retrieve
from app.modules.constraint_validation.services.engine import evaluate
from app.modules.hybrid_reasoning.adapters.model_service import generate
from app.modules.hybrid_reasoning.models.entities import ReasoningRun
from app.modules.blisk_cam.schemas.contracts import CamParameters
from pydantic import ValidationError
from app.modules.hybrid_reasoning.services.task_parser import parse_task


def run_reasoning(
    db, task, domain="cam", mode="template", parameters=None, resource_id=None
):
    specification = parse_task(task, domain, parameters)
    parameters = specification["parameters"]
    if domain == "cam":
        try:
            parameters = CamParameters.model_validate(parameters).model_dump()
        except ValidationError:
            raise HTTPException(422, "CAM参数需包含有效的正数转速、进给、切深和刀径")
    evidence = retrieve(db, task)
    if not evidence["evidence"]:
        raise HTTPException(422, "未检索到可用证据，请补充知识后重试")
    references = [item["evidence_id"] for item in evidence["evidence"][:4]]
    if mode == "external":
        candidates, metadata = generate(task, evidence, domain, parameters)
    elif domain == "cam":
        baseline = {
            "spindle_speed": 3200,
            "feed_rate": 600,
            "cut_depth": 0.3,
            "tool_diameter": 8,
            **parameters,
        }
        candidates = [
            {
                "name": "稳健加工方案",
                "description": "依据示例工艺模板组织粗加工、半精加工和精加工；参数需由工艺人员复核。",
                "parameters": baseline,
                "evidence_ids": references,
                "actions": [
                    "检查几何与装夹",
                    "分层粗加工",
                    "叶片侧铣精加工",
                    "仿真验证",
                ],
            },
            {
                "name": "低负载加工方案",
                "description": "降低进给和切深，作为候选参数组合用于比选。",
                "parameters": {
                    **baseline,
                    "feed_rate": min(float(baseline["feed_rate"]), 400),
                    "cut_depth": min(float(baseline["cut_depth"]), 0.2),
                },
                "evidence_ids": references,
                "actions": [
                    "检查刀具伸出量",
                    "低负载半精加工",
                    "叶片精加工",
                    "仿真验证",
                ],
            },
        ]
        metadata = {
            "mode": "template",
            "model": "deterministic-process-template",
            "version": "1.0",
            "result_source": "演示规则模板",
        }
    else:
        candidates = [
            {
                "name": "主轴轴承状态检查",
                "description": "候选原因，需结合频谱、温升和现场检查确认。",
                "parameters": parameters,
                "evidence_ids": references,
                "actions": ["复核传感器安装", "检查轴承特征频率", "核对润滑状态"],
            },
            {
                "name": "润滑或装配状态检查",
                "description": "候选原因，优先补充润滑记录和振动测量。",
                "parameters": parameters,
                "evidence_ids": references,
                "actions": ["检查润滑供给", "检查紧固与同轴度", "复测振动及温度"],
            },
        ]
        metadata = {
            "mode": "template",
            "model": "deterministic-diagnostic-template",
            "version": "1.0",
            "result_source": "演示规则模板",
        }
    for index, candidate in enumerate(candidates):
        candidate["id"] = f"candidate-{index + 1}"
        candidate["validation"] = evaluate(
            db,
            domain,
            candidate["parameters"],
            resource_id=resource_id,
            name=candidate["name"],
        )
    metadata["task_specification"] = specification
    record = ReasoningRun(
        title=task[:160],
        task=task,
        domain=domain,
        mode=mode,
        evidence=evidence,
        candidates=candidates,
        service_metadata=metadata,
    )
    db.add(record)
    db.flush()
    return record.as_dict()
