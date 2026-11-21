# /ml – ReVolt SOH model (Person A)

Preliminary screening only, not a safety certification.

## Setup
```
cd ml
pip install -r requirements.txt
```

## 1. Get the real data (NASA Li-ion Battery Aging Datasets)
Official page: https://data.nasa.gov/dataset/li-ion-battery-aging-datasets
(Kaggle also hosts a mirror: search "NASA Battery Dataset".)
Unzip it and copy `B0005.mat`, `B0006.mat`, `B0007.mat`, `B0018.mat` into `ml/data/raw/`.

## 2. Run
```
python train.py        # loads, cleans, compares models, saves model.pkl + model_meta.json
python predict.py      # quick test with the example from the API contract
python plots.py        # 4 PNG charts in ml/plots/
```
No data yet? `python make_demo_data.py` then `python train.py --demo` (FAKE data, for testing only).

## 3. Use from the backend
```python
from ml.predict import predict_soh      # run Flask from the repo root
result = predict_soh({"cycle_number": 120, "avg_voltage": 3.65, "avg_current": -1.8,
                      "avg_temperature": 32.5, "discharge_time": 2800})
```
It raises `ValueError` with a readable message for bad input (return HTTP 400) and
`FileNotFoundError` if `model.pkl` is missing.

## Dataset columns (NASA)
Each battery file holds a list of cycles. Each cycle has `type` (charge / discharge / impedance),
`ambient_temperature` (°C), `time` (start date) and a `data` block.

| Cycle type | Column | Meaning |
|---|---|---|
| charge | Voltage_measured | Battery terminal voltage (V) |
| charge | Current_measured | Battery current (A) |
| charge | Temperature_measured | Battery temperature (°C) |
| charge | Current_charge / Voltage_charge | Current / voltage at the charger (A / V) |
| charge | Time | Seconds since the cycle started |
| discharge | Voltage_measured, Current_measured, Temperature_measured, Time | Same as above (current is negative while discharging) |
| discharge | Current_load / Voltage_load | Current / voltage at the load (A / V) |
| discharge | **Capacity** | Ah delivered until the cut-off voltage. **Our target.** |
| impedance | Re, Rct, Battery_impedance, ... | Internal resistance measurements (not used) |

Test setup: charge 1.5 A until 4.2 V; discharge 2 A down to a cut-off voltage (2.7 V for B0005,
2.5 V for B0006 and B0018, 2.2 V for B0007); the cells are rated 2 Ah; the experiment stops at about 30% fade.

## Our table (one row per discharge cycle)
`cycle_number, avg_voltage, avg_current, avg_temperature, discharge_time, capacity_ah` → `soh_percent`.

## Notes for the team
- `rated_capacity_ah` in the API is the average starting capacity of the training batteries
  (about 1.85 Ah for the real NASA cells, not exactly 2.0). SOH is measured against it.
- Thresholds (80 / 60) and the disclaimer text are in `config.py`.
