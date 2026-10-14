from typing import Literal
from pydantic import Field, model_validator
from app.modules.knowledge_graph.schemas.contracts import Contract


class RuleInput(Contract):
    name: str = Field(min_length=1, max_length=120)
    scope: Literal["cam", "phm", "global"]
    field: str = Field(min_length=1, max_length=80)
    operator: Literal["between", "lte", "gte", "eq", "in", "required"]
    expected: dict = Field(default_factory=dict)
    unit: str = Field(default="", max_length=30)
    severity: Literal["hard", "soft"] = "hard"
    enabled: bool = True

    @model_validator(mode="after")
    def valid_expected(self):
        import math

        if self.operator in {"between", "lte", "gte"}:
            keys = ["min", "max"] if self.operator == "between" else ["value"]
            if any(
                type(self.expected.get(k)) not in (int, float)
                or not math.isfinite(self.expected[k])
                for k in keys
            ):
                raise ValueError("数值规则需要有效的有限数值")
            if (
                self.operator == "between"
                and self.expected["min"] > self.expected["max"]
            ):
                raise ValueError("下界不能大于上界")
        if self.operator == "in" and not isinstance(self.expected.get("values"), list):
            raise ValueError("in规则需要values数组")
        if self.operator == "eq" and "value" not in self.expected:
            raise ValueError("eq规则需要value")
        return self


class ValidationInput(Contract):
    name: str = Field(default="工业约束验证", max_length=160)
    scope: Literal["cam", "phm"]
    parameters: dict
    units: dict[str, str] = Field(default_factory=dict)
    resource_id: str | None = None
    semantic_constraints: "SemanticConstraints" = Field(
        default_factory=lambda: SemanticConstraints()
    )


class SemanticEntity(Contract):
    entity_id: str
    expected_kind: str = Field(min_length=1, max_length=60)


class SemanticRelation(Contract):
    source_id: str
    target_id: str
    kind: str = Field(min_length=1, max_length=60)


class SemanticConstraints(Contract):
    entities: list[SemanticEntity] = Field(default_factory=list, max_length=100)
    relations: list[SemanticRelation] = Field(default_factory=list, max_length=100)
