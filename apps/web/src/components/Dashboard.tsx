"use client";

import { useEffect, useState } from "react";
import { AlertCircle, ArrowUpRight, Bookmark, Clock3, Database, Info, MapPin } from "lucide-react";
import Link from "next/link";
import { fallbackCoverage, getCoverage, getRisk, saveLocation } from "@/lib/api";
import { getSupabase } from "@/lib/supabase";
import type { Coverage, RiskResult, Variable } from "@/lib/types";

const variableLabels: Record<Variable, string> = { rainfall: "Rainfall", temperature: "Temperature", wind: "Wind" };
const formatTime = (value?: string | null) => value ? new Date(value).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short", timeZone: "Asia/Kolkata" }) + " IST" : "Not available";
const percent = (value: number) => Math.round(value * 100) + "%";

export function Dashboard() {
  const [coverage, setCoverage] = useState<Coverage>(fallbackCoverage);
  const [regionId, setRegionId] = useState("mumbai");
  const [variable, setVariable] = useState<Variable>("rainfall");
  const [leadDay, setLeadDay] = useState(4);
  const [result, setResult] = useState<RiskResult | null>(null);
  const [connected, setConnected] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saveMessage, setSaveMessage] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    getCoverage(controller.signal).then(({ data }) => {
      if (controller.signal.aborted) return;
      setCoverage(data);
      const requestedRegion = new URLSearchParams(window.location.search).get("region"); if (requestedRegion && data.regions.some((region) => region.id === requestedRegion)) setRegionId(requestedRegion); else if (data.regions.length && !data.regions.some((region) => region.id === regionId)) setRegionId(data.regions[0].id);
      if (data.variables.length && !data.variables.some((entry) => entry.id === variable)) setVariable(data.variables[0].id);
      if (data.lead_days.length && !data.lead_days.includes(leadDay)) setLeadDay(data.lead_days[0]);
    });
    return () => controller.abort();
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    getRisk(regionId, variable, leadDay, controller.signal).then(({ data, connected: ready }) => {
      if (controller.signal.aborted) return;
      setResult(data); setConnected(ready); setLoading(false);
    });
    return () => controller.abort();
  }, [regionId, variable, leadDay]);

  async function saveSelected() {
    const supabase = getSupabase();
    if (!supabase) { setSaveMessage("Saving places is not available yet."); return; }
    const { data } = await supabase.auth.getSession();
    if (!data.session) { setSaveMessage("Sign in to save this place."); return; }
    try { await saveLocation(regionId, data.session.access_token); setSaveMessage("Place saved to your account."); }
    catch { setSaveMessage("Could not save this place right now. Please try again."); }
  }

  const region = coverage.regions.find((entry) => entry.id === regionId) || coverage.regions[0];
  const selected = loading ? null : result;
  const live = selected?.mode === "live";
  const probability = live ? selected?.risk.probability : null;
  const unit = coverage.variables.find((entry) => entry.id === variable)?.unit || "";
  const source = typeof selected?.source === "string" ? selected.source : selected?.source?.name;
  const modes = selected?.risk.possible_failure_modes || [];
  const evidence = selected?.evidence || [];
  const intervalAvailable = live && selected?.predicted_error_p10 != null && selected?.predicted_error_p90 != null;

  return <>
    <div className="notice" role="status"><AlertCircle size={18} /><div>
      <strong>{live ? "Published model result" : connected ? "Demonstration experience" : "Forecast service unavailable"}</strong>
      {live ? "This result is based on a published model run. Review the issue time, source, and limitations below." : connected ? selected?.disclaimer || "This selection has no measured forecast risk. All scenarios are illustrative." : "The forecast API could not be reached. This view contains no live weather guidance."}
    </div></div>
    <div className="dashboard-layout">
      <aside className="control-panel" aria-label="Dashboard filters">
        <span className="panel-eyebrow">YOUR VIEW</span><h2>Explore a forecast</h2>
        <div className="field"><label htmlFor="region">Location</label><select id="region" value={regionId} onChange={(event) => { setLoading(true); setRegionId(event.target.value); }}>{coverage.regions.map((entry) => <option value={entry.id} key={entry.id}>{entry.name}{entry.state ? ", " + entry.state : ""}</option>)}</select></div>
        <div className="field"><label>Weather variable</label><div className="variable-buttons" role="group" aria-label="Weather variable">{coverage.variables.map(({ id, label }) => <button key={id} type="button" className={variable === id ? "active" : ""} aria-pressed={variable === id} onClick={() => { setLoading(true); setVariable(id); }}>{label || variableLabels[id]}</button>)}</div></div>
        <div className="field"><label>Forecast lead day</label><div className="lead-grid" role="group" aria-label="Forecast lead day">{coverage.lead_days.map((day) => <button key={day} type="button" className={leadDay === day ? "active" : ""} aria-pressed={leadDay === day} onClick={() => { setLoading(true); setLeadDay(day); }}>D{day}</button>)}</div></div>
        <button type="button" className="save-place" onClick={saveSelected}><Bookmark size={16} /> Save this place</button>
        {saveMessage && <p className="save-message" role="status">{saveMessage} {saveMessage.includes("Sign in") && <Link href="/account">Open account</Link>}</p>}
        <div className="control-note">Lead day counts from when the forecast is issued. A longer lead time can mean more uncertainty, but the risk must be measured for each situation.</div>
      </aside>
      <div className="result-stack">
        <section className="result-panel" aria-live="polite">
          <div className="result-top"><div><span className="panel-eyebrow">SELECTED FORECAST</span><h2>{selected?.region.name || region?.name || "Selected place"}</h2><p><MapPin size={12} style={{ verticalAlign: "middle" }} /> {selected?.region.state || region?.state || "India"} · {variableLabels[variable]} · Day {leadDay}</p></div><span className="mode-badge">{live ? "Published" : "No live estimate"}</span></div>
          <div className="scenario-card"><div><span className="panel-eyebrow">{live ? "FORECAST RELIABILITY" : "WHAT FBIE WILL SHOW"}</span><h3>{loading ? "Loading forecast…" : selected?.risk.summary || "Forecast risk is unavailable."}</h3><p>{probability != null ? "Estimated chance of exceeding the defined error threshold: " + percent(probability) + "." : "No measured risk percentage is available for this selection."}</p></div><div className="scenario-gauge"><span>{probability != null ? <>{percent(probability)}<br />BUST RISK</> : <>NO MEASURED<br />RISK</>}</span></div></div>
          <div className="region-strip" aria-label="Quick location selection">{coverage.regions.slice(0, 8).map((entry) => <button type="button" key={entry.id} className={entry.id === regionId ? "active" : ""} onClick={() => { setLoading(true); setRegionId(entry.id); }}><b>{entry.name}</b><small>{entry.state || "India"}</small></button>)}</div>
        </section>

        {live && <section className="info-panel"><span className="panel-eyebrow">MEASURED FORECAST DETAIL</span><h3>What the estimate means</h3><div className="metrics-grid">
          <div><small>Forecast value</small><strong>{selected?.forecast_value != null ? selected.forecast_value + " " + unit : "Unavailable"}</strong></div>
          <div><small>Bust threshold</small><strong>{selected?.error_threshold != null ? selected.error_threshold + " " + unit : "Unavailable"}</strong></div>
          <div><small>Predicted error, p10–p90</small><strong>{intervalAvailable ? selected?.predicted_error_p10 + " to " + selected?.predicted_error_p90 + " " + unit : "Unavailable"}</strong></div>
        </div>{intervalAvailable && <p className="detail-note">The p10–p90 range covers the middle 80% of predicted errors. Negative values mean the observed value may be lower than forecast.</p>}</section>}

        <div className="detail-grid"><section className="info-panel"><span className="panel-eyebrow">{live ? "HOW IT COULD FAIL" : "RESEARCH ROADMAP"}</span><h3>{live ? "Potential failure modes" : "Example failure types"}</h3><ul className="mode-list">{modes.map((item, index) => <li key={item.name + index}>{item.name}{live && item.probability != null ? " · " + percent(item.probability) : ""}</li>)}{!modes.length && <li>No failure mode analysis is available.</li>}</ul></section>
        <section className="info-panel"><span className="panel-eyebrow">{live ? "SUPPORTING SIGNALS" : "FUTURE SIGNALS"}</span><h3>{live ? "Evidence to inspect" : "Signals to research"}</h3><ul className="evidence-list">{evidence.map((item, index) => <li key={item.title + index}><strong>{item.title}</strong><p>{item.detail}</p></li>)}{!evidence.length && <li><strong>No evidence yet</strong><p>Source data and model signals are unavailable for this selection.</p></li>}</ul></section></div>

        <section className="info-panel"><span className="panel-eyebrow">RESULT RECORD</span><h3>Source and timing</h3><div className="provenance-grid">
          <div><Clock3 size={16} /><span>Forecast issued</span><strong>{formatTime(selected?.issued_at)}</strong></div>
          <div><Clock3 size={16} /><span>Valid for</span><strong>{formatTime(selected?.valid_at)}</strong></div>
          <div><Database size={16} /><span>Forecast source</span><strong>{live ? source || "Unavailable" : "Illustrative scenario"}</strong></div>
          <div><Info size={16} /><span>Model version</span><strong>{live ? selected?.model?.version || "Unavailable" : "No validated model"}</strong></div>
        </div>{selected?.explanation && <p className="detail-note">{selected.explanation}</p>}
        {live && selected?.provenance && <details className="provenance-details"><summary>Technical provenance</summary><pre>{JSON.stringify(selected.provenance, null, 2)}</pre></details>}</section>
        <div className="notice"><Info size={18} /><div><strong>How to use this result</strong>Review the definition and evaluation of a forecast bust before acting on a risk estimate. <Link href="/methodology">Read the methodology <ArrowUpRight size={12} /></Link></div></div>
      </div>
    </div>
  </>;
}
