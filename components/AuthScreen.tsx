"use client";

import { useState } from "react";
import { createClient } from "@/lib/supabase/client";
import MotherBabyMark from "@/components/MotherBabyMark";

type Mode = "signIn" | "signUp" | "forgotPassword";

// Runs before the language picker in ChatApp, so copy is hardcoded side-by-side
// (Kinyarwanda · English) rather than going through useLanguage()/tr() -- same
// precedent as ChatApp.tsx's own pre-language-choice screen.
export default function AuthScreen() {
  const [mode, setMode] = useState<Mode>("signIn");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    setNotice("");
    const supabase = createClient();
    try {
      if (mode === "forgotPassword") {
        const { error: err } = await supabase.auth.resetPasswordForEmail(email, {
          redirectTo: `${window.location.origin}/auth/reset`,
        });
        if (err) throw err;
        setNotice("Reba imeyili yawe kugira ngo uhindure ijambo ry'ibanga · Check your email for a reset link.");
      } else if (mode === "signUp") {
        const { error: err } = await supabase.auth.signUp({ email, password });
        if (err) throw err;
        setNotice("Konti yaremwe. Ushobora kwinjira nonaha · Account created. You can now log in.");
        setMode("signIn");
      } else {
        const { error: err } = await supabase.auth.signInWithPassword({ email, password });
        if (err) throw err;
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Habaye ikibazo · Something went wrong");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="hero">
      <div className="hero-visual"><MotherBabyMark /></div>
      <div className="hero-content">
        <h1>Muraho, mama.</h1>
        <p className="lead">
          {mode === "signUp"
            ? "Kora konti kugira ngo ibiganiro n'aho ugeze bibikwe neza."
            : mode === "forgotPassword"
              ? "Injiza imeyili yawe kugira ngo uhindure ijambo ry'ibanga."
              : "Injira kugira ngo ubone ibiganiro n'aho ugeze byawe."}
        </p>
        <p className="leadEn">
          {mode === "signUp"
            ? "Create an account so your chats and progress are saved to you."
            : mode === "forgotPassword"
              ? "Enter your email to reset your password."
              : "Log in to see your chats and progress."}
        </p>

        <form onSubmit={submit} style={{ display: "flex", flexDirection: "column", gap: 10, marginTop: 20, maxWidth: 320, marginLeft: "auto", marginRight: "auto" }}>
          <input
            className="thread-rename-input"
            type="email"
            required
            autoComplete="email"
            placeholder="Imeyili · Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
          {mode !== "forgotPassword" && (
            <input
              className="thread-rename-input"
              type="password"
              required
              minLength={6}
              autoComplete={mode === "signUp" ? "new-password" : "current-password"}
              placeholder="Ijambo ry'ibanga · Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          )}
          {error && <div style={{ color: "#b23a48" }}>{error}</div>}
          {notice && <div className="disc">{notice}</div>}
          <button className="btn btn-primary hero-cta" type="submit" disabled={busy}>
            {busy
              ? "Turimo…"
              : mode === "signUp" ? "Kwiyandikisha · Sign up"
                : mode === "forgotPassword" ? "Ohereza · Send reset link"
                  : "Injira · Log in"}
          </button>
        </form>

        <div style={{ marginTop: 16, display: "flex", gap: 10, justifyContent: "center", flexWrap: "wrap" }}>
          {mode !== "signIn" && (
            <button className="btn btn-sm" onClick={() => { setMode("signIn"); setError(""); setNotice(""); }}>
              Injira · Log in
            </button>
          )}
          {mode !== "signUp" && (
            <button className="btn btn-sm" onClick={() => { setMode("signUp"); setError(""); setNotice(""); }}>
              Kwiyandikisha · Sign up
            </button>
          )}
          {mode !== "forgotPassword" && (
            <button className="btn btn-sm" onClick={() => { setMode("forgotPassword"); setError(""); setNotice(""); }}>
              Wibagiwe ijambo ry&apos;ibanga? · Forgot password?
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
