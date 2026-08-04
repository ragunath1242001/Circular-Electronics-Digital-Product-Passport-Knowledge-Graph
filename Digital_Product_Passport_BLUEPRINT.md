# Digital Product Passport Knowledge Graph Platform
## Production-Grade Implementation Blueprint for Codex

**Project name:** Circular Electronics Digital Product Passport Knowledge Graph  
**Primary use case:** Smartphones and embedded batteries  
**Target root folder:** `D:\Digital Product Passport`  
**Document purpose:** End-to-end implementation blueprint for Codex  
**Recommended implementation approach:** Incremental, test-driven, Docker-first, ontology-first

---

# 1. Executive Summary

This project will implement a production-grade Digital Product Passport (DPP) Knowledge Graph platform for circular electronics, with smartphones as the main product and embedded batteries as deeply modelled sub-products.

The platform must ingest product and supply-chain data from heterogeneous sources, transform it into RDF, validate it with SHACL, store it in a knowledge graph, expose SPARQL and REST APIs, and provide web dashboards for:

- Product identity
- Product composition
- Manufacturers and suppliers
- Critical raw materials
- Carbon footprint
- Repairability
- Software support
- Certificates
- Supply-chain traceability
- Recycling and end-of-life processing
- Semantic quality and observability

The project must be suitable for a professional portfolio and demonstrate:

- Knowledge graph engineering
- Semantic interoperability
- Ontology design
- SHACL validation
- Data governance
- Data quality
- Provenance
- Digital Product Passport concepts
- Circular economy analytics
- API development
- Production deployment
- Automated testing
- Documentation

---

# 2. Project Vision

Build a semantic Digital Product Passport platform in which every electronic product is represented as a connected graph of:

```text
Product
  ├── Manufacturer
  ├── Product model
  ├── Product item or batch
  ├── Components
  ├── Materials
  ├── Suppliers
  ├── Manufacturing facilities
  ├── Carbon footprint assessments
  ├── Certificates
  ├── Repair instructions
  ├── Software support commitments
  ├── Recycling instructions
  ├── Supply-chain events
  └── Provenance records
```

The system must enable users to answer complex questions through SPARQL and dashboards.

Example questions:

- Which smartphones contain cobalt from high-risk regions?
- Which products have batteries that are not user-replaceable?
- Which certificates are expired or missing?
- Which models have the highest carbon footprint?
- Which suppliers contribute to the greatest number of validation failures?
- Which products use deprecated ontology terms?
- Which products have incomplete recycling information?
- Which products contain more than a defined percentage of recycled material?
- Which software-support commitments are below policy thresholds?
- Which supply-chain facts lack sufficient provenance?

---

# 3. Scope

## 3.1 MVP Scope

The MVP must support:

### Product types

- Smartphone
- Battery
- Display
- Printed circuit board
- Chassis
- Camera module
- Charger

### Business entities

- Manufacturer
- Supplier
- Material producer
- Certification body
- Repair operator
- Recycler
- Logistics provider
- Manufacturing facility

### Materials

- Lithium
- Cobalt
- Nickel
- Graphite
- Copper
- Gold
- Tin
- Tantalum
- Tungsten
- Aluminium
- Plastics
- Rare-earth elements

### Passport information

- Product identifier
- Product model
- Serial number or batch identifier
- Manufacturer
- Manufacturing date
- Manufacturing location
- Major components
- Material composition
- Carbon footprint
- Recycled-content percentage
- Repairability score
- Battery cycle endurance
- Battery replaceability
- Spare-part availability
- Software-support period
- Certificates
- Repair instructions
- Recycling instructions
- End-of-life route
- Provenance
- Access classification

## 3.2 Out of Scope for MVP

Do not implement these in the first release:

- Blockchain
- Full legal compliance certification
- Real manufacturer integrations
- Every electronic component
- Every chemical substance
- Real-time IoT battery telemetry
- AI-generated compliance decisions
- Production identity verification
- Public cloud deployment with paid services
- Verifiable credentials
- Digital signatures
- Complex multi-tenant billing

These may be added later.

---

# 4. Primary Personas

## 4.1 Consumer

Needs to view:

- Product identity
- Repairability
- Battery durability
- Carbon footprint
- Software support
- Recycling instructions

## 4.2 Manufacturer

Needs to:

- Create and update product passports
- Upload product and supplier data
- Review validation failures
- Track completeness
- Manage certificates

## 4.3 Supplier

Needs to:

- Submit component and material data
- Upload evidence
- Correct validation errors
- Maintain certificate data

## 4.4 Repair Operator

Needs to view:

- Component replacement instructions
- Required tools
- Spare-part references
- Disassembly steps
- Safety information

## 4.5 Recycler

Needs to view:

- Material composition
- Hazardous substances
- Dismantling instructions
- Recovery routes
- Material percentages

## 4.6 Regulator or Auditor

Needs to:

- Query products
- Inspect provenance
- Check SHACL conformance
- Review expired certificates
- Compare manufacturers
- Export evidence

## 4.7 Data Steward

Needs to:

- Monitor data quality
- Resolve duplicate entities
- Review vocabulary usage
- Track ontology versions
- Investigate semantic inconsistencies

---

# 5. Functional Requirements

## 5.1 Product Passport Management

The system must allow users to:

- Create a passport
- Update a passport
- View a passport
- Archive a passport
- Version a passport
- Link a passport to a product model, batch, or item
- Generate a stable URI
- Generate a QR code
- Export passport data as JSON-LD and Turtle

## 5.2 Data Ingestion

Support:

- CSV upload
- JSON upload
- JSON-LD upload
- REST API ingestion
- Seed-data generation
- Batch ingestion
- Validation before persistence
- Ingestion audit logs
- Failed-record quarantine

## 5.3 Semantic Transformation

The ingestion pipeline must:

- Map source fields to ontology terms
- Generate canonical URIs
- Normalize units
- Normalize dates
- Resolve known entities
- Validate controlled vocabularies
- Convert source records into RDF
- Attach provenance
- Store transformation errors

## 5.4 Knowledge Graph

The graph must support:

- RDF storage
- SPARQL 1.1 queries
- Named graphs
- Versioned data
- Provenance
- Inference where appropriate
- Graph export
- Bulk loading
- Query templates

## 5.5 SHACL Validation

Validation must support:

- Required properties
- Cardinality
- Datatypes
- Value ranges
- Controlled vocabularies
- Cross-field constraints
- Identifier rules
- Date consistency
- Unit presence
- Certificate validity
- Product-component consistency
- Severity levels
- Human-readable validation messages

## 5.6 Dashboard

The dashboard must include:

- Total passports
- Valid passports
- Invalid passports
- Validation errors by category
- Products by manufacturer
- Carbon footprint by model
- Repairability score by model
- Recycled-content percentage
- Expiring certificates
- Supplier completeness
- Material usage
- Product lifecycle status
- Ontology version distribution

## 5.7 SPARQL Workbench

The application must allow:

- Running custom SPARQL queries
- Using saved query templates
- Viewing results as tables
- Viewing graph results
- Exporting CSV
- Viewing query execution time
- Restricting unsafe update operations

## 5.8 Graph Explorer

The graph explorer must support:

- Product-centric graph navigation
- Expand/collapse relationships
- Entity detail panels
- Relationship labels
- Search
- Filtering by node type
- Depth limitation
- Link to source passport

## 5.9 Search

Search by:

- Product name
- Product identifier
- Manufacturer
- Supplier
- Material
- Certificate
- Component
- Country
- Lifecycle status

## 5.10 Reporting

Generate reports for:

- Passport validation
- Product sustainability
- Supplier completeness
- Certificate expiry
- Material traceability
- Semantic quality
- Product comparison

---

# 6. Non-Functional Requirements

## 6.1 Performance

MVP targets:

- Product search under 2 seconds
- Passport page under 2 seconds
- Standard SPARQL queries under 5 seconds
- Batch import of 1,000 products under 3 minutes
- Validation of one passport under 2 seconds

## 6.2 Reliability

- Idempotent imports
- Transaction-safe metadata updates
- Retry handling for transient failures
- Failed-job logging
- Health checks
- Backup and restore scripts

## 6.3 Security

- Role-based access control
- Password hashing
- JWT or secure session authentication
- Input validation
- File-type validation
- Maximum upload size
- Secrets via environment variables
- No secrets committed to Git
- Read-only public SPARQL access
- Administrative update permissions

## 6.4 Maintainability

- Modular architecture
- Type annotations
- Unit tests
- Integration tests
- Architecture decision records
- OpenAPI documentation
- Clear folder structure
- Automated linting and formatting

## 6.5 Portability

The complete platform must run using:

```powershell
docker compose up --build
```

on Windows with Docker Desktop.

---

# 7. Recommended Technology Stack

## 7.1 Backend

- Python 3.12
- FastAPI
- Pydantic v2
- SQLAlchemy
- Alembic
- RDFLib
- SPARQLWrapper or HTTPX
- Pandas
- PySHACL
- Celery or lightweight background jobs
- Redis
- PostgreSQL

## 7.2 Knowledge Graph

Primary recommendation:

- Apache Jena Fuseki

Alternative:

- GraphDB Free

Use Fuseki for the default implementation because it is open-source, Docker-friendly, and suitable for portfolio deployment.

## 7.3 Frontend

- React
- TypeScript
- Vite
- React Router
- TanStack Query
- Material UI
- Cytoscape.js
- Recharts
- React Hook Form
- Zod

## 7.4 Semantic Tooling

- Protégé
- OWL
- SHACL
- SKOS
- PROV-O
- DCAT
- Dublin Core Terms
- QUDT
- W3C ORG
- GeoSPARQL
- ODRL

## 7.5 DevOps

- Docker
- Docker Compose
- GitHub Actions
- Ruff
- Black
- MyPy
- Pytest
- ESLint
- Prettier
- Vitest
- Playwright
- Trivy
- Makefile or PowerShell task scripts

---

# 8. High-Level Architecture

```text
┌──────────────────────────────────────────────────────────────┐
│                        Frontend                              │
│ React + TypeScript                                          │
│ Passport UI | Dashboard | Graph Explorer | SPARQL Workbench │
└──────────────────────────┬───────────────────────────────────┘
                           │ REST / JSON-LD
┌──────────────────────────▼───────────────────────────────────┐
│                        Backend API                           │
│ FastAPI                                                     │
│ Auth | Products | Passports | Validation | Search | Reports │
└──────────────┬───────────────────────────────┬───────────────┘
               │                               │
┌──────────────▼──────────────┐   ┌────────────▼──────────────┐
│ Relational Application DB  │   │ Semantic Processing Layer │
│ PostgreSQL                 │   │ RDF mapping | URI minting │
│ Users | Jobs | Audit logs  │   │ SHACL | provenance       │
└─────────────────────────────┘   └────────────┬──────────────┘
                                               │ SPARQL
                                  ┌────────────▼──────────────┐
                                  │ Knowledge Graph          │
                                  │ Apache Jena Fuseki       │
                                  │ Named graphs + SPARQL    │
                                  └───────────────────────────┘
```

---

# 9. Repository Structure

Codex must create the following structure inside:

`D:\Digital Product Passport`

```text
Digital Product Passport/
│
├── .github/
│   └── workflows/
│       ├── backend-ci.yml
│       ├── frontend-ci.yml
│       ├── integration-ci.yml
│       └── security-scan.yml
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── dependencies.py
│   │   │   └── v1/
│   │   │       ├── auth.py
│   │   │       ├── products.py
│   │   │       ├── passports.py
│   │   │       ├── components.py
│   │   │       ├── materials.py
│   │   │       ├── suppliers.py
│   │   │       ├── certificates.py
│   │   │       ├── validation.py
│   │   │       ├── sparql.py
│   │   │       ├── search.py
│   │   │       ├── reports.py
│   │   │       ├── ingestion.py
│   │   │       └── health.py
│   │   │
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   ├── logging.py
│   │   │   ├── security.py
│   │   │   ├── exceptions.py
│   │   │   └── constants.py
│   │   │
│   │   ├── db/
│   │   │   ├── base.py
│   │   │   ├── session.py
│   │   │   ├── models/
│   │   │   └── repositories/
│   │   │
│   │   ├── schemas/
│   │   ├── services/
│   │   │   ├── passport_service.py
│   │   │   ├── product_service.py
│   │   │   ├── ingestion_service.py
│   │   │   ├── mapping_service.py
│   │   │   ├── rdf_service.py
│   │   │   ├── shacl_service.py
│   │   │   ├── sparql_service.py
│   │   │   ├── provenance_service.py
│   │   │   ├── report_service.py
│   │   │   ├── search_service.py
│   │   │   └── qr_service.py
│   │   │
│   │   ├── semantic/
│   │   │   ├── namespaces.py
│   │   │   ├── uri_factory.py
│   │   │   ├── graph_builder.py
│   │   │   ├── entity_resolution.py
│   │   │   ├── unit_normalization.py
│   │   │   └── vocabulary_service.py
│   │   │
│   │   ├── workers/
│   │   ├── main.py
│   │   └── __init__.py
│   │
│   ├── alembic/
│   ├── tests/
│   │   ├── unit/
│   │   ├── integration/
│   │   ├── contract/
│   │   └── fixtures/
│   ├── Dockerfile
│   ├── pyproject.toml
│   ├── alembic.ini
│   └── README.md
│
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   ├── app/
│   │   ├── components/
│   │   ├── features/
│   │   │   ├── auth/
│   │   │   ├── dashboard/
│   │   │   ├── passports/
│   │   │   ├── products/
│   │   │   ├── graph-explorer/
│   │   │   ├── sparql-workbench/
│   │   │   ├── validation/
│   │   │   ├── ingestion/
│   │   │   └── reports/
│   │   ├── hooks/
│   │   ├── layouts/
│   │   ├── pages/
│   │   ├── routes/
│   │   ├── types/
│   │   ├── utils/
│   │   └── main.tsx
│   ├── tests/
│   ├── public/
│   ├── Dockerfile
│   ├── package.json
│   └── README.md
│
├── ontology/
│   ├── core/
│   │   ├── dpp-core.ttl
│   │   ├── dpp-products.ttl
│   │   ├── dpp-organizations.ttl
│   │   ├── dpp-materials.ttl
│   │   ├── dpp-supply-chain.ttl
│   │   ├── dpp-circularity.ttl
│   │   ├── dpp-certificates.ttl
│   │   └── dpp-provenance.ttl
│   ├── shapes/
│   │   ├── product-shapes.ttl
│   │   ├── smartphone-shapes.ttl
│   │   ├── battery-shapes.ttl
│   │   ├── component-shapes.ttl
│   │   ├── material-shapes.ttl
│   │   ├── certificate-shapes.ttl
│   │   ├── supply-chain-shapes.ttl
│   │   └── provenance-shapes.ttl
│   ├── vocabularies/
│   │   ├── lifecycle-status.ttl
│   │   ├── material-types.ttl
│   │   ├── certificate-types.ttl
│   │   ├── repairability-status.ttl
│   │   ├── risk-classification.ttl
│   │   └── access-levels.ttl
│   ├── examples/
│   ├── competency-questions.md
│   ├── ontology-guidelines.md
│   └── README.md
│
├── data/
│   ├── raw/
│   │   ├── products/
│   │   ├── suppliers/
│   │   ├── materials/
│   │   ├── certificates/
│   │   └── supply-chain/
│   ├── processed/
│   ├── invalid/
│   ├── seed/
│   │   ├── smartphones.csv
│   │   ├── batteries.csv
│   │   ├── components.csv
│   │   ├── suppliers.csv
│   │   ├── materials.csv
│   │   ├── certificates.csv
│   │   └── supply_chain_events.csv
│   └── generated/
│       ├── rdf/
│       ├── validation-reports/
│       └── exports/
│
├── mappings/
│   ├── csv/
│   ├── json/
│   ├── jsonld/
│   ├── mapping-specification.md
│   └── examples/
│
├── sparql/
│   ├── product/
│   ├── materials/
│   ├── carbon/
│   ├── repairability/
│   ├── certificates/
│   ├── supply-chain/
│   ├── observability/
│   └── README.md
│
├── infrastructure/
│   ├── fuseki/
│   │   ├── config.ttl
│   │   └── datasets/
│   ├── postgres/
│   │   └── init.sql
│   ├── nginx/
│   │   └── nginx.conf
│   ├── monitoring/
│   │   ├── prometheus.yml
│   │   └── grafana/
│   └── scripts/
│       ├── bootstrap.ps1
│       ├── seed-data.ps1
│       ├── backup.ps1
│       ├── restore.ps1
│       └── reset-environment.ps1
│
├── docs/
│   ├── 01_Project_Vision.md
│   ├── 02_System_Architecture.md
│   ├── 03_Domain_Model.md
│   ├── 04_Ontology_Design.md
│   ├── 05_SHACL_Validation.md
│   ├── 06_Data_Ingestion.md
│   ├── 07_API_Specification.md
│   ├── 08_UI_UX_Design.md
│   ├── 09_Security_Model.md
│   ├── 10_Testing_Strategy.md
│   ├── 11_Deployment.md
│   ├── 12_Semantic_Observability.md
│   ├── 13_SPARQL_Query_Catalog.md
│   ├── 14_Data_Governance.md
│   ├── 15_Demo_Scenarios.md
│   ├── 16_Portfolio_Guide.md
│   ├── 17_Development_Roadmap.md
│   ├── 18_Future_Work.md
│   └── adr/
│
├── scripts/
│   ├── generate_seed_data.py
│   ├── validate_ontology.py
│   ├── load_graph.py
│   ├── run_shacl.py
│   ├── export_graph.py
│   └── smoke_test.py
│
├── tests/
│   ├── end_to_end/
│   ├── performance/
│   ├── semantic/
│   └── security/
│
├── .env.example
├── .gitignore
├── docker-compose.yml
├── Makefile
├── README.md
├── CONTRIBUTING.md
├── LICENSE
└── BLUEPRINT.md
```

---

# 10. Ontology Design

## 10.1 Namespace

Use a stable development namespace:

```turtle
@prefix dpp: <https://example.org/dpp/> .
@prefix dpp-res: <https://example.org/dpp/resource/> .
```

Do not use blank nodes for key business entities.

## 10.2 Core Classes

```text
dpp:DigitalProductPassport
dpp:Product
dpp:ProductModel
dpp:ProductBatch
dpp:ProductItem
dpp:ElectronicProduct
dpp:Smartphone
dpp:Component
dpp:Battery
dpp:Display
dpp:PrintedCircuitBoard
dpp:CameraModule
dpp:Chassis
dpp:Charger
dpp:Material
dpp:Substance
dpp:EconomicOperator
dpp:Manufacturer
dpp:Supplier
dpp:Recycler
dpp:RepairOperator
dpp:CertificationBody
dpp:Facility
dpp:SupplyChainEvent
dpp:CarbonFootprintAssessment
dpp:Certificate
dpp:RepairInstruction
dpp:RecyclingInstruction
dpp:SoftwareSupportCommitment
dpp:ProvenanceRecord
dpp:EvidenceDocument
```

## 10.3 Core Object Properties

```text
dpp:hasPassport
dpp:describesProduct
dpp:manufacturedBy
dpp:suppliedBy
dpp:containsComponent
dpp:containsMaterial
dpp:assembledAt
dpp:manufacturedAt
dpp:hasCarbonFootprint
dpp:hasCertificate
dpp:hasRepairInstruction
dpp:hasRecyclingInstruction
dpp:hasSoftwareSupportCommitment
dpp:hasSupplyChainEvent
dpp:hasEvidence
dpp:generatedBy
dpp:derivedFrom
dpp:recycledBy
dpp:repairedBy
dpp:originatesFrom
dpp:hasLifecycleStatus
dpp:hasAccessPolicy
```

## 10.4 Core Datatype Properties

```text
dpp:productIdentifier
dpp:modelNumber
dpp:serialNumber
dpp:batchNumber
dpp:manufacturingDate
dpp:carbonValue
dpp:recycledContentPercentage
dpp:repairabilityScore
dpp:recyclabilityScore
dpp:softwareSupportYears
dpp:batteryCapacity
dpp:batteryCycleEndurance
dpp:isUserReplaceable
dpp:sparePartsAvailableUntil
dpp:validFrom
dpp:validUntil
dpp:version
dpp:createdAt
dpp:updatedAt
dpp:sourceSystem
dpp:confidenceScore
```

## 10.5 Reused Vocabularies

Reuse:

```text
dct:title
dct:description
dct:identifier
dct:issued
dct:modified
prov:wasGeneratedBy
prov:wasDerivedFrom
prov:wasAttributedTo
prov:generatedAtTime
org:Organization
skos:Concept
skos:prefLabel
qudt:QuantityValue
qudt:numericValue
qudt:unit
geo:hasGeometry
odrl:hasPolicy
```

## 10.6 Product Granularity

Support:

```text
ProductModel
   ↓ hasBatch
ProductBatch
   ↓ hasItem
ProductItem
```

Every passport must explicitly declare whether it describes:

- A model
- A batch
- An individual item

---

# 11. URI Strategy

Use deterministic URIs.

Examples:

```text
https://example.org/dpp/resource/product/CFX1
https://example.org/dpp/resource/product-item/CFX1-EU-000145
https://example.org/dpp/resource/battery/BAT-00012
https://example.org/dpp/resource/company/eco-devices-bv
https://example.org/dpp/resource/material/cobalt
https://example.org/dpp/resource/certificate/CERT-0012
```

Rules:

- Lowercase slugs where practical
- No spaces
- Stable identifiers
- No database IDs in public URIs
- Preserve external identifiers as literals
- Support `owl:sameAs` cautiously
- Record URI-generation rules in documentation

---

# 12. SHACL Validation Requirements

## 12.1 Smartphone Shape

A smartphone must have:

- One product identifier
- One manufacturer
- One product model
- At least one battery
- At least one display
- One manufacturing date
- One lifecycle status
- One repairability score
- One software-support commitment
- One recycling instruction
- One carbon-footprint assessment

## 12.2 Battery Shape

A battery must have:

- Battery identifier
- Chemistry
- Capacity and unit
- Cycle endurance
- Replaceability status
- At least one material
- Carbon-footprint value and unit
- End-of-life instruction
- Manufacturer or supplier
- Provenance

## 12.3 Certificate Shape

A certificate must have:

- Certificate identifier
- Certificate type
- Issuer
- Valid-from date
- Valid-until date
- Covered product or component
- Evidence URL or document reference

## 12.4 Cross-Field Rules

Examples:

- `validUntil` must be later than `validFrom`
- Carbon value requires a unit
- Battery capacity requires a unit
- Repairability score must be between 0 and 10
- Recycled-content percentage must be between 0 and 100
- Product manufacturing date cannot be in the future
- Archived products must have an archive date
- Every critical material must have origin information or a documented exception
- Every environmental claim must have provenance
- A product cannot reference itself as a component

## 12.5 Severity

Use:

- `sh:Violation`
- `sh:Warning`
- `sh:Info`

Persist validation results in PostgreSQL and optionally as RDF named graphs.

---

# 13. Data Model in PostgreSQL

PostgreSQL is not the primary semantic store. It must hold application data.

Suggested tables:

```text
users
roles
user_roles
organizations
ingestion_jobs
ingestion_files
ingestion_errors
passport_registry
passport_versions
validation_runs
validation_results
saved_queries
audit_logs
api_keys
report_jobs
system_settings
```

Key principle:

- Business semantics live in the graph.
- Operational metadata lives in PostgreSQL.

---

# 14. Named Graph Strategy

Use named graphs:

```text
urn:dpp:graph:ontology
urn:dpp:graph:shapes
urn:dpp:graph:reference-data
urn:dpp:graph:passport:{passport-id}
urn:dpp:graph:provenance:{passport-id}
urn:dpp:graph:validation:{validation-run-id}
```

Benefits:

- Isolated passport updates
- Versioning
- Easier deletion
- Provenance separation
- Controlled access
- Better testability

---

# 15. Data Ingestion Pipeline

```text
Upload
  ↓
File validation
  ↓
Schema detection
  ↓
Column mapping
  ↓
Normalization
  ↓
Entity resolution
  ↓
URI generation
  ↓
RDF generation
  ↓
SHACL validation
  ↓
Persist valid graph
  ↓
Store validation report
  ↓
Update dashboard metrics
```

## 15.1 Job States

```text
PENDING
RUNNING
MAPPING
VALIDATING
COMPLETED
COMPLETED_WITH_WARNINGS
FAILED
QUARANTINED
```

## 15.2 Idempotency

An import must not create duplicates when rerun.

Use:

- Source-system identifier
- Product identifier
- Source record hash
- Mapping version
- Import timestamp
- Idempotency key

---

# 16. Entity Resolution

Implement conservative entity resolution.

## Exact Matching

- Product identifier
- VAT or registration number
- Certificate number
- GS1-style identifier
- Canonical material code

## Normalized Matching

- Lowercase names
- Whitespace removal
- Punctuation normalization
- Country normalization
- Address normalization

## Fuzzy Matching

Use only as a suggestion, not an automatic merge.

Store:

- Match candidate
- Match score
- Match rule
- Approval status
- Steward decision

---

# 17. Provenance Model

Every important claim must capture:

- Source system
- Source document
- Source record
- Responsible organization
- Import job
- Import time
- Mapping version
- Transformation activity
- Confidence
- Evidence link

Example:

```turtle
dpp-res:claim-001
    a rdf:Statement ;
    rdf:subject dpp-res:product-CFX1 ;
    rdf:predicate dpp:repairabilityScore ;
    rdf:object "8.2"^^xsd:decimal ;
    prov:wasDerivedFrom dpp-res:source-file-22 ;
    prov:wasGeneratedBy dpp-res:import-job-51 ;
    prov:wasAttributedTo dpp-res:manufacturer-eco-devices ;
    prov:generatedAtTime "2026-08-04T17:00:00Z"^^xsd:dateTime .
```

For the MVP, RDF-star may be evaluated, but standard reification or named graphs should be the safe default.

---

# 18. Semantic Observability

This is a differentiating module.

## 18.1 Metrics

Track:

- Passport conformance rate
- SHACL violations by shape
- Missing mandatory fields
- Unknown vocabulary terms
- Deprecated ontology term usage
- Ontology version distribution
- Custom vocabulary usage
- Missing provenance
- Broken certificate references
- Supplier completeness score
- Duplicate-entity candidates
- Unit-normalization failures
- Unmapped source fields
- Carbon-data completeness
- Repair-data completeness
- Recycling-data completeness
- Validation failures over time

## 18.2 Dashboard Views

- Semantic health score
- Top failing rules
- Failing suppliers
- Failing product models
- Quality trend
- Vocabulary adoption
- Data lineage coverage
- Ontology-version usage

## 18.3 Suggested Quality Score

```text
Semantic Quality Score =
  30% completeness
+ 25% SHACL conformance
+ 20% provenance coverage
+ 15% controlled vocabulary conformance
+ 10% reference integrity
```

All weights must be configurable.

---

# 19. REST API Specification

Base path:

```text
/api/v1
```

## Authentication

```text
POST /auth/login
POST /auth/refresh
GET  /auth/me
```

## Products

```text
GET    /products
POST   /products
GET    /products/{product_id}
PUT    /products/{product_id}
DELETE /products/{product_id}
GET    /products/{product_id}/graph
GET    /products/{product_id}/passport
```

## Passports

```text
GET  /passports
POST /passports
GET  /passports/{passport_id}
PUT  /passports/{passport_id}
POST /passports/{passport_id}/validate
GET  /passports/{passport_id}/versions
GET  /passports/{passport_id}/export
GET  /passports/{passport_id}/qr
```

## Ingestion

```text
POST /ingestion/files
GET  /ingestion/jobs
GET  /ingestion/jobs/{job_id}
POST /ingestion/jobs/{job_id}/retry
GET  /ingestion/jobs/{job_id}/errors
```

## Validation

```text
GET /validation/runs
GET /validation/runs/{run_id}
GET /validation/summary
GET /validation/rules
```

## SPARQL

```text
POST /sparql/query
GET  /sparql/templates
POST /sparql/templates
```

Only SELECT, ASK, CONSTRUCT, and DESCRIBE are allowed for ordinary users.

## Dashboard

```text
GET /dashboard/overview
GET /dashboard/carbon
GET /dashboard/repairability
GET /dashboard/materials
GET /dashboard/certificates
GET /dashboard/semantic-quality
```

## Reports

```text
POST /reports
GET  /reports/{report_id}
GET  /reports/{report_id}/download
```

---

# 20. Frontend Pages

## Public

- Landing page
- Product passport
- QR resolver
- Public product search
- Recycling instructions
- Repair information

## Authenticated

- Login
- Overview dashboard
- Passport list
- Passport detail
- Product comparison
- Data ingestion
- Validation results
- Graph explorer
- SPARQL workbench
- Supplier dashboard
- Certificate dashboard
- Semantic observability dashboard
- Reports
- Administration

---

# 21. Dashboard KPIs

Display:

```text
Total passports
Valid passports
Invalid passports
Passports with warnings
Average repairability score
Average recycled-content percentage
Average carbon footprint
Certificates expiring in 30 days
Products with incomplete provenance
Products with critical-material traceability
Semantic quality score
Supplier completeness score
```

---

# 22. SPARQL Query Catalogue

Codex must create at least 20 saved queries.

Required examples:

1. List all smartphones and manufacturers
2. List components for one product
3. List materials used in one battery
4. Find products with user-replaceable batteries
5. Find products with software support below threshold
6. Find products with expired certificates
7. Find products with high carbon footprint
8. Find products with repairability above threshold
9. Find products with recycled content above threshold
10. Trace product to material origin
11. Trace product to recycler
12. List critical materials by supplier
13. List missing-provenance claims
14. List suppliers associated with validation failures
15. List ontology versions in use
16. Find deprecated properties
17. List products with missing recycling instructions
18. Compare product models
19. List passport versions
20. Show supply-chain path

---

# 23. Seed Data

Generate synthetic but realistic data.

## Minimum Dataset

- 50 smartphone models
- 200 product items or batches
- 100 batteries
- 300 components
- 25 manufacturers
- 80 suppliers
- 30 facilities
- 20 recyclers and repair operators
- 25 material types
- 150 certificates
- 500 supply-chain events
- 1,000 provenance records
- At least 15 intentionally invalid passports

## Data Quality Scenarios

Include:

- Missing manufacturer
- Invalid carbon unit
- Expired certificate
- Missing material origin
- Duplicate supplier
- Unknown vocabulary term
- Missing provenance
- Repairability score above 10
- Future manufacturing date
- Battery without recycling instruction
- Product referencing itself
- Invalid identifier
- Unsupported ontology version
- Unmapped material
- Broken evidence link

---

# 24. Testing Strategy

## 24.1 Unit Tests

Test:

- URI generation
- RDF generation
- Datatype conversion
- Unit normalization
- Entity matching
- SHACL execution
- API validation
- Authentication
- Query restrictions
- Score calculations

## 24.2 Integration Tests

Test:

- PostgreSQL
- Fuseki
- Redis
- API-to-graph interaction
- File ingestion
- Passport persistence
- Validation persistence
- Export functionality

## 24.3 Semantic Tests

Test:

- Ontology consistency
- Required classes and properties
- SHACL shapes
- Competency questions
- Expected inference
- No unintended domain/range contradictions
- Query result correctness

## 24.4 End-to-End Tests

Use Playwright to test:

- Login
- Upload data
- Review validation result
- Open passport
- Explore graph
- Run SPARQL query
- Download report
- Scan or open QR URL

## 24.5 Performance Tests

Test:

- 1,000-passport ingestion
- Concurrent product search
- Standard dashboard queries
- Graph expansion
- Export job

## 24.6 Security Tests

Test:

- Unauthorized access
- Malicious file upload
- SPARQL update injection
- Oversized query
- Path traversal
- JWT expiry
- Role restrictions
- CORS
- Secret leakage

---

# 25. Docker Compose Services

Create services:

```text
frontend
backend
worker
postgres
redis
fuseki
nginx
prometheus
grafana
```

The monitoring services may be optional profiles.

Example startup:

```powershell
cd "D:\Digital Product Passport"
Copy-Item .env.example .env
docker compose up --build
```

Expected URLs:

```text
Frontend:     http://localhost:3000
Backend API:  http://localhost:8000
Swagger:      http://localhost:8000/docs
Fuseki:       http://localhost:3030
Grafana:      http://localhost:3001
```

---

# 26. Configuration

Create `.env.example` containing:

```env
APP_NAME=Digital Product Passport
APP_ENV=development
APP_DEBUG=true

POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=dpp
POSTGRES_USER=dpp
POSTGRES_PASSWORD=change_me

FUSEKI_URL=http://fuseki:3030/dpp
FUSEKI_QUERY_URL=http://fuseki:3030/dpp/query
FUSEKI_UPDATE_URL=http://fuseki:3030/dpp/update
FUSEKI_USERNAME=admin
FUSEKI_PASSWORD=change_me

REDIS_URL=redis://redis:6379/0

JWT_SECRET_KEY=change_me
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

PUBLIC_BASE_URL=http://localhost:3000
API_BASE_URL=http://localhost:8000
```

---

# 27. Logging and Auditability

Use structured JSON logging.

Log:

- User
- Request ID
- Job ID
- Passport ID
- Source system
- Action
- Result
- Duration
- Error category

Audit events:

- Passport created
- Passport updated
- Passport archived
- Data uploaded
- Validation run
- Certificate changed
- Query saved
- User role changed
- Graph export
- Report generated

Never log:

- Passwords
- JWT tokens
- Secrets
- Sensitive file contents

---

# 28. Error Handling

Create consistent API errors:

```json
{
  "error": {
    "code": "PASSPORT_VALIDATION_FAILED",
    "message": "The passport contains validation violations.",
    "details": [],
    "request_id": "..."
  }
}
```

Required error categories:

- AuthenticationError
- AuthorizationError
- NotFoundError
- ValidationError
- MappingError
- GraphStoreError
- DatabaseError
- FileUploadError
- QueryRejectedError
- ExternalReferenceError

---

# 29. Development Phases

## Phase 0 — Bootstrap

Deliver:

- Repository
- Docker Compose
- Backend skeleton
- Frontend skeleton
- PostgreSQL
- Fuseki
- Health checks
- CI

Acceptance criteria:

- `docker compose up --build` succeeds
- Frontend loads
- Backend `/health` succeeds
- Fuseki responds
- CI passes

## Phase 1 — Ontology Foundation

Deliver:

- Core ontology
- Smartphone ontology
- Battery ontology
- Materials
- Organizations
- Provenance
- Initial documentation
- Competency questions

Acceptance criteria:

- Ontology parses
- Semantic tests pass
- Example product graph loads
- 10 competency questions have SPARQL queries

## Phase 2 — SHACL Validation

Deliver:

- Product shapes
- Smartphone shapes
- Battery shapes
- Certificate shapes
- Validation service
- Validation API
- Validation reports

Acceptance criteria:

- Valid sample passes
- Invalid samples fail correctly
- Severity levels work
- Reports are persisted

## Phase 3 — Ingestion Pipeline

Deliver:

- CSV ingestion
- JSON ingestion
- Mapping layer
- URI generation
- RDF generation
- Job tracking
- Error quarantine

Acceptance criteria:

- Seed CSV loads
- Re-running is idempotent
- Invalid records are isolated
- Import status is visible

## Phase 4 — Product Passport API

Deliver:

- Product CRUD
- Passport CRUD
- Versioning
- JSON-LD export
- Turtle export
- QR generation

Acceptance criteria:

- Product can be created and retrieved
- Passport graph is stored
- Export is valid RDF
- QR resolves to passport page

## Phase 5 — Frontend MVP

Deliver:

- Login
- Dashboard
- Passport list
- Passport detail
- Validation page
- Ingestion page

Acceptance criteria:

- Main workflows are usable
- Errors are visible
- Loading states exist
- Responsive desktop layout

## Phase 6 — SPARQL and Graph Explorer

Deliver:

- Query workbench
- Saved templates
- Result table
- CSV export
- Cytoscape graph explorer

Acceptance criteria:

- 20 templates work
- Unsafe updates are blocked
- Product graph expands interactively

## Phase 7 — Semantic Observability

Deliver:

- Quality metrics
- Quality score
- Trends
- Vocabulary usage
- Ontology-version metrics
- Supplier completeness

Acceptance criteria:

- Metrics derive from real graph and validation results
- Dashboard filters work
- Scores are reproducible

## Phase 8 — Reports and Governance

Deliver:

- Compliance report
- Sustainability report
- Supplier-quality report
- Certificate report
- Audit log viewer

Acceptance criteria:

- Reports generate successfully
- Reports cite source data
- Exported files are downloadable

## Phase 9 — Hardening

Deliver:

- Security tests
- Performance tests
- Backup and restore
- Monitoring
- Documentation
- Demo script

Acceptance criteria:

- All test suites pass
- Security scan has no critical findings
- Backup restores successfully
- Portfolio demo is reproducible

---

# 30. Definition of Done

A feature is done only when:

- Code is implemented
- Types are defined
- Unit tests exist
- Integration tests exist where relevant
- Documentation is updated
- API is documented
- Errors are handled
- Logging is included
- Security implications are reviewed
- Acceptance criteria pass
- CI passes

---

# 31. Codex Operating Rules

Codex must follow these rules:

1. Work phase by phase.
2. Do not implement the entire system in one uncontrolled pass.
3. Keep the application runnable after every phase.
4. Create tests before or alongside implementation.
5. Do not leave placeholder functions without explicit TODO documentation.
6. Do not hardcode secrets.
7. Do not silently ignore errors.
8. Do not invent legal compliance claims.
9. Document assumptions.
10. Prefer small, reviewable commits.
11. Preserve backward compatibility unless documented.
12. Run lint, type checks, tests, and smoke tests before completing a phase.
13. Update `README.md` and relevant docs after every phase.
14. Use deterministic seed data.
15. Add migration scripts for all database changes.
16. Validate RDF and SHACL files in CI.
17. Keep business logic out of API route files.
18. Keep semantic logic in the semantic and service layers.
19. Use dependency injection for external services.
20. Never store passwords in plain text.

---

# 32. First Codex Prompt

Use the following as the first implementation prompt:

```text
You are implementing a production-grade Digital Product Passport Knowledge Graph platform.

The project root is:

D:\Digital Product Passport

Read BLUEPRINT.md completely before modifying files.

Implement only Phase 0 — Bootstrap.

Requirements:

1. Create the repository structure required for Phase 0.
2. Create a FastAPI backend with:
   - GET /health
   - GET /ready
   - structured logging
   - environment-based configuration
3. Create a React + TypeScript + Vite frontend with:
   - landing page
   - health status panel
4. Create Docker services for:
   - backend
   - frontend
   - PostgreSQL
   - Apache Jena Fuseki
   - Redis
5. Add:
   - .env.example
   - .gitignore
   - docker-compose.yml
   - root README.md
   - backend README.md
   - frontend README.md
6. Add backend tests for health and configuration.
7. Add frontend tests for the landing page.
8. Add GitHub Actions for backend and frontend CI.
9. Create PowerShell bootstrap and reset scripts.
10. Ensure this command works:

   docker compose up --build

Do not implement ontology, SHACL, ingestion, dashboards, authentication, or product features yet.

Before finishing:
- run backend tests
- run frontend tests
- validate docker compose configuration
- report created files
- report commands executed
- report any unresolved issues
```

---

# 33. Subsequent Codex Prompt Pattern

For each phase, use:

```text
Read BLUEPRINT.md and all existing architecture documentation.

Implement only Phase X.

Before coding:
1. Inspect the existing repository.
2. Identify dependencies and affected modules.
3. Create or update tests.
4. Preserve all working functionality.

During implementation:
- Follow the repository architecture.
- Use type-safe code.
- Add logging and error handling.
- Update documentation.

Before finishing:
- Run linting.
- Run type checks.
- Run unit tests.
- Run integration tests where applicable.
- Run semantic validation where applicable.
- Run the application smoke test.
- List all files created or changed.
- State all acceptance criteria and whether each passed.
- Document unresolved issues without hiding them.
```

---

# 34. Demo Scenario

The final system must support this demonstration:

1. Start the system with Docker Compose.
2. Log in as a manufacturer.
3. Upload a smartphone CSV file.
4. Observe ingestion progress.
5. View SHACL validation errors.
6. Correct or replace invalid data.
7. Re-run validation.
8. Open the product passport.
9. Scan or open the QR code.
10. Explore the product graph.
11. Trace the battery to its materials and suppliers.
12. Run a SPARQL query for high-risk materials.
13. View expired certificates.
14. Compare repairability scores.
15. View semantic-observability metrics.
16. Export the passport as JSON-LD.
17. Generate a sustainability report.

---

# 35. Portfolio Deliverables

The completed repository must include:

- Architecture diagram
- Ontology diagram
- SHACL examples
- Product screenshots
- Dashboard screenshots
- Graph explorer screenshot
- SPARQL examples
- Demo video script
- Deployment instructions
- Testing evidence
- Data-governance explanation
- Semantic-observability explanation
- CV bullet points
- LinkedIn project description
- Interview talking points

Suggested CV bullet:

> Built a production-grade Digital Product Passport Knowledge Graph for circular electronics using RDF, OWL, SHACL, SPARQL, FastAPI, React, PostgreSQL and Apache Jena Fuseki, enabling product traceability, supply-chain provenance, compliance validation, repairability analytics and semantic observability.

---

# 36. Future Extensions

Potential advanced phases:

- Natural-language-to-SPARQL
- Data-space connector integration
- TNO Knowledge Engine integration
- ODRL-based access policies
- Verifiable credentials
- Digital signatures
- GS1 Digital Link
- Real-time battery state-of-health
- Product event streaming
- Graph embeddings
- Supplier risk scoring
- Automated ontology alignment
- DPP registry simulation
- Multi-tenant organizations
- Cloud deployment
- Kubernetes
- Statement-level access control
- Regulatory rule packs
- AI-assisted data mapping

---

# 37. Final Success Criteria

The project is successful when:

- The full system runs locally using Docker Compose.
- A smartphone passport can be created from uploaded data.
- RDF is generated and stored in Fuseki.
- SHACL validation produces understandable results.
- Products, components, materials, suppliers, carbon data, certificates, repairability, recycling and provenance are connected in the graph.
- Users can query the graph through SPARQL.
- Users can navigate the graph visually.
- Dashboards derive metrics from actual stored data.
- Semantic-observability metrics expose interoperability and data-quality problems.
- Tests and CI protect core functionality.
- Documentation allows another developer to run and understand the system.
- The repository is credible as a professional portfolio project.

---

# 38. Immediate Next Action

1. Save this document as:

```text
D:\Digital Product Passport\BLUEPRINT.md
```

2. Open Codex in the project folder.

3. Paste the Phase 0 prompt from Section 32.

4. Review Phase 0 before asking Codex to continue to Phase 1.

5. Do not allow Codex to skip tests or combine all phases into one implementation pass.
