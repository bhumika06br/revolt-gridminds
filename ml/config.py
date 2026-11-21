"""
config.py - ONE place for all settings shared by train.py, predict.py and plots.py.
If the team decides to change a threshold or a folder, change it here only.
"""
from pathlib import Path

# ---- Folders (all relative to this file, so it works from any directory) ----
ML_DIR = Path(__file__).resolve().parent
RAW_DIR = ML_DIR / "data" / "raw"              # put the real NASA .mat files here
DEMO_RAW_DIR = ML_DIR / "data" / "demo_raw"    # fake NASA-style files (make_demo_data.py)
PROCESSED_DIR = ML_DIR / "data" / "processed"  # cleaned tables written by train.py
PLOTS_DIR = ML_DIR / "plots"
MODEL_PATH = ML_DIR / "model.pkl"
META_PATH = ML_DIR / "model_meta.json"

# ---- The model's inputs (ORDER MATTERS, must match the API contract) ----
FEATURES = [
    "cycle_number",
    "avg_voltage",
    "avg_current",
    "avg_temperature",
    "discharge_time",
]
TARGET = "capacity_ah"

# The Kaggle dataset has ~34 batteries tested under DIFFERENT conditions (different
# temperature and discharge current). We use the 4 classic 2 Ah batteries that were
# tested the same way, so the data is consistent. Set to None to use all (not advised).
BATTERIES = ["B0005", "B0006", "B0007", "B0018"]

# ---- Category thresholds (adjustable assumptions, in SOH %) ----
CANDIDATE_MIN_SOH = 80.0   # SOH >= 80          -> "candidate_for_testing"
ASSESSMENT_MIN_SOH = 60.0  # 60 <= SOH < 80     -> "needs_assessment"
                           # SOH < 60           -> "recycle"

DISCLAIMER = "Preliminary screening only, not a safety certification."
