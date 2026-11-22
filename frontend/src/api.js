// All backend calls live in this one file.
// To switch between mock data and the real backend, edit the ".env" file:
//   VITE_USE_MOCK=true   -> mock data
//   VITE_USE_MOCK=false  -> real Flask API at VITE_API_URL

import { mockAssess, mockSampleData, mockSimulate, mockHistory } from "./mockData";

export const USE_MOCK = import.meta.env.VITE_USE_MOCK === "true";
export const API_URL = import.meta.env.VITE_API_URL || "http://localhost:5000";

const delay = (ms) => new Promise((r) => setTimeout(r, ms));

async function request(path, options) {
  let res;
  try {
    res = await fetch(API_URL + path, options);
  } catch {
    throw new Error(
      `Cannot reach the backend at ${API_URL}. Is "python backend/app.py" running?`
    );
  }
  if (!res.ok) {
    let msg = `Server error (${res.status})`;
    try {
      const body = await res.json();
      msg = body.error || body.message || msg;
    } catch {
      /* response had no JSON body */
    }
    throw new Error(msg);
  }
  return res.json();
}

const postJson = (path, body) =>
  request(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

export async function assessBattery(input) {
  if (USE_MOCK) {
    await delay(500);
    const result = mockAssess(input);
    mockHistory.unshift({ ...result, cycle_number: input.cycle_number, created_at: new Date().toLocaleString() });
    return result;
  }
  return postJson("/api/battery/assess", input);
}

export async function getSampleData() {
  if (USE_MOCK) {
    await delay(300);
    return mockSampleData;
  }
  return request("/api/sample-data");
}

export async function runSimulation(input) {
  const data = USE_MOCK
    ? (await delay(600), mockSimulate(input))
    : await postJson("/api/simulate", input);
  // The backend sends soc as a fraction (0-1). Charts want percent (0-100).
  return { ...data, soc_percent: data.soc.map((v) => v * 100) };
}

export async function getHistory() {
  if (USE_MOCK) return { count: mockHistory.length, assessments: mockHistory };
  return request("/api/history");
}
