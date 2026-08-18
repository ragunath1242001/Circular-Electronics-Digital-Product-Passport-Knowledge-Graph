import argparse
import hashlib
import json
import random
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import TypedDict, cast

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "data" / "synthetic" / "scenario.json"
DEFAULT_OUTPUT = ROOT / "data" / "synthetic" / "generated"
DPP = "https://example.org/dpp/"
SYNTHETIC = f"{DPP}synthetic/"
ARCHETYPES = (
    "strict_current",
    "legacy",
    "customizer",
    "external_vocab_heavy",
    "poor_quality",
    "innovator",
)
FAULT_NAMES = (
    "unknown_term",
    "custom_term",
    "deprecated_term",
    "datatype_error",
    "missing_required",
    "mapping_gap",
)
FAULT_DETAILS = {
    "unknown_term": (f"{DPP}experimentalThermalResilience", "unknown_term_detector"),
    "custom_term": ("organisation vocabulary", "custom_term_classifier"),
    "deprecated_term": (f"{DPP}chemistry", "deprecated_term_detector"),
    "datatype_error": (f"{DPP}batteryCapacity", "shacl_validation"),
    "missing_required": (f"{DPP}productIdentifier", "shacl_validation"),
    "mapping_gap": ("https://external.example/vocab/energyStorageGrade", "mapping_gap_detector"),
    "legacy_version": (f"{DPP}ontologyVersion", "version_drift_detector"),
}
ARCHETYPE_FACTORS = {
    "strict_current": {name: 0.1 for name in FAULT_NAMES},
    "legacy": {"deprecated_term": 3.0},
    "customizer": {"custom_term": 4.0},
    "external_vocab_heavy": {"mapping_gap": 4.0},
    "poor_quality": {"datatype_error": 4.0, "missing_required": 4.0},
    "innovator": {"unknown_term": 4.0},
}


class Organisation(TypedDict):
    id: str
    name: str
    iri: str
    archetype: str


class GenerationSummary(TypedDict):
    scenario: str
    seed: int
    documents: int
    organisations: int
    archetypes: dict[str, int]
    domains: dict[str, int]
    ontology_versions: dict[str, int]
    faults: dict[str, int]
    documents_sha256: str
    ground_truth_sha256: str


@dataclass(frozen=True)
class Scenario:
    name: str
    seed: int
    documents: int
    organisations: int
    electronics_share: float
    legacy_version_share: float
    fault_rates: dict[str, float]


def _mapping(value: object, label: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise TypeError(f"{label} must be an object.")
    return cast(dict[str, object], value)


def _string(values: dict[str, object], key: str) -> str:
    value = values.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{key} must be a non-empty string.")
    return value


def _integer(values: dict[str, object], key: str) -> int:
    value = values.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"{key} must be an integer.")
    return value


def _rate(values: dict[str, object], key: str) -> float:
    value = values.get(key)
    if not isinstance(value, int | float) or isinstance(value, bool) or not 0 <= value <= 1:
        raise ValueError(f"{key} must be between 0 and 1.")
    return float(value)


def load_scenario(path: Path = DEFAULT_CONFIG) -> Scenario:
    raw = _mapping(json.loads(path.read_text(encoding="utf-8")), "scenario")
    rates_raw = _mapping(raw.get("fault_rates"), "fault_rates")
    if set(rates_raw) != set(FAULT_NAMES):
        raise ValueError(f"fault_rates must define: {', '.join(FAULT_NAMES)}.")
    scenario = Scenario(
        name=_string(raw, "name"),
        seed=_integer(raw, "seed"),
        documents=_integer(raw, "documents"),
        organisations=_integer(raw, "organisations"),
        electronics_share=_rate(raw, "electronics_share"),
        legacy_version_share=_rate(raw, "legacy_version_share"),
        fault_rates={name: _rate(rates_raw, name) for name in FAULT_NAMES},
    )
    if scenario.documents < 1 or scenario.organisations < len(ARCHETYPES):
        raise ValueError(
            f"documents must be positive and organisations at least {len(ARCHETYPES)}."
        )
    return scenario


def _json_bytes(value: object, *, pretty: bool = False) -> bytes:
    if pretty:
        text = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False)
    else:
        text = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return (text + "\n").encode()


def _organisations(count: int, legacy_share: float) -> list[Organisation]:
    nonlegacy = tuple(item for item in ARCHETYPES if item != "legacy")
    legacy_count = min(count - len(nonlegacy), round(count * legacy_share))
    archetypes = ["legacy"] * legacy_count + [
        nonlegacy[index % len(nonlegacy)] for index in range(count - legacy_count)
    ]
    return [
        {
            "id": f"org-{index + 1:02d}",
            "name": f"Fictional Circular Organisation {index + 1:02d}",
            "iri": f"{SYNTHETIC}organisation/org-{index + 1:02d}",
            "archetype": archetypes[index],
        }
        for index in range(count)
    ]


def _should_inject(rng: random.Random, scenario: Scenario, archetype: str, fault: str) -> bool:
    factor = ARCHETYPE_FACTORS.get(archetype, {}).get(fault, 1.0)
    return rng.random() < min(1.0, scenario.fault_rates[fault] * factor)


def _fault(
    faults: list[dict[str, object]],
    scenario: Scenario,
    document_id: str,
    organisation_id: str,
    domain: str,
    fault_type: str,
    target: str | None = None,
) -> None:
    default_target, detector = FAULT_DETAILS[fault_type]
    faults.append(
        {
            "document_id": document_id,
            "organisation_id": organisation_id,
            "domain": domain,
            "fault_type": fault_type,
            "target_term_or_path": target or default_target,
            "expected_detector": detector,
            "seed": scenario.seed,
            "scenario": scenario.name,
        }
    )


def _document(
    rng: random.Random,
    scenario: Scenario,
    index: int,
    organisation: Organisation,
) -> tuple[dict[str, object], list[dict[str, object]]]:
    document_id = f"dpp-{index + 1:05d}"
    domain = "electronics" if rng.random() < scenario.electronics_share else "battery"
    legacy = organisation["archetype"] == "legacy"
    version = rng.choice(("1.0.0", "1.1.0")) if legacy else "2.0.0"
    profile = f"{domain}-2.0"
    product_id = f"product-{index + 1:05d}"
    battery_id = f"battery-{index + 1:05d}"
    battery: dict[str, object] = {
        "@id": f"{SYNTHETIC}battery/{battery_id}",
        "@type": ["dpp:Battery", "dpp:ProductModel"] if domain == "battery" else "dpp:Battery",
        "dpp:productIdentifier": battery_id.upper(),
        "dpp:batteryCapacity": {
            "@value": 3200 + index % 2801,
            "@type": "xsd:decimal",
        },
        "dpp:batteryCycleEndurance": 500 + index % 1001,
        "dpp:isUserReplaceable": index % 3 == 0,
    }
    chemistry_property = "dpp:chemistry" if version == "1.0.0" else "dpp:batteryChemistry"
    battery[chemistry_property] = ("LFP", "NMC 811", "NCA")[index % 3]

    product: dict[str, object]
    if domain == "electronics":
        product = {
            "@id": f"{SYNTHETIC}product/{product_id}",
            "@type": ["dpp:Smartphone", "dpp:ProductModel"],
            "dpp:productIdentifier": product_id.upper(),
            "dpp:modelNumber": f"SYN-{index % 200:03d}",
            "dpp:containsComponent": battery,
        }
    else:
        product = battery
    product["dpp:manufacturingDate"] = {
        "@value": f"{2020 + index % 6}-{index % 12 + 1:02d}-{index % 28 + 1:02d}",
        "@type": "xsd:date",
    }
    product["dpp:manufacturedBy"] = {
        "@id": organisation["iri"],
        "@type": "dpp:Manufacturer",
        "http://purl.org/dc/terms/title": organisation["name"],
    }

    payload: dict[str, object] = {
        "@context": {"dpp": DPP, "xsd": "http://www.w3.org/2001/XMLSchema#"},
        "@id": f"{SYNTHETIC}passport/{document_id}",
        "@type": "dpp:DigitalProductPassport",
        "dpp:ontologyVersion": version,
        "dpp:describesProduct": product,
    }
    faults: list[dict[str, object]] = []
    if legacy:
        _fault(faults, scenario, document_id, organisation["id"], domain, "legacy_version")
    if chemistry_property == "dpp:chemistry":
        _fault(faults, scenario, document_id, organisation["id"], domain, "deprecated_term")

    archetype = organisation["archetype"]
    for fault_type in FAULT_NAMES:
        if not _should_inject(rng, scenario, archetype, fault_type):
            continue
        if fault_type == "unknown_term":
            product["dpp:experimentalThermalResilience"] = index % 10
        elif fault_type == "custom_term":
            target = f"https://{organisation['id']}.fictional.example/vocab/repairTier"
            product[target] = f"tier-{index % 4}"
            _fault(
                faults, scenario, document_id, organisation["id"], domain, fault_type, target
            )
            continue
        elif fault_type == "deprecated_term":
            if "dpp:chemistry" in battery:
                continue
            battery["dpp:chemistry"] = battery.pop("dpp:batteryChemistry")
        elif fault_type == "datatype_error":
            battery["dpp:batteryCapacity"] = {"@value": "invalid", "@type": "xsd:decimal"}
        elif fault_type == "missing_required":
            product.pop("dpp:productIdentifier", None)
        elif fault_type == "mapping_gap":
            product["https://external.example/vocab/energyStorageGrade"] = f"grade-{index % 5}"
        _fault(faults, scenario, document_id, organisation["id"], domain, fault_type)

    payload_bytes = _json_bytes(payload).rstrip(b"\n")
    envelope: dict[str, object] = {
        "document_id": document_id,
        "external_identifier": product_id.upper(),
        "organisation_id": organisation["id"],
        "domain": domain,
        "semantic_profile_id": profile,
        "declared_ontology_version": version,
        "document_hash": hashlib.sha256(payload_bytes).hexdigest(),
        "payload": payload,
    }
    return envelope, faults


def generate(scenario: Scenario, output: Path = DEFAULT_OUTPUT) -> GenerationSummary:
    output.mkdir(parents=True, exist_ok=True)
    rng = random.Random(scenario.seed)
    organisations = _organisations(scenario.organisations, scenario.legacy_version_share)
    domain_counts: Counter[str] = Counter()
    version_counts: Counter[str] = Counter()
    fault_counts: Counter[str] = Counter()
    document_digest = hashlib.sha256()
    truth_digest = hashlib.sha256()

    with (output / "documents.jsonl").open("wb") as documents_file, (
        output / "ground-truth.jsonl"
    ).open("wb") as truth_file:
        for index in range(scenario.documents):
            organisation = rng.choice(organisations)
            document, faults = _document(rng, scenario, index, organisation)
            document_line = _json_bytes(document)
            documents_file.write(document_line)
            document_digest.update(document_line)
            domain_counts[str(document["domain"])] += 1
            version_counts[str(document["declared_ontology_version"])] += 1
            for fault in faults:
                truth_line = _json_bytes(fault)
                truth_file.write(truth_line)
                truth_digest.update(truth_line)
                fault_counts[str(fault["fault_type"])] += 1

    (output / "organisations.json").write_bytes(
        _json_bytes(
            {
                "scenario": scenario.name,
                "seed": scenario.seed,
                "organisations": organisations,
            },
            pretty=True,
        )
    )
    summary: GenerationSummary = {
        "scenario": scenario.name,
        "seed": scenario.seed,
        "documents": scenario.documents,
        "organisations": scenario.organisations,
        "archetypes": dict(Counter(item["archetype"] for item in organisations)),
        "domains": dict(sorted(domain_counts.items())),
        "ontology_versions": dict(sorted(version_counts.items())),
        "faults": dict(sorted(fault_counts.items())),
        "documents_sha256": document_digest.hexdigest(),
        "ground_truth_sha256": truth_digest.hexdigest(),
    }
    (output / "summary.json").write_bytes(_json_bytes(summary, pretty=True))
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the synthetic DPP ecosystem.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    summary = generate(load_scenario(args.config), args.output)
    print(
        f"Generated {summary['documents']} DPPs for {summary['organisations']} organisations "
        f"in {args.output}"
    )


if __name__ == "__main__":
    main()
