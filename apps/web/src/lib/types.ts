export type Variable = "rainfall" | "temperature" | "wind";

export interface Region {
  id: string;
  name: string;
  state?: string;
  lat?: number;
  lon?: number;
}

export interface Coverage {
  mode: "demo" | "live";
  disclaimer?: string;
  generated_at?: string;
  regions: Region[];
  variables: Array<{ id: Variable; label: string }>;
  lead_days: number[];
}

export interface Evidence {
  title: string;
  detail: string;
}

export interface RiskResult {
  mode: "demo" | "live";
  disclaimer?: string;
  region: Region;
  variable: Variable;
  lead_day: number;
  issued_at?: string;
  valid_at?: string;
  risk: {
    level: string;
    probability: number | null;
    summary: string;
    possible_failure_modes: string[];
  };
  evidence: Evidence[];
  historical_cases: unknown[];
  model?: { status: string; version: string | null };
  data_freshness?: { status: string };
}

export interface Verification {
  mode: "demo" | "live";
  disclaimer?: string;
  summary: { verified_predictions: number; skill: number | null };
  cases: Array<{
    id: string;
    region_name: string;
    variable: string;
    forecast_date: string;
    observed_date?: string;
    predicted_risk?: number | null;
    outcome: string;
    summary: string;
  }>;
}
