from app.schemas.validation import StoredSemanticDocument
from app.services.semantic_signal_service import collect_signals


def test_signal_collection_classifies_terms_and_mappings() -> None:
    document = StoredSemanticDocument(
        document_id="signal-test",
        organisation_id="org-test",
        domain="battery",
        semantic_profile_id="battery-2.0",
        declared_ontology_version="1.1.0",
        graph_uri="urn:dpp:signal-test",
    )
    graph = b"""
        @prefix dpp: <https://example.org/dpp/> .
        @prefix dcterms: <http://purl.org/dc/terms/> .
        <urn:test:battery> a dpp:Battery ;
            dpp:batteryChemistry "LFP" ;
            dpp:chemistry "LFP" ;
            dpp:experimentalThermalResilience 8 ;
            dcterms:title "Test battery" ;
            <https://org-test.fictional.example/vocab/repairTier> "tier-1" ;
            <https://external.example/vocab/energyStorageGrade> "grade-2" .
    """

    observations = collect_signals(document, graph)
    categories = {
        item.term_iri: item.category
        for item in observations
        if item.observation_type == "term_classification"
    }
    mapped = {
        item.term_iri
        for item in observations
        if item.observation_type == "mapping_used"
    }
    missing = {
        item.term_iri
        for item in observations
        if item.observation_type == "mapping_missing"
    }

    assert categories["https://example.org/dpp/batteryChemistry"] == "standard"
    assert categories["https://example.org/dpp/chemistry"] == "deprecated"
    assert categories["https://example.org/dpp/experimentalThermalResilience"] == "unknown"
    assert categories["http://purl.org/dc/terms/title"] == "external_approved"
    assert categories["https://org-test.fictional.example/vocab/repairTier"] == "custom"
    assert "https://example.org/dpp/chemistry" in mapped
    assert "https://external.example/vocab/energyStorageGrade" in missing
    assert "https://example.org/dpp/experimentalThermalResilience" not in missing
    assert "https://org-test.fictional.example/vocab/repairTier" not in missing
