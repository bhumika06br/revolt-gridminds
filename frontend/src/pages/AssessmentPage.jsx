import { useEffect, useState } from "react";
import Gauge from "../components/Gauge.jsx";
import { assessBattery, getHistory } from "../api.js";

// Text + colour for each category the backend can return
const CATEGORIES = {
  candidate_for_testing: { label: "Candidate for second-life testing", color: "#34d399", cls: "green" },
  needs_assessment: { label: "Needs further assessment", color: "#fbbf24", cls: "amber" },
  recycle: { label: "Recycle recommended", color: "#f87171", cls: "red" },
};

// The form fields (same names as the API request)
const FIELDS = [
  { key: "cycle_number", label: "Cycle number", step: "1", hint: "How many charge cycles so far" },
  { key: "avg_voltage", label: "Average voltage (V)", step: "0.01", hint: "e.g. 3.65" },
  { key: "avg_current", label: "Average current (A)", step: "0.01", hint: "negative = discharging" },
  { key: "avg_temperature", label: "Average temperature (°C)", step: "0.1", hint: "e.g. 32.5" },
  { key: "discharge_time", label: "Discharge time (s)", step: "1", hint: "e.g. 2800" },
];

const DEFAULTS = {
  cycle_number: 120, avg_voltage: 3.65, avg_current: -1.8, avg_temperature: 32.5, discharge_time: 2800,
};

// Read a CSV: first line = column names, second line = values
function parseCsv(text) {
  const lines = text.split(/\r?\n/).filter((l) => l.trim() !== "");
  if (lines.length < 2) throw new Error("CSV needs a header row and one data row.");
  const headers = lines[0].split(",").map((h) => h.trim().toLowerCase());
  const values = lines[1].split(",").map((v) => v.trim());
  const out = {};
  for (const f of FIELDS) {
    const i = headers.indexOf(f.key);
    if (i === -1) throw new Error(`CSV is missing the column "${f.key}".`);
    const n = Number(values[i]);
    if (Number.isNaN(n)) throw new Error(`"${f.key}" must be a number.`);
    out[f.key] = n;
  }
  return out;
}

export default function AssessmentPage({ onResult }) {
  const [form, setForm] = useState(DEFAULTS);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [history, setHistory] = useState([]);

  const loadHistory = () =>
    getHistory()
      .then((h) => setHistory(h.assessments || []))
      .catch(() => {}); // history is a bonus, so ignore errors

  useEffect(() => { loadHistory(); }, []);

  const handleChange = (key, value) => setForm({ ...form, [key]: value });

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    // Convert text from the inputs into numbers
    const payload = {};
    for (const f of FIELDS) {
      const n = Number(form[f.key]);
      if (form[f.key] === "" || Number.isNaN(n)) {
        setError(`Please enter a valid number for "${f.label}".`);
        return;
      }
      payload[f.key] = n;
    }
    setLoading(true);
    try {
      const data = await assessBattery(payload);
      setResult(data);
      onResult(data); // share SOH with the simulation page
      loadHistory();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  function handleCsv(e) {
    const file = e.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      try {
        setForm(parseCsv(String(reader.result)));
        setError("");
      } catch (err) {
        setError(err.message);
      }
    };
    reader.readAsText(file);
    e.target.value = ""; // allow re-uploading the same file
  }

  const cat = result ? CATEGORIES[result.category] || CATEGORIES.needs_assessment : null;

  return (
    <div>
      <div className="grid-2">
        {/* ---------- Left: input form ---------- */}
        <section className="card">
          <h2>Battery inputs</h2>
          <form onSubmit={handleSubmit}>
            {FIELDS.map((f) => (
              <label key={f.key} className="field">
                <span>{f.label}</span>
                <input type="number" step={f.step} value={form[f.key]}
                       onChange={(e) => handleChange(f.key, e.target.value)} />
                <small>{f.hint}</small>
              </label>
            ))}
            <div className="row">
              <button className="btn primary" type="submit" disabled={loading}>
                {loading ? "Assessing…" : "Assess battery"}
              </button>
              <label className="btn ghost">
                Upload CSV
                <input type="file" accept=".csv" onChange={handleCsv} hidden />
              </label>
            </div>
            <small className="muted">
              CSV columns: {FIELDS.map((f) => f.key).join(", ")} (one data row)
            </small>
          </form>
          {error && <div className="error">{error}</div>}
        </section>

        {/* ---------- Right: result ---------- */}
        <section className="card result">
          <h2>Assessment result</h2>
          {!result ? (
            <p className="muted">Fill in the battery data and press “Assess battery”.</p>
          ) : (
            <>
              <Gauge value={result.soh_percent} color={cat.color} />
              <div className={"category-badge " + cat.cls}>{cat.label}</div>
              <div className="stats">
                <div className="stat">
                  <div className="stat-num">{result.remaining_capacity_ah} Ah</div>
                  <div className="stat-label">Remaining capacity</div>
                </div>
                <div className="stat">
                  <div className="stat-num">{result.rated_capacity_ah} Ah</div>
                  <div className="stat-label">Rated capacity</div>
                </div>
              </div>
              <div className="disclaimer">⚠ {result.disclaimer}</div>
            </>
          )}
        </section>
      </div>

      {/* ---------- Past assessments (from /api/history) ---------- */}
      {history.length > 0 && (
        <section className="card" style={{ marginTop: 20 }}>
          <h2>Recent assessments</h2>
          <table>
            <thead>
              <tr><th>#</th><th>Cycles</th><th>SOH</th><th>Category</th><th>Time</th></tr>
            </thead>
            <tbody>
              {history.slice(0, 8).map((row, i) => {
                // Be flexible: the backend may nest fields under "input"/"result"
                const h = { ...row, ...(row.input || {}), ...(row.result || {}) };
                const c = CATEGORIES[h.category];
                const soh = Number(h.soh_percent);
                return (
                  <tr key={row.id ?? i}>
                    <td>{row.id ?? i + 1}</td>
                    <td>{h.cycle_number ?? "—"}</td>
                    <td>{Number.isFinite(soh) ? soh.toFixed(1) + "%" : "—"}</td>
                    <td>{c ? <span className={"pill " + c.cls}>{c.label}</span> : h.category ?? "—"}</td>
                    <td>{row.created_at ?? row.timestamp ?? "—"}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </section>
      )}
    </div>
  );
}
