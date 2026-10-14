from typing import Literal
from pydantic import Field
from app.modules.knowledge_graph.schemas.contracts import Contract


class AgentInput(Contract):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=5000)
    capabilities: list[str] = Field(min_length=1, max_length=30)
    protocol: Literal["internal", "mcp", "a2a"] = "internal"
    endpoint: str = Field(default="", max_length=255)
    version: str = Field(default="1.0.0", max_length=30)


class WorkflowNode(Contract):
    id: str = Field(pattern=r"^[a-zA-Z][a-zA-Z0-9_-]{0,39}$")
    action: str
    depends_on: list[str] = Field(default_factory=list, max_length=30)
    input: dict = Field(default_factory=dict)


class WorkflowInput(Contract):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=5000)
    nodes: list[WorkflowNode] = Field(min_length=1, max_length=30)


class WorkflowRunInput(Contract):
    context: dict = Field(default_factory=dict)
    idempotency_key: str | None = Field(default=None, max_length=100)
