"""
make_demo_data.py - creates FAKE battery files in the SAME format as the real NASA files.

Use it ONLY to test the pipeline when you do not have the real data yet.
Results from fake data must never be shown to judges as real results.

Run:  python make_demo_data.py
"""
import numpy as np
from scipy.io import savemat

try:
    from . import config as cfg
except ImportError:
    import config as cfg

rng = np.random.default_rng(7)

# name, starting capacity (Ah), fade speed a, fade acceleration b, number of cycles
BATTERIES = [
    ("B0005", 2.00, 0.0009, 5.0e-6, 168),
    ("B0006", 1.98, 0.0011, 6.0e-6, 168),
    ("B0007", 2.01, 0.0008, 4.5e-6, 168),
    ("B0018", 1.99, 0.0010, 5.5e-6, 132),
]


def struct(**fields):
    """Build a 1x1 MATLAB-style struct, the way the NASA files store data."""
    arr = np.empty((1, 1), dtype=np.dtype([(k, "O") for k in fields]))
    for k, v in fields.items():
        arr[0, 0][k] = v
    return arr


def make_battery(name, c0, a, b, n_cycles):
    entries = []
    for n in range(1, n_cycles + 1):
        # a charge cycle first (the loader must ignore it)
        t = np.linspace(0, 3600, 50)
        entries.append(("charge", struct(
            Voltage_measured=3.8 + 0.4 * t / 3600, Current_measured=np.full(50, 1.5),
            Temperature_measured=np.full(50, 25.0), Time=t)))

        cap = c0 * (1 - a * n - b * n * n) + rng.normal(0, 0.008)
        if n % 25 == 0:
            cap += 0.04                      # small "capacity recovery" bump, as in real data
        if name == "B0006" and n in (60, 61):
            cap = 0.02                       # deliberately broken cycles -> cleaning must remove them
        current = -2.0 + rng.normal(0, 0.01)
        t_end = max(cap * 3600 / abs(current), 5.0)
        t = np.linspace(0, t_end, 120)
        x = t / t_end
        volt = (4.19 - 0.0004 * n) - (1.5 - 0.0003 * n) * x ** 1.2 + rng.normal(0, 0.005, 120)
        temp = 25 + 0.03 * n + 8 * x ** 2 + rng.normal(0, 0.2, 120)
        entries.append(("discharge", struct(
            Voltage_measured=volt, Current_measured=np.full(120, current),
            Temperature_measured=temp, Time=t, Capacity=np.array([[cap]]))))

    cycles = np.empty((1, len(entries)), dtype=np.dtype(
        [("type", "O"), ("ambient_temperature", "O"), ("time", "O"), ("data", "O")]))
    for i, (typ, data) in enumerate(entries):
        cycles[0, i]["type"] = typ
        cycles[0, i]["ambient_temperature"] = np.array([[24]])
        cycles[0, i]["time"] = np.array([[2008, 4, 2, 13, 8, i]])
        cycles[0, i]["data"] = data
    return struct(cycle=cycles)


if __name__ == "__main__":
    cfg.DEMO_RAW_DIR.mkdir(parents=True, exist_ok=True)
    for name, c0, a, b, n in BATTERIES:
        savemat(cfg.DEMO_RAW_DIR / f"{name}.mat", {name: make_battery(name, c0, a, b, n)})
        print("wrote", cfg.DEMO_RAW_DIR / f"{name}.mat")
    print("\nDONE. These are FAKE data. Train with:  python train.py --demo")
