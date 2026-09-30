"use client";

import { useEffect, useState } from "react";
import { Archive, ArrowUpRight, ShieldCheck } from "lucide-react";
import Link from "next/link";
import { fallbackVerification, getVerification } from "@/lib/api";
import type { Verification, VerificationSummary } from "@/lib/types";

const MIN_METRIC_CASES = 100;
const MIN_BIN_CASES = 10;

function referenceLabel(kind?: string | null) {
  if (!kind) return "Reference source not specified";
  if (/era5|reanalysis/i.test(kind)) return "ERA5 reanalysis proxy";
  if (/observation/i.test(kind)) return "Direct observations";
  if (kind === "mixed") return "Mixed references";
  return "Reference: " + kind.replaceAll("_", " ");
}
function percent(value: number) { return Math.round(value * 100) + "%"; }
function utcDay(value: string) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleDateString("en-IN", {
    day: "numeric", month: "short", year: "numeric", timeZone: "UTC",
  });
}
function bounded(value: unknown): value is number { return typeof value === "number" && Number.isFinite(value) && value >= 0 && value <= 1; }
function firstRate(summary: VerificationSummary) {
  const value = summary.bust_rate;
  return bounded(value) ? value : null;
}

export function VerificationView() {
  const [verification, setVerification] = useState<Verification>(fallbackVerification);
  const [connected, setConnected] = useState(false);
  useEffect(() => {
    const controller = new AbortController();
    getVerification(controller.signal).then(({ data, connected }) => {
      if (!controller.signal.aborted) { setVerification(data); setConnected(connected); }
    });
    return () => controller.abort();
  }, []);
  const summary = verification.summary;
  const count = summary.verified_predictions;
  const enough = count >= MIN_METRIC_CASES;
  const rate = firstRate(summary);
  const brier = typeof summary.brier_score === "number" && Number.isFinite(summary.brier_score) ? summary.brier_score : null;
  const meanRisk = bounded(summary.mean_predicted_risk) ? summary.mean_predicted_risk : null;
  const metricsAvailable = verification.mode === "live" && enough && brier !== null && meanRisk !== null && rate !== null;
  const bins = metricsAvailable ? (summary.calibration_bins || []).filter((bin) =>
    bin.count >= MIN_BIN_CASES && bounded(bin.mean_probability) && bounded(bin.observed_rate)
  ) : [];
  const metricReference = summary.reference_kind || verification.reference_kind;
  return <>
    <div className="notice" role="status"><ShieldCheck size={18} /><div><strong>{count ? "Post-publication comparisons available" : "Verification status"}</strong>{verification.disclaimer || (count ? "Published forecasts are compared after their valid dates. Each case identifies its reference data." : "Published forecasts and reference data are being prepared.")} {connected ? "" : "The API is unavailable."}</div></div>
    {count > 0 && <div className="verification-summary"><div><small>Compared published forecasts</small><strong>{count.toLocaleString("en-IN")}</strong></div><div><small>Reference data</small><strong>{referenceLabel(metricReference)}</strong></div><div><small>Measured performance</small><strong>{metricsAvailable ? "Available" : "Awaiting enough cases"}</strong></div></div>}
    {count > 0 && <section className="info-panel verification-metrics"><span className="panel-eyebrow">AFTER THE FORECAST</span><h2>How well did risk estimates hold up?</h2>{metricsAvailable ? <>
      <p className="verification-context">Scores below use {count.toLocaleString("en-IN")} published predictions after outcomes became available. Reference: {referenceLabel(metricReference).toLowerCase()}. Lower Brier score is better; predicted and observed rates should be close over many cases.</p>
      <div className="metrics-grid"><div><small>Brier score</small><strong>{brier.toFixed(3)}</strong></div><div><small>Mean predicted bust risk</small><strong>{percent(meanRisk)}</strong></div><div><small>Observed bust rate</small><strong>{percent(rate)}</strong></div></div>
      {bins.length > 0 && <div className="calibration-section"><h3>Calibration by risk range</h3><p>Each row compares the average forecast risk with the share of cases that exceeded the error threshold.</p><div className="calibration-list">{bins.map((bin, index) => <div className="calibration-row" key={index}><strong>{percent(bin.lower)}–{percent(bin.upper)}</strong><div className="calibration-bars" aria-hidden="true"><i style={{ width: percent(bin.mean_probability) }} /><b style={{ width: percent(bin.observed_rate) }} /></div><span>Predicted {percent(bin.mean_probability)} · observed {percent(bin.observed_rate)} · n={bin.count}</span></div>)}</div><div className="calibration-legend"><span>Predicted risk</span><span>Observed rate</span></div></div>}
      {!bins.length && <p className="metric-limitation">Calibration ranges will appear when each range has at least {MIN_BIN_CASES} cases.</p>}
    </> : <p className="metric-limitation">Aggregate accuracy and calibration need at least {MIN_METRIC_CASES} post-publication comparisons with complete outcomes. Individual cases below are visible sooner, but small samples are not presented as model performance.</p>}</section>}
    {verification.cases.length ? <div className="method-grid">{verification.cases.map((entry) => <article className="method-card verification-card" key={entry.id}><span className="method-num">{utcDay(entry.forecast_date)} · {entry.region_name}</span><h2>{entry.variable}</h2><p>{entry.summary}</p><div className="case-foot"><strong>{entry.outcome}</strong><span>{entry.predicted_risk != null && verification.mode === "live" ? percent(entry.predicted_risk) + " predicted risk" : "Risk unavailable"}</span></div><small className="reference-note">{referenceLabel(entry.reference_kind || verification.reference_kind)}</small></article>)}</div>
    : <div className="empty-panel"><Archive size={40} strokeWidth={1.5} /><h2>No historical comparisons yet.</h2><p>Archived forecasts need to be matched with reference data before performance can be measured. Reanalysis comparisons will be labelled as proxies; station observations will be identified separately.</p><Link href="/methodology" className="button button-outline" style={{ marginTop: 26 }}>See the methodology <ArrowUpRight size={17} /></Link></div>}
  </>;
}
