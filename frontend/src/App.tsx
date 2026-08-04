import { type FormEvent, lazy, Suspense, useEffect, useState } from "react";
import { api, apiBaseUrl } from "./api";
import Observability from "./Observability";
import Reports from "./Reports";

const GraphWorkbench = lazy(() => import("./GraphWorkbench"));

type Product = {
  id: string;
  product_identifier: string;
  product_name: string;
  model_number: string;
  manufacturer_name: string;
  manufacturing_date: string;
  repairability_score: string;
  recycled_content_percentage: string;
  carbon_kg_co2e: string;
  battery_chemistry: string;
  battery_capacity_mah: string;
  supplier_name: string;
  material_name: string;
  material_origin: string;
};

type Passport = {
  id: string;
  product_id: string;
  current_version: number;
  status: "ACTIVE" | "ARCHIVED";
  updated_at: string;
};

type PassportVersion = {
  passport_id: string;
  version: number;
  graph_uri: string;
  created_at: string;
};

type ValidationResult = { severity: string; message: string; path?: string };
type ValidationReport = {
  id: string;
  conforms: boolean;
  created_at: string;
  violations: number;
  warnings: number;
  info: number;
  results: ValidationResult[];
};

type IngestionJob = {
  id: string;
  source_system: string;
  file_name: string;
  status: string;
  total_records: number;
  imported_records: number;
  duplicate_records: number;
  quarantined_records: number;
  created_at: string;
};

type IngestionError = {
  id: number;
  record_number: number;
  product_identifier?: string;
  error_code: string;
  message: string;
};

async function apiText(path: string): Promise<string> {
  const response = await fetch(`${apiBaseUrl}${path}`);
  if (!response.ok) throw new Error(`Request failed with HTTP ${response.status}`);
  return response.text();
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("en", { dateStyle: "medium" }).format(new Date(value));
}

function average(values: string[]): string {
  if (!values.length) return "—";
  return (values.reduce((total, value) => total + Number(value), 0) / values.length).toFixed(1);
}

function ErrorNotice({ message }: { message: string }) {
  return <p className="notice error" role="alert">{message}</p>;
}

function Loading({ label = "Loading workspace" }: { label?: string }) {
  return <p className="loading" role="status"><span />{label}…</p>;
}

function Login({ onLogin }: { onLogin: (email: string) => void }) {
  const [email, setEmail] = useState("manufacturer@example.com");
  const [password, setPassword] = useState("demo");

  function submit(event: FormEvent) {
    event.preventDefault();
    if (email && password) onLogin(email);
  }

  return (
    <main className="login-shell">
      <section className="login-story">
        <a className="wordmark" href="#login">DPP / Graph</a>
        <div>
          <p className="eyebrow">Circular electronics intelligence</p>
          <h1>Proof for every part.</h1>
          <p>Trace materials, validate claims, and publish product passports from one semantic workspace.</p>
        </div>
        <p className="story-note">Built for manufacturers, repair networks, and circularity teams.</p>
      </section>
      <section className="login-panel" aria-labelledby="login-title">
        <form className="login-card" onSubmit={submit}>
          <p className="eyebrow">Workspace access</p>
          <h2 id="login-title">Welcome back</h2>
          <p className="muted">Use the local demo account to enter the product passport workspace.</p>
          <label>Email<input type="email" value={email} onChange={(event) => setEmail(event.target.value)} required /></label>
          <label>Password<input type="password" value={password} onChange={(event) => setPassword(event.target.value)} required /></label>
          <button className="primary" type="submit">Enter workspace <span aria-hidden="true">→</span></button>
          <p className="demo-note">Demo session only · production identity verification is outside this MVP.</p>
        </form>
      </section>
    </main>
  );
}

function Dashboard() {
  const [data, setData] = useState<{ products: Product[]; passports: Passport[]; reports: ValidationReport[]; jobs: IngestionJob[] }>();
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([
      api<Product[]>("/api/v1/products?limit=200"),
      api<Passport[]>("/api/v1/passports?limit=200"),
      api<ValidationReport[]>("/api/v1/validation/runs?limit=200"),
      api<IngestionJob[]>("/api/v1/ingestion/jobs?limit=50"),
    ]).then(([products, passports, reports, jobs]) => setData({ products, passports, reports, jobs })).catch((reason: Error) => setError(reason.message));
  }, []);

  if (error) return <ErrorNotice message={error} />;
  if (!data) return <Loading />;
  const passed = data.reports.filter((report) => report.conforms).length;
  const quarantined = data.jobs.reduce((total, job) => total + job.quarantined_records, 0);
  const metrics = [
    ["Total passports", String(data.passports.length), "Published semantic records"],
    ["Active products", String(data.products.length), "Managed product models"],
    ["Validation pass rate", data.reports.length ? `${Math.round((passed / data.reports.length) * 100)}%` : "—", `${data.reports.length} recorded runs`],
    ["Avg. repairability", average(data.products.map((item) => item.repairability_score)), "Out of 10"],
    ["Avg. recycled content", `${average(data.products.map((item) => item.recycled_content_percentage))}%`, "Across tracked materials"],
    ["Avg. carbon footprint", `${average(data.products.map((item) => item.carbon_kg_co2e))} kg`, "CO₂e per product"],
  ];

  return (
    <>
      <section className="page-heading"><div><p className="eyebrow">Portfolio pulse</p><h1>Overview</h1><p>Live product, graph, and data-quality signals.</p></div><a className="primary link-button" href="#ingestion">Import product data</a></section>
      <section className="metric-grid" aria-label="Portfolio metrics">
        {metrics.map(([label, value, note]) => <article className="metric" key={label}><p>{label}</p><strong>{value}</strong><span>{note}</span></article>)}
      </section>
      <section className="dashboard-grid">
        <article className="panel"><div className="panel-title"><div><p className="eyebrow">Recent activity</p><h2>Ingestion jobs</h2></div><a href="#ingestion">View all</a></div>
          {data.jobs.length ? <div className="activity-list">{data.jobs.slice(0, 5).map((job) => <div key={job.id}><span className={`dot ${job.status.toLowerCase()}`} /><div><strong>{job.file_name}</strong><p>{job.imported_records} imported · {job.quarantined_records} isolated</p></div><span>{formatDate(job.created_at)}</span></div>)}</div> : <p className="empty">No imports yet.</p>}
        </article>
        <article className="panel quality-panel"><p className="eyebrow">Quality watch</p><h2>{quarantined ? `${quarantined} records need attention` : "No quarantined records"}</h2><p>{quarantined ? "Open ingestion to review field-level issues." : "Recent data imports contain no isolated records."}</p><a href="#validation">Open validation center <span aria-hidden="true">→</span></a></article>
      </section>
    </>
  );
}

function PassportList() {
  const [items, setItems] = useState<{ passports: Passport[]; products: Map<string, Product> }>();
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([api<Passport[]>("/api/v1/passports?limit=200"), api<Product[]>("/api/v1/products?limit=200")])
      .then(([passports, products]) => setItems({ passports, products: new Map(products.map((item) => [item.id, item])) }))
      .catch((reason: Error) => setError(reason.message));
  }, []);

  return <><section className="page-heading"><div><p className="eyebrow">Registry</p><h1>Product passports</h1><p>Browse published passport graphs and their current versions.</p></div></section>{error ? <ErrorNotice message={error} /> : !items ? <Loading label="Loading passports" /> : <section className="panel table-panel">{items.passports.length ? <div className="table-wrap"><table><thead><tr><th>Product</th><th>Manufacturer</th><th>Version</th><th>Status</th><th>Updated</th><th /></tr></thead><tbody>{items.passports.map((passport) => { const product = items.products.get(passport.product_id); return <tr key={passport.id}><td><strong>{product?.product_name ?? "Unknown product"}</strong><span>{product?.product_identifier}</span></td><td>{product?.manufacturer_name ?? "—"}</td><td>v{passport.current_version}.0</td><td><span className={`badge ${passport.status.toLowerCase()}`}>{passport.status}</span></td><td>{formatDate(passport.updated_at)}</td><td><a className="row-link" href={`#passports/${passport.id}`}>Open <span aria-hidden="true">→</span></a></td></tr>; })}</tbody></table></div> : <p className="empty">No passports yet. Create a product and passport through the API.</p>}</section>}</>;
}

function PassportDetail({ id }: { id: string }) {
  const [data, setData] = useState<{ passport: Passport; product: Product; versions: PassportVersion[] }>();
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  async function load() {
    try {
      const passport = await api<Passport>(`/api/v1/passports/${id}`);
      const [product, versions] = await Promise.all([api<Product>(`/api/v1/products/${passport.product_id}`), api<PassportVersion[]>(`/api/v1/passports/${id}/versions`)]);
      setData({ passport, product, versions });
    } catch (reason) { setError((reason as Error).message); }
  }

  useEffect(() => { void load(); }, [id]);

  async function createVersion() {
    setBusy(true); setError(""); setMessage("");
    try { const passport = await api<Passport>(`/api/v1/passports/${id}`, { method: "PUT" }); setMessage(`Version ${passport.current_version}.0 created.`); await load(); }
    catch (reason) { setError((reason as Error).message); }
    finally { setBusy(false); }
  }

  async function validate() {
    setBusy(true); setError(""); setMessage("");
    try { const report = await api<ValidationReport>(`/api/v1/passports/${id}/validate`, { method: "POST" }); setMessage(report.conforms ? "Passport graph conforms to SHACL." : `${report.violations} validation violations found.`); }
    catch (reason) { setError((reason as Error).message); }
    finally { setBusy(false); }
  }

  if (error && !data) return <ErrorNotice message={error} />;
  if (!data) return <Loading label="Loading passport" />;
  const { passport, product, versions } = data;
  return <><a className="back-link" href="#passports">← All passports</a><section className="detail-hero"><div><p className="eyebrow">Digital product passport</p><h1>{product.product_name}</h1><p>{product.manufacturer_name} · {product.model_number}</p><div className="actions"><button className="primary" onClick={createVersion} disabled={busy}>Create new version</button><button className="secondary" onClick={validate} disabled={busy}>Validate graph</button></div>{message && <p className="notice success" role="status">{message}</p>}{error && <ErrorNotice message={error} />}</div><img className="qr" src={`${apiBaseUrl}/api/v1/passports/${id}/qr`} alt={`QR code for ${product.product_name}`} /></section>
    <section className="detail-grid"><article className="panel"><p className="eyebrow">Product record</p><h2>Core identity</h2><dl className="data-list"><div><dt>Identifier</dt><dd>{product.product_identifier}</dd></div><div><dt>Manufactured</dt><dd>{product.manufacturing_date}</dd></div><div><dt>Repairability</dt><dd>{product.repairability_score} / 10</dd></div><div><dt>Carbon footprint</dt><dd>{product.carbon_kg_co2e} kg CO₂e</dd></div><div><dt>Battery</dt><dd>{product.battery_chemistry}, {product.battery_capacity_mah} mAh</dd></div><div><dt>Material origin</dt><dd>{product.material_name} · {product.material_origin}</dd></div></dl></article>
      <article className="panel"><div className="panel-title"><div><p className="eyebrow">Immutable history</p><h2>Versions</h2></div><span className="badge active">{passport.status}</span></div><div className="version-list">{versions.map((version) => <div key={version.version}><strong>v{version.version}.0</strong><span>{formatDate(version.created_at)}</span><div><a href={`${apiBaseUrl}/api/v1/passports/${id}/export?format=json-ld&version=${version.version}`}>JSON-LD</a><a href={`${apiBaseUrl}/api/v1/passports/${id}/export?format=turtle&version=${version.version}`}>Turtle</a></div></div>)}</div><a className="public-link" href={`${apiBaseUrl}/passports/${id}`}>Open public passport <span aria-hidden="true">↗</span></a></article></section></>;
}

function ValidationPage() {
  const [data, setData] = useState("");
  const [format, setFormat] = useState<"turtle" | "json-ld">("turtle");
  const [reports, setReports] = useState<ValidationReport[]>();
  const [result, setResult] = useState<ValidationReport>();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => { api<ValidationReport[]>("/api/v1/validation/runs?limit=10").then(setReports).catch((reason: Error) => setError(reason.message)); }, []);

  async function loadPassport() {
    setBusy(true); setError("");
    try { const passports = await api<Passport[]>("/api/v1/passports?limit=1"); if (!passports.length) throw new Error("No passport graph is available yet."); setData(await apiText(`/api/v1/passports/${passports[0].id}/export?format=turtle`)); setFormat("turtle"); }
    catch (reason) { setError((reason as Error).message); }
    finally { setBusy(false); }
  }

  async function submit(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError(""); setResult(undefined);
    try { const report = await api<ValidationReport>("/api/v1/validation/runs", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ data, format }) }); setResult(report); setReports((current) => [report, ...(current ?? [])]); }
    catch (reason) { setError((reason as Error).message); }
    finally { setBusy(false); }
  }

  return <><section className="page-heading"><div><p className="eyebrow">Semantic quality</p><h1>Validation center</h1><p>Run SHACL checks against Turtle or JSON-LD before publication.</p></div><button className="secondary" onClick={loadPassport} disabled={busy}>Load current passport</button></section>{error && <ErrorNotice message={error} />}<section className="validation-grid"><form className="panel validator" onSubmit={submit}><div className="panel-title"><h2>RDF input</h2><select aria-label="RDF format" value={format} onChange={(event) => setFormat(event.target.value as "turtle" | "json-ld")}><option value="turtle">Turtle</option><option value="json-ld">JSON-LD</option></select></div><textarea aria-label="RDF data" value={data} onChange={(event) => setData(event.target.value)} placeholder="Paste RDF here or load the current passport graph…" required /><button className="primary" disabled={busy}>{busy ? "Checking…" : "Run validation"}</button></form><article className="panel result-panel"><p className="eyebrow">Latest result</p>{result ? <><h2 className={result.conforms ? "good" : "bad"}>{result.conforms ? "Graph conforms" : "Action required"}</h2><div className="result-counts"><span><strong>{result.violations}</strong> Violations</span><span><strong>{result.warnings}</strong> Warnings</span><span><strong>{result.info}</strong> Info</span></div>{result.results.length > 0 && <ul>{result.results.map((item, index) => <li key={`${item.path}-${index}`}><strong>{item.severity}</strong>{item.message}</li>)}</ul>}</> : <div className="empty-state"><span aria-hidden="true">◇</span><h2>Ready to inspect</h2><p>Validation results and field-level messages appear here.</p></div>}</article></section><section className="panel table-panel"><div className="panel-title"><h2>Recent validation runs</h2><span>{reports?.length ?? 0} shown</span></div>{!reports ? <Loading label="Loading validation history" /> : reports.length ? <div className="table-wrap"><table><thead><tr><th>Run</th><th>Result</th><th>Violations</th><th>Warnings</th><th>Date</th></tr></thead><tbody>{reports.map((report) => <tr key={report.id}><td className="mono">{report.id.slice(0, 8)}</td><td><span className={`badge ${report.conforms ? "active" : "failed"}`}>{report.conforms ? "Conforms" : "Invalid"}</span></td><td>{report.violations}</td><td>{report.warnings}</td><td>{formatDate(report.created_at)}</td></tr>)}</tbody></table></div> : <p className="empty">No validation runs yet.</p>}</section></>;
}

function IngestionPage() {
  const [jobs, setJobs] = useState<IngestionJob[]>();
  const [file, setFile] = useState<File>();
  const [source, setSource] = useState("manufacturer-portal");
  const [errors, setErrors] = useState<IngestionError[]>();
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function refresh() { setJobs(await api<IngestionJob[]>("/api/v1/ingestion/jobs?limit=50")); }
  useEffect(() => { refresh().catch((reason: Error) => setError(reason.message)); }, []);

  async function submit(event: FormEvent) {
    event.preventDefault(); if (!file) return;
    setBusy(true); setError(""); setMessage(""); setErrors(undefined);
    const body = new FormData(); body.append("source_system", source); body.append("file", file);
    try { const job = await api<IngestionJob>("/api/v1/ingestion/files", { method: "POST", body }); setMessage(`${job.imported_records} records imported; ${job.quarantined_records} isolated.`); await refresh(); if (job.quarantined_records) setErrors(await api<IngestionError[]>(`/api/v1/ingestion/jobs/${job.id}/errors`)); }
    catch (reason) { setError((reason as Error).message); }
    finally { setBusy(false); }
  }

  async function showErrors(job: IngestionJob) {
    try { setErrors(await api<IngestionError[]>(`/api/v1/ingestion/jobs/${job.id}/errors`)); }
    catch (reason) { setError((reason as Error).message); }
  }

  return <><section className="page-heading"><div><p className="eyebrow">Data operations</p><h1>Ingestion</h1><p>Map CSV or JSON product records into validated passport graphs.</p></div></section><section className="ingestion-grid"><form className="panel upload-card" onSubmit={submit}><p className="eyebrow">New import</p><h2>Upload source data</h2><label>Source system<input value={source} pattern="[A-Za-z0-9._-]+" onChange={(event) => setSource(event.target.value)} required /></label><label className="file-drop"><span>{file ? file.name : "Choose a CSV or JSON file"}</span><small>UTF-8 · maximum 2 MB</small><input type="file" accept=".csv,.json,text/csv,application/json" onChange={(event) => setFile(event.target.files?.[0])} required /></label><button className="primary" disabled={busy}>{busy ? "Processing…" : "Start ingestion"}</button>{message && <p className="notice success" role="status">{message}</p>}{error && <ErrorNotice message={error} />}</form><article className="panel process-card"><p className="eyebrow">Pipeline</p><h2>From source to graph</h2>{["Validate source fields", "Map ontology terms", "Generate stable URIs", "Run SHACL checks", "Persist named graph"].map((step, index) => <div className="process-step" key={step}><span>{index + 1}</span><p>{step}</p></div>)}</article></section><section className="panel table-panel"><div className="panel-title"><h2>Import history</h2><button className="text-button" onClick={() => refresh().catch((reason: Error) => setError(reason.message))}>Refresh</button></div>{!jobs ? <Loading label="Loading import history" /> : jobs.length ? <div className="table-wrap"><table><thead><tr><th>File</th><th>Status</th><th>Imported</th><th>Duplicates</th><th>Isolated</th><th>Date</th></tr></thead><tbody>{jobs.map((job) => <tr key={job.id}><td><strong>{job.file_name}</strong><span>{job.source_system}</span></td><td><span className={`badge ${job.status.toLowerCase()}`}>{job.status.replaceAll("_", " ")}</span></td><td>{job.imported_records}</td><td>{job.duplicate_records}</td><td>{job.quarantined_records ? <button className="error-link" onClick={() => showErrors(job)}>{job.quarantined_records} view</button> : "0"}</td><td>{formatDate(job.created_at)}</td></tr>)}</tbody></table></div> : <p className="empty">No ingestion jobs yet.</p>}</section>{errors && <section className="panel error-panel"><div className="panel-title"><h2>Quarantined records</h2><button className="text-button" onClick={() => setErrors(undefined)}>Close</button></div>{errors.length ? errors.map((item) => <article key={item.id}><span>Row {item.record_number}</span><div><strong>{item.product_identifier || "Unknown product"} · {item.error_code}</strong><p>{item.message}</p></div></article>) : <p className="empty">This job has no quarantined records.</p>}</section>}</>;
}

const nav = [["dashboard", "Overview"], ["passports", "Passports"], ["validation", "Validation"], ["ingestion", "Ingestion"], ["graph", "Graph & SPARQL"], ["observability", "Observability"], ["reports", "Reports & governance"]];

export default function App() {
  const [user, setUser] = useState(() => sessionStorage.getItem("dpp-demo-user") || "");
  const [route, setRoute] = useState(() => window.location.hash.slice(1) || "dashboard");

  useEffect(() => { const update = () => setRoute(window.location.hash.slice(1) || "dashboard"); window.addEventListener("hashchange", update); return () => window.removeEventListener("hashchange", update); }, []);

  if (!user) return <Login onLogin={(email) => { sessionStorage.setItem("dpp-demo-user", email); setUser(email); window.location.hash = "dashboard"; }} />;
  const section = route.split("/")[0];
  let content = <Dashboard />;
  if (route === "passports") content = <PassportList />;
  else if (route.startsWith("passports/")) content = <PassportDetail id={route.split("/")[1]} />;
  else if (route === "validation") content = <ValidationPage />;
  else if (route === "ingestion") content = <IngestionPage />;
  else if (route === "graph") content = <GraphWorkbench />;
  else if (route === "observability") content = <Observability />;
  else if (route === "reports") content = <Reports />;

  return <div className="app-shell"><aside><a className="wordmark" href="#dashboard">DPP / Graph</a><nav aria-label="Workspace navigation">{nav.map(([path, label], index) => <a key={path} className={section === path ? "active" : ""} href={`#${path}`}><span aria-hidden="true">0{index + 1}</span>{label}</a>)}</nav><div className="user-card"><span>{user.slice(0, 2).toUpperCase()}</span><div><strong>{user.split("@")[0]}</strong><small>Manufacturer</small></div><button aria-label="Sign out" onClick={() => { sessionStorage.removeItem("dpp-demo-user"); setUser(""); }}>↗</button></div></aside><main className="workspace"><header><div><span className="live-dot" />Graph services live</div><a href={`${apiBaseUrl}/docs`}>API docs ↗</a></header><div className="page-content"><Suspense fallback={<Loading />}>{content}</Suspense></div></main></div>;
}
