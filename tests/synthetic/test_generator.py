from dataclasses import replace
from pathlib import Path

from scripts.generate_synthetic import ARCHETYPES, FAULT_NAMES, generate, load_scenario

ROOT = Path(__file__).resolve().parents[2]


def test_synthetic_ecosystem_is_reproducible(tmp_path: Path) -> None:
    configured = load_scenario(ROOT / "data" / "synthetic" / "scenario.json")
    assert configured.documents == 10_000
    assert configured.organisations == 20

    scenario = replace(configured, documents=600)
    first = generate(scenario, tmp_path / "first")
    second = generate(scenario, tmp_path / "second")

    assert first == second
    assert (tmp_path / "first" / "documents.jsonl").read_bytes() == (
        tmp_path / "second" / "documents.jsonl"
    ).read_bytes()
    assert set(first["archetypes"]) == set(ARCHETYPES)
    assert set(first["ontology_versions"]) == {"1.0.0", "1.1.0", "2.0.0"}
    assert set(first["faults"]) >= set(FAULT_NAMES)
