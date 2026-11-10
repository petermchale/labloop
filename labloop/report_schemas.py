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


class IgvView(Schema):
    start: int = Field(ge=1, le=2_147_483_647, description="First base, 1-based inclusive")
    end: int = Field(ge=1, le=2_147_483_647, description="Last base, 1-based inclusive")
    display: Literal["collapse", "squish", "expand"]
    sort: Literal["POSITION", "BASE", "STRAND", "QUALITY", "READNAME", "HAPLOTYPE"]
    group: Literal["NONE", "STRAND", "SAMPLE", "READ_GROUP", "PHASE"]
    color: Literal["NONE", "READ_STRAND", "SAMPLE", "READ_GROUP", "MAPPED_SIZE"]
    track_indices: list[int] | None = Field(
        description="Zero-based indices into the product's track list, in display order, or null for all",
    )


class IgvSnapshot(Schema):
    reference: str = Field(description="Project-relative indexed FASTA")
    tracks: list[str] = Field(min_length=1, description="Project-relative indexed BAM and optional VCF.gz tracks")
    chromosome: str = Field(pattern=r"^[A-Za-z0-9_.-]+$")
    view: IgvView


class IgvWorkProduct(WorkProduct):
    igv_snapshot: IgvSnapshot | None


class IgvActorReport(ActorReport):
    products: list[IgvWorkProduct]


class IgvCritique(Critique):
    igv_views: list[IgvView] | None = Field(
        max_length=4, description="Additional views to inspect before returning a final verdict, or null",
    )


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
