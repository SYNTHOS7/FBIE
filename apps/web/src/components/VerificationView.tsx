"use client";

import { useEffect, useState } from "react";
import { Archive, ArrowUpRight, ShieldCheck } from "lucide-react";
import Link from "next/link";
import { fallbackVerification, getVerification } from "@/lib/api";
import type { Verification } from "@/lib/types";

export function VerificationView() {
  const [verification, setVerification] = useState<Verification>(fallbackVerification);
  const [connected, setConnected] = useState(false);
  useEffect(() => { const controller = new AbortController(); getVerification(controller.signal).then(({ data, connected }) => { if (!controller.signal.aborted) { setVerification(data); setConnected(connected); } }); return () => controller.abort(); }, []);
  return <><div className="notice"><ShieldCheck size={18} /><div><strong>Verification status</strong>{verification.disclaimer || "Historical forecast and observation pairs are being prepared."} {connected ? "The demo API is connected." : "Showing the local demo state."}</div></div>{verification.cases.length ? <div className="method-grid">{verification.cases.map((entry) => <article className="method-card" key={entry.id}><span className="method-num">{entry.forecast_date} · {entry.region_name}</span><h2>{entry.variable}</h2><p>{entry.summary}</p><strong>{entry.outcome}</strong></article>)}</div> : <div className="empty-panel"><Archive size={40} strokeWidth={1.5} /><h2>No verified forecasts yet.</h2><p>We need an archive of forecasts as originally issued, matching observations, and a defined failure threshold before we can claim performance. The first verified results will appear here.</p><Link href="/methodology" className="button button-outline" style={{ marginTop: 26 }}>See the methodology <ArrowUpRight size={17} /></Link></div>}</>;
}
