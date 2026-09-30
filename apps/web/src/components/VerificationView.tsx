"use client";

import { useEffect, useState } from "react";
import { Archive, ArrowUpRight, ShieldCheck } from "lucide-react";
import Link from "next/link";
import { fallbackVerification, getVerification } from "@/lib/api";
import type { Verification } from "@/lib/types";

function referenceLabel(kind?: string | null) {
  if (!kind) return "Reference source not specified";
  if (/era5|reanalysis/i.test(kind)) return "Compared with reanalysis (proxy)";
  if (/observation/i.test(kind)) return "Compared with observations";
  return "Reference: " + kind.replaceAll("_", " ");
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
  const count = verification.summary.verified_predictions;
  return <>
    <div className="notice" role="status"><ShieldCheck size={18} /><div><strong>{count ? "Historical comparisons available" : "Verification status"}</strong>{verification.disclaimer || (count ? "Each case identifies its reference data." : "Historical forecast and reference pairs are being prepared.")} {connected ? "" : "The API is unavailable."}</div></div>
    {count > 0 && <div className="verification-summary"><div><small>Compared forecasts</small><strong>{count.toLocaleString("en-IN")}</strong></div><div><small>Skill against baseline</small><strong>{verification.summary.skill != null ? verification.summary.skill.toFixed(2) : "Not published"}</strong></div><div><small>Reference data</small><strong>{referenceLabel(verification.reference_kind)}</strong></div></div>}
    {verification.cases.length ? <div className="method-grid">{verification.cases.map((entry) => <article className="method-card verification-card" key={entry.id}><span className="method-num">{entry.forecast_date} · {entry.region_name}</span><h2>{entry.variable}</h2><p>{entry.summary}</p><div className="case-foot"><strong>{entry.outcome}</strong><span>{entry.predicted_risk != null && verification.mode === "live" ? Math.round(entry.predicted_risk * 100) + "% predicted risk" : "Risk unavailable"}</span></div><small className="reference-note">{referenceLabel(entry.reference_kind || verification.reference_kind)}</small></article>)}</div>
    : <div className="empty-panel"><Archive size={40} strokeWidth={1.5} /><h2>No historical comparisons yet.</h2><p>Archived forecasts need to be matched with reference data before performance can be measured. Reanalysis comparisons will be labelled as proxies; station observations will be identified separately.</p><Link href="/methodology" className="button button-outline" style={{ marginTop: 26 }}>See the methodology <ArrowUpRight size={17} /></Link></div>}
  </>;
}
