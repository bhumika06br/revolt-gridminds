# ReVolt backend (Person B)

Flask API for battery assessment, solar/battery simulation and assessment history.
Prototype only: the SOH result is a **preliminary screening indicator, not a safety certification**.

## Folder structure

```
repo-root/
├── ml/                  <- Person A (predict.py, model.pkl, model_meta.json)
├── frontend/            <- React app
├── docs/
└── backend/
    ├── app.py           <- the web server + the 4 endpoints (start here)
    ├── simulation.py    <- hour-by-hour solar/battery maths + tips
    ├── database.py      <- SQLite: saves and reads assessments
    ├── sample_data.py   <- sample 24h solar (bell curve) and load
    ├── fake_model.py    <- dummy predict_soh, used only if the real one can't load
    ├── validation.py    <- checks that inputs are real numbers
    ├── test_api.py      <- automated tests
    ├── requirements.txt
    ├── examples/        <- JSON files for the curl commands below
    └── revolt.db        <- created automatically on first run (not committed)
```

## Setup and run

Always run from the **repo root** (the folder that contains `backend/` and `ml/`).

```bash
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r backend/requirements.txt
# plus Person A's packages (scikit-learn, pandas, numpy, joblib), same versions they used

python backend/app.py
```

The API is now at http://localhost:5000. Check which model is active:

```bash
curl http://localhost:5000/api/health
# {"model": "real", "status": "ok"}   <- Person A's model is loaded
# {"model": "fake", "status": "ok"}   <- fallback dummy values (a warning is printed at startup)
```

`app.py` tries `from ml.predict import predict_soh` automatically. If that fails it falls
back to `fake_model.py` and prints the reason. You do not need to change any code to swap.
To force the fake one: set `REVOLT_FAKE_MODEL=1`.

## Endpoints

| Method | URL | What it does |
|---|---|---|
| POST | `/api/battery/assess` | 5 battery readings in, SOH + category out (also saved to history) |
| POST | `/api/simulate` | 24h solar/load + battery in, hourly results + summary + tips out |
| GET | `/api/sample-data` | sample 24 solar and load numbers |
| GET | `/api/history?limit=50` | saved assessments, newest first (limit 1-500) |
| GET | `/api/health` | server alive + which model is used |

Errors are always JSON: `{"error": "message"}` with status 400 (bad input), 503 (ML model
files missing) or 500 (unexpected).

## Try it with curl

macOS/Linux/Git Bash use `curl`. On Windows PowerShell use `curl.exe` (plain `curl` is a different command).
The `@file` form avoids quoting problems on every system.

```bash
# 1. sample data
curl http://localhost:5000/api/sample-data

# 2. assess a battery
curl -X POST http://localhost:5000/api/battery/assess \
  -H "Content-Type: application/json" \
  -d @backend/examples/assess.json

# 3. simulate a day (uses the sample data inside the file)
curl -X POST http://localhost:5000/api/simulate \
  -H "Content-Type: application/json" \
  -d @backend/examples/simulate.json

# 4. history
curl "http://localhost:5000/api/history?limit=5"

# 5. see an error (missing fields -> HTTP 400)
curl -i -X POST http://localhost:5000/api/battery/assess \
  -H "Content-Type: application/json" -d '{"cycle_number": 120}'
```

**Postman:** method POST, URL as above, Body -> raw -> JSON, paste the contents of a file from `examples/`.

## Run the tests

```bash
python -m unittest discover -s backend -v
```

The tests always use the fake model and a temporary database, so they never touch your real data.

## How the simulation works

Each hour (1 hour, so kW = kWh):

- **Solar > load:** the extra charges the battery. If the battery is full, the rest is wasted.
- **Load > solar:** the battery covers the gap. If it is empty, the rest comes from the grid.
- **Usable capacity** = `battery_capacity_kwh * soh_percent / 100`.
- **SOC limits:** the battery stays between 10% and 90% **of its usable capacity**.
- `initial_soc` outside 10-90% is moved to the nearest limit.
- `soc` in the response is a **fraction 0-1** (0.5 = 50%), measured at the **end** of each hour.
- **Solar utilisation %** = (total solar - wasted solar) / total solar * 100.

Simplifications (fine for a prototype): no charging losses and no maximum charge/discharge power.

## Extra fields beyond the contract (the frontend can ignore them)

- `/api/simulate` -> `summary` also has `usable_capacity_kwh`, `solar_wasted_kwh`, `total_solar_kwh`, `total_load_kwh`.
- `/api/history` response shape: `{"count": 2, "assessments": [{"id", "inputs": {...5 fields}, "soh_percent", "remaining_capacity_ah", "rated_capacity_ah", "category", "created_at"}]}` (`created_at` is UTC).
