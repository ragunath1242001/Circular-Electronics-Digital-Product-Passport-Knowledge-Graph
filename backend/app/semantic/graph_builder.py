from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from rdflib import DCTERMS, RDF, XSD, Graph, Literal, Namespace, URIRef

from app.schemas.ingestion import SmartphoneRecord
from app.semantic.uri_factory import resource_uri, slugify

DPP = Namespace("https://example.org/dpp/")
DPP_MATERIAL = Namespace("https://example.org/dpp/material/")
PROV = Namespace("http://www.w3.org/ns/prov#")
QUDT = Namespace("http://qudt.org/schema/qudt/")
UNIT = Namespace("http://qudt.org/vocab/unit/")
MAPPING_VERSION = "1.0.0"
ONTOLOGY_VERSION = "2.0.0"


def _quantity(graph: Graph, node: URIRef, value: Decimal, unit: URIRef) -> None:
    graph.add((node, RDF.type, QUDT.QuantityValue))
    graph.add((node, QUDT.numericValue, Literal(value, datatype=XSD.decimal)))
    graph.add((node, QUDT.unit, unit))


def record_to_graph(
    record: SmartphoneRecord,
    source_system: str,
    job_id: UUID,
    version: int = 1,
) -> Graph:
    graph = Graph()
    graph.bind("dpp", DPP)
    graph.bind("dct", DCTERMS)
    graph.bind("prov", PROV)
    graph.bind("qudt", QUDT)

    product = resource_uri("product", record.product_identifier)
    passport = resource_uri("passport", f"{record.product_identifier}-v{version}")
    manufacturer = resource_uri("company", record.manufacturer_name)
    battery = resource_uri("battery", record.battery_identifier)
    display = resource_uri("display", record.display_identifier)
    supplier = resource_uri("company", record.supplier_name)
    material = resource_uri("material", f"{record.battery_identifier}-{record.material_name}")
    facility = resource_uri("facility", record.material_origin)
    activity = resource_uri("import-job", str(job_id))
    provenance = resource_uri("provenance", f"{record.product_identifier}-{job_id}")
    battery_provenance = resource_uri("provenance", f"{record.battery_identifier}-{job_id}")
    product_carbon = resource_uri("assessment", f"{record.product_identifier}-carbon")
    battery_carbon = resource_uri("assessment", f"{record.battery_identifier}-carbon")
    product_carbon_quantity = resource_uri("quantity", f"{record.product_identifier}-carbon")
    battery_carbon_quantity = resource_uri("quantity", f"{record.battery_identifier}-carbon")
    battery_capacity_quantity = resource_uri("quantity", f"{record.battery_identifier}-capacity")
    software = resource_uri("commitment", f"{record.product_identifier}-support")
    product_recycling = resource_uri("instruction", f"{record.product_identifier}-recycling")
    battery_recycling = resource_uri("instruction", f"{record.battery_identifier}-recycling")

    graph.add((product, RDF.type, DPP.Smartphone))
    graph.add((product, RDF.type, DPP.ProductModel))
    graph.add((product, DCTERMS.title, Literal(record.product_name)))
    graph.add((product, DPP.productIdentifier, Literal(record.product_identifier)))
    graph.add((product, DPP.modelNumber, Literal(record.model_number)))
    graph.add(
        (product, DPP.manufacturingDate, Literal(record.manufacturing_date, datatype=XSD.date))
    )
    graph.add((product, DPP.manufacturedBy, manufacturer))
    graph.add((product, DPP.containsComponent, battery))
    graph.add((product, DPP.containsComponent, display))
    graph.add((product, DPP.hasPassport, passport))
    graph.add((product, DPP.hasCarbonFootprint, product_carbon))
    graph.add((product, DPP.hasRecyclingInstruction, product_recycling))
    graph.add((product, DPP.hasSoftwareSupportCommitment, software))
    graph.add((product, DPP.hasLifecycleStatus, DPP.Active))
    graph.add(
        (
            product,
            DPP.repairabilityScore,
            Literal(record.repairability_score, datatype=XSD.decimal),
        )
    )
    graph.add((product, DPP.hasProvenance, provenance))

    graph.add((passport, RDF.type, DPP.DigitalProductPassport))
    graph.add((passport, DPP.describesProduct, product))
    graph.add((passport, DPP.version, Literal(f"{version}.0.0")))
    graph.add((passport, DPP.ontologyVersion, Literal(ONTOLOGY_VERSION)))
    graph.add((manufacturer, RDF.type, DPP.Manufacturer))
    graph.add((manufacturer, DCTERMS.title, Literal(record.manufacturer_name)))

    graph.add((battery, RDF.type, DPP.Battery))
    graph.add((battery, DPP.productIdentifier, Literal(record.battery_identifier)))
    graph.add((battery, DPP.batteryChemistry, Literal(record.battery_chemistry)))
    graph.add(
        (
            battery,
            DPP.batteryCapacity,
            Literal(record.battery_capacity_mah, datatype=XSD.decimal),
        )
    )
    graph.add((battery, DPP.batteryCycleEndurance, Literal(record.battery_cycle_endurance)))
    graph.add((battery, DPP.isUserReplaceable, Literal(record.battery_user_replaceable)))
    graph.add((battery, DPP.suppliedBy, supplier))
    graph.add((battery, DPP.containsMaterial, material))
    graph.add((battery, DPP.quantityValue, battery_capacity_quantity))
    graph.add((battery, DPP.hasCarbonFootprint, battery_carbon))
    graph.add((battery, DPP.hasRecyclingInstruction, battery_recycling))
    graph.add((battery, DPP.hasProvenance, battery_provenance))
    graph.add((supplier, RDF.type, DPP.Supplier))
    graph.add((supplier, DCTERMS.title, Literal(record.supplier_name)))
    graph.add((display, RDF.type, DPP.Display))
    graph.add((display, DPP.productIdentifier, Literal(record.display_identifier)))

    graph.add((material, RDF.type, DPP.Material))
    graph.add((material, DPP.materialType, DPP_MATERIAL[slugify(record.material_name)]))
    graph.add((material, DPP.originatesFrom, facility))
    graph.add((material, DPP.suppliedBy, supplier))
    graph.add(
        (
            material,
            DPP.recycledContentPercentage,
            Literal(record.recycled_content_percentage, datatype=XSD.decimal),
        )
    )
    graph.add((facility, RDF.type, DPP.Facility))
    graph.add((facility, DCTERMS.title, Literal(record.material_origin)))

    graph.add((product_carbon, RDF.type, DPP.CarbonFootprintAssessment))
    graph.add(
        (
            product_carbon,
            DPP.carbonValue,
            Literal(record.carbon_kg_co2e, datatype=XSD.decimal),
        )
    )
    graph.add((product_carbon, DPP.quantityValue, product_carbon_quantity))
    graph.add((battery_carbon, RDF.type, DPP.CarbonFootprintAssessment))
    graph.add(
        (
            battery_carbon,
            DPP.carbonValue,
            Literal(record.battery_carbon_kg_co2e, datatype=XSD.decimal),
        )
    )
    graph.add((battery_carbon, DPP.quantityValue, battery_carbon_quantity))
    _quantity(graph, product_carbon_quantity, record.carbon_kg_co2e, UNIT.KiloGM)
    _quantity(graph, battery_carbon_quantity, record.battery_carbon_kg_co2e, UNIT.KiloGM)
    _quantity(graph, battery_capacity_quantity, record.battery_capacity_mah, UNIT["MilliA-HR"])

    graph.add((software, RDF.type, DPP.SoftwareSupportCommitment))
    graph.add((software, DPP.softwareSupportYears, Literal(record.software_support_years)))
    graph.add((product_recycling, RDF.type, DPP.RecyclingInstruction))
    graph.add((battery_recycling, RDF.type, DPP.RecyclingInstruction))

    generated_at = Literal(datetime.now(UTC), datatype=XSD.dateTime)
    graph.add((activity, RDF.type, DPP.ImportActivity))
    graph.add((activity, DPP.version, Literal(MAPPING_VERSION)))
    for record_node in (provenance, battery_provenance):
        graph.add((record_node, RDF.type, DPP.ProvenanceRecord))
        graph.add((record_node, DPP.sourceSystem, Literal(source_system)))
        graph.add((record_node, DPP.confidenceScore, Literal("1.0", datatype=XSD.decimal)))
        graph.add((record_node, DPP.generatedBy, activity))
        graph.add((record_node, PROV.generatedAtTime, generated_at))
    return graph
