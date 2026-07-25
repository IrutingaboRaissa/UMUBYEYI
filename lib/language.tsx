"use client";

import { createContext, useContext, useEffect, useState, ReactNode } from "react";

export type Lang = "rw" | "en";
const LANG_KEY = "umubyeyi_lang_v1";

type LanguageCtx = { lang: Lang | null; ready: boolean; setLang: (l: Lang) => void };

const LanguageContext = createContext<LanguageCtx>({ lang: null, ready: false, setLang: () => {} });

// Whole-app language preference, chosen once on first launch (see the picker gate in
// ChatApp.tsx) and remembered locally -- not tied to whatever language a given chat message
// happens to be in, which the backend still auto-detects per message regardless of this.
export function LanguageProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Lang | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    try {
      const saved = localStorage.getItem(LANG_KEY);
      if (saved === "rw" || saved === "en") setLangState(saved);
    } catch { /* ignore */ }
    setReady(true);
  }, []);

  const setLang = (l: Lang) => {
    setLangState(l);
    try { localStorage.setItem(LANG_KEY, l); } catch { /* ignore */ }
  };

  return (
    <LanguageContext.Provider value={{ lang, ready, setLang }}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage() {
  return useContext(LanguageContext);
}

/** Pick between a Kinyarwanda and an English string for the active whole-app language.
 * Defaults to Kinyarwanda if somehow called before a preference is set. */
export function useT() {
  const { lang } = useLanguage();
  return (rw: string, en: string) => (lang === "en" ? en : rw);
}

/** Splits a "Kinyarwanda part · English part" string (the convention used throughout this
 * app's authored copy) on its first separator and returns the requested side. For data that's
 * still stored as one combined string (e.g. CHECKIN_FIELDS labels) rather than a [rw, en] pair. */
export function splitBi(combined: string): [string, string] {
  const idx = combined.indexOf(" · ");
  if (idx === -1) return [combined, combined];
  return [combined.slice(0, idx), combined.slice(idx + 3)];
}

/** Convenience hook combining splitBi() with the active language, for existing data that's
 * a single "rw · en" string (nav labels, field labels, option labels) rather than a tuple. */
export function useBi() {
  const { lang } = useLanguage();
  return (combined: string) => splitBi(combined)[lang === "en" ? 1 : 0];
}
