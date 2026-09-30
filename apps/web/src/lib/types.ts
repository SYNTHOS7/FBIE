export type Variable = "rainfall" | "temperature" | "wind";
export interface Region { id: string; name: string; state?: string; latitude?: number; longitude?: number }
export interface Coverage {
  mode: "demo" | "live"; disclaimer?: string; latest_run?: string | null;
  regions: Region[]; variables: Array<{ id: Variable; label: string; unit?: string }>; lead_days: number[];
  operational_coverage?: Array<{ region_id?: string; variable?: Variable; lead_day?: number }>;
}
export interface Evidence { title: string; detail: string }
export interface FailureMode { name: string; probability: number | null }
export interface RiskResult {
  id?: string; mode: "demo" | "live"; disclaimer?: string; region: Region; variable: Variable; lead_day: number;
  issued_at?: string | null; valid_at?: string | null;
  risk: { level: string; probability: number | null; summary: string; possible_failure_modes: FailureMode[] };
  explanation?: string; evidence: Evidence[]; historical_cases: unknown[];
  model?: { status: string; version: string | null };
  source?: { name?: string; type?: string; retrieved_at?: string | null } | string | null;
  provenance?: Record<string, unknown> | null;
  forecast_value?: number | null; error_threshold?: number | null;
  predicted_error_p10?: number | null; predicted_error_p90?: number | null;
}
export interface VerificationCase {
  id: string; region_name: string; variable: string; forecast_date: string; observed_date?: string;
  predicted_risk?: number | null; outcome: string; summary: string; reference_kind?: string | null;
}
export interface CalibrationBin { lower: number; upper: number; count: number; mean_probability: number; observed_rate: number }
export interface VerificationSummary {
  verified_predictions: number; skill: number | null; calibration?: number | null;
  brier_score?: number | null; mean_predicted_risk?: number | null;
  bust_rate?: number | null; calibration_bins?: CalibrationBin[];
  reference_kind?: string | null;
}
export interface Verification {
  mode: "demo" | "live"; disclaimer?: string; reference_kind?: string | null;
  summary: VerificationSummary;
  cases: VerificationCase[];
}

export interface ModelStatus {
  status: string;
  active_model_version: string | null;
  model_kind?: string | null;
  training_period?: { through?: string | null } | null;
  evaluation?: Record<string, unknown> | null;
  latest_publication?: string | null;
  message?: string | null;
}
