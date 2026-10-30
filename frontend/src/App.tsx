import { useState, useEffect, useRef } from "react";

const API = window.location.port === "5173" ? "http://localhost:8000" : "";

const css = `
* { box-sizing: border-box; }
body { margin: 0; font-family: system-ui, -apple-system, sans-serif; background: #f5f7fa; color: #1a1a2e; }
.app { max-width: 1100px; margin: 0 auto; padding: 20px; }
.card { background: #fff; border-radius: 8px; padding: 16px; margin: 12px 0; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }
.row { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
.btn { padding: 6px 12px; border: none; border-radius: 6px; cursor: pointer; background: #2563eb; color: #fff; font-size: 13px; }
.btn.secondary { background: #6b7280; }
.btn.danger { background: #dc2626; }
.btn.sm { padding: 3px 8px; font-size: 11px; }
input, select, textarea { padding: 6px 8px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 13px; }
table { width: 100%; border-collapse: collapse; font-size: 13px; }
th, td { padding: 6px 8px; border-bottom: 1px solid #e5e7eb; text-align: left; }
th { background: #f3f4f6; font-weight: 600; }
.right { text-align: right; }
.tabs { display: flex; gap: 4px; margin: 12px 0; }
.tab { padding: 8px 16px; cursor: pointer; border-radius: 6px 6px 0 0; background: #e5e7eb; }
.tab.active { background: #fff; font-weight: 600; }
h1,h2,h3 { margin: 8px 0; }
.badge { display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 11px; background: #e0e7ff; color: #3730a3; }
mark { background: #fef08a; color: #1a1a2e; padding: 0 2px; border-radius: 2px; }

@media (max-width: 640px) { table { font-size: 11px; } .row { flex-direction: column; align-items: stretch; } input { width: 100%; } }
`;

export default function App() {
  const [token, setToken] = useState<string | null>(localStorage.getItem("token"));
  const [email, setEmail] = useState("demo@example.com");
  const [password, setPassword] = useState("demo123");
  const [tab, setTab] = useState("projects");
  const [projects, setProjects] = useState<any[]>([]);
  const [filterType, setFilterType] = useState("");
  const [filterStatus, setFilterStatus] = useState("");
  const [selected, setSelected] = useState<any>(null);
  const [calc, setCalc] = useState<any>(null);
  const [takeoff, setTakeoff] = useState<any>(null);
  const [necQuery, setNecQuery] = useState("");
  const [necResults, setNecResults] = useState<any>(null);
  const [necContent, setNecContent] = useState<any>(null);
  const [necOffset, setNecOffset] = useState(0);
  const [chatInput, setChatInput] = useState("");
  const [chatHistory, setChatHistory] = useState<{ role: string; text: string }[]>([]);
  const [clients, setClients] = useState<any[]>([]);
  const [newClient, setNewClient] = useState({ name: "", email: "", phone: "", address: "" });
  const [workDesc, setWorkDesc] = useState("");
  const [workDescResult, setWorkDescResult] = useState<any>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [newProj, setNewProj] = useState({ name: "", type: "single_family", area: "1500" });
  const [workEst, setWorkEst] = useState({ name: "", area: "1500", description: "" });
  const [showWorkEst, setShowWorkEst] = useState(false);
  const chatRef = useRef<HTMLDivElement>(null);

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { if (token) { loadProjects(); loadClients(); } }, [token]);
  useEffect(() => { if (chatRef.current) chatRef.current.scrollTop = chatRef.current.scrollHeight; }, [chatHistory]);

  async function api(path: string, opts: any = {}) {
    const r = await fetch(`${API}${path}`, {
      ...opts,
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}`, ...(opts.headers || {}) },
    });
    if (!r.ok) throw new Error(await r.text());
    return r.json();
  }

  async function login() {
    setError("");
    try {
      const r = await fetch(`${API}/auth/login`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email, password }) });
      if (!r.ok) throw new Error("login failed");
      const d = await r.json();
      localStorage.setItem("token", d.access_token);
      setToken(d.access_token);
    } catch (e: any) { setError(e.message); }
  }
  async function register() {
    await fetch(`${API}/auth/register`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email, password }) });
    login();
  }
  function logout() { localStorage.removeItem("token"); setToken(null); }

  async function loadProjects() {
    try {
      const qs = new URLSearchParams();
      if (filterType) qs.set("project_type", filterType);
      if (filterStatus) qs.set("status", filterStatus);
      const d = await api(`/projects?${qs}`);
      setProjects(d);
    } catch (e: any) { setError(e.message); }
  }
  async function loadClients() {
    try { setClients(await api("/clients")); }
    catch (e: any) { setError(e.message); }
  }
  async function createClient() {
    if (busy) return;
    setBusy(true);
    try {
      await api("/clients", { method: "POST", body: JSON.stringify(newClient) });
      setNewClient({ name: "", email: "", phone: "", address: "" });
      loadClients();
      alert("Client added");
    } catch (e: any) { setError(e.message); }
    finally { setBusy(false); }
  }
  async function linkClientToProject(clientId: string) {
    if (!selected) return;
    try {
      await api(`/projects/${selected.id}`, { method: "PATCH", body: JSON.stringify({ client_id: clientId || null }) });
      const updated = await api(`/projects/${selected.id}`);
      setSelected(updated);
      loadProjects();
    } catch (e: any) { setError(e.message); }
  }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { if (token) loadProjects(); }, [filterType, filterStatus]);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (!token || projects.length === 0) return;
    const id = new URLSearchParams(window.location.search).get("project");
    if (id && !selected) {
      const p = projects.find((x: any) => x.id === id);
      if (p) selectProject(p);
    }
  }, [projects, token]); // eslint-disable-line react-hooks/exhaustive-deps

  async function createProject() {
    if (busy) return;
    setBusy(true);
    try {
      await api("/projects", { method: "POST", body: JSON.stringify({
        name: newProj.name, project_type: newProj.type, floor_area_sqft: parseFloat(newProj.area),
        num_units: 1, small_appliance_circuits: 2, laundry_circuits: 1,
        appliances: [{ name: "water_heater", va: 4500, fastened: true }],
        range_count: 1, range_kw_each: 8, dryer_count: 1, dryer_kw_each: 5,
        hvac: { cooling_va: 3000, heating_va: 0 }, largest_motor_va: 3000,
      }) });
      setNewProj({ name: "", type: "single_family", area: "1500" });
      loadProjects();
    } catch (e: any) { setError(e.message); }
    finally { setBusy(false); }
  }

  async function selectProject(p: any) {
    setSelected(p); setCalc(null); setTakeoff(null); setChatHistory([]);
    const url = new URL(window.location.href);
    url.searchParams.set("project", p.id);
    window.history.replaceState({}, "", url);
    try {
      const lc = await api(`/projects/${p.id}/load-calc`);
      setCalc(lc);
    } catch {}
  }
  async function runCalc() {
    if (!selected || busy) return;
    setBusy(true);
    try { const d = await api(`/projects/${selected.id}/calculate`, { method: "POST" }); setCalc({ project_id: selected.id, calculations: Object.fromEntries(Object.entries(d.results).map(([k, v]) => [k, { results: v }])) }); }
    catch (e: any) { setError(e.message); }
    finally { setBusy(false); }
  }
  async function runTakeoff() {
    if (!selected || busy) return;
    setBusy(true);
    try { const d = await api(`/projects/${selected.id}/takeoff`, { method: "POST" }); setTakeoff(d); }
    catch (e: any) { setError(e.message); }
    finally { setBusy(false); }
  }
  async function generateFromDescription() {
    if (!selected || !workDesc.trim() || busy) return;
    setBusy(true);
    try {
      const d = await api(`/projects/${selected.id}/takeoff-items/from-description`, { method: "POST", body: JSON.stringify({ description: workDesc }) });
      setWorkDescResult(d);
      const s = await api(`/projects/${selected.id}/takeoff-items/`);
      if (takeoff) setTakeoff({ ...takeoff, line_items: s.items, total_materials: s.total_material_cost, total_labor_hours: s.total_labor_hours, total_cost: s.grand_total });
    } catch (e: any) { setError(e.message); }
    finally { setBusy(false); }
  }
  async function saveTakeoff() {
    if (!selected || !takeoff) return;
    try {
      await api(`/projects/${selected.id}/estimates/${takeoff.id}`, { method: "PUT", body: JSON.stringify({ line_items: takeoff.line_items, markup_pct: takeoff.markup_pct, contingency_pct: takeoff.contingency_pct, tax_pct: takeoff.tax_pct, scope_of_work: takeoff.scope_of_work, assumptions: takeoff.assumptions, labor_summary: takeoff.labor_summary }) });
      alert("Saved");
    } catch (e: any) { setError(e.message); }
  }
  async function exportPdf() {
    if (!selected || !takeoff) return;
    const r = await fetch(`${API}/projects/${selected.id}/export-pdf?estimate_id=${takeoff.id}`, { headers: { Authorization: `Bearer ${token}` } });
    const blob = await r.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a"); a.href = url; a.download = `${selected.name}.pdf`; a.click();
  }
  async function searchNec() {
    try { setNecResults(await api(`/nec/search?q=${encodeURIComponent(necQuery)}&limit=8`)); }
    catch (e: any) { setError(e.message); }
  }
  async function loadTable(t: string) {
    try { setNecResults(await api(`/nec/tables/${t}`)); }
    catch (e: any) { setError(e.message); }
  }
  async function loadNecContent(off: number = 0) {
    try {
      const d = await api(`/nec/content?offset=${off}&limit=8000`);
      setNecContent(d);
      setNecOffset(off);
    } catch (e: any) { setError(e.message); }
  }
  async function sendChat() {
    if (!selected || !chatInput.trim() || busy) return;
    const msg = chatInput.trim();
    setChatHistory(h => [...h, { role: "user", text: msg }]);
    setChatInput("");
    setBusy(true);
    try {
      const d = await api(`/projects/${selected.id}/chat`, { method: "POST", body: JSON.stringify({ message: msg }) });
      setChatHistory(h => [...h, { role: "assistant", text: d.reply }]);
    } catch (e: any) {
      setChatHistory(h => [...h, { role: "assistant", text: `Error: ${e.message}` }]);
    } finally { setBusy(false); }
  }

  if (!token) {
    return (
      <div className="app"><style>{css}</style>
        <div className="card" style={{ maxWidth: 400, margin: "40px auto" }}>
          <h2>Electrical Estimator</h2>
          <div className="row"><input value={email} onChange={e => setEmail(e.target.value)} placeholder="email" style={{ flex: 1 }} /></div>
          <div className="row" style={{ marginTop: 8 }}><input value={password} onChange={e => setPassword(e.target.value)} type="password" placeholder="password" style={{ flex: 1 }} /></div>
          <div className="row" style={{ marginTop: 8 }}>
            <button className="btn" onClick={login}>Login</button>
            <button className="btn secondary" onClick={register}>Register</button>
          </div>
          {error && <p style={{ color: "red" }}>{error}</p>}
          <p style={{ fontSize: 12, color: "#6b7280" }}>Try demo@example.com / demo123</p>
        </div>
      </div>
    );
  }

  const std = calc?.calculations?.standard?.results;

  return (
    <div className="app"><style>{css}</style>
      <h1>Electrical Estimator</h1>
      {error && (
        <div style={{ position: "fixed", top: 12, right: 12, background: "#dc2626", color: "#fff", padding: "10px 14px", borderRadius: 6, zIndex: 1000, maxWidth: 360, boxShadow: "0 2px 8px rgba(0,0,0,0.2)" }}>
          <span>{error}</span>
          <button onClick={() => setError("")} style={{ marginLeft: 10, background: "transparent", border: "none", color: "#fff", cursor: "pointer", fontWeight: "bold" }}>×</button>
        </div>
      )}
      {busy && <div style={{ position: "fixed", top: 12, left: 12, background: "#2563eb", color: "#fff", padding: "6px 12px", borderRadius: 6, zIndex: 1000, fontSize: 12 }}>Working…</div>}
      <div className="tabs">
        {["projects", "clients", "nec"].map(t => (
          <div key={t} className={`tab ${tab === t ? "active" : ""}`} onClick={() => setTab(t)}>{t.toUpperCase()}</div>
        ))}
      </div>

      {tab === "projects" && (
        <>
          <div className="card">
            <h3>Dashboard</h3>
            <div className="row">
              <select value={filterType} onChange={e => setFilterType(e.target.value)}>
                <option value="">All types</option>
                <option value="single_family">Single-family</option>
                <option value="multi_family">Multi-family</option>
                <option value="adu">ADU</option>
              </select>
              <select value={filterStatus} onChange={e => setFilterStatus(e.target.value)}>
                <option value="">All statuses</option>
                <option value="draft">Draft</option>
                <option value="complete">Complete</option>
              </select>
              <button className="btn secondary sm" onClick={logout}>Logout</button>
            </div>
          </div>

          <div className="card">
            <h3>Estimate from Work Description</h3>
            {!showWorkEst ? (
              <button className="btn" onClick={() => setShowWorkEst(true)}>New Estimate from Work</button>
            ) : (
              <div>
                <div className="row">
                  <input value={workEst.name} onChange={e => setWorkEst({ ...workEst, name: e.target.value })} placeholder="Project name" />
                  <input value={workEst.area} onChange={e => setWorkEst({ ...workEst, area: e.target.value })} placeholder="sqft" style={{ width: 80 }} />
                </div>
                <textarea value={workEst.description} onChange={e => setWorkEst({ ...workEst, description: e.target.value })} placeholder="Describe the work, e.g. 'Install 100A service, 20 duplex receptacles, 8 switches'" style={{ width: "100%", marginTop: 8 }} rows={3} />
                <div className="row" style={{ marginTop: 8 }}>
                  <button className="btn" disabled={busy} onClick={async () => {
                    if (busy) return;
                    setBusy(true);
                    try {
                      const proj = await api("/projects", { method: "POST", body: JSON.stringify({ name: workEst.name || "Work Estimate", project_type: "single_family", floor_area_sqft: parseFloat(workEst.area) || 1500, num_units: 1, small_appliance_circuits: 2, laundry_circuits: 1, appliances: [{ name: "water_heater", va: 4500, fastened: true }], range_count: 1, range_kw_each: 8, dryer_count: 1, dryer_kw_each: 5, hvac: { cooling_va: 3000, heating_va: 0 }, largest_motor_va: 3000 }) });
                      await api(`/projects/${proj.id}/takeoff-items/from-description`, { method: "POST", body: JSON.stringify({ description: workEst.description }) });
                      setShowWorkEst(false);
                      setWorkEst({ name: "", area: "1500", description: "" });
                      await loadProjects();
                      selectProject(proj);
                      alert("Estimate created from work description");
                    } catch (e: any) { setError(e.message); }
                    finally { setBusy(false); }
                  }}>Create Estimate</button>
                  <button className="btn secondary" onClick={() => setShowWorkEst(false)}>Cancel</button>
                </div>
              </div>
            )}
          </div>

          <div className="card">
            <h3>New Project</h3>
            <div className="row">
              <input value={newProj.name} onChange={e => setNewProj({ ...newProj, name: e.target.value })} placeholder="Project name" />
              <select value={newProj.type} onChange={e => setNewProj({ ...newProj, type: e.target.value })}>
                <option value="single_family">Single-family</option>
                <option value="multi_family">Multi-family</option>
                <option value="adu">ADU</option>
              </select>
              <input value={newProj.area} onChange={e => setNewProj({ ...newProj, area: e.target.value })} placeholder="sqft" style={{ width: 80 }} />
              <button className="btn" onClick={createProject} disabled={busy}>Create</button>
            </div>
          </div>

          <div className="card">
            <h3>Projects ({projects.length})</h3>
            <table>
              <thead><tr><th>Name</th><th>Type</th><th>Area</th><th>Actions</th></tr></thead>
              <tbody>
                {projects.map(p => (
                  <tr key={p.id}>
                    <td>{p.name}</td>
                    <td><span className="badge">{p.project_type}</span></td>
                    <td>{p.floor_area_sqft} sqft</td>
                    <td>
                      <button className="btn sm" onClick={() => selectProject(p)}>Open</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {selected && (
            <div className="card">
              <h3>{selected.name} <span className="badge">{selected.project_type}</span></h3>
              <div className="row" style={{ marginBottom: 8 }}>
                <button className="btn" onClick={runCalc} disabled={busy}>Run Calculation</button>
                <button className="btn secondary" onClick={runTakeoff} disabled={busy}>Generate Takeoff (Legacy)</button>
                <button className="btn" onClick={async () => {
                  if (!selected) return;
                  try {
                    const d = await api(`/projects/${selected.id}/takeoff-items/generate?floor_area_sqft=${selected.floor_area_sqft || 1500}`, { method: "POST" });
                    await api(`/projects/${selected.id}/takeoff-items/`);
                    alert(`Generated ${d.length} takeoff items`);
                  } catch (e: any) { setError(e.message); }
                }}>Generate Takeoff Items</button>
                <button className="btn" disabled={busy} onClick={async () => {
                  if (!selected || busy) return;
                  setBusy(true);
                  try {
                    const r = await fetch(`${API}/projects/${selected.id}/estimate-from-takeoff`, { method: "POST", headers: { Authorization: `Bearer ${token}` } });
                    if (!r.ok) throw new Error(await r.text());
                    const blob = await r.blob();
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement("a"); a.href = url; a.download = `${selected.name}_estimate.pdf`; a.click();
                  } catch (e: any) { setError(e.message); }
                  finally { setBusy(false); }
                }}>Generate Client Estimate (PDF)</button>
                <button className="btn secondary" disabled={busy} onClick={async () => {
                  if (!selected || busy) return;
                  const to = prompt("Send estimate to email:", selected.client_id ? (clients.find(c => c.id === selected.client_id)?.email || "") : "");
                  if (!to) return;
                  setBusy(true);
                  try {
                    await api(`/projects/${selected.id}/email-estimate`, { method: "POST", body: JSON.stringify({ to, subject: `Electrical Estimate - ${selected.name}`, body: "Please find your estimate attached." }) });
                    alert(`Estimate emailed to ${to}`);
                  } catch (e: any) { setError(e.message); }
                  finally { setBusy(false); }
                }}>Email Estimate to Client</button>
              </div>
              <div className="row" style={{ marginBottom: 8 }}>
                <label style={{ fontSize: 13 }}>Client:</label>
                <select value={selected.client_id || ""} onChange={e => linkClientToProject(e.target.value)}>
                  <option value="">— none —</option>
                  {clients.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
                </select>
                {selected.client_id && <span className="badge">{clients.find(c => c.id === selected.client_id)?.name}</span>}
              </div>

              <h4 style={{ marginTop: 12 }}>Estimate from Work Description</h4>
              <textarea value={workDesc} onChange={e => setWorkDesc(e.target.value)} placeholder="Describe the work, e.g. 'Install 100A service, 20 duplex receptacles, 8 switches, GFCI in kitchen, smoke detectors' (reference NEC articles like 210.8)" style={{ width: "100%" }} rows={3} />
              <div className="row" style={{ marginTop: 8 }}>
                <button className="btn" onClick={generateFromDescription} disabled={busy}>Generate Estimate</button>
              </div>
              {workDescResult && (
                <div style={{ marginTop: 8, fontSize: 13 }}>
                  <p>Created {workDescResult.count} takeoff items.</p>
                  {workDescResult.nec_references?.length > 0 && (
                    <>
                      <p style={{ fontWeight: 600 }}>NEC references:</p>
                      {workDescResult.nec_references.map((r: string, i: number) => (
                        <div key={i} style={{ padding: 6, background: "#f4f4f4", marginBottom: 4, borderRadius: 4, fontSize: 12 }}>{r}</div>
                      ))}
                    </>
                  )}
                </div>
              )}

              {std && (
                <>
                  <h4>Load Calculation (Standard Method)</h4>
                  <table>
                    <tbody>
                      {[
                        ["General lighting (3 VA/sqft)", std.general_lighting_va],
                        ["Small-appliance", std.small_appliance_va],
                        ["Laundry", std.laundry_va],
                        ["Lighting load (before demand)", std.lighting_load_va],
                        ["Lighting demand (Tbl 220.42)", std.lighting_demand_va],
                        ["Fastened appliances (connected)", std.fastened_appliances_va],
                        ["Fastened appliances (demand)", std.fastened_demand_va],
                        ["Ranges (connected)", std.range_connected_va],
                        ["Ranges (demand, Tbl 220.55)", std.range_demand_va],
                        ["Dryers (connected)", std.dryer_connected_va],
                        ["Dryers (demand, Tbl 220.54)", std.dryer_demand_va],
                        ["HVAC (noncoincident)", std.hvac_va],
                        ["Motor adder (25%)", std.motor_adder_va],
                        ["Total VA", std.total_va],
                        ["Total Amps (240V)", std.total_amps],
                        ["Neutral VA", std.neutral_va],
                        ["Recommended service", `${std.recommended_service_amps}A`],
                      ].map(([k, v]) => (
                        <tr key={String(k)}><td>{k}</td><td className="right">{typeof v === "number" ? v.toLocaleString() : v}</td></tr>
                      ))}
                    </tbody>
                  </table>
                  {calc?.calculations && (
                    <p style={{ fontSize: 12, color: "#6b7280", marginTop: 8 }}>
                      Optional methods available: {Object.keys(calc.calculations).filter(k => k !== "standard").join(", ")}
                    </p>
                  )}
                </>
              )}

              {takeoff && (
                <>
                  <h4>Material Takeoff</h4>
                  <table>
                    <thead><tr><th>Item</th><th>Qty</th><th>Unit</th><th>Unit Cost</th><th>Total</th><th>Labor Hrs</th><th></th></tr></thead>
                    <tbody>
                      {takeoff.line_items.map((li: any, i: number) => (
                        <tr key={i}>
                          <td><input value={li.name} onChange={e => { const x = [...takeoff.line_items]; x[i].name = e.target.value; setTakeoff({ ...takeoff, line_items: x }); }} style={{ width: "100%" }} /></td>
                          <td><input type="number" value={li.qty} onChange={e => { const x = [...takeoff.line_items]; x[i].qty = parseFloat(e.target.value) || 0; setTakeoff({ ...takeoff, line_items: x }); }} style={{ width: 60 }} /></td>
                          <td>{li.unit}</td>
                          <td><input type="number" step="0.01" value={li.unit_cost} onChange={e => { const x = [...takeoff.line_items]; x[i].unit_cost = parseFloat(e.target.value) || 0; setTakeoff({ ...takeoff, line_items: x }); }} style={{ width: 70 }} /></td>
                          <td className="right">{(li.qty * li.unit_cost).toFixed(2)}</td>
                          <td><input type="number" step="0.01" value={li.labor_hours} onChange={e => { const x = [...takeoff.line_items]; x[i].labor_hours = parseFloat(e.target.value) || 0; setTakeoff({ ...takeoff, line_items: x }); }} style={{ width: 60 }} /></td>
                          <td><button className="btn danger sm" onClick={() => { if (!confirm("Delete this item?")) return; const x = takeoff.line_items.filter((_: any, j: number) => j !== i); setTakeoff({ ...takeoff, line_items: x }); }}>x</button></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  <div className="row" style={{ marginTop: 8 }}>
                    <button className="btn" onClick={() => {
                      const x = [...takeoff.line_items, { name: "New Item", qty: 1, unit: "ea", unit_cost: 0, labor_hours: 0, labor_category: "rough_in" }];
                      setTakeoff({ ...takeoff, line_items: x });
                    }}>Add Row</button>
                    <button className="btn" onClick={saveTakeoff}>Save</button>
                    <button className="btn secondary" onClick={exportPdf}>Export PDF</button>
                  </div>
                  <p style={{ fontSize: 12, color: "#6b7280" }}>
                    Materials: ${takeoff.total_materials} | Labor hours: {takeoff.total_labor_hours} | Total: ${takeoff.total_cost}
                  </p>
                  <textarea value={takeoff.scope_of_work || ""} onChange={e => setTakeoff({ ...takeoff, scope_of_work: e.target.value })} placeholder="Scope of work" style={{ width: "100%", marginTop: 8 }} rows={3} />
                  <textarea value={takeoff.assumptions || ""} onChange={e => setTakeoff({ ...takeoff, assumptions: e.target.value })} placeholder="Assumptions" style={{ width: "100%", marginTop: 8 }} rows={3} />
                </>
              )}

              <h4 style={{ marginTop: 12 }}>Estimator Chat (main)</h4>
              <div ref={chatRef} style={{ border: "1px solid #e5e7eb", borderRadius: 6, padding: 8, maxHeight: 240, overflowY: "auto", background: "#fafafa" }}>
                {chatHistory.length === 0 && <p style={{ color: "#6b7280", fontSize: 13 }}>Type 'help' for commands. Try "nec grounding", "describe install 5 receptacles", "generate takeoff", "summary".</p>}
                {chatHistory.map((m, i) => (
                  <div key={i} style={{ marginBottom: 6, textAlign: m.role === "user" ? "right" : "left" }}>
                    <span style={{ display: "inline-block", padding: "4px 8px", borderRadius: 6, background: m.role === "user" ? "#2563eb" : "#e5e7eb", color: m.role === "user" ? "#fff" : "#111", fontSize: 13, whiteSpace: "pre-wrap" }}>{m.text}</span>
                  </div>
                ))}
              </div>
              <div className="row" style={{ marginTop: 8 }}>
                <input value={chatInput} onChange={e => setChatInput(e.target.value)} onKeyDown={e => e.key === "Enter" && sendChat()} placeholder="Message the estimator..." style={{ flex: 1 }} />
                <button className="btn" onClick={sendChat} disabled={busy}>Send</button>
              </div>
            </div>
          )}
        </>
      )}

      {tab === "clients" && (
        <div className="card">
          <h3>Clients ({clients.length})</h3>
          <div className="row" style={{ marginBottom: 8 }}>
            <input value={newClient.name} onChange={e => setNewClient({ ...newClient, name: e.target.value })} placeholder="Name" />
            <input value={newClient.email} onChange={e => setNewClient({ ...newClient, email: e.target.value })} placeholder="Email" />
            <input value={newClient.phone} onChange={e => setNewClient({ ...newClient, phone: e.target.value })} placeholder="Phone" />
            <input value={newClient.address} onChange={e => setNewClient({ ...newClient, address: e.target.value })} placeholder="Address" />
            <button className="btn" onClick={createClient} disabled={busy}>Add Client</button>
          </div>
          <table>
            <thead><tr><th>Name</th><th>Email</th><th>Phone</th><th>Address</th></tr></thead>
            <tbody>
              {clients.map(c => (
                <tr key={c.id}>
                  <td>{c.name}</td><td>{c.email}</td><td>{c.phone}</td><td>{c.address}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tab === "nec" && (
        <div className="card">
          <h3>NEC 2017 Reference Search</h3>
          <div className="row">
            <input value={necQuery} onChange={e => setNecQuery(e.target.value)} placeholder="Search NEC text..." style={{ flex: 1 }} onKeyDown={e => e.key === "Enter" && searchNec()} />
            <button className="btn" onClick={searchNec}>Search</button>
          </div>
          <div className="row" style={{ marginTop: 8 }}>
            <button className="btn secondary sm" onClick={() => loadTable("220.42")}>Table 220.42</button>
            <button className="btn secondary sm" onClick={() => loadTable("220.54")}>Table 220.54</button>
            <button className="btn secondary sm" onClick={() => loadTable("220.55")}>Table 220.55</button>
            <button className="btn secondary sm" onClick={() => loadTable("220.84")}>Table 220.84</button>
          </div>
          <div style={{ marginTop: 12 }}>
            <button className="btn secondary sm" onClick={() => loadNecContent(0)}>Load Full NEC 2017 Text</button>
            {necContent && (
              <div style={{ marginTop: 8 }}>
                <p style={{ fontSize: 12, color: "#6b7280" }}>Showing {necContent.offset}–{Math.min(necContent.offset + necContent.limit, necContent.total)} of {necContent.total} chars</p>
                <pre style={{ background: "#f4f4f4", padding: 12, maxHeight: 400, overflow: "auto", fontSize: 12, whiteSpace: "pre-wrap" }}>{necContent.text}</pre>
                <div className="row" style={{ marginTop: 8 }}>
                  <button className="btn secondary sm" disabled={necOffset <= 0} onClick={() => loadNecContent(Math.max(0, necOffset - 8000))}>Prev</button>
                  <button className="btn secondary sm" disabled={necOffset + 8000 >= necContent.total} onClick={() => loadNecContent(necOffset + 8000)}>Next</button>
                </div>
              </div>
            )}
          </div>

          {necResults && (
            <div style={{ marginTop: 12 }}>
              {necResults.results ? (
                necResults.results.map((r: any, i: number) => (
                  <div key={i} style={{ padding: 8, borderBottom: "1px solid #e5e7eb", fontSize: 13 }}>
                    <div dangerouslySetInnerHTML={{ __html: r.snippet || "" }} />
                  </div>
                ))
              ) : (
                <pre style={{ background: "#f4f4f4", padding: 12 }}>{JSON.stringify(necResults, null, 2)}</pre>
              )}
            </div>
          )}
        </div>
      )}

    </div>
  );
}
