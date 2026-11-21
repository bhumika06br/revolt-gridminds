"""
predict.py - the function the backend (Person B) calls.

    from ml.predict import predict_soh
    predict_soh({"cycle_number": 120, "avg_voltage": 3.65, "avg_current": -1.8,
                 "avg_temperature": 32.5, "discharge_time": 2800})

Quick test:  python predict.py
"""
import json
import math

import joblib
import pandas as pd

try:
    from . import config as cfg
except ImportError:
    import config as cfg

_model = None   # loaded once, then reused (loading a model on every request would be slow)
_meta = None


def _load():
    global _model, _meta
    if _model is None:
        if not cfg.MODEL_PATH.exists():
            raise FileNotFoundError("model.pkl not found. Run train.py first.")
        _model = joblib.load(cfg.MODEL_PATH)
        _meta = json.loads(cfg.META_PATH.read_text())
    return _model, _meta


def categorize(soh):
    """Turn an SOH % into one of the 3 screening categories (thresholds live in config.py)."""
    if soh >= cfg.CANDIDATE_MIN_SOH:
        return "candidate_for_testing"
    if soh >= cfg.ASSESSMENT_MIN_SOH:
        return "needs_assessment"
    return "recycle"


def _check_inputs(features):
    """Return clean float values, or raise ValueError with a message the API can show."""
    if not isinstance(features, dict):
        raise ValueError("features must be a dict")
    missing = [f for f in cfg.FEATURES if f not in features]
    if missing:
        raise ValueError(f"missing field(s): {', '.join(missing)}")
    values = {}
    for f in cfg.FEATURES:
        try:
            v = float(features[f])
        except (TypeError, ValueError):
            raise ValueError(f"{f} must be a number")
        if not math.isfinite(v):
            raise ValueError(f"{f} must be a finite number")
        values[f] = v
    if values["cycle_number"] < 0:
        raise ValueError("cycle_number must be 0 or more")
    if values["discharge_time"] <= 0:
        raise ValueError("discharge_time must be greater than 0 (seconds)")
    if not 2.0 <= values["avg_voltage"] <= 4.5:
        raise ValueError("avg_voltage must be between 2.0 and 4.5 V")
    if not -20 <= values["avg_temperature"] <= 100:
        raise ValueError("avg_temperature must be between -20 and 100 C")
    return values


def predict_soh(features: dict) -> dict:
    model, meta = _load()
    values = _check_inputs(features)
    X = pd.DataFrame([values], columns=cfg.FEATURES)       # same column order as training

    capacity = float(model.predict(X)[0])                  # predicted capacity in Ah
    rated = meta["reference_capacity_ah"]
    soh = min(max(capacity / rated * 100, 0.0), 100.0)     # keep SOH between 0 and 100

    return {
        "soh_percent": round(soh, 1),
        "remaining_capacity_ah": round(soh / 100 * rated, 2),
        "rated_capacity_ah": round(rated, 2),
        "category": categorize(soh),
        "disclaimer": cfg.DISCLAIMER,
    }


if __name__ == "__main__":
    example = {"cycle_number": 120, "avg_voltage": 3.65, "avg_current": -1.8,
               "avg_temperature": 32.5, "discharge_time": 2800}
    print(json.dumps(predict_soh(example), indent=2))
