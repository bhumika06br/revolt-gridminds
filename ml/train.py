"""
train.py - trains the SOH model.

Steps (each is printed when you run it):
  1. Load the NASA .mat files  -> one row per discharge cycle
  2. Clean the table
  3. Compute SOH = capacity / initial capacity * 100
  4. Compare several models with "leave-one-battery-out" testing
  5. Pick the best, retrain it on all data, save model.pkl

Run (real data in ml/data/raw/):   python train.py
Run (fake test data):              python make_demo_data.py   then   python train.py --demo
"""
import argparse
import json
import sys

import joblib
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

try:
    from . import config as cfg
    from . import data_loader as dl
except ImportError:
    import config as cfg
    import data_loader as dl


def get_models():
    """The candidates. Linear Regression needs scaled inputs, so it gets a StandardScaler."""
    return {
        "Baseline (always predict the average)": DummyRegressor(strategy="mean"),
        "Linear Regression": make_pipeline(StandardScaler(), LinearRegression()),
        "Random Forest": RandomForestRegressor(n_estimators=200, min_samples_leaf=3, random_state=42),
        "Gradient Boosting": GradientBoostingRegressor(random_state=42),
    }


def leave_one_battery_out(models, df):
    """
    Fair test: for each battery, train on the OTHER batteries and predict this one.
    The model never sees the battery it is tested on - like a real retired battery
    it has never met. (A random row split would be too easy: neighbouring cycles
    of the same battery look almost identical.)
    """
    preds = {name: np.zeros(len(df)) for name in models}
    for b in sorted(df["battery_id"].unique()):
        test = (df["battery_id"] == b).values
        for name, model in models.items():
            m = clone(model).fit(df.loc[~test, cfg.FEATURES], df.loc[~test, cfg.TARGET])
            preds[name][test] = m.predict(df.loc[test, cfg.FEATURES])
    return preds


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--demo", action="store_true", help="use FAKE data from make_demo_data.py")
    args = parser.parse_args()
    raw_dir = cfg.DEMO_RAW_DIR if args.demo else cfg.RAW_DIR

    # ---------------- 1. LOAD ----------------
    print(f"\n[1/5] Loading battery files from {raw_dir}")
    df = dl.load_all(raw_dir, cfg.BATTERIES)
    if df is None or df.empty:
        sys.exit(f"No battery data found in {raw_dir} (looked for metadata.csv or B*.mat files).\n"
                 "Unzip the Kaggle/NASA download into that folder (see README.md),\n"
                 "or test with fake data:  python make_demo_data.py  then  python train.py --demo")
    if args.demo:
        print("\n  *** DEMO MODE: FAKE DATA. Do not present these numbers as real results. ***\n")

    # ---------------- 2. CLEAN ----------------
    print("\n[2/5] Cleaning")
    df = dl.clean_cycles(df)
    if df["battery_id"].nunique() < 2:
        sys.exit("Need at least 2 batteries to test on an unseen battery.")

    # ---------------- 3. SOH ----------------
    print("\n[3/5] Computing SOH = capacity / initial capacity * 100")
    df = dl.add_soh(df)
    reference_capacity = round(float(df.groupby("battery_id")["initial_capacity_ah"].first().mean()), 3)
    print(f"  average initial capacity (used as the 'rated' capacity): {reference_capacity} Ah")
    cfg.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(cfg.PROCESSED_DIR / "cycles_clean.csv", index=False)

    # ---------------- 4. COMPARE MODELS ----------------
    print("\n[4/5] Comparing models (each tested on batteries it has never seen)")
    models = get_models()
    preds = leave_one_battery_out(models, df)

    y = df[cfg.TARGET].values
    results = []
    for name in models:
        mae = mean_absolute_error(y, preds[name])
        per_battery = [
            mean_absolute_error(y[(df["battery_id"] == b).values], preds[name][(df["battery_id"] == b).values])
            for b in sorted(df["battery_id"].unique())
        ]
        results.append({
            "model": name,
            "MAE_Ah": round(mae, 4),
            "MAE_SOH_points": round(mae / reference_capacity * 100, 2),
            "R2": round(r2_score(y, preds[name]), 4),
            "worst_battery_MAE_Ah": round(max(per_battery), 4),
        })
    res = pd.DataFrame(results)
    print(res.to_string(index=False))

    # pick the best REAL model (not the baseline) by lowest MAE
    real = res[~res["model"].str.startswith("Baseline")]
    best_name = real.sort_values("MAE_Ah").iloc[0]["model"]
    print(f"\n  Best model: {best_name}")

    # save things the plots need
    out = df[["battery_id", "cycle_number", "capacity_ah", "soh_percent"]].copy()
    for name in models:
        out[f"pred_{name}"] = preds[name]
    out.to_csv(cfg.PROCESSED_DIR / "cv_predictions.csv", index=False)
    res.to_csv(cfg.PROCESSED_DIR / "model_comparison.csv", index=False)

    # ---------------- 5. SAVE ----------------
    print("\n[5/5] Retraining the best model on ALL batteries and saving model.pkl")
    final = clone(models[best_name]).fit(df[cfg.FEATURES], df[cfg.TARGET])
    joblib.dump(final, cfg.MODEL_PATH)
    meta = {
        "data_source": "DEMO (fake data)" if args.demo else "real data",
        "best_model": best_name,
        "features": cfg.FEATURES,
        "reference_capacity_ah": reference_capacity,
        "batteries": sorted(df["battery_id"].unique().tolist()),
        "n_rows": int(len(df)),
        "results": results,
    }
    cfg.META_PATH.write_text(json.dumps(meta, indent=2))
    print(f"  saved {cfg.MODEL_PATH.name} and {cfg.META_PATH.name}\n\nDone. Next: python predict.py  and  python plots.py")


if __name__ == "__main__":
    main()
