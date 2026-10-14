from typing import Literal
from pydantic import Field
from app.modules.knowledge_graph.schemas.contracts import Contract


class CamParameters(Contract):
    spindle_speed: float = Field(default=3200, gt=0, le=100000)
    feed_rate: float = Field(default=600, gt=0, le=100000)
    cut_depth: float = Field(default=0.3, gt=0, le=100)
    tool_diameter: float = Field(default=8, gt=0, le=500)


class CamProjectInput(Contract):
    name: str = Field(min_length=1, max_length=160)
    material: str = Field(default="TC4", min_length=1, max_length=80)
    description: str = Field(default="", max_length=10000)
    resource_id: str | None = None
    geometry_file_id: str | None = None
    parameters: CamParameters = Field(default_factory=CamParameters)


class SimulationInput(Contract):
    mode: Literal["demonstration", "external"] = "demonstration"


class AlgorithmInput(Contract):
    mode: Literal["local", "external"] = "local"
    engagement_width_mm: float = Field(default=1, gt=0, le=500)


class MachiningFeedback(Contract):
    operator: str = Field(min_length=1, max_length=80)
    accepted: bool
    notes: str = Field(min_length=1, max_length=5000)
