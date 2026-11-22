# ⚡ ReVolt – From Retired EV Batteries to Smarter Solar Energy Storage

**Team GridMinds** · SIT Tumakuru · Hackathon Theme 6 (Virtual Power Plants / Distributed Energy Resources)

ReVolt is a hackathon prototype that helps give retired electric-vehicle (EV) batteries a **second life** as home solar storage.

1. **Assess** – an ML model estimates a retired battery's *State of Health* (SOH) and screens whether it is suitable for second-life use.
2. **Simulate** – a solar charge/discharge simulation shows how that battery would behave in a home over 24 hours.
3. **Visualise** – a dashboard shows the results with gauges and charts.

> ⚠ **Disclaimer:** ReVolt's output is a *preliminary screening indicator only, not a safety certification.* This is a prototype. It uses no real hardware, and a real second-life battery must be tested by qualified professionals.

---

## Tech stack

| Part | Technology |
|------|-----------|
| Frontend | React (Vite), Plotly.js |
| Backend | Flask (Python), SQLite |
| ML | scikit-learn, Pandas, NumPy |

## Project structure

```
ReVolt/
├── ml/          # SOH prediction model  -> predict_soh()
├── backend/     # Flask API (port 5000)
├── frontend/    # React dashboard (port 5173)
└── docs/        # Slides, demo script, notes
```

## How to run (step by step)

**One-time setup:** install [Python 3.10+](https://www.python.org/downloads/) and [Node.js LTS](https://nodejs.org/) (check with `python --version` and `node --version`).

You need **two terminals** open at the same time, both starting in the repo root folder (the folder that contains `backend/`, `frontend/`, `ml/`, `docs/`). Each terminal runs one program, and both must stay open while you use the app.

### Terminal 1 – Backend

```bash
git checkout backend-module            # make sure you are on this branch
pip install -r backend/requirements.txt   # first time only, if the file exists
python backend/app.py
```

Leave it running. The API is now at http://localhost:5000. Quick check: open http://localhost:5000/api/sample-data in your browser. You should see numbers.

### Terminal 2 – Frontend

```bash
cd frontend
npm install                # first time only, takes 1-2 minutes
cp .env.example .env       # first time only (Windows: copy .env.example .env)
npm run dev
```

Open **http://localhost:5173** in your browser. The badge at the top right should say **Live API** (green).

To stop either program, click its terminal and press `Ctrl + C`.

### Common problems

| What you see | Fix |
|--------------|-----|
| `npm: command not found` | Node.js is not installed (or restart the terminal after installing). |
| Red box: "Cannot reach the backend" | Terminal 1 is not running, or it is not on port 5000. |
| Blank page | Press `Ctrl + R`; look at the terminal running `npm run dev` for errors. |
| Changed `.env` but nothing changed | Stop `npm run dev` (`Ctrl + C`) and start it again. |

### Where is everything? (frontend/src)

| File | What it does |
|------|--------------|
| `api.js` | The only file that talks to the backend (and switches to mock data). |
| `mockData.js` | Fake data that follows the API contract, for working without the backend. |
| `App.jsx` | Page frame: title, tabs, disclaimer footer. |
| `pages/AssessmentPage.jsx` | Page 1: form / CSV upload, gauge, badge, history table. |
| `pages/SimulationPage.jsx` | Page 2: settings, Plotly charts, summary, recommendations. |
| `components/` | Reusable pieces: `Gauge.jsx` (SOH gauge), `PlotlyChart.jsx` (dark chart style). |
| `styles.css` | All colours and layout (dark blue/purple theme). |

### Mock mode (no backend needed)

Open `frontend/.env` and set:

```
VITE_USE_MOCK=true
```

Restart `npm run dev`. The header badge changes to **Mock data**. Set it back to `false` to use the real API. If the backend runs somewhere else, change `VITE_API_URL`.

## Features

- **Battery Assessment** – enter 5 inputs (or upload a CSV) and get SOH on a gauge, remaining capacity, and a green / amber / red category badge.
- **Solar Simulation** – set battery capacity and see solar vs load, battery state of charge (limits 10–90%), grid import, solar utilisation and recommendations.
- **Recent assessments** – table of past results saved by the backend.

### SOH categories (adjustable assumptions)

| SOH | Category | Colour |
|-----|----------|--------|
| ≥ 80% | Candidate for second-life testing | 🟢 |
| 60–80% | Needs further assessment | 🟠 |
| < 60% | Recycle recommended | 🔴 |

### CSV format for uploads

```
cycle_number,avg_voltage,avg_current,avg_temperature,discharge_time
120,3.65,-1.8,32.5,2800
```

## API

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/battery/assess` | Estimate SOH and category |
| POST | `/api/simulate` | 24-hour solar + battery simulation |
| GET | `/api/sample-data` | Sample 24 h solar and load profiles |
| GET | `/api/history` | Past assessments |

Full details: `backend/README.md`.

## Limitations

- Prototype only: no real battery hardware, no real-time data.
- The ML model's accuracy depends on its training data and is not validated for safety decisions.
- The simulation uses simple 1-hour steps and ignores efficiency losses and tariffs.

## Team

**GridMinds** – Person A (ML), Person B (Backend), Person C (Frontend & Pitch)
