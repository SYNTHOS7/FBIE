import type { Coverage, Region, RiskResult, Variable, Verification } from "./types";

const API_BASE = (process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000").replace(/\/$/, "");

export const fallbackRegions: Region[] = [
  { id: "mumbai", name: "Mumbai", state: "Maharashtra", lat: 19.08, lon: 72.88 },
  { id: "pune", name: "Pune", state: "Maharashtra", lat: 18.52, lon: 73.86 },
  { id: "delhi", name: "Delhi", state: "Delhi", lat: 28.61, lon: 77.21 },
  { id: "jaipur", name: "Jaipur", state: "Rajasthan", lat: 26.91, lon: 75.79 },
  { id: "ahmedabad", name: "Ahmedabad", state: "Gujarat", lat: 23.02, lon: 72.57 },
  { id: "bengaluru", name: "Bengaluru", state: "Karnataka", lat: 12.97, lon: 77.59 },
  { id: "chennai", name: "Chennai", state: "Tamil Nadu", lat: 13.08, lon: 80.27 },
  { id: "kolkata", name: "Kolkata", state: "West Bengal", lat: 22.57, lon: 88.36 },
];

export const fallbackCoverage: Coverage = {
  mode: "demo",
  disclaimer: "Illustrative interface. No trained model or live forecast risk is available yet.",
  regions: fallbackRegions,
  variables: [
    { id: "rainfall", label: "Rainfall" },
    { id: "temperature", label: "Temperature" },
    { id: "wind", label: "Wind" },
  ],
  lead_days: Array.from({ length: 10 }, (_, i) => i + 1),
};

export function fallbackRisk(regionId: string, variable: Variable, leadDay: number): RiskResult {
  const region = fallbackRegions.find((entry) => entry.id === regionId) || fallbackRegions[0];
  const labels = {
    rainfall: {
      summary: "Explore how rainfall forecasts could differ from what eventually happens.",
      modes: ["Rain may fall in a different location", "Arrival time may shift", "Amount may differ"],
    },
    temperature: {
      summary: "Explore how temperature forecasts could differ from what eventually happens.",
      modes: ["A hotter or cooler day", "Peak temperature at a different time"],
    },
    wind: {
      summary: "Explore how wind forecasts could differ from what eventually happens.",
      modes: ["Stronger or weaker wind", "Direction or timing may change"],
    },
  }[variable];
  return {
    mode: "demo",
    disclaimer: "Demonstration scenario only. This is not an actual weather forecast or measured risk.",
    region,
    variable,
    lead_day: leadDay,
    risk: { level: "illustrative", probability: null, summary: labels.summary, possible_failure_modes: labels.modes },
    evidence: [
      { title: "Forecast agreement", detail: "A future model will compare available forecasts and identify meaningful disagreement." },
      { title: "Past outcomes", detail: "A verified archive will show how similar forecasts performed for this place and season." },
      { title: "Latest changes", detail: "Successive forecast runs will reveal whether predicted conditions are moving or stabilizing." },
    ],
    historical_cases: [],
    model: { status: "not_trained", version: null },
    data_freshness: { status: "synthetic_scenario" },
  };
}

export const fallbackVerification: Verification = {
  mode: "demo",
  disclaimer: "No archived forecasts have been verified against observations yet.",
  summary: { verified_predictions: 0, skill: null },
  cases: [],
};

async function request<T>(path: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, { signal, cache: "no-store" });
  if (!response.ok) throw new Error(`API ${response.status}`);
  return response.json() as Promise<T>;
}

export async function getCoverage(signal?: AbortSignal): Promise<{ data: Coverage; connected: boolean }> {
  try {
    const data = await request<Coverage>("/v1/coverage", signal);
    const variables = Array.isArray(data.variables) ? data.variables : fallbackCoverage.variables;
    return { data: { ...fallbackCoverage, ...data, variables }, connected: true };
  } catch {
    return { data: fallbackCoverage, connected: false };
  }
}

export async function getRisk(regionId: string, variable: Variable, leadDay: number, signal?: AbortSignal): Promise<{ data: RiskResult; connected: boolean }> {
  try {
    const query = new URLSearchParams({ region_id: regionId, variable, lead_day: String(leadDay) });
    const raw = await request<Record<string, unknown>>(`/v1/risk?${query}`, signal);
    if (raw.risk && raw.evidence) return { data: raw as unknown as RiskResult, connected: true };
    const region = (raw.region as Region | undefined) || fallbackRegions.find((entry) => entry.id === regionId) || fallbackRegions[0];
    const drivers = Array.isArray(raw.drivers) ? raw.drivers as Array<Record<string, unknown>> : [];
    const failureModes = Array.isArray(raw.failure_modes) ? raw.failure_modes as Array<Record<string, unknown>> : [];
    const data: RiskResult = {
      mode: raw.mode === "live" ? "live" : "demo",
      disclaimer: typeof raw.disclaimer === "string" ? raw.disclaimer : undefined,
      region,
      variable,
      lead_day: leadDay,
      issued_at: typeof raw.forecast_time === "string" ? raw.forecast_time : undefined,
      valid_at: typeof raw.valid_time === "string" ? raw.valid_time : undefined,
      risk: {
        level: typeof raw.risk_level === "string" ? raw.risk_level : "illustrative",
        probability: typeof raw.probability === "number" ? raw.probability : null,
        summary: typeof raw.headline === "string" ? raw.headline : "Forecast reliability is unavailable.",
        possible_failure_modes: failureModes.map((mode) => String(mode.name || mode.label || "Possible forecast error")),
      },
      evidence: drivers.map((driver) => ({ title: String(driver.label || driver.title || "Signal"), detail: String(driver.detail || "") })),
      historical_cases: [],
      model: { status: raw.mode === "live" ? "published" : "not_trained", version: typeof raw.model_version === "string" ? raw.model_version : null },
      data_freshness: { status: raw.mode === "live" ? "published" : "synthetic_scenario" },
    };
    return { data, connected: true };
  } catch {
    return { data: fallbackRisk(regionId, variable, leadDay), connected: false };
  }
}

export async function getVerification(signal?: AbortSignal): Promise<{ data: Verification; connected: boolean }> {
  try {
    return { data: await request<Verification>("/v1/verification", signal), connected: true };
  } catch {
    return { data: fallbackVerification, connected: false };
  }
}
