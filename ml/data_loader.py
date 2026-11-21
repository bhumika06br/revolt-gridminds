"""
data_loader.py - turns the NASA battery .mat files into ONE ROW PER DISCHARGE CYCLE.

Why discharge cycles? In the NASA data, the "Capacity" number (in Ah) is only
recorded during discharge: it is how much charge the battery gave out before
hitting its cut-off voltage. That is exactly the "how healthy is the battery" number.
"""
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.io import loadmat


def load_battery_file(path):
    """Read one NASA file (e.g. B0005.mat). Returns a list of dicts, one per discharge cycle."""
    mat = loadmat(str(path), struct_as_record=False, squeeze_me=True)
    # The file holds one variable named like the battery (B0005); skip '__header__' etc.
    key = [k for k in mat.keys() if not k.startswith("__")][0]
    cycles = np.atleast_1d(mat[key].cycle)

    rows, discharge_count, skipped = [], 0, 0
    for c in cycles:
        if str(c.type) != "discharge":   # ignore 'charge' and 'impedance' cycles
            continue
        discharge_count += 1             # cycle_number = which discharge this is (1, 2, 3, ...)
        try:
            d = c.data
            volt = np.asarray(d.Voltage_measured, dtype=float)
            curr = np.asarray(d.Current_measured, dtype=float)
            temp = np.asarray(d.Temperature_measured, dtype=float)
            time = np.asarray(d.Time, dtype=float)
            cap = float(np.asarray(d.Capacity, dtype=float).ravel()[0])
            rows.append({
                "battery_id": key,
                "cycle_number": discharge_count,
                "avg_voltage": float(np.nanmean(volt)),
                "avg_current": float(np.nanmean(curr)),
                "avg_temperature": float(np.nanmean(temp)),
                "discharge_time": float(np.nanmax(time)),   # seconds until cut-off voltage
                "capacity_ah": cap,
            })
        except Exception:
            skipped += 1                 # a broken cycle should not crash the whole run
    if skipped:
        print(f"  {key}: skipped {skipped} unreadable cycle(s)")
    return rows


def load_kaggle_csv(raw_dir, batteries):
    """
    Kaggle version of the NASA data: a metadata.csv (one row per cycle: type, battery_id,
    Capacity, filename, ...) plus one small CSV per cycle (Voltage_measured, Current_measured,
    Temperature_measured, Time, ...). Returns a DataFrame, or None if metadata.csv is not found.
    """
    raw_dir = Path(raw_dir)
    metas = sorted(raw_dir.rglob("metadata.csv"))
    if not metas:
        return None
    meta = pd.read_csv(metas[0])
    meta.columns = [c.strip().lower() for c in meta.columns]      # make names lower-case
    needed = {"type", "battery_id", "filename", "capacity"}
    if not needed.issubset(meta.columns):
        raise SystemExit(f"metadata.csv has columns {list(meta.columns)}; expected at least {sorted(needed)}")
    print(f"  found {metas[0]}")

    # index every cycle CSV by file name, wherever it is inside the unzipped folder
    files = {p.name: p for p in raw_dir.rglob("*.csv") if p.name != "metadata.csv"}

    meta = meta[meta["type"].astype(str).str.lower() == "discharge"]
    if batteries:
        meta = meta[meta["battery_id"].isin(batteries)]
    sort_col = "uid" if "uid" in meta.columns else "filename"
    meta = meta.sort_values(["battery_id", sort_col])

    rows, skipped = [], 0
    for battery, group in meta.groupby("battery_id"):
        n = 0
        for _, r in group.iterrows():
            n += 1                                   # cycle_number = which discharge this is
            try:
                d = pd.read_csv(files[str(r["filename"])])
                d.columns = [c.strip().lower() for c in d.columns]
                rows.append({
                    "battery_id": battery,
                    "cycle_number": n,
                    "avg_voltage": float(d["voltage_measured"].mean()),
                    "avg_current": float(d["current_measured"].mean()),
                    "avg_temperature": float(d["temperature_measured"].mean()),
                    "discharge_time": float(d["time"].max()),
                    "capacity_ah": float(pd.to_numeric(r["capacity"], errors="coerce")),
                })
            except Exception:
                skipped += 1
        print(f"  {battery}: {n} discharge cycles")
    if skipped:
        print(f"  skipped {skipped} unreadable cycle(s)")
    return pd.DataFrame(rows)


def load_all(raw_dir, batteries=None):
    """
    Load the data from raw_dir (searches sub-folders). Understands BOTH formats:
      - Kaggle CSV version (metadata.csv + cycle CSVs)
      - original NASA .mat files
    `batteries` = list of battery ids to use (None = all).
    """
    df = load_kaggle_csv(raw_dir, batteries)
    if df is not None:
        return df
    files = sorted(Path(raw_dir).rglob("B*.mat"))
    if not files:
        return None
    all_rows = []
    for f in files:
        if batteries and f.stem not in batteries:
            continue
        rows = load_battery_file(f)
        print(f"  loaded {f.name}: {len(rows)} discharge cycles")
        all_rows.extend(rows)
    return pd.DataFrame(all_rows)


def clean_cycles(df):
    """Remove rows that are obviously broken. Prints what it removed so nothing is hidden."""
    start = len(df)
    df = df.drop_duplicates(subset=["battery_id", "cycle_number"])
    df = df.replace([np.inf, -np.inf], np.nan).dropna()                 # missing values
    df = df[df["capacity_ah"] > 0.1]          # glitch cycles with ~0 capacity
    df = df[df["discharge_time"] > 60]        # a discharge shorter than 1 minute is a glitch
    df = df[df["avg_temperature"].between(0, 80)]
    df = df[df["avg_voltage"].between(2.0, 4.5)]
    df = df.sort_values(["battery_id", "cycle_number"]).reset_index(drop=True)
    print(f"  cleaning removed {start - len(df)} bad row(s); {len(df)} rows remain")
    return df


def add_soh(df, first_n=3):
    """
    SOH (%) = capacity / initial capacity * 100.
    'Initial capacity' = average of each battery's first few cycles (a bit steadier
    than trusting a single, possibly noisy, first cycle).
    """
    df = df.copy()
    initial = (
        df.sort_values("cycle_number")
        .groupby("battery_id")["capacity_ah"]
        .apply(lambda s: s.head(first_n).mean())
    )
    df["initial_capacity_ah"] = df["battery_id"].map(initial)
    df["soh_percent"] = df["capacity_ah"] / df["initial_capacity_ah"] * 100
    return df
