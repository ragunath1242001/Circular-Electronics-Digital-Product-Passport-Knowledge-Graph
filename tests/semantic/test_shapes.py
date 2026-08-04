from pathlib import Path

from app.services.validation_service import validate_data

ROOT = Path(__file__).resolve().parents[2]


def test_valid_passport_conforms() -> None:
    data = (ROOT / "ontology" / "examples" / "circular-phone.ttl").read_text(encoding="utf-8")

    report = validate_data(data).report

    assert report.conforms
    assert report.results == []


def test_invalid_passport_reports_all_severities() -> None:
    data = (ROOT / "ontology" / "fixtures" / "invalid-phone.ttl").read_text(encoding="utf-8")

    report = validate_data(data).report

    assert not report.conforms
    assert report.violations >= 2
    assert report.warnings >= 2
    assert report.info >= 1
    assert {result.severity for result in report.results} == {"Violation", "Warning", "Info"}

