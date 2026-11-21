"""Stand-in for Person A's ML model.

It returns believable DUMMY numbers so the frontend is never blocked.
app.py uses this only when `from ml.predict import predict_soh` fails.
"""
from validation import require_number

RATED_CAPACITY_AH = 2.0  # the real model uses about 1.9


def predict_soh(features):
    """Same input/output shape as ml.predict.predict_soh (see API contract)."""
    cycle = require_number(features.get("cycle_number"), "cycle_number", min_value=0)
    require_number(features.get("avg_voltage"), "avg_voltage", min_value=0.1)
    require_number(features.get("avg_current"), "avg_current")
    temp = require_number(features.get("avg_temperature"), "avg_temperature",
                          min_value=-40, max_value=100)
    require_number(features.get("discharge_time"), "discharge_time", min_value=0)

    # Fake rule: batteries lose ~0.18% SOH per cycle, and extra when hot.
    # cycle 120 -> 100 - 21.6 = 78.4, which matches the example in the contract.
    soh = 100 - 0.18 * cycle - max(0.0, temp - 35) * 0.3
    soh = round(max(30.0, min(100.0, soh)), 1)

    if soh >= 80:
        category = "candidate_for_testing"
    elif soh >= 60:
        category = "needs_assessment"
    else:
        category = "recycle"

    return {
        "soh_percent": soh,
        "remaining_capacity_ah": round(RATED_CAPACITY_AH * soh / 100, 2),
        "rated_capacity_ah": RATED_CAPACITY_AH,
        "category": category,
        "disclaimer": "Preliminary screening only, not a safety certification.",
    }
