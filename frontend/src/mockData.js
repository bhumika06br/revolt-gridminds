// Mock data that follows the API contract exactly.
// Used when VITE_USE_MOCK=true, so the frontend works without the backend.

export const DISCLAIMER =
  "Preliminary screening only, not a safety certification.";

const RATED_CAPACITY_AH = 2.0;

// Same thresholds as the contract (adjustable assumptions)
export function categoryFromSoh(soh) {
  if (soh >= 80) return "candidate_for_testing";
  if (soh >= 60) return "needs_assessment";
  return "recycle";
}

// A made-up SOH formula, just so the mock reacts to the inputs.
export function mockAssess(input) {
  const { cycle_number, avg_temperature, discharge_time } = input;
  let soh =
    100 -
    0.165 * cycle_number -
    0.25 * Math.max(0, avg_temperature - 25) +
    (discharge_time - 2800) * 0.004;
  soh = Math.min(100, Math.max(0, soh));
  soh = Math.round(soh * 10) / 10;
  return {
    soh_percent: soh,
    remaining_capacity_ah: Math.round(RATED_CAPACITY_AH * (soh / 100) * 100) / 100,
    rated_capacity_ah: RATED_CAPACITY_AH,
    category: categoryFromSoh(soh),
    disclaimer: DISCLAIMER,
  };
}

// 24-hour sample: solar peaks at midday, load peaks in the evening
export const mockSampleData = {
  solar_kw: Array.from({ length: 24 }, (_, h) =>
    h >= 6 && h <= 18 ? Math.round(5 * Math.sin((Math.PI * (h - 6)) / 12) * 100) / 100 : 0
  ),
  load_kw: [
    0.6, 0.5, 0.5, 0.5, 0.6, 0.9, 1.4, 1.8, 1.5, 1.2, 1.1, 1.1,
    1.2, 1.1, 1.1, 1.3, 1.8, 2.6, 3.2, 3.4, 2.9, 2.1, 1.2, 0.8,
  ],
};

// Simple hour-by-hour battery simulation (1 hour steps).
export function mockSimulate(req) {
  const { battery_capacity_kwh, soh_percent, initial_soc, solar_kw, load_kw } = req;
  const usable = battery_capacity_kwh * (soh_percent / 100);
  const minE = usable * 0.1;
  const maxE = usable * 0.9;
  let energy = Math.min(maxE, Math.max(minE, usable * initial_soc));

  const out = { hours: [], soc: [], charge_kw: [], discharge_kw: [], grid_import_kw: [], solar_wasted_kw: [] };
  const r = (x) => Math.round(x * 100) / 100;

  for (let h = 0; h < 24; h++) {
    const net = solar_kw[h] - load_kw[h];
    let charge = 0, discharge = 0, grid = 0, wasted = 0;
    if (net >= 0) {
      charge = Math.min(net, maxE - energy);
      energy += charge;
      wasted = net - charge;
    } else {
      const need = -net;
      discharge = Math.min(need, energy - minE);
      energy -= discharge;
      grid = need - discharge;
    }
    out.hours.push(h);
    out.soc.push(r(energy / usable)); // fraction 0-1, like the real backend
    out.charge_kw.push(r(charge));
    out.discharge_kw.push(r(discharge));
    out.grid_import_kw.push(r(grid));
    out.solar_wasted_kw.push(r(wasted));
  }

  const totalSolar = solar_kw.reduce((a, b) => a + b, 0);
  const totalWasted = out.solar_wasted_kw.reduce((a, b) => a + b, 0);
  const gridKwh = out.grid_import_kw.reduce((a, b) => a + b, 0);
  const util = totalSolar > 0 ? ((totalSolar - totalWasted) / totalSolar) * 100 : 0;

  const recs = [];
  if (totalWasted > 0.5) recs.push("Some solar energy is wasted at midday. A larger battery or shifting loads to the daytime would help.");
  if (gridKwh > 5) recs.push("Evening grid import is high. More storage capacity would reduce it.");
  if (recs.length === 0) recs.push("This battery size covers the profile well.");

  out.summary = {
    solar_utilisation_percent: r(util),
    grid_import_kwh: r(gridKwh),
    recommendations: recs,
  };
  return out;
}

// Pretend history so the history table has something to show in mock mode
export const mockHistory = [];
