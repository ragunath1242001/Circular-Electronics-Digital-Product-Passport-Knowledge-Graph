from app.services.report_service import render_csv


def test_csv_export_cites_sources_and_neutralizes_formulas() -> None:
    exported = render_csv(
        [{"product": "=2+2", "source": "http://localhost:8000/api/v1/products/1"}],
        [],
    ).decode("utf-8-sig")

    assert "'=2+2" in exported
    assert "http://localhost:8000/api/v1/products/1" in exported
