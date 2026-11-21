"""Realistic sample 24-hour data for /api/sample-data.

Index 0 = 00:00-01:00, index 23 = 23:00-24:00. Values are average kW in that hour.
The data is fixed (no randomness) so demos and tests give the same result every time.
"""
import math

PEAK_SOLAR_KW = 4.5   # a typical ~4.5 kW rooftop system on a clear day


def _solar_profile():
    """Bell curve: zero at night, rising after sunrise, peak at midday."""
    values = []
    for hour in range(24):
        if 6 <= hour <= 17:                      # the sun is up
            middle_of_hour = hour + 0.5
            spread = 2.6                         # bigger = wider bell
            kw = PEAK_SOLAR_KW * math.exp(-((middle_of_hour - 12.5) ** 2) / (2 * spread ** 2))
        else:
            kw = 0.0
        values.append(round(kw, 2))
    return values


# Typical home: small night load, morning bump, small midday dip, big evening peak.
_LOAD = [
    0.45, 0.40, 0.38, 0.38, 0.40, 0.55,   # 00:00 - 05:59
    0.95, 1.40, 1.20, 0.80, 0.70, 0.70,   # 06:00 - 11:59
    0.85, 0.80, 0.70, 0.75, 0.95, 1.50,   # 12:00 - 17:59
    2.10, 2.60, 2.40, 1.90, 1.10, 0.65,   # 18:00 - 23:59
]

_SOLAR = _solar_profile()


def get_sample_data():
    """Return fresh copies so callers can't change the originals."""
    return {"solar_kw": list(_SOLAR), "load_kw": list(_LOAD)}
