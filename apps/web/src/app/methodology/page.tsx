import type { Metadata } from "next";
import { ArrowUpRight } from "lucide-react";
import Link from "next/link";
import { MethodologyStatus } from "@/components/MethodologyStatus";

export const metadata: Metadata = { title: "How FBIE works | FBIE", description: "See FBIE's current research baseline, published-model status, data limits, and future research plan." };

const stages = [
  { number: "01", title: "Archive issued forecasts", body: "Keep forecast values, issue times, valid days, lead days, locations, and source run IDs. A training row must use only information available when that forecast was issued." },
  { number: "02", title: "Match a reference", body: "Align daily rainfall forecasts with the same place and time in reference data. ERA5 is a reanalysis proxy; direct rain-gauge observations are a separate, stronger reference when available." },
  { number: "03", title: "Define a rainfall bust", body: "Mark whether daily rainfall error exceeds a declared threshold. Keep that definition fixed before testing on later, untouched periods." },
  { number: "04", title: "Train the first baseline", body: "Estimate a smoothed historical bust rate for season, lead day, forecast amount band, and variable. Measure Brier score against a simpler historical-rate benchmark." },
  { number: "05", title: "Publish and compare", body: "Only approved prediction batches with source and model provenance appear as measured risk. Later, pair those warnings with reference outcomes and report aggregate performance." },
];

export default function MethodologyPage() {
  return <><section className="page-top"><div className="page-shell"><span className="kicker">HOW IT WORKS</span><h1>Trust comes from <em>being checked.</em></h1><p>FBIE separates research methods, published estimates, and historical outcomes. Each measured risk needs a source, a defined error threshold, and an evaluation record.</p></div></section>
    <div className="page-body page-shell"><MethodologyStatus />
      <div className="method-grid methodology-steps">{stages.map((stage) => <article className="method-card" key={stage.number}><span className="method-num">{stage.number} / 05</span><h2>{stage.title}</h2><p>{stage.body}</p></article>)}</div>
      <div className="method-long"><div><span className="kicker">CURRENT METHOD</span><h2>What the baseline can measure</h2></div><div><p>The first measurable target is daily rainfall amount error for selected Indian places and lead days. Its risk estimate is the chance of exceeding a declared rainfall error threshold, based on historical patterns in paired data.</p><p>The offline historical-rate baseline uses season, lead day, and forecast rainfall amount band. It does not compare multiple forecast models or track changes between successive forecast runs.</p><p>Reanalysis comparisons can help develop the method, but ERA5 is a proxy for the weather that occurred. Results using it are labelled separately from comparisons with direct observations.</p></div></div>
      <div className="method-long"><div><span className="kicker">RESEARCH ROADMAP</span><h2>What we want to add</h2></div><div><p>Forecast agreement, run-to-run movement, timing shifts, spatial rainfall displacement, historical analogues, and temperature and wind models are later research steps. Each needs suitable data and held-out evaluation before FBIE can claim it works.</p><p>Probability calibration and measured skill matter more than the number of algorithms. We publish a feature only after it improves decisions and its limits can be explained.</p></div></div>
      <div className="cta-section" style={{ marginBottom: 0 }}><div><span className="kicker">SEE THE RECORD</span><h2>Inspect a <em>forecast.</em></h2><p>Published results show their source and issue time. Unsupported selections show an explicit no-data state.</p></div><Link href="/explore" className="button button-light">Open dashboard <ArrowUpRight size={18} /></Link></div>
    </div></>;
}
