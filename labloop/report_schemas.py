"""Structured report schemas for actor, critic, and distiller outputs."""
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, WithJsonSchema, create_model


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


class BatchVerdict(Critique):
    key: str


class IgvBatchVerdict(IgvCritique):
    key: str


class CritiqueBatch(Schema):
    reviews: list[BatchVerdict]


class IgvCritiqueBatch(Schema):
    reviews: list[IgvBatchVerdict]


def batch_review_schema(product_keys: tuple[str, ...], *, igv: bool):
    batch, verdict = (IgvCritiqueBatch, IgvBatchVerdict) if igv else (CritiqueBatch, BatchVerdict)
    keyed_verdict = create_model(verdict.__name__, __base__=verdict,
                                 key=(_allowed_strings(product_keys), ...))
    count = len(product_keys)
    return create_model(batch.__name__, __base__=batch,
                        reviews=(list[keyed_verdict], Field(min_length=count, max_length=count)))


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


def _allowed_strings(values: tuple[str, ...]):
    return Annotated[Literal[values], WithJsonSchema({"type": "string", "enum": list(values)})]


def distillation_schema(observation_ids: tuple[str, ...]) -> type[Distillation]:
    if not observation_ids:
        return create_model(
            "Distillation", __base__=Distillation,
            lessons=(list[Lesson], Field(max_length=0)),
            retract=(list[Retraction], Field(max_length=0)),
        )

    citation = _allowed_strings(observation_ids)
    lesson = create_model("Lesson", __base__=Lesson,
                          because=(list[citation], Field(min_length=1)))
    retraction = create_model("Retraction", __base__=Retraction,
                              because=(list[citation], Field(min_length=1)))
    return create_model("Distillation", __base__=Distillation,
                        lessons=(list[lesson], ...), retract=(list[retraction], ...))
