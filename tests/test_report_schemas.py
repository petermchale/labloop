"""Keep model-facing ontology names compatible with the receiving vault."""
import pytest
from pydantic import ValidationError

from labloop.knowledge import Vault
from labloop.report_schemas import ActorReport, Distillation


@pytest.mark.parametrize("name", ["CrossoverCandidate", "GenomicCrossoverCandidate", "A", "A" * 64])
def test_report_type_names_are_accepted_by_vault(tmp_path, name):
    actor = ActorReport.model_validate({
        "summary": "Baseline candidates", "needs_input": None,
        "products": [{"key": "CO01", "type_name": name,
                      "description": "Proposed candidate", "evidence": ["candidate.tsv"]}],
    })
    distillation = Distillation(lessons=[], retract=[], new_types=[name], needs_input=None)
    vault = Vault(tmp_path / "vault")
    vault.add_type(actor.products[0].type_name)
    vault.add_type(distillation.new_types[0])
    assert name in vault.records


@pytest.mark.parametrize("name", [
    "genomic_crossover_candidate", "crossover_candidate_ledger", "scientific_analysis",
    "", "lowercase", "Two Words", "../Escape", "A" * 65, "Candidate\n",
])
def test_invalid_names_fail_at_report_boundary(name):
    with pytest.raises(ValidationError):
        ActorReport.model_validate({
            "summary": "Invalid type", "needs_input": None,
            "products": [{"key": "CO01", "type_name": name,
                          "description": "Candidate", "evidence": ["candidate.tsv"]}],
        })
    with pytest.raises(ValidationError):
        Distillation(lessons=[], retract=[], new_types=[name], needs_input=None)


def test_codex_json_schemas_expose_type_name_constraints():
    actor = ActorReport.model_json_schema()
    actor_type = actor["$defs"]["WorkProduct"]["properties"]["type_name"]
    distiller_type = Distillation.model_json_schema()["properties"]["new_types"]["items"]
    for constraint in (actor_type, distiller_type):
        assert constraint["pattern"] == r"^[A-Z][A-Za-z0-9]{0,63}$"
        assert constraint["maxLength"] == 64
