"use client";

import { useEffect, useState, type FormEvent } from "react";
import Link from "next/link";
import { Bookmark, Mail, MapPin } from "lucide-react";
import type { Session } from "@supabase/supabase-js";
import { getSavedLocations, deleteSavedLocation } from "@/lib/api";
import { getSupabase } from "@/lib/supabase";
import type { Region } from "@/lib/types";

export function AccountView() {
  const supabase = getSupabase();
  const [session, setSession] = useState<Session | null>(null);
  const [places, setPlaces] = useState<Region[]>([]);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [action, setAction] = useState<"sign-in" | "sign-up">("sign-in");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  useEffect(() => {
    if (!supabase) return;
    supabase.auth.getSession().then(({ data }) => setSession(data.session));
    const { data } = supabase.auth.onAuthStateChange((_event, next) => setSession(next));
    return () => data.subscription.unsubscribe();
  }, [supabase]);
  useEffect(() => {
    if (!session) { setPlaces([]); return; }
    getSavedLocations(session.access_token).then(setPlaces).catch(() => setMessage("Saved places could not load. Check the API configuration."));
  }, [session]);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (!supabase) return;
    setBusy(true); setMessage("");
    const result = action === "sign-in" ? await supabase.auth.signInWithPassword({ email, password }) : await supabase.auth.signUp({ email, password });
    setBusy(false);
    if (result.error) setMessage(result.error.message);
    else if (action === "sign-up" && !result.data.session) setMessage("Account created. Check your email to confirm your address, then sign in.");
    else setMessage(action === "sign-in" ? "Signed in." : "Account created.");
  }
  async function remove(id: string) {
    if (!session) return;
    try { await deleteSavedLocation(id, session.access_token); setPlaces((current) => current.filter((entry) => entry.id !== id)); setMessage("Place removed."); }
    catch { setMessage("Could not remove this place. Try again."); }
  }
  if (!supabase) return <div className="empty-panel account-empty"><Mail size={40} /><h2>Accounts are not connected yet.</h2><p>Account sign-in is being set up. You can still explore forecasts without an account.</p><Link className="button button-outline" href="/explore">Explore forecasts</Link></div>;
  if (session) return <div className="account-layout"><section className="info-panel"><span className="panel-eyebrow">YOUR ACCOUNT</span><h2>Signed in</h2><p>{session.user.email}</p><button className="save-place" type="button" onClick={async () => { await supabase.auth.signOut(); setMessage("Signed out."); }}>Sign out</button></section><section className="info-panel"><span className="panel-eyebrow">YOUR PLACES</span><h2>Saved locations</h2>{places.length ? <ul className="saved-list">{places.map((place) => <li key={place.id}><MapPin size={18} /><span><Link href={"/explore?region=" + encodeURIComponent(place.id)}><strong>{place.name}</strong><small>{place.state || "India"}</small></Link></span><button type="button" onClick={() => remove(place.id)}>Remove</button></li>)}</ul> : <div className="saved-empty"><Bookmark size={28} /><p>No places saved yet. Open the dashboard and select “Save this place.”</p></div>}<Link href="/explore" className="text-link">Explore forecasts →</Link></section>{message && <p role="status">{message}</p>}</div>;
  return <div className="account-layout"><section className="info-panel"><span className="panel-eyebrow">YOUR ACCOUNT</span><h2>Keep the places you follow close.</h2><p>Save locations for quick access. Forecast exploration stays public.</p></section><section className="info-panel"><div className="auth-switch"><button type="button" className={action === "sign-in" ? "active" : ""} onClick={() => { setAction("sign-in"); setMessage(""); }}>Sign in</button><button type="button" className={action === "sign-up" ? "active" : ""} onClick={() => { setAction("sign-up"); setMessage(""); }}>Create account</button></div><form className="auth-form" onSubmit={submit}><label htmlFor="auth-email">Email</label><input id="auth-email" type="email" autoComplete="email" required value={email} onChange={(event) => setEmail(event.target.value)} /><label htmlFor="auth-password">Password</label><input id="auth-password" type="password" autoComplete={action === "sign-in" ? "current-password" : "new-password"} minLength={6} required value={password} onChange={(event) => setPassword(event.target.value)} /><button type="submit" className="button button-primary" disabled={busy}>{busy ? "Please wait…" : action === "sign-in" ? "Sign in" : "Create account"}</button></form>{message && <p className="auth-message" role="status">{message}</p>}</section></div>;
}
