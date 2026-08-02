"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  AFFIRM, ApiWakingUpError, CHECKIN_FIELDS, CRISIS_LINE, MOOD_LABEL, MOOD_TIPS, STORE_CURRENT_KEY, TIPS,
  Thread, newThread, sendChat,
  generateTitle, optionLabel, optionValue, sendScreen, sortThreads, touchThread, ScreenResponse,
} from "@/lib/chat";
import {
  loadThreads, saveThread, deleteThread,
  loadMoodHistory, saveMoodEntry,
  saveCheckinEntry,
  saveConcernEntry,
} from "@/lib/supabase/data";
import { createClient } from "@/lib/supabase/client";
import EpdsAssessment from "@/components/EpdsAssessment";
import ProgressDashboard from "@/components/ProgressDashboard";
import HorizontalBarChart from "@/components/charts/HorizontalBarChart";
import Mark from "@/components/Mark";
import MotherBabyMark from "@/components/MotherBabyMark";
import { hasPin, setPin, verifyPin, removePin } from "@/lib/lock";
import { useT, useBi, useLanguage } from "@/lib/language";

type PinFormMode = "set" | "change" | "remove" | null;
type PinForm = { mode: PinFormMode; current: string; next: string; confirm: string; error: string };

// Real message content the mother could send as-is -- shown in whichever language is
// currently selected, same as everything else, so clicking one always matches what she'd
// actually type in that mode.
const EXAMPLE_PROMPTS_EN = ["I feel exhausted all the time", "I'm anxious about my baby",
  "I feel guilty as a mother", "I feel alone since giving birth"];
const EXAMPLE_PROMPTS_RW = ["Numva ndushye buri gihe", "Mfite impungenge ku mwana wanjye",
  "Numva mfite icyaha nk'umubyeyi", "Numva ndi wenyine kuva mbyara"];

type View = "chat" | "checkin" | "epds" | "progress" | "selfcare" | "about";

const NAV: { id: View; rw: string; en: string }[] = [
  { id: "chat", rw: "Ikiganiro", en: "Chat" },
  { id: "checkin", rw: "Isuzuma", en: "Check-in" },
  { id: "epds", rw: "Ikizamini cy'imibereho", en: "Wellness test" },
  { id: "progress", rw: "Aho ngeze", en: "Progress" },
  { id: "selfcare", rw: "Kwiyitaho", en: "Self-care" },
  { id: "about", rw: "Ibyerekeye", en: "About" },
];

export default function ChatApp() {
  const tr = useT();
  const bi = useBi();
  const { lang, ready: langReady, setLang } = useLanguage();
  const [consented, setConsented] = useState(false);
  const [uiReady, setUiReady] = useState(false);
  const [threads, setThreads] = useState<Thread[]>([]);
  const [currentId, setCurrentId] = useState("");
  const [draftThread, setDraftThread] = useState<Thread | null>(null);
  const [view, setView] = useState<View>("chat");
  const [panelOpen, setPanelOpen] = useState(false);
  const [input, setInput] = useState("");
  const [typing, setTyping] = useState(false);
  const [lastMeta, setLastMeta] = useState<{ lang?: string; mode?: string }>({});
  const [modal, setModal] = useState<"breathe" | "help" | "pin" | null>(null);
  const [menuThreadId, setMenuThreadId] = useState<string | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<{ id: string; title: string } | null>(null);
  const [locked, setLocked] = useState(false);
  const [pinEntry, setPinEntry] = useState("");
  const [pinError, setPinError] = useState("");
  const [pinForm, setPinForm] = useState<PinForm | null>(null);
  const [forgotConfirm, setForgotConfirm] = useState(false);
  const [pendingLockThreadId, setPendingLockThreadId] = useState<string | null>(null);
  const [pinPrompt, setPinPrompt] = useState<
    { purpose: "view" | "unlock"; threadId: string; entry: string; error: string } | null
  >(null);
  const [checkin, setCheckin] = useState<Record<string, string | number>>(() => {
    const initial: Record<string, string | number> = { Age: "" };
    for (const [key] of CHECKIN_FIELDS) initial[key] = "";
    return initial;
  });
  const [screenResult, setScreenResult] = useState<ScreenResponse | null>(null);
  const [screening, setScreening] = useState(false);
  const [screenError, setScreenError] = useState("");
  const [saveCheckinHistory, setSaveCheckinHistory] = useState(false);
  const [moodHistory, setMoodHistory] = useState<{ mood: string; date: string }[]>([]);
  // Entries dismissed from the Self-care "Recent" strip only -- the real history in
  // umubyeyi_moods_v1 (and therefore the Progress dashboard) is never touched by this.
  const [dismissedMoodDates, setDismissedMoodDates] = useState<string[]>([]);
  const [moodTip, setMoodTip] = useState<{ mood: string; en: string; rw: string } | null>(null);
  const lastMoodTipIndex = useRef<Record<string, number>>({});
  // Fixed, not rotated: "Asking for help is a sign of strength, not weakness."
  const welcomeQuote = AFFIRM[4];
  const bottomRef = useRef<HTMLDivElement>(null);
  const hydrated = useRef(false);
  const retriedTitles = useRef(false);

  useEffect(() => {
    if (hasPin()) setLocked(true);
    // The welcome screen is a deliberate landing page on a brand-new browser session --
    // it's shown the first time a tab opens and only ever dismissed by an explicit click
    // on "Start" (or the Home button). Within that same tab, a reload restores whichever
    // screen the mother was on instead of sending her back to the welcome page again --
    // sessionStorage (not localStorage) is what keeps that scoped to the current tab/session
    // rather than becoming a permanent skip-the-welcome-screen state. Her data underneath
    // (chats, EPDS results, moods, check-ins) is untouched either way.
    try {
      if (sessionStorage.getItem("umubyeyi_consented_v1") === "1") setConsented(true);
      const storedView = sessionStorage.getItem("umubyeyi_view_v1") as View | null;
      if (storedView && NAV.some((n) => n.id === storedView)) setView(storedView);
    } catch { /* ignore */ }
    try {
      setDismissedMoodDates(JSON.parse(localStorage.getItem("umubyeyi_moods_dismissed_v1") || "[]"));
    } catch { /* ignore */ }

    (async () => {
      const [{ threads: loaded, currentId: cid }, moods] = await Promise.all([
        loadThreads(),
        loadMoodHistory(),
      ]);
      setMoodHistory(moods);
      if (loaded.length) {
        setThreads(loaded);
        // Never resume directly into a locked thread on load -- the remembered "last open
        // chat" could be one the user locked since, and that must still require the PIN.
        const resumeTarget = loaded.find((t) => t.id === cid);
        if (resumeTarget?.locked) {
          const firstUnlocked = loaded.find((t) => !t.locked);
          if (firstUnlocked) {
            setCurrentId(firstUnlocked.id);
          } else {
            const t = newThread();
            setDraftThread(t);
            setCurrentId(t.id);
          }
        } else {
          setCurrentId(cid);
        }
      } else {
        const t = newThread();
        setDraftThread(t);
        setCurrentId(t.id);
      }
      hydrated.current = true;
      setUiReady(true);
    })();
  }, []);

  // Re-lock as soon as the tab is hidden (switched away, minimized, screen off) so a PIN
  // is required again on return -- protects everything (unlocked chats, EPDS results,
  // progress, self-care), not just the chats a mother remembered to lock individually.
  useEffect(() => {
    const onVisibility = () => {
      if (document.hidden && hasPin()) setLocked(true);
    };
    document.addEventListener("visibilitychange", onVisibility);
    return () => document.removeEventListener("visibilitychange", onVisibility);
  }, []);

  // Which thread is open is a pure per-device UI preference, so it's kept in localStorage
  // rather than synced to the account -- see lib/supabase/data.ts loadThreads().
  useEffect(() => {
    if (!hydrated.current) return;
    try { localStorage.setItem(STORE_CURRENT_KEY, currentId); } catch { /* ignore */ }
  }, [currentId]);

  useEffect(() => {
    if (!hydrated.current) return;
    try { sessionStorage.setItem("umubyeyi_consented_v1", consented ? "1" : "0"); } catch { /* ignore */ }
  }, [consented]);

  useEffect(() => {
    if (!hydrated.current) return;
    try { sessionStorage.setItem("umubyeyi_view_v1", view); } catch { /* ignore */ }
  }, [view]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [threads, typing, currentId]);

  // Self-heal thread titles that never got upgraded past the raw-truncated placeholder
  // (e.g. the Groq call failed the first time round). Runs once per session; never
  // touches a title the mother generated successfully or renamed herself.
  useEffect(() => {
    if (!hydrated.current || retriedTitles.current || !threads.length) return;
    retriedTitles.current = true;
    threads.forEach((t) => {
      const firstUser = t.msgs.find((m) => m.role === "user");
      const firstBot = t.msgs.find((m) => m.role === "bot");
      if (!firstUser || !firstBot) return;
      if (t.titleSource === "generated" || t.titleSource === "manual") return;
      const looksUnupgraded = t.titleSource === "fallback" || t.title === firstUser.text.slice(0, 40);
      if (!looksUnupgraded) return;
      generateTitle(firstUser.text, firstBot.text, firstBot.lang ?? "en").then((title) => {
        if (!title) return;
        const titled: Thread = { ...t, title, titleSource: "generated" };
        setThreads((prev) => prev.map((th) => (th.id === t.id ? titled : th)));
        saveThread(titled).catch((err) => console.error("Failed to save chat title", err));
      });
    });
  }, [threads]);

  const current = threads.find((t) => t.id === currentId)
    ?? (draftThread?.id === currentId ? draftThread : threads[0]);
  const checkinReady = checkin.Age !== "" && CHECKIN_FIELDS.every(([key]) => checkin[key] !== "");

  const setCurrent = useCallback((id: string) => {
    setCurrentId(id);
    setMenuThreadId(null);
    setPanelOpen(false);
  }, []);

  const updateThread = useCallback(async (updated: Thread) => {
    const touched = touchThread(updated);
    setThreads((prev) => sortThreads([touched, ...prev.filter((t) => t.id !== touched.id)]));
    try {
      await saveThread(touched);
    } catch (err) {
      console.error("Failed to save chat", err);
    }
    return touched;
  }, []);

  const handleSend = async (text: string) => {
    if (!text.trim() || typing || !current) return;
    const userMsg = text.trim();
    const isFirstMessage = !current.title;
    const t = { ...current, msgs: [...current.msgs, { role: "user" as const, text: userMsg }] };
    if (!t.title) {
      t.title = userMsg.slice(0, 40);
      t.titleSource = "fallback";
    }
    await updateThread(t);
    if (draftThread?.id === t.id) setDraftThread(null);
    setInput("");
    setTyping(true);

    try {
      const res = await sendChat(userMsg, null, current.msgs);
      const botMsg = {
        role: "bot" as const, text: res.answer, danger: res.danger, mode: res.mode, lang: res.language,
      };
      const withReply = { ...t, msgs: [...t.msgs, botMsg] };
      await updateThread(withReply);
      setLastMeta({ lang: res.language, mode: res.mode });
      if (res.concern_signal) {
        try {
          await saveConcernEntry({ score: res.concern_signal.score, level: res.concern_signal.level });
        } catch (err) { console.error("Failed to save concern signal", err); }
      }
      if (isFirstMessage) {
        generateTitle(userMsg, res.answer, res.language).then((title) => {
          if (!title) return;
          const titled: Thread = { ...withReply, title, titleSource: "generated" };
          setThreads((prev) => prev.map((th) => (th.id === t.id ? titled : th)));
          saveThread(titled).catch((err) => console.error("Failed to save chat title", err));
        });
      }
    } catch (err) {
      const fallbackText = err instanceof ApiWakingUpError
        ? "The assistant is just waking up - please try again in a moment. Umufasha araza kuboneka - ongera ugerageze mu kanya."
        : lastMeta.lang === "en"
          ? "Sorry, something went wrong. Please try again."
          : lastMeta.lang === "rw"
            ? "Mbabarira, hari ikibazo. Ongera ugerageze."
            : "Sorry, something went wrong. Mbabarira, hari ikibazo. Ongera ugerageze.";
      await updateThread({
        ...t,
        msgs: [...t.msgs, { role: "bot", text: fallbackText }],
      });
    } finally {
      setTyping(false);
    }
  };

  const startNewChat = () => {
    const t = newThread();
    setDraftThread(t);
    setCurrentId(t.id);
    setMenuThreadId(null);
    setPanelOpen(false);
    setView("chat");
  };

  const goToView = (v: View) => {
    setView(v);
    setPanelOpen(false);
  };

  const handleUnlock = async () => {
    const ok = await verifyPin(pinEntry);
    if (ok) {
      setLocked(false);
      setPinEntry("");
      setPinError("");
      setForgotConfirm(false);
    } else {
      setPinError(tr("Ntibihuye", "Incorrect PIN"));
      setPinEntry("");
    }
  };

  // Forgetting the local PIN no longer wipes anything -- the mother's data lives in her
  // Supabase account, not this device, so this just signs her out of the device. AuthGate's
  // onAuthStateChange listener unmounts ChatApp back to the sign-in screen once the session
  // clears, and everything re-loads from the account on her next sign-in.
  const handleForgotPin = async () => {
    removePin();
    setPinEntry("");
    setPinError("");
    setForgotConfirm(false);
    setModal(null);
    setPinForm(null);
    try {
      await createClient().auth.signOut();
    } catch (err) {
      console.error("Failed to sign out", err);
    }
  };

  const openPinModal = () => {
    setPinForm(hasPin()
      ? { mode: null, current: "", next: "", confirm: "", error: "" }
      : { mode: "set", current: "", next: "", confirm: "", error: "" });
    setModal("pin");
  };

  // Locking a chat never needs the PIN -- like locking a door from outside without a key.
  // If no PIN exists yet at all, there's nothing to gate an unlock with, so send the user to
  // set one first; the thread gets locked automatically the moment that PIN is created.
  const lockThread = (id: string) => {
    if (!hasPin()) {
      setPendingLockThreadId(id);
      setPinForm({ mode: "set", current: "", next: "", confirm: "", error: "" });
      setModal("pin");
      return;
    }
    const target = threads.find((t) => t.id === id);
    setThreads((prev) => prev.map((t) => (t.id === id ? { ...t, locked: true } : t)));
    if (target) saveThread({ ...target, locked: true }).catch((err) => console.error("Failed to lock chat", err));
    setMenuThreadId(null);
    // If the chat being locked is the one currently open, leave its messages immediately --
    // otherwise "locking" it would do nothing visible until the user happened to navigate away.
    if (currentId === id) {
      const next = threads.find((t) => t.id !== id && !t.locked);
      if (next) {
        setCurrentId(next.id);
      } else {
        const t = newThread();
        setDraftThread(t);
        setCurrentId(t.id);
      }
    }
  };

  const requestUnlockThread = (id: string) => {
    setMenuThreadId(null);
    setPinPrompt({ purpose: "unlock", threadId: id, entry: "", error: "" });
  };

  const requestViewLockedThread = (id: string) => {
    setPinPrompt({ purpose: "view", threadId: id, entry: "", error: "" });
  };

  const openThreadRow = (t: Thread) => {
    if (t.locked) {
      requestViewLockedThread(t.id);
    } else {
      setCurrent(t.id);
      setView("chat");
    }
  };

  const submitPinPrompt = async () => {
    if (!pinPrompt) return;
    const ok = await verifyPin(pinPrompt.entry);
    if (!ok) {
      setPinPrompt({ ...pinPrompt, error: tr("Ntibihuye", "Incorrect PIN"), entry: "" });
      return;
    }
    if (pinPrompt.purpose === "unlock") {
      const target = threads.find((t) => t.id === pinPrompt.threadId);
      setThreads((prev) => prev.map((t) => (t.id === pinPrompt.threadId ? { ...t, locked: false } : t)));
      if (target) saveThread({ ...target, locked: false }).catch((err) => console.error("Failed to unlock chat", err));
    } else {
      setCurrent(pinPrompt.threadId);
      setView("chat");
    }
    setPinPrompt(null);
  };

  const submitPinForm = async () => {
    if (!pinForm) return;
    const { mode, current, next, confirm } = pinForm;
    if (mode === "remove") {
      if (!(await verifyPin(current))) {
        setPinForm({ ...pinForm, error: tr("Ntibihuye", "Incorrect PIN") });
        return;
      }
      removePin();
      setModal(null);
      setPinForm(null);
      return;
    }
    if (mode === "change" && !(await verifyPin(current))) {
      setPinForm({ ...pinForm, error: tr("Ntibihuye", "Incorrect PIN") });
      return;
    }
    if (!/^\d{4,6}$/.test(next)) {
      setPinForm({ ...pinForm, error: tr("Koresha imibare 4-6", "Use 4-6 digits") });
      return;
    }
    if (next !== confirm) {
      setPinForm({ ...pinForm, error: tr("Ntibihuye", "PINs don't match") });
      return;
    }
    await setPin(next);
    if (pendingLockThreadId) {
      const target = threads.find((t) => t.id === pendingLockThreadId);
      setThreads((prev) => prev.map((t) => (t.id === pendingLockThreadId ? { ...t, locked: true } : t)));
      if (target) saveThread({ ...target, locked: true }).catch((err) => console.error("Failed to lock chat", err));
      setPendingLockThreadId(null);
    }
    setModal(null);
    setPinForm(null);
  };

  const confirmDelete = async () => {
    if (!deleteTarget) return;
    const remaining = threads.filter((t) => t.id !== deleteTarget.id);
    setThreads(sortThreads(remaining));
    if (currentId === deleteTarget.id) {
      if (remaining.length) {
        setCurrentId(remaining[0].id);
      } else {
        const t = newThread();
        setDraftThread(t);
        setCurrentId(t.id);
      }
    }
    try {
      await deleteThread(deleteTarget.id);
    } catch (err) {
      console.error("Failed to delete chat", err);
    }
    setDeleteTarget(null);
    setMenuThreadId(null);
  };

  const openMenu = (t: Thread, e: React.MouseEvent) => {
    e.stopPropagation();
    setMenuThreadId(menuThreadId === t.id ? null : t.id);
  };

  if (!uiReady || !langReady) {
    return <div className="app-loading" aria-hidden />;
  }

  if (!lang) {
    return (
      <div className="hero">
        <div className="hero-visual"><MotherBabyMark /></div>
        <div className="hero-content">
          <h1>Hitamo ururimi</h1>
          <p className="lead">Hitamo ururimi rwo gukoresha muri Umubyeyi.</p>
          <p className="leadEn">Choose the language you&apos;d like to use in Umubyeyi.</p>
          <div style={{ display: "flex", gap: 12, marginTop: 20, justifyContent: "center", flexWrap: "wrap" }}>
            <button className="btn btn-primary hero-cta" onClick={() => setLang("rw")}>Ikinyarwanda</button>
            <button className="btn btn-primary hero-cta" onClick={() => setLang("en")}>English</button>
          </div>
        </div>
      </div>
    );
  }

  if (locked) {
    return (
      <div className="hero">
        <div className="hero-content">
          <h1>{tr("Ikiganiro gifunze", "App locked")}</h1>
          <p className="lead">{tr("Injiza PIN yawe kugira ngo ubone ibiganiro byawe.", "Enter your PIN to unlock your chats.")}</p>
          <div style={{ marginTop: 20 }}>
            <input
              className="thread-rename-input"
              type="password"
              inputMode="numeric"
              maxLength={6}
              autoFocus
              value={pinEntry}
              onChange={(e) => { setPinEntry(e.target.value.replace(/\D/g, "")); setPinError(""); }}
              onKeyDown={(e) => { if (e.key === "Enter") handleUnlock(); }}
              placeholder="PIN"
            />
          </div>
          {pinError && <div style={{ color: "#b23a48", marginTop: 8 }}>{pinError}</div>}
          <div style={{ marginTop: 16 }}>
            <button className="btn btn-primary" onClick={handleUnlock}>{tr("Fungura →", "Unlock →")}</button>
          </div>
          <div style={{ marginTop: 24 }}>
            {!forgotConfirm ? (
              <button className="btn btn-sm" onClick={() => setForgotConfirm(true)}>
                {tr("Wibagiwe PIN?", "Forgot PIN?")}
              </button>
            ) : (
              <div className="card">
                {tr(
                  "Kwibagirwa PIN bizagusohora kuri iyi mudasobwa. Nta kintu gisibwa - ibiganiro byawe, imibereho, n'ibizamini byabitswe kuri konti yawe. Injira ukoresheje imeyili n'ijambo ry'ibanga kugira ngo ukomeze, hanyuma ushobora gushyiraho PIN nshya.",
                  "Forgetting your PIN signs you out of this device. Nothing is deleted - your chats, mood history, and check-ins are saved to your account. Sign back in with your email and password to continue, and you can set a new PIN."
                )}
                <div className="modal-actions" style={{ marginTop: 12 }}>
                  <button className="btn" onClick={() => setForgotConfirm(false)}>{tr("Reka", "Cancel")}</button>
                  <button className="btn btn-primary btn-danger-solid" onClick={handleForgotPin}>
                    {tr("Gusohoka", "Sign out")}
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    );
  }

  if (!consented) {
    return (
      <div className="hero">
        <div className="hero-visual"><MotherBabyMark /></div>
        <div className="hero-content">
          <h1>{tr("Muraho, mama.", "Hello, mama.")}</h1>
          <p className="lead">
            {tr(
              "Nturi wenyine. Umubyeyi ari hano ngo agufashe kwita ku mibereho myiza yo mu mutima.",
              "You're not alone. Umubyeyi is here to support your emotional wellbeing."
            )}
          </p>
          <button className="btn btn-primary hero-cta" onClick={() => setConsented(true)}>
            {tr("Tangira ikiganiro →", "Start →")}
          </button>
          <div style={{ marginTop: 14 }}>
            <button className="btn btn-sm" onClick={() => setLang(lang === "rw" ? "en" : "rw")}>
              {lang === "rw" ? "English" : "Ikinyarwanda"}
            </button>
          </div>
          <div style={{ marginTop: 16, display: "flex", gap: 10, justifyContent: "center", flexWrap: "wrap" }}>
            <Link href="/privacy" className="btn btn-sm">{tr("Politiki y'ibanga", "Privacy Policy")}</Link>
            <Link href="/eula" className="btn btn-sm">{tr("Amasezerano", "Terms")}</Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="app-shell">
      {panelOpen && <div className="sidebar-backdrop" aria-hidden />}

      <aside className={`sidebar ${panelOpen ? "open" : ""}`}>
        <div className="sidebar-header">
          <div className="sbrand">Umubyeyi</div>
          <button className="sidebar-lock-btn" onClick={() => setLang(lang === "rw" ? "en" : "rw")}
            aria-label="Switch language" title={lang === "rw" ? "Switch to English" : "Hindura ku Kinyarwanda"}>
            {lang === "rw" ? "EN" : "RW"}
          </button>
          <button className="sidebar-lock-btn" onClick={openPinModal} aria-label="Privacy lock" title={tr("Kurinda ibanga", "Privacy lock")}>🔒</button>
          <button
            className="sidebar-lock-btn"
            onClick={() => createClient().auth.signOut().catch((err) => console.error("Failed to sign out", err))}
            aria-label="Sign out"
            title={tr("Gusohoka", "Sign out")}
          >
            ⏻
          </button>
          <button className="sidebar-close" onClick={() => setPanelOpen(false)} aria-label="Close menu">✕</button>
        </div>

        <nav className="sidebar-nav">
          {NAV.map((n) => (
            <button
              key={n.id}
              type="button"
              className={`sidebar-nav-btn ${view === n.id ? "active" : ""}`}
              onClick={() => goToView(n.id)}
            >
              {tr(n.rw, n.en)}
            </button>
          ))}
        </nav>

        <button className="btn btn-primary sidebar-new" onClick={startNewChat}>
          {tr("＋ Ikiganiro gishya", "＋ New chat")}
        </button>

        <div className="sblbl">{tr("Ibiganiro", "Recent")}</div>
        <div className="thread-list">
          {threads.map((th) => {
            const realLabel = th.title || tr("Ikiganiro gishya", "New chat");
            const label = th.locked ? tr("🔒 Ikiganiro kirinzwe", "🔒 Locked chat") : realLabel;
            const active = th.id === currentId;
            return (
              <div key={th.id} className={`thread-row ${active ? "active" : ""}`}>
                <button className="thread-btn" onClick={() => openThreadRow(th)}>
                  {active ? "• " : ""}{label}
                </button>
                <button
                  className="thread-menu-btn"
                  onClick={(e) => openMenu(th, e)}
                  aria-label="Chat options"
                >
                  ⋯
                </button>
                {menuThreadId === th.id && (
                  <div className="thread-menu" onClick={(e) => e.stopPropagation()}>
                    <div className="thread-menu-actions">
                      {th.locked ? (
                        <button type="button" className="btn btn-sm" onClick={() => requestUnlockThread(th.id)}>
                          {tr("🔓 Kuzibura", "🔓 Unlock")}
                        </button>
                      ) : (
                        <button type="button" className="btn btn-sm" onClick={() => lockThread(th.id)}>
                          {tr("🔒 Fungisha", "🔒 Lock")}
                        </button>
                      )}
                      <button
                        type="button"
                        className="btn btn-sm btn-danger"
                        onClick={() => setDeleteTarget({ id: th.id, title: realLabel })}
                      >
                        {tr("Siba", "Delete")}
                      </button>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </aside>

      <div className="main">
        <div className="main-toolbar">
          <button className="menu-toggle" onClick={() => setPanelOpen(true)} aria-label="Open menu">
            ☰
          </button>
        </div>

        {view === "chat" && current && (
          <>
            <div className="topbar">
              <div className="av"><Mark /></div>
              <div>
                <div className="t">Umubyeyi</div>
                <div className="s">{tr("Umufasha w'imibereho myiza yo mu mutima", "a mental-wellbeing companion")}</div>
              </div>
              <div className="actions">
                <button className="btn btn-sm" onClick={() => setConsented(false)}>{tr("Ahabanza", "Home")}</button>
                <button className="btn btn-sm" onClick={() => setModal("breathe")}>{tr("Guhumeka", "Breathe")}</button>
                <button className="btn btn-sm" onClick={() => setModal("help")}>{tr("Ubufasha", "Help")}</button>
              </div>
            </div>

            <div className="chat-area">
              {current.msgs.length === 0 && (
                <div className="chat-welcome">
                  <div className="quote">
                    &ldquo;{tr(welcomeQuote[1], welcomeQuote[0])}&rdquo;
                  </div>
                  <div className="prompts">
                    {(lang === "rw" ? EXAMPLE_PROMPTS_RW : EXAMPLE_PROMPTS_EN).map((p) => (
                      <button key={p} type="button" className="prompt-chip" onClick={() => setInput(p)}>
                        {p}
                      </button>
                    ))}
                  </div>
                </div>
              )}
              {current.msgs.map((m, i) => (
                <div key={i} className={`row ${m.role === "user" ? "me" : ""}`}>
                  <div className={`bubble ${m.role === "user" ? "me" : "bot"} ${m.danger ? "danger" : ""}`}>
                    {m.text}
                    {m.sub && <div className="subtext">{m.sub}</div>}
                  </div>
                </div>
              ))}
              {typing && <div className="typing">{tr("Umubyeyi arimo arandika…", "Umubyeyi is typing…")}</div>}
              <div ref={bottomRef} />
            </div>

          </>
        )}

        {view === "selfcare" && (
          <>
            <div className="topbar">
              <div className="av"><Mark /></div>
              <div>
                <div className="t">{tr("Kwiyitaho", "Self-care")}</div>
                <div className="s">{tr("Wowe wanitaye ku mwana - noneho niwiyiteho", "You care for your baby - now care for yourself too")}</div>
              </div>
              <div className="actions">
                <button className="btn btn-sm" onClick={() => setConsented(false)}>{tr("Ahabanza", "Home")}</button>
                <button className="btn btn-sm" onClick={() => setModal("help")}>{tr("Ubufasha", "Help")}</button>
              </div>
            </div>
            <div className="section-h">{tr("Uko wiyumva", "Mood check")}</div>
            <div className="card">
              <div className="tt">{tr("Uyu munsi wiyumva ute?", "How are you today?")}</div>
              <div className="mood-grid">
                {["Great", "Okay", "Low", "Anxious", "Exhausted"].map((mood) => (
                  <button key={mood} onClick={async () => {
                    try {
                      setMoodHistory(await saveMoodEntry(mood));
                    } catch (err) {
                      console.error("Failed to save mood", err);
                    }

                    const pool = MOOD_TIPS[mood] ?? [];
                    if (pool.length > 0) {
                      const last = lastMoodTipIndex.current[mood];
                      let index = Math.floor(Math.random() * pool.length);
                      if (pool.length > 1 && index === last) index = (index + 1) % pool.length;
                      lastMoodTipIndex.current[mood] = index;
                      const [en, rw] = pool[index];
                      setMoodTip({ mood, en, rw });
                    }
                  }}>{bi(MOOD_LABEL[mood] ?? mood)}</button>
                ))}
              </div>
              {moodTip && (
                <div className="tip mood-tip">
                  <div className="tt">{bi(MOOD_LABEL[moodTip.mood] ?? moodTip.mood)}</div>
                  <div className="td">{tr(moodTip.rw, moodTip.en)}</div>
                </div>
              )}
              {(() => {
                const visibleMoodHistory = moodHistory
                  .filter((entry) => !dismissedMoodDates.includes(entry.date))
                  .slice(0, 7);
                if (!visibleMoodHistory.length) return null;
                return (
                  <div className="disc">
                    <div>{tr("Vuba aha", "Recent")}:</div>
                    <div className="mood-history">
                      {visibleMoodHistory.map((entry, i) => (
                        <span key={`${entry.date}-${i}`} className="mood-pill mood-pill-removable" style={{ animationDelay: `${i * 45}ms` }}>
                          {bi(MOOD_LABEL[entry.mood] ?? entry.mood)}
                          <button
                            type="button"
                            className="mood-pill-remove"
                            aria-label={`Remove ${entry.mood} entry from view`}
                            onClick={() => {
                              // Removes this entry from the Self-care "Recent" strip only.
                              // The real mood history (and the Progress dashboard trend it
                              // feeds) is untouched -- nothing gets deleted.
                              const next = [...dismissedMoodDates, entry.date];
                              setDismissedMoodDates(next);
                              localStorage.setItem("umubyeyi_moods_dismissed_v1", JSON.stringify(next));
                            }}
                          >
                            ×
                          </button>
                        </span>
                      ))}
                    </div>
                    <div style={{ marginTop: 8 }}>
                      {tr("Bibikwa kuri konti yawe. Ganira n'umukozi w'ubuzima niba ibibazo bikomeje.",
                        "Saved to your account. Discuss persistent distress with a health worker.")}
                    </div>
                  </div>
                );
              })()}
            </div>
            <div className="section-h">{tr("Inama zo kwita ku mutima", "Self-care tips")}</div>
            <div className="tipgrid">
              {TIPS.map(([rw, en, drw, den]) => (
                <div key={rw} className="tip">
                  <div className="tt">{tr(rw, en)}</div>
                  <div className="td">{tr(drw, den)}</div>
                </div>
              ))}
            </div>
            <div className="section-h" style={{ marginTop: 20 }}>{tr("Amagambo yo kongera imbaraga", "Gentle reminders")}</div>
            <div className="tipgrid">
              {AFFIRM.map(([en, rw]) => (
                <div key={en} className="aff">{tr(rw, en)}</div>
              ))}
            </div>
          </>
        )}

        {view === "checkin" && (
          <section className="view-section">
            <div className="topbar"><div className="av"><Mark /></div><div>
              <div className="t">{tr("Isuzuma ryoroheje", "Guided check-in")}</div>
              <div className="s">
                {tr("Ubufasha bwo kwisuzuma ku bushake, ntabwo ari isuzuma ry'ubuvuzi, ibisubizo ntibibikwa",
                  "Optional screening support · not a diagnosis · answers are not stored")}
              </div>
            </div>
              <div className="actions">
                <button className="btn btn-sm" onClick={() => setConsented(false)}>{tr("Ahabanza", "Home")}</button>
                <button className="btn btn-sm" onClick={() => setModal("help")}>{tr("Ubufasha", "Help")}</button>
              </div>
            </div>
            <div className="card">
              <p>
                {tr(
                  `Subiza buri kibazo hakurikijwe uko byifashe mu byumweru bishize, hanyuma ukande "Reba ibisubizo." Iri suzuma ry'ubushakashatsi rirebera niba ibisubizo byawe bisa n'ay'itsinda rifite ibyago byinshi mu bushakashatsi. Ntabwo rishobora kuvuga neza ko ufite indwara yo kwiheba nyuma yo kubyara, kandi nta kintu wandika kibikwa.`,
                  `Answer every question below based on how things have actually been recently, then press "Check result." This research check-in estimates whether your answers resemble the dataset's elevated screening-risk group. It cannot diagnose postpartum depression, and nothing you enter is stored.`
                )}
              </p>
              <label className="thread-menu-label">{tr("Imyaka", "Age")}</label>
              <input className="thread-rename-input" type="number" min={18} max={60}
                placeholder={tr("Urugero: 25", "e.g. 25")}
                value={checkin.Age} onChange={(e) => setCheckin({ ...checkin, Age: e.target.value })} />
              <div className="tipgrid" style={{ marginTop: 14 }}>
                {CHECKIN_FIELDS.map(([key, label, options]) => (
                  <label className="tip" key={key}>
                    <span className="tt">{bi(label)}</span>
                    <select
                      className="thread-rename-input"
                      value={String(checkin[key])}
                      style={checkin[key] === "" ? { color: "#A08E97" } : undefined}
                      onChange={(e) => setCheckin({ ...checkin, [key]: e.target.value })}
                    >
                      <option value="" disabled hidden>{tr("Hitamo", "Select")}</option>
                      {options.map((option) => (
                        <option key={optionValue(option)} value={optionValue(option)}>{bi(optionLabel(option))}</option>
                      ))}
                    </select>
                  </label>
                ))}
              </div>
              <label className="subtext" style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 12 }}>
                <input type="checkbox" checked={saveCheckinHistory}
                  onChange={(e) => setSaveCheckinHistory(e.target.checked)} />
                {tr("Bika iki gisubizo kuri konti yawe kugira ngo ubone uko ugenda ku mudasobwa iyo ari yo yose.",
                  "Save this result to your account so you can see your trend across devices.")}
              </label>
              <button className="btn btn-primary" style={{ marginTop: 10 }} disabled={screening || !checkinReady} onClick={async () => {
                setScreening(true); setScreenError(""); setScreenResult(null);
                try {
                  const result = await sendScreen(checkin);
                  setScreenResult(result);
                  if (saveCheckinHistory) {
                    try {
                      await saveCheckinEntry({ risk: result.risk, elevated: result.elevated });
                    } catch (err) { console.error("Failed to save check-in result", err); }
                  }
                }
                catch (e) { setScreenError(e instanceof Error ? e.message : tr("Ntibyakunze gusoza isuzuma", "Unable to complete check-in")); }
                finally { setScreening(false); }
              }}>{screening ? tr("Birasuzumwa…", "Checking…") : tr("Reba ibisubizo", "Check result")}</button>
              {!checkinReady && (
                <div className="subtext" style={{ marginTop: 8 }}>
                  {tr("Subiza ibibazo byose hejuru kugira ngo ubone ibisubizo.", "Answer all the questions above to see your result.")}
                </div>
              )}
              {screenError && <div className="card danger">{screenError}</div>}
              {screenResult && <div className={`card ${screenResult.elevated ? "danger" : ""}`}>
                <b style={{ fontSize: 16 }}>
                  {screenResult.elevated
                    ? tr("Ushobora gukenera ubufasha bwinyongera", "You may benefit from some extra support")
                    : tr("Nta bimenyetso bikomeye byagaragaye", "Nothing concerning stood out today")}
                </b>
                <p style={{ marginTop: 10 }}>{tr(screenResult.message_rw, screenResult.message_en)}</p>
                <div className="disc" style={{ marginTop: 12 }}>
                  {tr(screenResult.disclaimer_rw ?? screenResult.disclaimer, screenResult.disclaimer)}
                </div>
                {screenResult.explainability_available && screenResult.explanation && (
                  <>
                    <div className="section-h" style={{ marginTop: 22 }}>
                      {tr("Ibyagize uruhare runini kuri iki gisubizo", "What played the biggest role in this result")}
                    </div>
                    <HorizontalBarChart data={screenResult.explanation} />
                    <div className="subtext" style={{ marginTop: 6 }}>
                      {tr("Ibi biva ku bisubizo byawe bwite, ntabwo ari itegeko rihamye. Buri mubyeyi afite ishusho itandukanye.",
                        "This comes straight from your own answers, not a fixed rule. Every mother's chart looks different.")}
                    </div>
                  </>
                )}
              </div>}
            </div>
          </section>
        )}

        {view === "epds" && (
          <section className="view-section">
            <div className="topbar"><div className="av"><Mark /></div><div>
              <div className="t">{tr("Ikizamini cy'imibereho", "Wellness test")}</div>
              <div className="s">
                {tr("Ishingiye ku kizamini cya EPDS-10 (Edinburgh Postnatal Depression Scale), si isuzuma ry'ubuvuzi",
                  "Based on the Edinburgh Postnatal Depression Scale (EPDS-10) · not a diagnosis")}
              </div>
            </div>
              <div className="actions">
                <button className="btn btn-sm" onClick={() => setConsented(false)}>{tr("Ahabanza", "Home")}</button>
                <button className="btn btn-sm" onClick={() => setModal("help")}>{tr("Ubufasha", "Help")}</button>
              </div>
            </div>
            <EpdsAssessment onCrisis={() => setModal("help")} />
          </section>
        )}

        {view === "progress" && (
          <section className="view-section">
            <div className="topbar"><div className="av"><Mark /></div><div>
              <div className="t">{tr("Aho ngeze", "Your progress")}</div>
              <div className="s">
                {tr("Uko wagenze mu kizamini cy'imibereho, mu kwiyumva, no mu isuzuma ryoroheje",
                  "Trends from your wellness test, mood check-ins, and guided check-in")}
              </div>
            </div>
              <div className="actions">
                <button className="btn btn-sm" onClick={() => setConsented(false)}>{tr("Ahabanza", "Home")}</button>
                <button className="btn btn-sm" onClick={() => setModal("help")}>{tr("Ubufasha", "Help")}</button>
              </div>
            </div>
            <ProgressDashboard onGoToSelfcare={() => goToView("selfcare")} />
          </section>
        )}

        {view === "about" && (
          <>
            <div className="topbar">
              <div className="av"><Mark /></div>
              <div><div className="t">{tr("Ibyerekeye Umubyeyi", "About Umubyeyi")}</div>
                <div className="s">{tr("Umufasha wawe w'imibereho myiza", "Your wellness companion")}</div></div>
              <div className="actions">
                <button className="btn btn-sm" onClick={() => setConsented(false)}>{tr("Ahabanza", "Home")}</button>
                <button className="btn btn-sm" onClick={() => setModal("help")}>{tr("Ubufasha", "Help")}</button>
              </div>
            </div>
            <div className="card">
              {lang === "rw" ? (
                <>
                  <b>Umubyeyi</b> ni umufasha uvuga Ikinyarwanda n&apos;Icyongereza, witeguye kugufasha uko wiyumva mu
                  mezi 6 ya mbere nyuma yo kubyara. Ntiyita ku bibazo by&apos;umubiri cyangwa byo kwita ku mwana.
                </>
              ) : (
                <>
                  <b>Umubyeyi</b> is a bilingual companion for the emotional wellbeing of first-time mothers in the
                  first 6 months after birth. It does not address physical or baby-care concerns.
                </>
              )}
            </div>
            <div className="section-h" style={{ marginTop: 20 }}>{tr("Icyo dukora", "What Umubyeyi is (and isn't)")}</div>
            <div className="wcard">
              <div className="wrow">
                <b>{tr("Umufasha w'imibereho myiza yo mu mutima gusa.",
                  "A wellness companion for your mental wellbeing only, not for medical, baby-care, or other challenges.")}</b>
              </div>
              <div className="wrow">
                <b>
                  {tr(`Ku bibazo by'umubiri cyangwa umwana, reba umuganga. Mu kaga, hamagara ${CRISIS_LINE}. Ibiganiro byawe bibikwa kuri konti yawe irinzwe.`,
                    `For physical or baby concerns, see a health worker; in a crisis call ${CRISIS_LINE}. Your chats are saved to your secure account.`)}
                </b>
              </div>
            </div>
            <div className="section-h" style={{ marginTop: 20 }}>{tr("Amategeko", "Legal")}</div>
            <div className="wcard">
              <div className="wrow" style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
                <Link href="/privacy" className="btn btn-sm">{tr("Politiki y'ibanga", "Privacy Policy")}</Link>
                <Link href="/eula" className="btn btn-sm">{tr("Amasezerano y'ukoresha", "End User License Agreement")}</Link>
              </div>
            </div>
          </>
        )}
      </div>

      {view === "chat" && (
        <div className="input-bar">
          <form className="input-wrap" onSubmit={(e) => { e.preventDefault(); handleSend(input); }}>
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={tr("Andika uko wiyumva...", "Type how you feel...")}
              disabled={typing}
            />
            <button type="submit" disabled={typing || !input.trim()} aria-label="Send">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
                <path d="M5 12h13" /><path d="M13 6l6 6-6 6" />
              </svg>
            </button>
          </form>
          <div className="foot">
            {tr(`Umufasha w'imibereho myiza gusa, si uw'ibindi bibazo, mu kaga hamagara ${CRISIS_LINE}`,
              `Wellbeing support only, not other concerns -- in a crisis call ${CRISIS_LINE}`)}
          </div>
        </div>
      )}

      {modal && (
        <div className="modal-overlay" onClick={() => setModal(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h3>{modal === "breathe" ? tr("Guhumeka", "Breathe") : tr("Ubufasha", "Help")}</h3>
            {modal === "breathe" ? (
              <div className="card">
                {lang === "rw" ? (
                  <>Fata akanya gato uhumeke. Injiza umwuka mu mazuru ubara kugeza kuri <b>4</b>, uwushikire kugeza kuri <b>4</b>, hanyuma uwusohore buhoro kugeza kuri <b>6</b>. Subiramo inshuro eshanu.</>
                ) : (
                  <>Take a slow moment. Breathe in for <b>4</b>, hold for <b>4</b>, out gently for <b>6</b>. Repeat five times.</>
                )}
              </div>
            ) : (
              <div className="card">
                {lang === "rw" ? (
                  <>Niba uri mu kaga, hamagara <b>{CRISIS_LINE}</b> nonaha. Umubyeyi ni ubufasha bwo mu mutima, si umuganga.</>
                ) : (
                  <>If you are in danger, call <b>{CRISIS_LINE}</b> now. Umubyeyi is emotional support, not a doctor.</>
                )}
              </div>
            )}
            <button className="btn btn-primary" style={{ marginTop: 16, width: "100%" }} onClick={() => setModal(null)}>OK</button>
          </div>
        </div>
      )}

      {modal === "pin" && pinForm && (
        <div className="modal-overlay" onClick={() => { setModal(null); setPinForm(null); setPendingLockThreadId(null); setForgotConfirm(false); }}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h3>{tr("Kurinda ibanga", "Privacy lock")}</h3>
            {pinForm.mode === null ? (
              <>
                <div className="card">
                  {tr("Ikiganiro kirinzwe na PIN.", "This app has a PIN set.")}
                </div>
                <div className="modal-actions" style={{ flexDirection: "column", gap: 8, marginTop: 12 }}>
                  <button className="btn" onClick={() => setPinForm({ ...pinForm, mode: "change" })}>
                    {tr("Hindura PIN", "Change PIN")}
                  </button>
                  <button className="btn btn-danger" onClick={() => setPinForm({ ...pinForm, mode: "remove" })}>
                    {tr("Kuraho PIN burundu", "Remove PIN entirely")}
                  </button>
                </div>
                <button className="btn" style={{ marginTop: 12, width: "100%" }}
                  onClick={() => { setModal(null); setPinForm(null); setPendingLockThreadId(null); }}>
                  {tr("Funga", "Close")}
                </button>
              </>
            ) : (
              <>
                {pinForm.mode !== "set" && (
                  <input
                    className="thread-rename-input"
                    type="password" inputMode="numeric" maxLength={6}
                    placeholder={tr("PIN y'ubu", "Current PIN")}
                    value={pinForm.current}
                    onChange={(e) => setPinForm({ ...pinForm, current: e.target.value.replace(/\D/g, ""), error: "" })}
                  />
                )}
                {pinForm.mode !== "remove" && (
                  <>
                    <input
                      className="thread-rename-input"
                      type="password" inputMode="numeric" maxLength={6}
                      placeholder={tr("PIN nshya (imibare 4-6)", "New PIN (4-6 digits)")}
                      value={pinForm.next}
                      onChange={(e) => setPinForm({ ...pinForm, next: e.target.value.replace(/\D/g, ""), error: "" })}
                      style={{ marginTop: 8 }}
                    />
                    <input
                      className="thread-rename-input"
                      type="password" inputMode="numeric" maxLength={6}
                      placeholder={tr("Emeza PIN", "Confirm PIN")}
                      value={pinForm.confirm}
                      onChange={(e) => setPinForm({ ...pinForm, confirm: e.target.value.replace(/\D/g, ""), error: "" })}
                      style={{ marginTop: 8 }}
                    />
                  </>
                )}
                {pinForm.error && <div style={{ color: "#b23a48", marginTop: 8 }}>{pinForm.error}</div>}
                <div className="modal-actions" style={{ marginTop: 12 }}>
                  <button className="btn" onClick={() => {
                    if (hasPin()) {
                      setPinForm({ mode: null, current: "", next: "", confirm: "", error: "" });
                    } else {
                      setPinForm(null);
                      setModal(null);
                      setPendingLockThreadId(null);
                      setForgotConfirm(false);
                    }
                  }}>
                    {tr("Reka", "Cancel")}
                  </button>
                  <button className="btn btn-primary" onClick={submitPinForm}>{tr("Bika", "Save")}</button>
                </div>
              </>
            )}
          </div>
        </div>
      )}

      {pinPrompt && (
        <div className="modal-overlay" onClick={() => setPinPrompt(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h3>
              {pinPrompt.purpose === "unlock" ? tr("Injiza PIN kugira ngo ukuraho", "Enter PIN to unlock")
                : tr("Injiza PIN kugira ngo urebe", "Enter PIN to view")}
            </h3>
            <input
              className="thread-rename-input"
              type="password" inputMode="numeric" maxLength={6} autoFocus
              placeholder="PIN"
              value={pinPrompt.entry}
              onChange={(e) => setPinPrompt({ ...pinPrompt, entry: e.target.value.replace(/\D/g, ""), error: "" })}
              onKeyDown={(e) => { if (e.key === "Enter") submitPinPrompt(); }}
            />
            {pinPrompt.error && <div style={{ color: "#b23a48", marginTop: 8 }}>{pinPrompt.error}</div>}
            <div className="modal-actions" style={{ marginTop: 12 }}>
              <button className="btn" onClick={() => setPinPrompt(null)}>{tr("Reka", "Cancel")}</button>
              <button className="btn btn-primary" onClick={submitPinPrompt}>{tr("Emeza", "Confirm")}</button>
            </div>
          </div>
        </div>
      )}

      {deleteTarget && (
        <div className="modal-overlay" onClick={() => setDeleteTarget(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h3>{tr("Siba iki kiganiro?", "Delete this chat?")}</h3>
            <div className="card">
              {lang === "rw" ? (
                <>Uragiye gusiba <b>&quot;{deleteTarget.title}&quot;</b>. Iki gikorwa ntigisubirwaho.</>
              ) : (
                <>You are about to delete <b>&quot;{deleteTarget.title}&quot;</b>. This cannot be undone.</>
              )}
            </div>
            <div className="modal-actions">
              <button className="btn" onClick={() => setDeleteTarget(null)}>{tr("Reka", "Cancel")}</button>
              <button className="btn btn-primary btn-danger-solid" onClick={confirmDelete}>{tr("Yego, siba", "Delete")}</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
