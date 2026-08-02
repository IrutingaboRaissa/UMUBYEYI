"use client";

import { useState } from "react";
import { createClient } from "@/lib/supabase/client";

// Landing page for the link in Supabase's password-reset email. Supabase's redirect
// already exchanges the recovery token for a session before this renders, so submitting
// here just needs to call updateUser with the new password.
export default function ResetPasswordPage() {
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const { error: err } = await createClient().auth.updateUser({ password });
      if (err) throw err;
      setDone(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Habaye ikibazo · Something went wrong");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="hero">
      <div className="hero-content">
        <h1>Shyiraho ijambo ry&apos;ibanga rishya</h1>
        <p className="leadEn">Set a new password</p>
        {done ? (
          <p className="disc" style={{ marginTop: 16 }}>
            Ijambo ry&apos;ibanga ryahinduwe. Ushobora gusubira muri Umubyeyi nonaha.
            <br />
            Password updated. You can return to Umubyeyi now.
          </p>
        ) : (
          <form onSubmit={submit} style={{ display: "flex", flexDirection: "column", gap: 10, marginTop: 20, maxWidth: 320, marginLeft: "auto", marginRight: "auto" }}>
            <input
              className="thread-rename-input"
              type="password"
              required
              minLength={6}
              autoComplete="new-password"
              placeholder="Ijambo ry'ibanga rishya · New password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
            {error && <div style={{ color: "#b23a48" }}>{error}</div>}
            <button className="btn btn-primary hero-cta" type="submit" disabled={busy}>
              {busy ? "Turimo…" : "Bika · Save"}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
