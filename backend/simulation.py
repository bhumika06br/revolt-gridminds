"""Hour-by-hour solar + battery simulation.

Rules (each step is 1 hour, so kW and kWh are the same number):
  * solar > load  -> extra solar charges the battery; if the battery is full, the rest is wasted
  * load > solar  -> the battery discharges to cover the gap; if it hits its minimum,
                     whatever is still missing is imported from the grid
  * the battery only works between SOC_MIN and SOC_MAX of its USABLE capacity
  * usable capacity = battery_capacity_kwh * soh_percent / 100  (an old battery holds less)
"""
from validation import require_number

SOC_MIN = 0.10   # never discharge below 10%
SOC_MAX = 0.90   # never charge above 90%
HOURS = 24

# Used only for the plain-English tips. Same numbers as the SOH categories.
SOH_GOOD = 80
SOH_LOW = 60


def _hourly_list(values, name):
    """Check that `values` is a list of 24 non-negative numbers."""
    if not isinstance(values, list) or len(values) != HOURS:
        raise ValueError(f"'{name}' must be a list of exactly {HOURS} numbers")
    return [require_number(v, f"{name}[{i}]", min_value=0) for i, v in enumerate(values)]


def run_simulation(battery_capacity_kwh, soh_percent, initial_soc, solar_kw, load_kw):
    """Simulate one day. Returns a dict in the shape of the API contract."""
    capacity = require_number(battery_capacity_kwh, "battery_capacity_kwh")
    if capacity <= 0:
        raise ValueError("'battery_capacity_kwh' must be greater than 0")
    soh = require_number(soh_percent, "soh_percent", min_value=0, max_value=100)
    start_soc = require_number(initial_soc, "initial_soc", min_value=0, max_value=1)
    solar = _hourly_list(solar_kw, "solar_kw")
    load = _hourly_list(load_kw, "load_kw")

    usable = capacity * soh / 100          # kWh this battery can really hold
    energy_min = SOC_MIN * usable          # lowest allowed stored energy (kWh)
    energy_max = SOC_MAX * usable          # highest allowed stored energy (kWh)

    # Start-of-day energy, kept inside the allowed window.
    energy = min(max(start_soc * usable, energy_min), energy_max)

    soc, charge, discharge, grid, wasted = [], [], [], [], []

    for hour in range(HOURS):
        s, l = solar[hour], load[hour]
        charged = discharged = from_grid = lost = 0.0

        if s >= l:
            surplus = s - l
            room = max(0.0, energy_max - energy)      # how much more fits in the battery
            charged = min(surplus, room)
            lost = surplus - charged                  # battery full -> solar is wasted
            energy += charged
        else:
            deficit = l - s
            available = max(0.0, energy - energy_min)  # how much the battery can give
            discharged = min(deficit, available)
            from_grid = deficit - discharged           # battery empty -> use the grid
            energy -= discharged

        soc.append(energy / usable if usable > 0 else 0.0)   # SOC at END of this hour
        charge.append(charged)
        discharge.append(discharged)
        grid.append(from_grid)
        wasted.append(lost)

    total_solar = sum(solar)
    total_load = sum(load)
    wasted_kwh = sum(wasted)
    grid_kwh = sum(grid)
    # Solar "used" = used directly by the home + stored in the battery (= everything not wasted).
    utilisation = (total_solar - wasted_kwh) / total_solar * 100 if total_solar > 0 else 0.0

    tips = _recommendations(
        soh=soh, capacity_kwh=capacity, usable_kwh=usable,
        total_solar=total_solar, total_load=total_load,
        wasted_kwh=wasted_kwh, grid_kwh=grid_kwh,
        utilisation=utilisation, grid_kw=grid, soc=soc,
    )

    return {
        "hours": list(range(HOURS)),
        "soc": [round(x, 4) for x in soc],                 # fraction 0-1, end of each hour
        "charge_kw": [round(x, 3) for x in charge],
        "discharge_kw": [round(x, 3) for x in discharge],
        "grid_import_kw": [round(x, 3) for x in grid],
        "solar_wasted_kw": [round(x, 3) for x in wasted],
        "summary": {
            "solar_utilisation_percent": round(utilisation, 1),
            "grid_import_kwh": round(grid_kwh, 2),
            "recommendations": tips,
            # Extra numbers the dashboard may find handy:
            "usable_capacity_kwh": round(usable, 2),
            "solar_wasted_kwh": round(wasted_kwh, 2),
            "total_solar_kwh": round(total_solar, 2),
            "total_load_kwh": round(total_load, 2),
        },
    }


def _recommendations(soh, capacity_kwh, usable_kwh, total_solar, total_load,
                     wasted_kwh, grid_kwh, utilisation, grid_kw, soc):
    """Turn the numbers into 3-4 plain-English tips."""
    tips = []

    # 1 + 2: how well was solar used, and was any wasted?
    if total_solar <= 0:
        tips.append("There was no solar generation in the input, so the battery could not "
                    "be charged and all demand came from the grid.")
    else:
        if utilisation >= 90:
            tips.append(f"Great match: {utilisation:.0f}% of the solar energy was put to use "
                        "(used directly or stored in the battery).")
        elif utilisation >= 60:
            tips.append(f"{utilisation:.0f}% of the solar energy was used. Some was wasted, "
                        "so there is room to improve.")
        else:
            tips.append(f"Only {utilisation:.0f}% of the solar energy was used. "
                        "A large share of it was wasted.")

        if wasted_kwh >= 0.5:
            tips.append(f"{wasted_kwh:.1f} kWh of solar was wasted because the battery was full. "
                        "Running flexible loads (water heater, washing machine, EV charging) "
                        "at midday, or adding battery capacity, would capture it.")
        else:
            tips.append("Almost no solar was wasted: the battery absorbed the midday surplus.")

    # 3: grid usage
    if grid_kwh < 0.05:
        tips.append("No grid power was needed: solar and the battery covered the whole day.")
    else:
        share = grid_kwh / total_load * 100 if total_load > 0 else 0.0
        peak_hour = max(range(HOURS), key=lambda h: grid_kw[h])
        text = (f"The grid supplied {grid_kwh:.1f} kWh ({share:.0f}% of the day's demand), "
                f"with the highest import at {peak_hour:02d}:00.")
        at_minimum = [h for h in range(HOURS) if soc[h] <= SOC_MIN + 0.001]
        if at_minimum:
            text += (f" The battery reached its {SOC_MIN:.0%} minimum at {at_minimum[0]:02d}:00, "
                     "so demand after that came from the grid. A larger or healthier battery "
                     "would reduce imports.")
        tips.append(text)

    # 4: what the battery's health means
    window_kwh = (SOC_MAX - SOC_MIN) * usable_kwh
    if soh < SOH_LOW:
        tips.append(f"At {soh:.0f}% SOH this battery is below the {SOH_LOW}% level used for "
                    "screening, so recycling is likely the better option. "
                    "Treat this simulation as indicative only.")
    elif soh < SOH_GOOD:
        tips.append(f"At {soh:.0f}% SOH only {usable_kwh:.1f} kWh of the {capacity_kwh:g} kWh "
                    f"rating is usable, and about {window_kwh:.1f} kWh is actually cycled "
                    "within the 10-90% limits. It needs further testing before any real "
                    "second-life use.")
    else:
        tips.append(f"At {soh:.0f}% SOH this battery is a candidate for testing as second-life "
                    f"storage (about {window_kwh:.1f} kWh cycled within the 10-90% limits). "
                    "This is a screening result, not a safety certification.")

    return tips
