import cytoscape, { type Core, type ElementDefinition } from "cytoscape";
import { type FormEvent, useEffect, useRef, useState } from "react";
import { api } from "./api";

type Template = { id: string; title: string; query: string };
type QueryResult = { variables: string[]; rows: Record<string, string>[]; truncated: boolean };
type Product = { id: string; product_name: string; product_identifier: string };
type GraphNode = { id: string; label: string; type: string };
type GraphEdge = { id: string; source: string; target: string; label: string };
type GraphResult = { nodes: GraphNode[]; edges: GraphEdge[] };

function mergeGraph(current: GraphResult, incoming: GraphResult): GraphResult {
  return {
    nodes: [...new Map([...current.nodes, ...incoming.nodes].map((item) => [item.id, item])).values()],
    edges: [...new Map([...current.edges, ...incoming.edges].map((item) => [item.id, item])).values()],
  };
}

function csvCell(value: string): string {
  return `"${value.replaceAll('"', '""')}"`;
}

export default function GraphWorkbench() {
  const graphElement = useRef<HTMLDivElement>(null);
  const cy = useRef<Core>(undefined);
  const [templates, setTemplates] = useState<Template[]>([]);
  const [query, setQuery] = useState("");
  const [result, setResult] = useState<QueryResult>();
  const [queryError, setQueryError] = useState("");
  const [queryBusy, setQueryBusy] = useState(false);
  const [products, setProducts] = useState<Product[]>([]);
  const [productId, setProductId] = useState("");
  const [graph, setGraph] = useState<GraphResult>({ nodes: [], edges: [] });
  const [selectedNode, setSelectedNode] = useState("");
  const [graphError, setGraphError] = useState("");
  const [graphBusy, setGraphBusy] = useState(false);

  useEffect(() => {
    Promise.all([
      api<Template[]>("/api/v1/sparql/templates"),
      api<Product[]>("/api/v1/products?limit=200"),
    ]).then(([saved, productList]) => {
      setTemplates(saved);
      setQuery(saved[0]?.query ?? "");
      setProducts(productList);
      setProductId(productList[0]?.id ?? "");
    }).catch((reason: Error) => setQueryError(reason.message));
  }, []);

  async function loadGraph(id: string) {
    if (!id) return;
    setGraphBusy(true); setGraphError("");
    try {
      const next = await api<GraphResult>(`/api/v1/sparql/graph?product_id=${encodeURIComponent(id)}`);
      setGraph(next); setSelectedNode(next.nodes[0]?.id ?? "");
    } catch (reason) { setGraphError((reason as Error).message); }
    finally { setGraphBusy(false); }
  }

  useEffect(() => { void loadGraph(productId); }, [productId]);

  useEffect(() => {
    if (!graphElement.current) return;
    cy.current?.destroy();
    const elements: ElementDefinition[] = [
      ...graph.nodes.map((node) => ({ data: node })),
      ...graph.edges.map((edge) => ({ data: edge })),
    ];
    cy.current = cytoscape({
      container: graphElement.current,
      elements,
      style: [
        { selector: "node", style: { "background-color": "#c8ef72", color: "#18201d", label: "data(label)", "font-size": 10, "text-wrap": "wrap", "text-max-width": "90px", width: 38, height: 38 } },
        { selector: "node:selected", style: { "border-width": 4, "border-color": "#d86f3d" } },
        { selector: "edge", style: { width: 1.5, "line-color": "#8fa89b", "target-arrow-color": "#8fa89b", "target-arrow-shape": "triangle", "curve-style": "bezier", label: "data(label)", "font-size": 8, color: "#dce7e1", "text-background-color": "#123d2e", "text-background-opacity": 0.8 } },
      ],
      layout: { name: "cose", animate: false, padding: 35 },
    });
    cy.current.on("select", "node", (event) => setSelectedNode(event.target.id()));
    return () => { cy.current?.destroy(); cy.current = undefined; };
  }, [graph]);

  async function run(event: FormEvent) {
    event.preventDefault(); setQueryBusy(true); setQueryError("");
    try {
      setResult(await api<QueryResult>("/api/v1/sparql/query", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, limit: 200 }),
      }));
    } catch (reason) { setQueryError((reason as Error).message); }
    finally { setQueryBusy(false); }
  }

  async function expand() {
    if (!selectedNode) return;
    setGraphBusy(true); setGraphError("");
    try {
      const next = await api<GraphResult>(`/api/v1/sparql/graph?root_uri=${encodeURIComponent(selectedNode)}`);
      setGraph((current) => mergeGraph(current, next));
    } catch (reason) { setGraphError((reason as Error).message); }
    finally { setGraphBusy(false); }
  }

  function downloadCsv() {
    if (!result) return;
    const csv = [result.variables, ...result.rows.map((row) => result.variables.map((key) => row[key] ?? ""))]
      .map((row) => row.map(csvCell).join(",")).join("\n");
    const url = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
    const link = document.createElement("a"); link.href = url; link.download = "sparql-results.csv"; link.click();
    URL.revokeObjectURL(url);
  }

  return <>
    <section className="page-heading"><div><p className="eyebrow">Semantic discovery</p><h1>Graph &amp; SPARQL</h1><p>Query the passport dataset, export results, and follow product relationships.</p></div></section>
    <section className="workbench-grid">
      <form className="panel query-panel" onSubmit={run}>
        <div className="panel-title"><div><p className="eyebrow">Read-only workspace</p><h2>Query workbench</h2></div><span>{templates.length} saved templates</span></div>
        <label>Saved query<select aria-label="Saved query" onChange={(event) => setQuery(templates.find((item) => item.id === event.target.value)?.query ?? "")}>
          {templates.map((item) => <option key={item.id} value={item.id}>{item.id}. {item.title}</option>)}
        </select></label>
        <textarea aria-label="SPARQL query" value={query} onChange={(event) => setQuery(event.target.value)} required />
        <button className="primary" disabled={queryBusy}>{queryBusy ? "Running…" : "Run query"}</button>
        {queryError && <p className="notice error" role="alert">{queryError}</p>}
      </form>
      <article className="panel query-results">
        <div className="panel-title"><div><p className="eyebrow">Bindings</p><h2>Results</h2></div>{result && <button className="secondary compact-button" onClick={downloadCsv}>Download CSV</button>}</div>
        {!result ? <div className="empty-state"><span aria-hidden="true">⌁</span><h2>Ready to query</h2><p>Choose one of the saved templates or write a SELECT query.</p></div> : result.rows.length ? <><p className="result-meta">{result.rows.length} rows{result.truncated ? " · limited to 200" : ""}</p><div className="table-wrap"><table><thead><tr>{result.variables.map((item) => <th key={item}>{item}</th>)}</tr></thead><tbody>{result.rows.map((row, index) => <tr key={index}>{result.variables.map((item) => <td className="mono" key={item} title={row[item]}>{row[item] ?? "—"}</td>)}</tr>)}</tbody></table></div></> : <p className="empty">The query completed with no matching rows.</p>}
      </article>
    </section>
    <section className="panel graph-panel">
      <div className="panel-title"><div><p className="eyebrow">One relationship at a time</p><h2>Product graph explorer</h2></div><span>{graph.nodes.length} nodes · {graph.edges.length} edges</span></div>
      <div className="graph-controls">
        <label>Product<select aria-label="Graph product" value={productId} onChange={(event) => setProductId(event.target.value)}>{products.map((item) => <option key={item.id} value={item.id}>{item.product_name} · {item.product_identifier}</option>)}</select></label>
        <label>Selected node<select aria-label="Selected graph node" value={selectedNode} onChange={(event) => setSelectedNode(event.target.value)}>{graph.nodes.map((node) => <option key={node.id} value={node.id}>{node.label} · {node.type}</option>)}</select></label>
        <button className="secondary" onClick={expand} disabled={graphBusy || !selectedNode}>{graphBusy ? "Loading…" : "Expand selected"}</button>
        <button className="text-button" onClick={() => void loadGraph(productId)}>Reset graph</button>
      </div>
      {graphError && <p className="notice error" role="alert">{graphError}</p>}
      <div className="graph-canvas" ref={graphElement} role="img" aria-label="Interactive product knowledge graph. Select a node, then use Expand selected to load its neighbors." />
    </section>
  </>;
}
