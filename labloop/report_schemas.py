"""Structured report schemas for actor, critic, and distiller outputs."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class Schema(BaseModel):
    model_config = ConfigDict(extra="forbid")


class WorkProduct(Schema):
    key: str
    type_name: str
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
    new_types: list[str]
    needs_input: str | None
