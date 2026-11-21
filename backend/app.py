"""ReVolt backend (Person B): Flask API for battery assessment + solar simulation.

Run from the repo root:   python backend/app.py
"""
import os
import sys

# Make `import ml...` (repo root) and `import database` (this folder) work
# no matter where the server is started from.
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(BACKEND_DIR)
for _folder in (REPO_ROOT, BACKEND_DIR):
    if _folder not in sys.path:
        sys.path.insert(0, _folder)

from flask import Flask, abort, jsonify, request
from werkzeug.exceptions import HTTPException

import database
import simulation
from sample_data import get_sample_data
from validation import require_number

DISCLAIMER = "Preliminary screening only, not a safety certification."
FEATURE_NAMES = ["cycle_number", "avg_voltage", "avg_current", "avg_temperature", "discharge_time"]
SIMULATE_FIELDS = ["battery_capacity_kwh", "soh_percent", "initial_soc", "solar_kw", "load_kw"]


# --------------------------------------------------------------------------
# Pick the ML model: the real one from Person A, or a fake one as a fallback.
# --------------------------------------------------------------------------
def _load_predictor():
    from fake_model import predict_soh as fake_predict

    if os.environ.get("REVOLT_FAKE_MODEL") == "1":      # force the fake one (used by tests)
        return fake_predict, "fake"
    try:
        from ml.predict import predict_soh as real_predict
        return real_predict, "real"
    except Exception as exc:  # missing folder, missing scikit-learn, bad model file...
        print("=" * 64)
        print("WARNING: could not load the real ML model, using FAKE dummy values!")
        print(f"Reason: {type(exc).__name__}: {exc}")
        print("=" * 64)
        return fake_predict, "fake"


predict_soh, MODEL_SOURCE = _load_predictor()

app = Flask(__name__)
database.init_db()


# --------------------------------------------------------------------------
# CORS: lets the React app (another port, e.g. :3000/:5173) call this API.
# --------------------------------------------------------------------------
@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response


# --------------------------------------------------------------------------
# Errors: always answer with JSON like {"error": "..."}, never an HTML page.
# --------------------------------------------------------------------------
@app.errorhandler(HTTPException)
def handle_http_error(err):
    return jsonify({"error": err.description}), err.code


@app.errorhandler(Exception)
def handle_unexpected_error(err):
    app.logger.exception("Unexpected error")
    return jsonify({"error": "Internal server error"}), 500


def _json_body():
    """Read the request body as a JSON object, or answer 400."""
    data = request.get_json(force=True, silent=True)
    if not isinstance(data, dict):
        abort(400, "Request body must be a JSON object")
    return data


# --------------------------------------------------------------------------
# Endpoints
# --------------------------------------------------------------------------
@app.get("/api/health")
def health():
    """Quick check that the server is alive, and which model it is using."""
    return jsonify({"status": "ok", "model": MODEL_SOURCE})


@app.post("/api/battery/assess")
def assess_battery():
    data = _json_body()

    features = {}
    for name in FEATURE_NAMES:
        if name not in data:
            abort(400, f"Missing field: '{name}'")
        try:
            require_number(data[name], name)
        except ValueError as exc:
            abort(400, str(exc))
        features[name] = data[name]

    try:
        result = predict_soh(features)
    except ValueError as exc:                      # bad input rejected by the ML module
        abort(400, str(exc))
    except FileNotFoundError:
        app.logger.exception("ML model files not found")
        abort(503, "ML model files not found (ml/model.pkl, ml/model_meta.json). "
                   "Start the server from the repo root.")

    result = dict(result)
    result.setdefault("disclaimer", DISCLAIMER)

    # History is a bonus: if saving fails, still return the assessment.
    try:
        database.save_assessment(features, result)
    except Exception:
        app.logger.exception("Could not save assessment to history")

    return jsonify(result)


@app.post("/api/simulate")
def simulate():
    data = _json_body()
    for name in SIMULATE_FIELDS:
        if name not in data:
            abort(400, f"Missing field: '{name}'")

    try:
        result = simulation.run_simulation(
            battery_capacity_kwh=data["battery_capacity_kwh"],
            soh_percent=data["soh_percent"],
            initial_soc=data["initial_soc"],
            solar_kw=data["solar_kw"],
            load_kw=data["load_kw"],
        )
    except ValueError as exc:
        abort(400, str(exc))
    return jsonify(result)


@app.get("/api/sample-data")
def sample_data():
    return jsonify(get_sample_data())


@app.get("/api/history")
def history():
    """Saved assessments, newest first. Optional: /api/history?limit=10"""
    raw_limit = request.args.get("limit", "50")
    try:
        limit = int(raw_limit)
    except ValueError:
        abort(400, "'limit' must be a whole number")
    if not 1 <= limit <= 500:
        abort(400, "'limit' must be between 1 and 500")

    items = database.get_history(limit)
    return jsonify({"count": len(items), "assessments": items})


if __name__ == "__main__":
    # 127.0.0.1 = reachable only from your own computer. Do NOT use host="0.0.0.0"
    # together with debug=True: the debugger would let anyone on the network run code.
    app.run(host="127.0.0.1", port=5000, debug=True)
