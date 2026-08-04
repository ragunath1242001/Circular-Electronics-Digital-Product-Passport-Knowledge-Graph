# Smartphone import mapping 1.0.0

CSV headers and JSON keys are identical. Every field is required.

| Source field | RDF target |
| --- | --- |
| `product_identifier` | `dpp:productIdentifier` and deterministic product URI |
| `product_name` | `dct:title` |
| `model_number` | `dpp:modelNumber` |
| `manufacturer_name` | `dpp:manufacturedBy` organization |
| `manufacturing_date` | `dpp:manufacturingDate` |
| `repairability_score` | `dpp:repairabilityScore` |
| `software_support_years` | `dpp:SoftwareSupportCommitment` |
| `carbon_kg_co2e` | Product `dpp:CarbonFootprintAssessment` |
| `battery_*` | Embedded `dpp:Battery`, durability, capacity, and carbon claims |
| `display_identifier` | Embedded `dpp:Display` |
| `supplier_name` | Battery and material `dpp:suppliedBy` |
| `material_name` | Material occurrence and controlled material-type URI |
| `material_origin` | `dpp:originatesFrom` facility |
| `recycled_content_percentage` | `dpp:recycledContentPercentage` |

Identifiers use lowercase ASCII slugs. Organization, facility, and material names
resolve by exact normalized value only. The source system, canonical record hash,
and mapping version form the idempotency boundary.

