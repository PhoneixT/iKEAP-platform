from typing import Literal
from pydantic import Field
from app.modules.knowledge_graph.schemas.contracts import Contract


class ReasoningInput(Contract):
    task: str = Field(min_length=2, max_length=5000)
    domain: Literal["cam", "phm"] = "cam"
    mode: Literal["template", "external"] = "template"
    parameters: dict = Field(default_factory=dict)
    resource_id: str | None = None


class Candidate(Contract):
    name: str = Field(min_length=1, max_length=160)
    description: str = Field(max_length=5000)
    parameters: dict
    evidence_ids: list[str] = Field(min_length=1, max_length=30)
    actions: list[str] = Field(default_factory=list, max_length=30)


class ModelOutput(Contract):
    candidates: list[Candidate] = Field(min_length=1, max_length=5)
