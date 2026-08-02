"use client";

import { useEffect, useState } from "react";
import type { Session } from "@supabase/supabase-js";
import { createClient } from "@/lib/supabase/client";
import AuthScreen from "@/components/AuthScreen";

// Gates the app behind a real Supabase account -- this is the actual, recoverable
// identity layer the defense panel asked for. The PIN lock in lib/lock.ts is a
// separate, secondary "quick-lock the screen" layer that sits underneath this, inside
// ChatApp itself, once a session exists.
export default function AuthGate({ children }: { children: React.ReactNode }) {
  // undefined = still checking; null = signed out; Session = signed in.
  const [session, setSession] = useState<Session | null | undefined>(undefined);

  useEffect(() => {
    const supabase = createClient();
    supabase.auth.getSession().then(({ data }) => setSession(data.session));
    const { data: listener } = supabase.auth.onAuthStateChange((_event, next) => {
      setSession(next);
    });
    return () => listener.subscription.unsubscribe();
  }, []);

  if (session === undefined) {
    return <div className="app-loading" aria-hidden />;
  }

  if (!session) {
    return <AuthScreen />;
  }

  return <>{children}</>;
}
