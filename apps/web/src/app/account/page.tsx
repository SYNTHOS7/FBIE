import type { Metadata } from "next";
import { AccountView } from "@/components/AccountView";
export const metadata: Metadata = { title: "Account | FBIE", description: "Sign in and manage saved forecast locations." };
export default function AccountPage() { return <><section className="page-top"><div className="page-shell"><span className="kicker">YOUR PLACES</span><h1>Keep an eye on the places that <em>matter.</em></h1><p>Save locations and return to their forecast reliability view quickly.</p></div></section><div className="page-body page-shell"><AccountView /></div></>; }
