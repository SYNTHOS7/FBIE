import type { Metadata } from "next";
import "./globals.css";
import { Header, Footer } from "@/components/Brand";

export const metadata: Metadata = {
  title: "FBIE — Know where your forecast could go wrong",
  description: "Explore how weather forecasts can fail, why it matters, and what the evidence says. FBIE measures and explains rainfall forecast reliability where published results are available.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body><Header /><main>{children}</main><Footer /></body></html>;
}
