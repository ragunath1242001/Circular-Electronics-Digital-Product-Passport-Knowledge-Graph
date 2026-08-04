# SPARQL and Graph Explorer

Phase 6 adds a read-only semantic workbench at `#graph`.

## API

| Endpoint | Purpose |
| --- | --- |
| `GET /api/v1/sparql/templates` | Return the 20 version-controlled query templates |
| `POST /api/v1/sparql/query` | Execute a validated `SELECT` query and return tabular bindings |
| `GET /api/v1/sparql/graph` | Return one-hop nodes and edges for a product or DPP resource URI |

The query endpoint accepts at most 20,000 characters and returns at most 500 rows.
SPARQL update forms are rejected before reaching Fuseki. The graph endpoint accepts
only stable URIs under `https://example.org/dpp/resource/`.

## Workspace

The query workbench loads the catalogue from `sparql/competency`, renders bindings in
a result table, and exports the displayed bindings as CSV. The Cytoscape explorer
starts from a selected product. Selecting a node and choosing **Expand selected**
merges its immediate neighbors into the current graph; **Reset graph** returns to the
selected product's first hop.
