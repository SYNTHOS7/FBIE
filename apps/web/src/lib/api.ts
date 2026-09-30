import type { Coverage, FailureMode, ModelStatus, Region, RiskResult, Variable, Verification } from "./types";

const API_BASE = (process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000").replace(/\/$/, "");
export const fallbackRegions: Region[] = [
  { id: "mumbai", name: "Mumbai", state: "Maharashtra" },
  { id: "delhi", name: "Delhi", state: "Delhi" },
  { id: "jaipur", name: "Jaipur", state: "Rajasthan" },
  { id: "ahmedabad", name: "Ahmedabad", state: "Gujarat" },
  { id: "bengaluru", name: "Bengaluru", state: "Karnataka" },
  { id: "kolkata", name: "Kolkata", state: "West Bengal" },
];
export const fallbackCoverage: Coverage = {
  mode: "demo", disclaimer: "The API is unavailable. This interface contains no measured risk.",
  regions: fallbackRegions,
  variables: [{ id: "rainfall", label: "Rainfall", unit: "mm" }, { id: "temperature", label: "Temperature", unit: "°C" }, { id: "wind", label: "Wind", unit: "km/h" }],
  lead_days: Array.from({ length: 10 }, (_, i) => i + 1),
};
export function fallbackRisk(regionId: string, variable: Variable, leadDay: number): RiskResult {
  return {
    mode: "demo", disclaimer: "The API is unavailable. No forecast or measured risk can be shown.",
    region: fallbackRegions.find((item) => item.id === regionId) || fallbackRegions[0], variable, lead_day: leadDay,
    risk: { level: "unavailable", probability: null, summary: "Forecast risk is unavailable for this selection.", possible_failure_modes: [] },
    evidence: [], historical_cases: [], model: { status: "unavailable", version: null },
  };
}
export const fallbackVerification: Verification = {
  mode: "demo", disclaimer: "Verification data is unavailable.",
  summary: { verified_predictions: 0, skill: null }, cases: [],
};
async function request<T>(path: string, signal?: AbortSignal, options?: RequestInit): Promise<T> {
  const response = await fetch(API_BASE + path, { ...options, signal, cache: "no-store" });
  if (!response.ok) throw new Error("API " + response.status);
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}
export async function getCoverage(signal?: AbortSignal): Promise<{ data: Coverage; connected: boolean }> {
  try {
    const data = await request<Coverage>("/v1/coverage", signal);
    if (!Array.isArray(data.regions) || !Array.isArray(data.lead_days)) throw new Error("Invalid coverage response");
    return { data: { ...data, variables: Array.isArray(data.variables) ? data.variables : fallbackCoverage.variables }, connected: true };
  } catch { return { data: fallbackCoverage, connected: false }; }
}
function modes(raw: unknown): FailureMode[] {
  if (!Array.isArray(raw)) return [];
  return raw.map((item) => {
    if (typeof item === "string") return { name: item, probability: null };
    const value = item as Record<string, unknown>;
    return { name: String(value.name || value.label || "Forecast error"), probability: typeof value.probability === "number" && value.probability >= 0 && value.probability <= 1 ? value.probability : null };
  });
}
export async function getRisk(regionId: string, variable: Variable, leadDay: number, signal?: AbortSignal): Promise<{ data: RiskResult; connected: boolean }> {
  try {
    const query = new URLSearchParams({ region_id: regionId, variable, lead_day: String(leadDay) });
    const raw = await request<Record<string, unknown>>("/v1/risk?" + query, signal);
    const live = raw.mode === "live";
    const legacy = raw.risk && typeof raw.risk === "object" ? raw.risk as Record<string, unknown> : null;
    const candidate = typeof raw.probability === "number" ? raw.probability : typeof legacy?.probability === "number" ? legacy.probability : null;
    const drivers = Array.isArray(raw.drivers) ? raw.drivers as Array<Record<string, unknown>> : [];
    return { connected: true, data: {
      id: typeof raw.id === "string" ? raw.id : undefined,
      mode: live ? "live" : "demo", disclaimer: typeof raw.disclaimer === "string" ? raw.disclaimer : undefined,
      region: raw.region && typeof raw.region === "object" ? raw.region as Region : fallbackRegions.find((item) => item.id === regionId) || fallbackRegions[0],
      variable, lead_day: leadDay,
      issued_at: typeof raw.forecast_time === "string" ? raw.forecast_time : typeof raw.issued_at === "string" ? raw.issued_at : null,
      valid_at: typeof raw.valid_time === "string" ? raw.valid_time : typeof raw.valid_at === "string" ? raw.valid_at : null,
      risk: {
        level: typeof raw.risk_level === "string" ? raw.risk_level : typeof legacy?.level === "string" ? legacy.level : "unavailable",
        probability: live && candidate !== null && candidate >= 0 && candidate <= 1 ? candidate : null,
        summary: typeof raw.headline === "string" ? raw.headline : typeof legacy?.summary === "string" ? legacy.summary : "Forecast risk is unavailable.",
        possible_failure_modes: modes(raw.failure_modes || legacy?.possible_failure_modes),
      },
      explanation: typeof raw.explanation === "string" ? raw.explanation : undefined,
      evidence: drivers.map((item) => ({ title: String(item.label || item.title || "Signal"), detail: String(item.detail || "") })),
      historical_cases: Array.isArray(raw.historical_cases) ? raw.historical_cases : [],
      model: { status: live ? "published" : "not_trained", version: typeof raw.model_version === "string" ? raw.model_version : null },
      source: raw.source && (typeof raw.source === "string" || typeof raw.source === "object") ? raw.source as RiskResult["source"] : null,
      provenance: raw.provenance && typeof raw.provenance === "object" ? raw.provenance as Record<string, unknown> : null,
      forecast_value: live && typeof raw.forecast_value === "number" ? raw.forecast_value : null,
      error_threshold: live && typeof raw.error_threshold === "number" ? raw.error_threshold : null,
      predicted_error_p10: live && typeof raw.predicted_error_p10 === "number" ? raw.predicted_error_p10 : null,
      predicted_error_p90: live && typeof raw.predicted_error_p90 === "number" ? raw.predicted_error_p90 : null,
    }};
  } catch { return { data: fallbackRisk(regionId, variable, leadDay), connected: false }; }
}
export async function getVerification(signal?: AbortSignal): Promise<{ data: Verification; connected: boolean }> {
  try {
    const data = await request<Verification>("/v1/verification", signal);
    if (!data.summary || !Array.isArray(data.cases)) throw new Error("Invalid verification response");
    return { data, connected: true };
  } catch { return { data: fallbackVerification, connected: false }; }
}
export async function getSavedLocations(token: string): Promise<Region[]> {
  const data = await request<{ locations: Region[] }>("/v1/me/saved-locations", undefined, { headers: { Authorization: "Bearer " + token } });
  return data.locations;
}
export async function saveLocation(regionId: string, token: string): Promise<void> {
  await request("/v1/me/saved-locations", undefined, { method: "POST", headers: { Authorization: "Bearer " + token, "Content-Type": "application/json" }, body: JSON.stringify({ region_id: regionId }) });
}
export async function deleteSavedLocation(regionId: string, token: string): Promise<void> {
  await request("/v1/me/saved-locations/" + encodeURIComponent(regionId), undefined, { method: "DELETE", headers: { Authorization: "Bearer " + token } });
}

export async function getModelStatus(signal?: AbortSignal): Promise<{ data: ModelStatus; connected: boolean }> {
  try {
    const data = await request<ModelStatus>("/v1/models/status", signal);
    if (typeof data.status !== "string") throw new Error("Invalid model status response");
    return { data, connected: true };
  } catch {
    return { data: { status: "unavailable", active_model_version: null, message: "Model status cannot be reached." }, connected: false };
  }
}
