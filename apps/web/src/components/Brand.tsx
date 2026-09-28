import Link from "next/link";
import { ArrowUpRight, CloudSun } from "lucide-react";

export function Brand() {
  return <Link href="/" className="brand" aria-label="FBIE home"><span className="brand-mark"><CloudSun size={22} strokeWidth={2.3} /></span><span className="brand-word">FBIE<span className="brand-dot">.</span></span></Link>;
}

export function Header() {
  return <header className="site-header"><div className="nav-shell"><Brand /><nav className="main-nav" aria-label="Primary navigation"><Link href="/explore">Explore</Link><Link href="/history">Verification</Link><Link href="/methodology">How it works</Link></nav><Link href="/explore" className="nav-cta">Open dashboard <ArrowUpRight size={16} /></Link></div></header>;
}

export function Footer() {
  return <footer className="site-footer"><div className="footer-inner"><div><Brand /><p>Forecast reliability, made understandable.</p></div><div className="footer-links"><Link href="/explore">Explore</Link><Link href="/history">Verification</Link><Link href="/methodology">Methodology</Link></div><div className="footer-note">Built for clearer weather decisions in India.<br />Research prototype · Demo data is labelled.</div></div></footer>;
}
