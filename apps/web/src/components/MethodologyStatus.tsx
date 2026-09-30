"use client";

import { useEffect, useState } from "react";
import { AlertCircle, CheckCircle2 } from "lucide-react";
import { getCoverage, getModelStatus } from "@/lib/api";
import type { Coverage, ModelStatus } from "@/lib/types";

export function MethodologyStatus() {
  const [coverage, setCoverage] = useState<Coverage | null>(null);
  const [model, setModel] = useState<ModelStatus | null>(null);
  const [reachable, setReachable] = useState<boolean | null>(null);
  useEffect(() => {
    const controller = new AbortController();
    Promise.all([getCoverage(controller.signal), getModelStatus(controller.signal)]).then(([coverageResult, modelResult]) => {
      if (controller.signal.aborted) return;
      setCoverage(coverageResult.data);
      setModel(modelResult.data);
      setReachable(coverageResult.connected && modelResult.connected);
    });
    return () => controller.abort();
  }, []);
  const count = coverage?.operational_coverage?.length || 0;
  const published = reachable && model?.status === "published" && count > 0;
  const variables = [...new Set((coverage?.operational_coverage || []).map((entry) => entry.variable).filter(Boolean))].join(", ");
  const latest = coverage?.latest_run ? new Date(coverage.latest_run).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short", timeZone: "Asia/Kolkata" }) + " IST" : null;
  return <>
    <div className="notice" role="status">{published ? <CheckCircle2 size={18} /> : <AlertCircle size={18} />}<div>
      <strong>{reachable === null ? "Checking publication status" : published ? "Published estimates available" : reachable ? "No published model and forecast coverage yet" : "Publication status unavailable"}</strong>
      {reachable === null ? "The current model and data coverage are loading." : published ? "The API reports a published model and " + count + " supported location, variable, and lead-day combinations. Open the dashboard for an individual result." : reachable ? "The offline rainfall historical-rate baseline is research code. The API has no approved, published estimates for users yet." : "The API cannot be reached. An unavailable status should not be read as a low-risk forecast."}
    </div></div>
    <div className="status-list methodology-live-status">
      <div className="status-row"><div><strong>Product interface</strong><p>Explore forecasts, inspect evidence, review historical comparisons, and save places when accounts are configured.</p></div><span>Available</span></div>
      <div className="status-row"><div><strong>Offline research baseline</strong><p>A transparent daily rainfall historical-rate method can be trained and evaluated on paired forecast and reference files. It does not itself make a live prediction.</p></div><span>Research code</span></div>
      <div className="status-row"><div><strong>Published forecast risk</strong><p>{published ? "Model " + model?.active_model_version + " · " + variables + (latest ? " · latest run " + latest : "") : "Only approved and published model batches appear as measured risk in the dashboard."}</p></div><span>{published ? "Published" : reachable ? "No data" : "Unknown"}</span></div>
      <div className="status-row"><div><strong>Historical comparisons</strong><p>Comparisons are shown on the verification page and name their reference data. ERA5 reanalysis is a proxy, not a rain-gauge observation.</p></div><span>See record</span></div>
    </div>
  </>;
}
