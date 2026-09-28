"use client";

import { useEffect, useState } from "react";
import { AlertCircle, ArrowUpRight, CloudRain, Info, MapPin, RefreshCw } from "lucide-react";
import Link from "next/link";
import { fallbackCoverage, getCoverage, getRisk } from "@/lib/api";
import type { Coverage, RiskResult, Variable } from "@/lib/types";

const variableLabels: Record<Variable, string> = { rainfall: "Rainfall", temperature: "Temperature", wind: "Wind" };

export function Dashboard() {
  const [coverage, setCoverage] = useState<Coverage>(fallbackCoverage);
  const [regionId, setRegionId] = useState("mumbai");
  const [variable, setVariable] = useState<Variable>("rainfall");
  const [leadDay, setLeadDay] = useState(4);
  const [result, setResult] = useState<RiskResult | null>(null);
  const [connected, setConnected] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const controller = new AbortController();
    getCoverage(controller.signal).then(({ data, connected: ready }) => {
      if (controller.signal.aborted) return;
      setCoverage(data);
      setConnected(ready);
      if (data.regions.length && !data.regions.some((region) => region.id === regionId)) setRegionId(data.regions[0].id);
    });
    return () => controller.abort();
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    getRisk(regionId, variable, leadDay, controller.signal).then(({ data, connected: ready }) => {
      if (controller.signal.aborted) return;
      setResult(data);
      setConnected(ready);
      setLoading(false);
    });
    return () => controller.abort();
  }, [regionId, variable, leadDay]);

  const region = coverage.regions.find((entry) => entry.id === regionId) || coverage.regions[0];
  const title = result?.region?.name || region?.name || "Selected location";
  const modes = result?.risk?.possible_failure_modes || [];
  const evidence = result?.evidence || [];

  return <>
    <div className="notice" role="status"><AlertCircle size={18} /><div><strong>{result?.mode === "live" ? "Published model result" : "Demonstration experience"}</strong>{result?.mode === "live" ? "This estimate is based on a published model run. Check its source and valid time before use." : "FBIE does not yet have a trained or validated risk model. Scenarios below are illustrative and must not be used as weather advice."} {connected ? "The API is connected." : "The API is unavailable, so a local demo scenario is shown."}</div></div>
    <div className="dashboard-layout"><aside className="control-panel" aria-label="Dashboard filters"><span className="panel-eyebrow">YOUR VIEW</span><h2>Explore a forecast</h2><div className="field"><label htmlFor="region">Location</label><select id="region" value={regionId} onChange={(event) => { setLoading(true); setRegionId(event.target.value); }}>{coverage.regions.map((entry) => <option value={entry.id} key={entry.id}>{entry.name}{entry.state ? `, ${entry.state}` : ""}</option>)}</select></div><div className="field"><label>Weather variable</label><div className="variable-buttons" role="group" aria-label="Weather variable">{coverage.variables.map(({ id, label }) => <button key={id} type="button" className={variable === id ? "active" : ""} aria-pressed={variable === id} onClick={() => { setLoading(true); setVariable(id); }}>{label || variableLabels[id]}</button>)}</div></div><div className="field"><label>Forecast lead day</label><div className="lead-grid" role="group" aria-label="Forecast lead day">{coverage.lead_days.map((day) => <button key={day} type="button" className={leadDay === day ? "active" : ""} aria-pressed={leadDay === day} onClick={() => { setLoading(true); setLeadDay(day); }}>D{day}</button>)}</div></div><div className="control-note">Lead day is the number of days after a forecast is issued. Longer lead times often involve more uncertainty, but risk must be measured for each situation.</div></aside>
      <div className="result-stack"><section className="result-panel" aria-live="polite"><div className="result-top"><div><span className="panel-eyebrow">SELECTED SCENARIO</span><h2>{title}</h2><p><MapPin size={12} style={{ verticalAlign: "middle" }} /> {result?.region?.state || region?.state || "India"} · {variableLabels[variable]} · Day {leadDay}</p></div><span className="mode-badge">{result?.mode === "live" ? "Published result" : "Demo scenario"}</span></div><div className="scenario-card"><div><span className="panel-eyebrow">A POSSIBLE FAILURE TO EXPLORE</span><h3>{loading ? "Loading the scenario…" : result?.risk?.summary || "Explore how this forecast could fail."}</h3><p>{result?.risk?.probability != null ? `Estimated risk: ${Math.round(result.risk.probability * 100)}%.` : "A risk percentage will appear only after a model is trained and validated."}</p></div><div className="scenario-gauge"><span>{result?.risk?.probability != null ? <>{Math.round(result.risk.probability * 100)}%<br />BUST RISK</> : <>NO MEASURED<br />RISK YET</>}</span></div></div><div className="region-strip" aria-label="Quick location selection">{coverage.regions.slice(0, 8).map((entry) => <button type="button" key={entry.id} className={entry.id === regionId ? "active" : ""} onClick={() => { setLoading(true); setRegionId(entry.id); }}><b>{entry.name}</b><small>{entry.state || "India"}</small></button>)}</div></section>
      <div className="detail-grid"><section className="info-panel"><span className="panel-eyebrow">HOW IT COULD FAIL</span><h3>Potential failure modes</h3><ul className="mode-list">{modes.map((mode, index) => <li key={`${mode}-${index}`}>{mode}</li>)}{!modes.length && <li>Failure modes will appear here when data is available.</li>}</ul></section><section className="info-panel"><span className="panel-eyebrow">WHAT WOULD SUPPORT IT</span><h3>Evidence to inspect</h3><ul className="evidence-list">{evidence.map((item, index) => <li key={`${item.title}-${index}`}><strong>{item.title}</strong><p>{item.detail}</p></li>)}{!evidence.length && <li><strong>Evidence pending</strong><p>Source data and model signals have not been added yet.</p></li>}</ul></section></div><div className="notice"><Info size={18} /><div><strong>What comes next</strong>Live forecast data, measured risk, and verified historical comparisons will be published after data ingestion and scientific evaluation. <Link href="/methodology" style={{ textDecoration: "underline", fontWeight: 700 }}>See the plan <ArrowUpRight size={12} style={{ verticalAlign: "middle" }} /></Link></div></div></div></div>
  </>;
}
