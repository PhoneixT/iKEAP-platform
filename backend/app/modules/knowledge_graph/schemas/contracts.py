from pydantic import BaseModel, ConfigDict, Field


class Contract(BaseModel):
    model_config = ConfigDict(
        extra="forbid", str_strip_whitespace=True, allow_inf_nan=False
    )


class EntityInput(Contract):
    name: str = Field(min_length=1, max_length=120)
    kind: str = Field(min_length=1, max_length=60)
    aliases: list[str] = Field(default_factory=list, max_length=30)
    properties: dict = Field(default_factory=dict)
    description: str = Field(default="", max_length=10000)
    source: str = Field(min_length=1, max_length=255)


class RelationInput(Contract):
    source_id: str
    target_id: str
    kind: str = Field(min_length=1, max_length=60)
    properties: dict = Field(default_factory=dict)
    source: str = Field(min_length=1, max_length=255)


class DocumentInput(Contract):
    title: str = Field(min_length=1, max_length=160)
    content: str = Field(min_length=1, max_length=100000)
    source: str = Field(min_length=1, max_length=255)
    entity_ids: list[str] = Field(default_factory=list, max_length=100)


class SearchInput(Contract):
    query: str = Field(min_length=1, max_length=2000)
    limit: int = Field(default=8, ge=1, le=30)
    hops: int = Field(default=2, ge=0, le=3)


class ImportInput(Contract):
    entities: list[EntityInput] = Field(default_factory=list, max_length=500)
    relations: list[dict] = Field(default_factory=list, max_length=1000)
    documents: list["DocumentImportInput"] = Field(default_factory=list, max_length=200)


class DocumentImportInput(DocumentInput):
    entity_keys: list[str] = Field(default_factory=list, max_length=100)
