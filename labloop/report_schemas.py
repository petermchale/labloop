"""Structured report schemas for actor, critic, and distiller outputs."""
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field


class Schema(BaseModel):
    model_config = ConfigDict(extra="forbid")


TypeName = Annotated[str, Field(
    pattern=r"^[A-Z][A-Za-z0-9]{0,63}$",
    max_length=64,
    description="Short PascalCase ontology type, e.g. CrossoverCandidate; no spaces or underscores.",
)]


class WorkProduct(Schema):
    key: str
    type_name: TypeName
    description: str
    evidence: list[str]  # Workspace-relative paths, not invented literature citations.


class ActorReport(Schema):
    summary: str
    products: list[WorkProduct]
    needs_input: str | None


class Critique(Schema):
    verdict: Literal["supported", "contradicted", "uncertain"]
    diagnosis: str
    evidence: list[str]
    needs_input: str | None


class Lesson(Schema):
    claim: str
    because: list[str] = Field(min_length=1)  # Observation IDs supplied by the host.
    test: str


class Retraction(Schema):
    target: str
    because: list[str] = Field(min_length=1)


class Distillation(Schema):
    lessons: list[Lesson]
    retract: list[Retraction]
    new_types: list[TypeName]
    needs_input: str | None
