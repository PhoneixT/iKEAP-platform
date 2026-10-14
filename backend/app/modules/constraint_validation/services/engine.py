import math
from sqlalchemy import select
from app.modules.constraint_validation.models.entities import Rule, ValidationReport
from app.modules.platform.models.entities import Resource
from app.shared.services import require
from app.modules.knowledge_graph.models.entities import Entity, Relation

CONVERSIONS = {
    ("m/s", "mm/s"): 1000,
    ("mm/s", "m/s"): 0.001,
    ("m", "mm"): 1000,
    ("mm", "m"): 0.001,
    ("Hz", "rpm"): 60,
    ("rpm", "Hz"): 1 / 60,
}


def evaluate(
    db,
    scope,
    parameters,
    units=None,
    resource_id=None,
    name="工业约束验证",
    persist=True,
    semantic_constraints=None,
):
    units = units or {}
    findings = []
    for rule in db.scalars(
        select(Rule).where(Rule.enabled.is_(True), Rule.scope.in_([scope, "global"]))
    ):
        value = parameters.get(rule.field)
        state, reason = "unknown", "缺少必要参数"
        if value is not None:
            try:
                supplied_unit = units.get(rule.field, rule.unit)
                if supplied_unit != rule.unit:
                    if (supplied_unit, rule.unit) not in CONVERSIONS:
                        raise ValueError("不支持的单位换算")
                    value = float(value) * CONVERSIONS[(supplied_unit, rule.unit)]
                if rule.operator in {"between", "gte", "lte"}:
                    if (
                        isinstance(value, bool)
                        or not isinstance(value, (int, float))
                        or not math.isfinite(value)
                    ):
                        raise ValueError("参数必须为有限数值")
                exp = rule.expected
                if rule.operator == "between":
                    passed = exp["min"] <= value <= exp["max"]
                elif rule.operator == "gte":
                    passed = value >= exp["value"]
                elif rule.operator == "lte":
                    passed = value <= exp["value"]
                elif rule.operator == "eq":
                    passed = value == exp["value"]
                elif rule.operator == "in":
                    passed = value in exp["values"]
                else:
                    passed = value not in ("", [], {})
                state, reason = (
                    ("passed", "符合规则") if passed else ("failed", "不满足约束")
                )
            except (ValueError, TypeError, KeyError) as error:
                state, reason = "failed", str(error)
        findings.append(
            {
                "rule_id": rule.id,
                "rule_name": rule.name,
                "version": rule.version,
                "field": rule.field,
                "value": value,
                "unit": rule.unit,
                "expected": rule.expected,
                "severity": rule.severity,
                "status": state,
                "reason": reason,
            }
        )
    if resource_id:
        resource = require(db, Resource, resource_id)
        findings.append(
            {
                "rule_name": "资源可用性",
                "status": "passed" if resource.status == "available" else "failed",
                "severity": "hard",
                "value": resource.status,
                "reason": resource.name,
            }
        )
        for field, capability in [
            ("spindle_speed", "max_rpm"),
            ("feed_rate", "max_feed"),
            ("power", "max_power"),
        ]:
            if field in parameters:
                maximum = resource.capabilities.get(capability)
                value = parameters[field]
                canonical_unit = {
                    "spindle_speed": "rpm",
                    "feed_rate": "mm/min",
                    "power": "kW",
                }[field]
                unit = units.get(field, canonical_unit)
                if unit != canonical_unit:
                    factor = CONVERSIONS.get((unit, canonical_unit))
                    value = (
                        value * factor
                        if factor is not None and type(value) in (int, float)
                        else None
                    )
                valid_number = type(value) in (int, float) and math.isfinite(value)
                valid_maximum = type(maximum) in (int, float) and math.isfinite(maximum)
                state = (
                    "unknown"
                    if not valid_maximum
                    else "passed"
                    if valid_number and value <= maximum
                    else "failed"
                )
                findings.append(
                    {
                        "rule_name": f"资源能力：{field}",
                        "status": state,
                        "severity": "hard",
                        "value": value,
                        "expected": {"max": maximum},
                        "reason": resource.name,
                    }
                )
    semantic_constraints = semantic_constraints or {}
    for binding in semantic_constraints.get("entities", []):
        entity = db.get(Entity, binding["entity_id"])
        state = (
            "unknown"
            if not entity
            else "passed"
            if entity.kind == binding["expected_kind"]
            else "failed"
        )
        findings.append(
            {
                "rule_name": "语义实体类型检查",
                "severity": "hard",
                "status": state,
                "value": entity.kind if entity else None,
                "expected": {"kind": binding["expected_kind"]},
                "reason": entity.name if entity else "实体不存在",
            }
        )
    for binding in semantic_constraints.get("relations", []):
        relation = db.scalar(
            select(Relation).where(
                Relation.source_id == binding["source_id"],
                Relation.target_id == binding["target_id"],
                Relation.kind == binding["kind"],
            )
        )
        findings.append(
            {
                "rule_name": "语义关系一致性检查",
                "severity": "hard",
                "status": "passed" if relation else "failed",
                "expected": binding,
                "reason": relation.source if relation else "指定的有向关系不存在",
            }
        )
    hard = [f["status"] for f in findings if f["severity"] == "hard"]
    status = (
        "failed"
        if "failed" in hard
        else "unknown"
        if "unknown" in hard or not hard
        else "passed"
    )
    report = ValidationReport(
        name=name,
        scope=scope,
        status=status,
        input_data={
            "parameters": parameters,
            "units": units,
            "resource_id": resource_id,
            "semantic_constraints": semantic_constraints,
        },
        findings=findings,
    )
    if persist:
        db.add(report)
        db.flush()
        return report.as_dict()
    return {"status": status, "findings": findings}
