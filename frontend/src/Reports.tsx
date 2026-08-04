import { useEffect, useState } from "react";
import { api, apiBaseUrl } from "./api";

type ReportType = "compliance" | "sustainability" | "supplier-quality" | "certificate";
type Report = {
  id: string;
  report_type: ReportType;
  status: string;
  row_count: number;
  summary: Record<string, string | number>;
  sources: string[];
  generated_at: string;
};
type AuditLog = {
  id: string;
  actor: string;
  action: string;
  entity_type: string;
  entity_id: string;
  result: string;
  details: Record<string, string | number>;
  created_at: string;
};

const reportTypes: { type: ReportType; title: string; description: string }[] = [
  { type: "compliance", title: "Compliance", description: "Passport coverage, SHACL conformance, warnings, and violations." },
  { type: "sustainability", title: "Sustainability", description: "Carbon, repairability, and recycled-content performance by product." },
  { type: "supplier-quality", title: "Supplier quality", description: "Supplier coverage and completeness across sourced product records." },
  { type: "certificate", title: "Certificates", description: "Certificate inventory, expired records, and the next 30-day expiry window." },
];

function label(value: string): string {
  return value.replaceAll("_", " ").replaceAll("-", " ").replace(/^./, (letter) => letter.toUpperCase());
}

export default function Reports() {
  const [reports, setReports] = useState<Report[]>([]);
  const [audits, setAudits] = useState<AuditLog[]>([]);
  const [selected, setSelected] = useState<Report>();
  const [busy, setBusy] = useState<ReportType>();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function refresh() {
    const [reportList, auditList] = await Promise.all([
      api<Report[]>("/api/v1/reports?limit=50"),
      api<AuditLog[]>("/api/v1/audit-logs?limit=100"),
    ]);
    setReports(reportList); setAudits(auditList);
    setSelected((current) => current ?? reportList[0]);
  }

  useEffect(() => {
    refresh().catch((reason: Error) => setError(reason.message)).finally(() => setLoading(false));
  }, []);

  async function generate(reportType: ReportType) {
    setBusy(reportType); setError("");
    try {
      const report = await api<Report>("/api/v1/reports", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ report_type: reportType }),
      });
      setSelected(report); await refresh(); setSelected(report);
    } catch (reason) { setError((reason as Error).message); }
    finally { setBusy(undefined); }
  }

  return <>
    <section className="page-heading"><div><p className="eyebrow">Evidence &amp; accountability</p><h1>Reports &amp; governance</h1><p>Generate cited exports and inspect the immutable history of governance actions.</p></div></section>
    {error && <p className="notice error" role="alert">{error}</p>}
    <section className="report-type-grid" aria-label="Available reports">
      {reportTypes.map((item, index) => <article className="panel report-type" key={item.type}><span>0{index + 1}</span><h2>{item.title}</h2><p>{item.description}</p><button className="primary" disabled={Boolean(busy)} onClick={() => void generate(item.type)}>{busy === item.type ? "Generating…" : "Generate CSV"}</button></article>)}
    </section>
    {selected && <section className="panel report-summary">
      <div><p className="eyebrow">Latest generated report</p><h2>{label(selected.report_type)}</h2><p>{selected.row_count} source rows · generated {new Date(selected.generated_at).toLocaleString()}</p><a className="primary link-button" href={`${apiBaseUrl}/api/v1/reports/${selected.id}/download`}>Download cited CSV</a></div>
      <dl>{Object.entries(selected.summary).map(([key, value]) => <div key={key}><dt>{label(key)}</dt><dd>{value}</dd></div>)}</dl>
      <details><summary>{selected.sources.length} source reference{selected.sources.length === 1 ? "" : "s"}</summary><ul>{selected.sources.slice(0, 10).map((source) => <li key={source}><a href={source}>{source}</a></li>)}</ul>{selected.sources.length > 10 && <p>Plus {selected.sources.length - 10} additional references in the export.</p>}</details>
    </section>}
    <section className="governance-grid">
      <article className="panel table-panel report-history"><div className="panel-title"><div><p className="eyebrow">Exports</p><h2>Report history</h2></div><span>{reports.length} shown</span></div>{loading ? <p className="loading" role="status">Loading reports…</p> : reports.length ? <div className="table-wrap"><table><thead><tr><th>Report</th><th>Rows</th><th>Status</th><th>Generated</th><th /></tr></thead><tbody>{reports.map((report) => <tr key={report.id}><td><strong>{label(report.report_type)}</strong><span className="mono">{report.id.slice(0, 8)}</span></td><td>{report.row_count}</td><td><span className="badge active">{report.status}</span></td><td>{new Date(report.generated_at).toLocaleString()}</td><td><button className="text-button" onClick={() => setSelected(report)}>View</button></td></tr>)}</tbody></table></div> : <p className="empty">Generate the first governance report above.</p>}</article>
      <article className="panel audit-panel"><div className="panel-title"><div><p className="eyebrow">Accountability</p><h2>Audit log</h2></div><span>{audits.length} events</span></div>{audits.length ? <div className="audit-list">{audits.map((audit) => <div key={audit.id}><span className="audit-mark" aria-hidden="true" /><div><strong>{label(audit.action)}</strong><p>{label(String(audit.details.report_type ?? audit.entity_type))} · {audit.details.row_count ?? 0} rows</p><small>{audit.actor} · {new Date(audit.created_at).toLocaleString()}</small></div><span className="badge active">{audit.result}</span></div>)}</div> : <p className="empty">Generated reports will appear here as audit events.</p>}</article>
    </section>
  </>;
}
