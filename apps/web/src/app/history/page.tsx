import type { Metadata } from "next";
import { VerificationView } from "@/components/VerificationView";

export const metadata: Metadata = { title: "Forecast verification | FBIE", description: "See how FBIE will compare published forecast warnings against observed weather outcomes." };

export default function HistoryPage() {
  return <><section className="page-top"><div className="page-shell"><span className="kicker">THE PUBLIC RECORD</span><h1>Did the warning <em>hold up?</em></h1><p>Forecast reliability should be tested in public. Compare archived forecasts with reference weather data. Each case identifies whether the reference is an observation or a reanalysis proxy.</p></div></section><div className="page-body page-shell"><VerificationView /></div></>;
}
