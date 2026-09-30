import type { Metadata } from "next";
import { Dashboard } from "@/components/Dashboard";

export const metadata: Metadata = { title: "Explore forecast reliability | FBIE", description: "Explore an illustrative FBIE forecast reliability scenario by location, weather variable, and forecast day." };

export default function ExplorePage() {
  return <><section className="page-top"><div className="page-shell"><span className="kicker">EXPLORE FBIE</span><h1>See where a forecast <em>could fail.</em></h1><p>Choose a place, weather variable, and day. Published estimates appear where validated forecast runs are available. Other selections are explicitly labelled as demonstrations.</p></div></section><div className="page-body page-shell"><Dashboard /></div></>;
}
