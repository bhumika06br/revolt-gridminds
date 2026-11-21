"""
plots.py - makes 4 presentation-ready PNG charts in ml/plots/ (run train.py first).

  1. capacity_fade.png       capacity vs cycle for every battery
  2. soh_categories.png      SOH vs cycle with the 3 screening zones
  3. predicted_vs_actual.png how close the model gets on batteries it never saw
  4. model_comparison.png    error of each model
"""
import json

import matplotlib
matplotlib.use("Agg")                       # draw to files, no window needed
import matplotlib.pyplot as plt
import pandas as pd

try:
    from . import config as cfg
except ImportError:
    import config as cfg

# colour-blind-safe colours, assigned to batteries in a fixed order
COLORS = ["#0072B2", "#D55E00", "#009E73", "#CC79A7", "#E69F00"]
INK, MUTED, GRID = "#222222", "#666666", "#E3E3E3"

plt.rcParams.update({
    "font.size": 12, "axes.edgecolor": MUTED, "axes.labelcolor": INK,
    "xtick.color": MUTED, "ytick.color": MUTED, "axes.grid": True, "grid.color": GRID,
    "axes.spines.top": False, "axes.spines.right": False, "figure.dpi": 150,
})


def save(fig, name, note=""):
    if note:
        fig.text(0.01, 0.005, note, fontsize=9, color=MUTED)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(cfg.PLOTS_DIR / name)
    plt.close(fig)
    print("saved", cfg.PLOTS_DIR / name)


def main():
    cfg.PLOTS_DIR.mkdir(parents=True, exist_ok=True)
    meta = json.loads(cfg.META_PATH.read_text())
    cv = pd.read_csv(cfg.PROCESSED_DIR / "cv_predictions.csv")
    comp = pd.read_csv(cfg.PROCESSED_DIR / "model_comparison.csv")
    ref, best = meta["reference_capacity_ah"], meta["best_model"]
    note = "DEMO (fake) data - not real results" if meta["data_source"].startswith("DEMO") else ""
    batteries = sorted(cv["battery_id"].unique())
    color = {b: COLORS[i % len(COLORS)] for i, b in enumerate(batteries)}

    # 1. capacity fade
    fig, ax = plt.subplots(figsize=(8, 5))
    for b in batteries:
        d = cv[cv.battery_id == b]
        ax.plot(d.cycle_number, d.capacity_ah, color=color[b], lw=2, label=b)
    ax.axhline(0.7 * ref, color=MUTED, ls="--", lw=1.5)
    ax.text(cv.cycle_number.min(), 0.7 * ref + 0.015, "70% of initial capacity (common end-of-life mark)",
            color=MUTED, fontsize=10)
    ax.set_xlabel("Charge/discharge cycle")
    ax.set_ylabel("Capacity (Ah)")
    ax.set_title("Battery capacity fades with every cycle", loc="left", color=INK)
    ax.legend(frameon=False)
    save(fig, "capacity_fade.png", note)

    # 2. SOH with screening zones
    fig, ax = plt.subplots(figsize=(8, 5))
    xmax = cv.cycle_number.max()
    ax.axhspan(cfg.CANDIDATE_MIN_SOH, 105, color="#009E73", alpha=0.10, lw=0)
    ax.axhspan(cfg.ASSESSMENT_MIN_SOH, cfg.CANDIDATE_MIN_SOH, color="#E69F00", alpha=0.12, lw=0)
    ax.axhspan(0, cfg.ASSESSMENT_MIN_SOH, color="#D55E00", alpha=0.10, lw=0)
    for b in batteries:
        d = cv[cv.battery_id == b]
        ax.plot(d.cycle_number, d.soh_percent, color=color[b], lw=2, label=b)
    ax.text(2, 102, "candidate_for_testing (>= 80%)", ha="left", fontsize=10, color=INK)
    ax.text(2, 71, "needs_assessment (60-80%)", ha="left", fontsize=10, color=INK)
    ax.text(2, 52, "recycle (< 60%)", ha="left", fontsize=10, color=INK)
    ax.set_ylim(50, 106)
    ax.set_xlabel("Charge/discharge cycle")
    ax.set_ylabel("State of Health (%)")
    ax.set_title("Where each battery falls in the screening zones", loc="left", color=INK)
    ax.legend(frameon=False, loc="lower right", ncol=4)
    save(fig, "soh_categories.png", note)

    # 3. predicted vs actual (best model, tested on unseen batteries)
    fig, ax = plt.subplots(figsize=(6, 6))
    lo, hi = cv.soh_percent.min() - 2, 102
    ax.plot([lo, hi], [lo, hi], color=MUTED, ls="--", lw=1.5, label="perfect prediction")
    for b in batteries:
        d = cv[cv.battery_id == b]
        ax.scatter(d.soh_percent, d[f"pred_{best}"] / ref * 100, s=18, color=color[b],
                   edgecolor="white", linewidth=0.5, label=b)
    ax.set_xlabel("Actual SOH (%)")
    ax.set_ylabel("Predicted SOH (%)")
    ax.set_title(f"{best}: predicted vs actual\n(each battery was unseen by the model)",
                 loc="left", color=INK, fontsize=12)
    ax.set_aspect("equal")
    ax.legend(frameon=False)
    save(fig, "predicted_vs_actual.png", note)

    # 4. model comparison
    fig, ax = plt.subplots(figsize=(8, 4))
    comp = comp.sort_values("MAE_SOH_points", ascending=False)
    names = [n.replace(" (always predict the average)", "\n(always the average)") for n in comp.model]
    bars = ax.barh(names, comp.MAE_SOH_points,
                   color=["#0072B2" if m == best else "#B0B0B0" for m in comp.model])
    for bar, val in zip(bars, comp.MAE_SOH_points):
        ax.text(val + 0.05, bar.get_y() + bar.get_height() / 2, f"{val:.2f}", va="center", color=INK)
    ax.set_xlabel("Average error (SOH percentage points) - lower is better")
    ax.set_title("Model comparison (best model in blue)", loc="left", color=INK)
    ax.grid(axis="y", visible=False)
    save(fig, "model_comparison.png", note)


if __name__ == "__main__":
    main()
