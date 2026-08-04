from pathlib import Path

from rdflib import RDF, RDFS, BNode, Dataset, Graph, Namespace, URIRef
from rdflib.namespace import OWL

ROOT = Path(__file__).resolve().parents[1]
DPP = Namespace("https://example.org/dpp/")

REQUIRED_CLASSES = {
    DPP.DigitalProductPassport,
    DPP.Product,
    DPP.ProductModel,
    DPP.ProductBatch,
    DPP.ProductItem,
    DPP.ElectronicProduct,
    DPP.Smartphone,
    DPP.Component,
    DPP.Battery,
    DPP.Display,
    DPP.Material,
    DPP.Manufacturer,
    DPP.Supplier,
    DPP.Facility,
    DPP.ProvenanceRecord,
}
REQUIRED_PROPERTIES = {
    DPP.hasPassport,
    DPP.describesProduct,
    DPP.manufacturedBy,
    DPP.containsComponent,
    DPP.containsMaterial,
    DPP.hasCarbonFootprint,
    DPP.hasProvenance,
    DPP.productIdentifier,
    DPP.repairabilityScore,
    DPP.isUserReplaceable,
}
BUSINESS_CLASSES = REQUIRED_CLASSES | {DPP.EconomicOperator, DPP.EvidenceDocument}


def _is_subclass(graph: Graph, child: URIRef, parent: URIRef) -> bool:
    pending = [child]
    seen: set[URIRef] = set()
    while pending:
        current = pending.pop()
        if current == parent:
            return True
        if current in seen:
            continue
        seen.add(current)
        pending.extend(
            candidate
            for candidate in graph.objects(current, RDFS.subClassOf)
            if isinstance(candidate, URIRef)
        )
    return False


def validate() -> dict[str, int]:
    ontology_files = sorted((ROOT / "ontology" / "core").glob("*.ttl"))
    example_files = sorted((ROOT / "ontology" / "examples").glob("*.ttl"))
    query_files = sorted((ROOT / "sparql" / "competency").glob("*.rq"))
    assert ontology_files, "No ontology modules found"
    assert example_files, "No example graphs found"
    assert len(query_files) == 20, f"Expected 20 competency queries, found {len(query_files)}"

    graph = Graph()
    for path in ontology_files + example_files:
        graph.parse(path, format="turtle")

    classes = set(graph.subjects(RDF.type, OWL.Class))
    properties = set(graph.subjects(RDF.type, OWL.ObjectProperty)) | set(
        graph.subjects(RDF.type, OWL.DatatypeProperty)
    )
    assert not REQUIRED_CLASSES - classes, f"Missing classes: {REQUIRED_CLASSES - classes}"
    assert not REQUIRED_PROPERTIES - properties, (
        f"Missing properties: {REQUIRED_PROPERTIES - properties}"
    )
    assert _is_subclass(graph, DPP.Smartphone, DPP.Product)
    assert _is_subclass(graph, DPP.Battery, DPP.Component)
    assert not classes & properties, "A term cannot be both a class and a property"
    assert not any(
        isinstance(entity, BNode)
        for business_class in BUSINESS_CLASSES
        for entity in graph.subjects(RDF.type, business_class)
    ), "Key business entities must have stable IRIs"

    dataset = Dataset()
    named_graph = dataset.graph(URIRef("urn:dpp:test-catalogue"))
    for triple in graph:
        named_graph.add(triple)
    result_rows = 0
    for path in query_files:
        rows = list(dataset.query(path.read_text(encoding="utf-8")))
        result_rows += len(rows)
    assert result_rows, "The competency catalogue returned no results"

    return {
        "triples": len(graph),
        "ontology_modules": len(ontology_files),
        "example_graphs": len(example_files),
        "competency_queries": len(query_files),
        "query_result_rows": result_rows,
    }


if __name__ == "__main__":
    summary = validate()
    metrics = ", ".join(f"{key}={value}" for key, value in summary.items())
    print("Ontology validation passed:", metrics)
