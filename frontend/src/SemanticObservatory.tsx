import { type DependencyList, type FormEvent, useEffect, useState } from "react";
import { api, apiBaseUrl } from "./api";

type Metric = {
  metric_id: string;
  name: string;
  value: number | null;
  numerator: number | null;
  denominator: number | null;
  bucket_start?: string;
};
type Summary = {
  documents: number;
  organisations: number;
  domains: Record<string, number>;
  ontology_versions: Record<string, number>;
  main_metrics: Record<string, number | null>;
};
type Incident = {
  id: string;
  detector_type: string;
  severity: string;
  explanation: string;
  last_detected_at: string;
};
type Evidence = {
  id: string;
  candidate_type: string;
  status: "NEW" | "MARKED_FOR_REVIEW" | "DISMISSED";
  label: string;
  affected_concepts: string[];
  first_seen: string;
  last_seen: string;
  occurrence_count: number;
  organisation_count: number;
  domain_count: number;
  trend: string;
  growth_rate?: number;
  persistence_days: number;
  mapping_status: string;
  conformance_impact: number;
  recommendation: string;
  source_incident_id?: string;
  evidence_references: string[];
  annotation?: string;
};
type Adoption = {
  ontology_id: string;
  current_version: string;
  documents: number;
  current_documents: number;
  adoption_rate: number;
  version_distribution: Record<string, number>;
  lagging_organisations: {
    organisation_id: string;
    documents: number;
    current_documents: number;
    adoption_rate: number;
  }[];
};
type ValidationSummary = {
  total_documents: number;
  validated_documents: number;
  conforming_documents: number;
  nonconforming_documents: number;
  conformance_rate: number;
  violations: number;
  warnings: number;
};
type Constraint = {
  id: string;
  profile: string;
  path?: string;
  component: string;
  severity: string;
  message: string;
  violations: number;
  documents: number;
  organisations: number;
  domains: string[];
  evidence_references: string[];
};
type TermUsage = {
  term_iri: string;
  category: string;
  occurrences: number;
  documents: number;
  organisations: number;
  domains: string[];
};
type SignalSummary = {
  occurrences: number;
  by_category: Record<string, number>;
};
type Organisation = {
  organisation_id: string;
  documents: number;
  domains: Record<string, number>;
  profiles: Record<string, number>;
  ontology_versions: Record<string, number>;
  conformance_rate: number;
  metric_values: Record<string, number | null>;
};

function useLoad<T>(loader: () => Promise<T>, dependencies: DependencyList) {
  const [data, setData] = useState<T>();
  const [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    setData(undefined);
    setError("");
    loader().then((value) => active && setData(value)).catch((reason: Error) => {
      if (active) setError(reason.message);
    });
    return () => { active = false; };
  }, dependencies);
  return { data, error, setData };
}

function Loading() {
  return <p className="loading" role="status"><span />Loading observatory data...</p>;
}

function ErrorNotice({ message }: { message: string }) {
  return <p className="notice error" role="alert">{message}</p>;
}

function rate(value: number | null | undefined): string {
  return value == null ? "—" : `${(value * 100).toFixed(1)}%`;
}

function compact(value: number): string {
  return new Intl.NumberFormat("en", { notation: "compact", maximumFractionDigits: 1 }).format(value);
}

function MetricCard({ id, label, value, note }: {
  id: string;
  label: string;
  value: number | null | undefined;
  note: string;
}) {
  return <article className="metric compact"><p>{label}</p><strong>{rate(value)}</strong><span>{note}</span><a className="explain-link" href={`${apiBaseUrl}/api/v1/metrics/${id}/explain`}>Explain</a></article>;
}

function ObservatoryNav() {
  const items = [
    ["overview", "Overview"],
    ["ontology-adoption", "Ontology adoption"],
    ["validation-intelligence", "Validation"],
    ["vocabulary-drift", "Vocabulary & drift"],
    ["evidence", "Evidence"],
  ];
  return <nav className="observatory-tabs" aria-label="Semantic observatory views">
    {items.map(([path, label]) => <a key={path} href={`#${path}`}>{label}</a>)}
  </nav>;
}

function Bars({ values }: { values: Record<string, number> }) {
  const maximum = Math.max(...Object.values(values), 1);
  return <div className="bar-list">{Object.entries(values).map(([label, value]) => <div key={label}><span>{label}</span><div className="meter"><span style={{ width: `${value / maximum * 100}%` }} /></div><strong>{compact(value)}</strong></div>)}</div>;
}

function Overview() {
  const { data, error } = useLoad(async () => {
    const [summary, signals, incidents, evidence, trend] = await Promise.all([
      api<Summary>("/api/v1/ecosystem/summary"),
      api<SignalSummary>("/api/v1/signals/summary"),
      api<Incident[]>("/api/v1/incidents?status=OPEN&limit=5"),
      api<Evidence[]>("/api/v1/evidence?status=NEW&limit=5"),
      api<Metric[]>("/api/v1/metrics?granularity=day"),
    ]);
    return { summary, signals, incidents, evidence, trend };
  }, []);
  if (error) return <ErrorNotice message={error} />;
  if (!data) return <Loading />;
  const { summary, signals, incidents, evidence } = data;
  return <>
    <section className="page-heading"><div><p className="eyebrow">Semantic observatory</p><h1>Ecosystem overview</h1><p>Operational evidence from {compact(summary.documents)} product passports.</p></div></section>
    <section className="observatory-kpis">
      <article><span>DPPs observed</span><strong>{compact(summary.documents)}</strong></article>
      <article><span>Organisations</span><strong>{summary.organisations}</strong></article>
      <article><span>Domains</span><strong>{Object.keys(summary.domains).length}</strong></article>
      <MetricCard id="MET-001" label="Current ontology" value={summary.main_metrics["MET-001"]} note="Adoption" />
      <MetricCard id="MET-005" label="SHACL" value={summary.main_metrics["MET-005"]} note="Conformance" />
      <MetricCard id="MET-002" label="Vocabulary" value={summary.main_metrics["MET-002"]} note="Reuse" />
      <MetricCard id="MET-008" label="Mappings" value={summary.main_metrics["MET-008"]} note="Coverage" />
    </section>
    <section className="observatory-grid">
      <article className="panel"><div className="panel-title"><h2>Term category distribution</h2><span>{compact(signals.occurrences)} usages</span></div><Bars values={signals.by_category} /></article>
      <article className="panel"><div className="panel-title"><h2>Active incidents</h2><a href="#vocabulary-drift">Drill down</a></div><div className="observatory-list">{incidents.map((item) => <div key={item.id}><span className={`badge ${item.severity}`}>{item.detector_type}</span><strong>{item.explanation}</strong></div>)}</div></article>
    </section>
    <section className="panel table-panel"><div className="panel-title"><h2>Top evidence candidates</h2><a href="#evidence">Review all</a></div><div className="table-wrap"><table><thead><tr><th>Candidate</th><th>Type</th><th>Organisations</th><th>Occurrences</th></tr></thead><tbody>{evidence.map((item) => <tr key={item.id}><td><strong>{item.label}</strong></td><td>{item.candidate_type.replaceAll("_", " ")}</td><td>{item.organisation_count}</td><td>{compact(item.occurrence_count)}</td></tr>)}</tbody></table></div></section>
  </>;
}

function OntologyAdoptionView() {
  const { data, error } = useLoad(() => Promise.all([
    api<Adoption>("/api/v1/ontologies/products/adoption"),
    api<Metric[]>("/api/v1/metrics?metric_id=MET-001&granularity=day"),
  ]), []);
  if (error) return <ErrorNotice message={error} />;
  if (!data) return <Loading />;
  const [adoption, trend] = data;
  return <><section className="page-heading"><div><p className="eyebrow">Version intelligence</p><h1>Ontology adoption</h1><p>Current-version uptake and lagging organisations.</p></div></section>
    <section className="observatory-kpis"><MetricCard id="MET-001" label="Current adoption" value={adoption.adoption_rate} note={`Products ${adoption.current_version}`} /><article><span>Current documents</span><strong>{compact(adoption.current_documents)}</strong></article><article><span>Legacy documents</span><strong>{compact(adoption.documents - adoption.current_documents)}</strong></article><article><span>Daily buckets</span><strong>{trend.length}</strong></article></section>
    <section className="observatory-grid"><article className="panel"><h2>Version distribution</h2><Bars values={adoption.version_distribution} /></article><article className="panel"><h2>Migration trend</h2><div className="trend-points">{trend.map((item) => <div key={item.bucket_start}><span>{item.bucket_start}</span><strong>{rate(item.value)}</strong></div>)}</div></article></section>
    <section className="panel table-panel"><div className="panel-title"><h2>Lagging organisations</h2><span>{adoption.lagging_organisations.length}</span></div><div className="table-wrap"><table><thead><tr><th>Organisation</th><th>Current</th><th>Total</th><th>Adoption</th><th /></tr></thead><tbody>{adoption.lagging_organisations.map((item) => <tr key={item.organisation_id}><td>{item.organisation_id}</td><td>{item.current_documents}</td><td>{item.documents}</td><td>{rate(item.adoption_rate)}</td><td><a className="row-link" href={`#organisations/${item.organisation_id}`}>Inspect</a></td></tr>)}</tbody></table></div></section>
  </>;
}

function ValidationIntelligence() {
  const { data, error } = useLoad(() => Promise.all([
    api<ValidationSummary>("/api/v1/validation/summary"),
    api<Constraint[]>("/api/v1/validation/constraints?limit=25"),
    api<Metric[]>("/api/v1/metrics?metric_id=MET-005&granularity=day"),
  ]), []);
  if (error) return <ErrorNotice message={error} />;
  if (!data) return <Loading />;
  const [summary, constraints, trend] = data;
  return <><section className="page-heading"><div><p className="eyebrow">SHACL telemetry</p><h1>Validation intelligence</h1><p>Recurring rule failures with organisation and document impact.</p></div></section>
    <section className="observatory-kpis"><MetricCard id="MET-005" label="Conformance" value={summary.conformance_rate} note="Validated documents" /><article><span>Validated</span><strong>{compact(summary.validated_documents)}</strong></article><article><span>Nonconforming</span><strong>{compact(summary.nonconforming_documents)}</strong></article><article><span>Violations</span><strong>{compact(summary.violations)}</strong></article><article><span>Warnings</span><strong>{compact(summary.warnings)}</strong></article><article><span>Trend buckets</span><strong>{trend.length}</strong></article></section>
    <section className="panel table-panel"><div className="panel-title"><h2>Top failing constraints</h2><span>{constraints.length} shown</span></div><div className="table-wrap"><table><thead><tr><th>Rule</th><th>Profile</th><th>Severity</th><th>Documents</th><th>Organisations</th><th>Provenance</th></tr></thead><tbody>{constraints.map((item) => <tr key={item.id}><td><strong>{item.message}</strong><span>{item.path || item.component}</span></td><td>{item.profile}</td><td><span className="badge failed">{item.severity}</span></td><td>{item.documents}</td><td>{item.organisations}</td><td><details><summary>{item.evidence_references.length} links</summary><code>{item.evidence_references.join("\n")}</code></details></td></tr>)}</tbody></table></div></section>
  </>;
}

function TermTable({ title, items }: { title: string; items: TermUsage[] }) {
  return <article className="panel"><div className="panel-title"><h2>{title}</h2><span>{items.length}</span></div><div className="observatory-list">{items.slice(0, 8).map((item) => <div key={item.term_iri}><strong className="mono">{item.term_iri}</strong><span>{compact(item.occurrences)} uses · {item.organisations} orgs</span></div>)}</div></article>;
}

function VocabularyDrift() {
  const { data, error } = useLoad(async () => {
    const [signals, unknown, deprecated, custom, gaps, incidents] = await Promise.all([
      api<SignalSummary>("/api/v1/signals/summary"),
      api<TermUsage[]>("/api/v1/terms/unknown"),
      api<TermUsage[]>("/api/v1/terms/deprecated"),
      api<TermUsage[]>("/api/v1/terms/custom"),
      api<TermUsage[]>("/api/v1/mappings/gaps"),
      api<Incident[]>("/api/v1/incidents?status=OPEN&limit=100"),
    ]);
    return { signals, unknown, deprecated, custom, gaps, incidents };
  }, []);
  if (error) return <ErrorNotice message={error} />;
  if (!data) return <Loading />;
  return <><section className="page-heading"><div><p className="eyebrow">Vocabulary telemetry</p><h1>Vocabulary and drift</h1><p>Unknown, deprecated, custom, fragmented, and unmapped concepts.</p></div></section>
    <section className="observatory-kpis">{Object.entries(data.signals.by_category).map(([name, value]) => <article key={name}><span>{name.replaceAll("_", " ")}</span><strong>{compact(value)}</strong></article>)}</section>
    <section className="observatory-grid three"><TermTable title="Unknown terms" items={data.unknown} /><TermTable title="Deprecated terms" items={data.deprecated} /><TermTable title="Custom terms" items={data.custom} /></section>
    <section className="observatory-grid"><TermTable title="Mapping gaps" items={data.gaps} /><article className="panel"><div className="panel-title"><h2>Drift incidents</h2><span>{data.incidents.length}</span></div><div className="observatory-list">{data.incidents.map((item) => <div key={item.id}><span className={`badge ${item.severity}`}>{item.detector_type}</span><strong>{item.explanation}</strong></div>)}</div></article></section>
  </>;
}

function EvidenceView() {
  const { data, error, setData } = useLoad(() => api<Evidence[]>("/api/v1/evidence?limit=100"), []);
  const [saving, setSaving] = useState("");
  const [updateError, setUpdateError] = useState("");

  async function update(event: FormEvent<HTMLFormElement>, candidate: Evidence) {
    event.preventDefault();
    setSaving(candidate.id);
    setUpdateError("");
    const values = new FormData(event.currentTarget);
    try {
      const updated = await api<Evidence>(`/api/v1/evidence/${candidate.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status: values.get("status"), annotation: values.get("annotation") }),
      });
      setData((data ?? []).map((item) => item.id === updated.id ? updated : item));
    } catch (reason) {
      setUpdateError((reason as Error).message);
    } finally {
      setSaving("");
    }
  }

  if (error) return <ErrorNotice message={error} />;
  if (!data) return <Loading />;
  return <><section className="page-heading"><div><p className="eyebrow">Human review queue</p><h1>Evidence candidates</h1><p>Recurring observations are evidence for review, never automatic standard changes.</p></div><a className="primary link-button" href={`${apiBaseUrl}/api/v1/evidence`}>Export JSON</a></section>{updateError && <ErrorNotice message={updateError} />}
    <section className="evidence-list">{data.map((item) => <article className="panel" key={item.id}><div className="panel-title"><div><span className="badge">{item.candidate_type.replaceAll("_", " ")}</span><h2>{item.label}</h2></div><span>{item.status.replaceAll("_", " ")}</span></div><div className="evidence-stats"><span><strong>{compact(item.occurrence_count)}</strong> occurrences</span><span><strong>{item.organisation_count}</strong> organisations</span><span><strong>{item.domain_count}</strong> domains</span><span><strong>{item.persistence_days}</strong> days</span><span><strong>{item.trend}</strong> trend</span></div><details><summary>Inspect provenance and review</summary><div className="evidence-detail"><p><strong>Affected concepts</strong><br />{item.affected_concepts.join(", ")}</p><p>{item.recommendation}</p><p className="mono">First {item.first_seen}<br />Last {item.last_seen}<br />Mapping: {item.mapping_status}<br />Conformance impact: {item.conformance_impact}<br />Incident: {item.source_incident_id || "SHACL aggregation"}</p><details><summary>{item.evidence_references.length} linked observations</summary><code>{item.evidence_references.join("\n")}</code></details><form className="evidence-review" onSubmit={(event) => void update(event, item)}><label>Status<select name="status" defaultValue={item.status}><option>NEW</option><option>MARKED_FOR_REVIEW</option><option>DISMISSED</option></select></label><label>Reviewer annotation<textarea name="annotation" defaultValue={item.annotation || ""} maxLength={2000} /></label><button className="primary" disabled={saving === item.id}>{saving === item.id ? "Saving..." : "Save review"}</button></form></div></details></article>)}</section>
  </>;
}

function OrganisationView({ id }: { id: string }) {
  const { data, error } = useLoad(() => api<Organisation>(`/api/v1/ecosystem/organisations/${encodeURIComponent(id)}`), [id]);
  if (error) return <ErrorNotice message={error} />;
  if (!data) return <Loading />;
  return <><a className="back-link" href="#ontology-adoption">← Ontology adoption</a><section className="page-heading"><div><p className="eyebrow">Organisation comparison</p><h1>{data.organisation_id}</h1><p>Profile, version, conformance, and deviation metrics.</p></div></section><section className="observatory-kpis"><article><span>Documents</span><strong>{compact(data.documents)}</strong></article><MetricCard id="MET-005" label="Conformance" value={data.conformance_rate} note="Organisation" />{Object.entries(data.metric_values).slice(0, 5).map(([id, value]) => <MetricCard key={id} id={id} label={id} value={value} note="Canonical metric" />)}</section><section className="observatory-grid three"><article className="panel"><h2>Domains</h2><Bars values={data.domains} /></article><article className="panel"><h2>Profiles</h2><Bars values={data.profiles} /></article><article className="panel"><h2>Ontology versions</h2><Bars values={data.ontology_versions} /></article></section></>;
}

export default function SemanticObservatory({ route }: { route: string }) {
  const [section, id] = route.split("/");
  let content = <Overview />;
  if (section === "ontology-adoption") content = <OntologyAdoptionView />;
  else if (section === "validation-intelligence") content = <ValidationIntelligence />;
  else if (section === "vocabulary-drift") content = <VocabularyDrift />;
  else if (section === "evidence") content = <EvidenceView />;
  else if (section === "organisations" && id) content = <OrganisationView id={id} />;
  return <><ObservatoryNav />{content}</>;
}
