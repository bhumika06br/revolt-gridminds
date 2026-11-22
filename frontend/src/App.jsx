import { useState } from "react";
import AssessmentPage from "./pages/AssessmentPage.jsx";
import SimulationPage from "./pages/SimulationPage.jsx";
import { USE_MOCK, API_URL } from "./api.js";
import { DISCLAIMER } from "./mockData.js";

export default function App() {
  const [page, setPage] = useState("assess"); // "assess" or "simulate"
  // SOH from the last assessment is passed to the simulation page
  const [lastSoh, setLastSoh] = useState(78.4);

  return (
    <div className="app">
      <header className="header">
        <div>
          <div className="brand">⚡ ReVolt</div>
          <h1>ReVolt – From Retired EV Batteries to Smarter Solar Energy Storage</h1>
        </div>
        <span className={"badge-mode " + (USE_MOCK ? "mock" : "live")} title={USE_MOCK ? "Using built-in mock data" : API_URL}>
          {USE_MOCK ? "Mock data" : "Live API"}
        </span>
      </header>

      <nav className="tabs">
        <button className={page === "assess" ? "active" : ""} onClick={() => setPage("assess")}>
          1 · Battery Assessment
        </button>
        <button className={page === "simulate" ? "active" : ""} onClick={() => setPage("simulate")}>
          2 · Solar Simulation
        </button>
      </nav>

      <main>
        {page === "assess" ? (
          <AssessmentPage onResult={(r) => setLastSoh(r.soh_percent)} />
        ) : (
          <SimulationPage initialSoh={lastSoh} />
        )}
      </main>

      <footer className="footer">
        ⚠ {DISCLAIMER} Hackathon prototype · no real hardware · Team GridMinds
      </footer>
    </div>
  );
}
