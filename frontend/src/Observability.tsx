import { type CSSProperties, type FormEvent, useEffect, useState } from "react";

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

type Metrics = {
  generated_at: string;
  applied_filters: Record<string, string>;
  available_filters: { manufacturers: string[]; suppliers: string[]; models: string[] };
  products: number;
  passports: number;
  validation_runs: number;
  quality_score: number;
  score_components: Record<string, number>;
  score_weights: Record<string, number>;
  conformance_rate: number;
  supplier_completeness: number;
  carbon_completeness: number;
  repair_completeness: number;
  recycling_completeness: number;
  missing_mandatory_fields: number;
  missing_provenance: number;
  unknown_vocabulary_terms: number;
  deprecated_term_usage: number;
  duplicate_entity_candidates: number;
  vocabulary_usage: { term: string; count: number; controlled: boolean }[];
  ontology_versions: { version: string; products: number }[];
  supplier_scores: { supplier: string; products: number; completeness: number }[];
  top_failing_rules: { rule: string; count: number }[];
  validation_trend: { date: string; runs: number; passed: number; violations: number }[];
};

const labels: Record<string, string> = {
  completeness: "Mandatory fields",
  conformance: "SHACL conformance",
  provenance: "Provenance coverage",
  vocabulary: "Vocabulary control",
  reference_integrity: "Reference integrity",
};

export default function Observability() {
  const [metrics, setMetrics] = useState<Metrics>();
  const [filters, setFilters] = useState({ manufacturer: "", supplier: "", model: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  async function load(next = filters) {
    setLoading(true);
    setError("");
    const params = new URLSearchParams(
      Object.entries(next).filter((entry): entry is [string, string] => Boolean(entry[1])),
    );
    try {
      const response = await fetch(`${apiBaseUrl}/api/v1/observability/metrics?${params}`);
      if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        throw new Error(body.detail || `Request failed with HTTP ${response.status}`);
      }
      setMetrics(await response.json() as Metrics);
    } catch (reason) {
      setError((reason as Error).message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void load({ manufacturer: "", supplier: "", model: "" }); }, []);

  function apply(event: FormEvent) {
    event.preventDefault();
    void load();
  }

  function reset() {
    const empty = { manufacturer: "", supplier: "", model: "" };
    setFilters(empty);
    void load(empty);
  }

  return <>
    <section className="page-heading observability-heading"><div><p className="eyebrow">Semantic observability</p><h1>Knowledge health</h1><p>Reproducible quality signals derived from passport graphs and validation history.</p></div>{metrics && <span>Calculated {new Date(metrics.generated_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</span>}</section>
    <form className="panel metric-filters" onSubmit={apply}>
      <label>Manufacturer<select value={filters.manufacturer} onChange={(event) => setFilters({ ...filters, manufacturer: event.target.value })}><option value="">All manufacturers</option>{metrics?.available_filters.manufacturers.map((item) => <option key={item}>{item}</option>)}</select></label>
      <label>Supplier<select value={filters.supplier} onChange={(event) => setFilters({ ...filters, supplier: event.target.value })}><option value="">All suppliers</option>{metrics?.available_filters.suppliers.map((item) => <option key={item}>{item}</option>)}</select></label>
      <label>Product model<select value={filters.model} onChange={(event) => setFilters({ ...filters, model: event.target.value })}><option value="">All models</option>{metrics?.available_filters.models.map((item) => <option key={item}>{item}</option>)}</select></label>
      <button className="primary" disabled={loading}>Apply filters</button>
      <button className="text-button" type="button" onClick={reset}>Reset</button>
    </form>
    {error && <p className="notice error" role="alert">{error}</p>}
    {loading && !metrics ? <p className="loading" role="status"><span />Calculating semantic metrics…</p> : metrics && <>
      <section className="health-grid">
        <article className="quality-score panel"><div className="score-ring" style={{ "--score": metrics.quality_score } as CSSProperties}><strong>{metrics.quality_score}</strong><span>/ 100</span></div><div><p className="eyebrow">Semantic quality score</p><h2>{metrics.quality_score >= 90 ? "Graph health is strong" : metrics.quality_score >= 70 ? "Graph health is stable" : "Graph needs attention"}</h2><p>Weighted from completeness, SHACL conformance, provenance, vocabulary control, and reference integrity.</p><small>{metrics.products} products · {metrics.passports} passports · {metrics.validation_runs} validation runs</small></div></article>
        <article className="panel score-components"><div className="panel-title"><h2>Score composition</h2><span>Configured weights</span></div>{Object.entries(metrics.score_components).map(([name, value]) => <div className="component-row" key={name}><div><strong>{labels[name] ?? name}</strong><span>{Math.round(metrics.score_weights[name] * 100)}% weight</span></div><div className="meter"><span style={{ width: `${value}%` }} /></div><b>{value.toFixed(1)}</b></div>)}</article>
      </section>
      <section className="coverage-grid" aria-label="Quality coverage metrics">
        {[['SHACL conformance', metrics.conformance_rate], ['Supplier completeness', metrics.supplier_completeness], ['Carbon data', metrics.carbon_completeness], ['Repair data', metrics.repair_completeness], ['Recycling data', metrics.recycling_completeness]].map(([name, value]) => <article className="metric compact" key={String(name)}><p>{name}</p><strong>{Number(value).toFixed(1)}%</strong><div className="meter"><span style={{ width: `${value}%` }} /></div></article>)}
      </section>
      <section className="observability-grid">
        <article className="panel trend-panel"><div className="panel-title"><div><p className="eyebrow">30-day signal</p><h2>Validation trend</h2></div><span>{metrics.validation_trend.reduce((total, point) => total + point.violations, 0)} violations</span></div>{metrics.validation_trend.length ? <div className="trend-chart" role="img" aria-label="Validation pass rate by day">{metrics.validation_trend.map((point) => { const passRate = point.runs ? point.passed / point.runs * 100 : 0; return <div key={point.date}><span style={{ height: `${Math.max(passRate, 4)}%` }} title={`${passRate.toFixed(0)}% passed`} /><small>{new Date(`${point.date}T00:00:00`).toLocaleDateString([], { month: "short", day: "numeric" })}</small></div>; })}</div> : <p className="empty">No validation activity in the last 30 days.</p>}</article>
        <article className="panel issue-panel"><div className="panel-title"><div><p className="eyebrow">Open signals</p><h2>Quality exceptions</h2></div></div><dl><div><dt>Missing mandatory fields</dt><dd>{metrics.missing_mandatory_fields}</dd></div><div><dt>Missing provenance</dt><dd>{metrics.missing_provenance}</dd></div><div><dt>Unknown vocabulary terms</dt><dd>{metrics.unknown_vocabulary_terms}</dd></div><div><dt>Deprecated term usage</dt><dd>{metrics.deprecated_term_usage}</dd></div><div><dt>Duplicate candidates</dt><dd>{metrics.duplicate_entity_candidates}</dd></div></dl></article>
      </section>
      <section className="observability-grid lower">
        <article className="panel"><div className="panel-title"><div><p className="eyebrow">SHACL diagnostics</p><h2>Top failing rules</h2></div></div>{metrics.top_failing_rules.length ? <div className="rule-list">{metrics.top_failing_rules.map((item) => <div key={item.rule}><span>{item.rule}</span><strong>{item.count}</strong></div>)}</div> : <p className="empty">No SHACL violations recorded.</p>}</article>
        <article className="panel"><div className="panel-title"><div><p className="eyebrow">Vocabulary adoption</p><h2>Terms in use</h2></div><span>{metrics.vocabulary_usage.length} terms</span></div>{metrics.vocabulary_usage.length ? <div className="term-cloud">{metrics.vocabulary_usage.map((item) => <span className={item.controlled ? "controlled" : "custom"} key={item.term}>{item.term}<b>{item.count}</b></span>)}</div> : <p className="empty">No vocabulary terms match these filters.</p>}<div className="version-strip"><strong>Ontology versions</strong>{metrics.ontology_versions.map((item) => <span key={item.version}>v{item.version} · {item.products}</span>)}</div></article>
      </section>
      <section className="panel table-panel supplier-table"><div className="panel-title"><div><p className="eyebrow">Supply network</p><h2>Supplier completeness</h2></div><span>{metrics.supplier_scores.length} suppliers</span></div>{metrics.supplier_scores.length ? <div className="table-wrap"><table><thead><tr><th>Supplier</th><th>Products</th><th>Material and origin coverage</th><th>Score</th></tr></thead><tbody>{metrics.supplier_scores.map((item) => <tr key={item.supplier}><td><strong>{item.supplier}</strong></td><td>{item.products}</td><td><div className="meter"><span style={{ width: `${item.completeness}%` }} /></div></td><td>{item.completeness.toFixed(1)}%</td></tr>)}</tbody></table></div> : <p className="empty">No suppliers match these filters.</p>}</section>
    </>}
  </>;
}
