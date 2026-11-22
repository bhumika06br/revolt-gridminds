import { useEffect, useState } from "react";
import PlotlyChart from "../components/PlotlyChart.jsx";
import { getSampleData, runSimulation } from "../api.js";

const HOURS = Array.from({ length: 24 }, (_, i) => i);

export default function SimulationPage({ initialSoh }) {
  const [sample, setSample] = useState(null); // { solar_kw, load_kw }
  const [capacity, setCapacity] = useState(10);
  const [soh, setSoh] = useState(initialSoh);
  const [initialSoc, setInitialSoc] = useState(0.5);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Load the 24-hour sample data once, when the page opens
  useEffect(() => {
    getSampleData().then(setSample).catch((e) => setError(e.message));
  }, []);

  async function handleRun(e) {
    e.preventDefault();
    setError("");
    if (!sample) return;
    if (Number(capacity) <= 0) return setError("Battery capacity must be more than 0 kWh.");
    if (Number(soh) <= 0 || Number(soh) > 100) return setError("SOH must be between 1 and 100.");
    setLoading(true);
    try {
      const data = await runSimulation({
        battery_capacity_kwh: Number(capacity),
        soh_percent: Number(soh),
        initial_soc: Number(initialSoc),
        solar_kw: sample.solar_kw,
        load_kw: sample.load_kw,
      });
      setResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  const usable = ((Number(capacity) * Number(soh)) / 100).toFixed(2);

  return (
    <div>
      <section className="card">
        <h2>Simulation settings</h2>
        <form onSubmit={handleRun} className="sim-form">
          <label className="field">
            <span>Battery capacity (kWh)</span>
            <input type="number" min="1" step="0.5" value={capacity} onChange={(e) => setCapacity(e.target.value)} />
          </label>
          <label className="field">
            <span>Battery SOH (%)</span>
            <input type="number" min="1" max="100" step="0.1" value={soh} onChange={(e) => setSoh(e.target.value)} />
            <small>Filled in from your last assessment</small>
          </label>
          <label className="field">
            <span>Starting charge: {Math.round(initialSoc * 100)}%</span>
            <input type="range" min="0.1" max="0.9" step="0.05" value={initialSoc} onChange={(e) => setInitialSoc(e.target.value)} />
          </label>
          <div className="field">
            <span>Usable capacity</span>
            <div className="usable">{usable} kWh</div>
            <small>capacity × SOH</small>
          </div>
          <button className="btn primary" type="submit" disabled={loading || !sample}>
            {loading ? "Simulating…" : "Run simulation"}
          </button>
        </form>
        {error && <div className="error">{error}</div>}
      </section>

      {/* Chart 1: solar vs load (shown as soon as sample data loads) */}
      {sample && (
        <section className="card chart-card">
          <PlotlyChart
            title="Solar generation vs household load"
            yTitle="Power (kW)"
            data={[
              { x: HOURS, y: sample.solar_kw, name: "Solar (kW)", type: "scatter", mode: "lines", fill: "tozeroy", line: { color: "#fbbf24", width: 3 }, fillcolor: "rgba(251,191,36,0.15)" },
              { x: HOURS, y: sample.load_kw, name: "Load (kW)", type: "scatter", mode: "lines", line: { color: "#8b5cf6", width: 3 } },
            ]}
          />
        </section>
      )}

      {result && (
        <>
          <div className="stats-row">
            <div className="stat card">
              <div className="stat-num">{result.summary.solar_utilisation_percent}%</div>
              <div className="stat-label">Solar utilisation</div>
            </div>
            <div className="stat card">
              <div className="stat-num">{result.summary.grid_import_kwh} kWh</div>
              <div className="stat-label">Grid import (24 h)</div>
            </div>
            <div className="stat card">
              <div className="stat-num">{usable} kWh</div>
              <div className="stat-label">Usable battery capacity</div>
            </div>
          </div>

          <div className="grid-2">
            {/* Chart 2: battery state of charge */}
            <section className="card chart-card">
              <PlotlyChart
                title="Battery state of charge"
                yTitle="SOC (%)"
                yRange={[0, 100]}
                data={[
                  { x: result.hours, y: result.soc_percent, name: "SOC (%)", type: "scatter", mode: "lines+markers", line: { color: "#34d399", width: 3 }, marker: { size: 5 } },
                ]}
                shapes={[10, 90].map((v) => ({
                  type: "line", xref: "paper", x0: 0, x1: 1, y0: v, y1: v,
                  line: { color: "rgba(248,113,113,0.7)", width: 1, dash: "dash" },
                }))}
              />
              <small className="muted">Dashed lines = 10% and 90% safety limits used by the simulation.</small>
            </section>

            {/* Chart 3: grid import */}
            <section className="card chart-card">
              <PlotlyChart
                title="Grid import and wasted solar"
                yTitle="Power (kW)"
                barmode="group"
                data={[
                  { x: result.hours, y: result.grid_import_kw, name: "Grid import (kW)", type: "bar", marker: { color: "#f87171" } },
                  { x: result.hours, y: result.solar_wasted_kw, name: "Solar wasted (kW)", type: "bar", marker: { color: "#fbbf24" } },
                ]}
              />
            </section>
          </div>

          <section className="card">
            <h2>Recommendations</h2>
            <ul className="recs">
              {result.summary.recommendations.map((r, i) => <li key={i}>{r}</li>)}
            </ul>
          </section>
        </>
      )}
    </div>
  );
}
