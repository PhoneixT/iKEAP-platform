from datetime import datetime
from typing import Literal
from pydantic import Field, model_validator
from app.modules.knowledge_graph.schemas.contracts import Contract


class MachineInput(Contract):
    name: str = Field(min_length=1, max_length=120)
    code: str = Field(min_length=1, max_length=60)
    component: str = Field(default="主轴", max_length=80)
    thresholds: dict[str, float] = Field(
        default_factory=lambda: {"vibration_rms": 4.5, "temperature": 75}
    )


class Measurement(Contract):
    time: datetime
    vibration_rms: float = Field(ge=0, le=1000)
    temperature: float = Field(ge=-100, le=1000)


class TelemetryInput(Contract):
    samples: list[Measurement] = Field(min_length=1, max_length=5000)


class DiagnosticInput(Contract):
    mode: Literal["template", "external"] = "template"


class RulInput(Contract):
    failure_threshold: float = Field(default=7.1, gt=0, le=1000)


class MaintenanceInput(Contract):
    anomaly_id: str
    title: str = Field(min_length=1, max_length=160)
    assignee: str = Field(min_length=1, max_length=80)
    actions: list[str] = Field(min_length=1, max_length=30)


class MaintenanceUpdate(Contract):
    status: Literal["in_progress", "completed"]
    feedback: str = Field(default="", max_length=10000)

    @model_validator(mode="after")
    def completion_feedback(self):
        if self.status == "completed" and not self.feedback:
            raise ValueError("完成维护需要填写反馈")
        return self
