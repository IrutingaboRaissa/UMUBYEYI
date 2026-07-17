"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  AFFIRM, CHECKIN_FIELDS, CRISIS_LINE, MOOD_TIPS, TIPS,
  Thread, loadThreads, newThread, saveThreads, sendChat, sendFeedback,
  generateTitle, logEvent, optionLabel, optionValue, sendScreen, sessionId, sortThreads, touchThread, ScreenResponse,
} from "@/lib/chat";
import EpdsAssessment from "@/components/EpdsAssessment";
import ProgressDashboard from "@/components/ProgressDashboard";
import HorizontalBarChart from "@/components/charts/HorizontalBarChart";
import Mark from "@/components/Mark";
import MotherBabyMark from "@/components/MotherBabyMark";

const EXAMPLE_PROMPTS = [
  "I feel exhausted all the time",
  "I'm anxious about my baby",
  "I feel guilty as a mother",
  "I feel alone since giving birth",
];

type View = "chat" | "checkin" | "epds" | "progress" | "selfcare" | "about";

const NAV: { id: View; label: string }[] = [
  { id: "chat", label: "Ikiganiro · Chat" },
  { id: "checkin", label: "Isuzuma · Check-in" },
  { id: "epds", label: "Ikizamini cy'imibereho · Wellness test" },
  { id: "progress", label: "Aho ngeze · Progress" },
  { id: "selfcare", label: "Kwiyitaho · Self-care" },
  { id: "about", label: "Ibyerekeye · About" },
];

const CHECKIN_HISTORY_KEY = "umubyeyi_checkin_v1";

export default function ChatApp() {
  const [consented, setConsented] = useState(false);
  const [threads, setThreads] = useState<Thread[]>([]);
  const [currentId, setCurrentId] = useState("");
  const [draftThread, setDraftThread] = useState<Thread | null>(null);
  const [view, setView] = useState<View>("chat");
  const [panelOpen, setPanelOpen] = useState(false);
  const [input, setInput] = useState("");
  const [typing, setTyping] = useState(false);
  const [lastMeta, setLastMeta] = useState<{ lang?: string; mode?: string }>({});
  const [modal, setModal] = useState<"breathe" | "help" | null>(null);
  const [menuThreadId, setMenuThreadId] = useState<string | null>(null);
  const [renameDraft, setRenameDraft] = useState("");
  const [deleteTarget, setDeleteTarget] = useState<{ id: string; title: string } | null>(null);
  const [ratedThreads, setRatedThreads] = useState<Record<string, boolean>>({});
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
  const [moodTip, setMoodTip] = useState<{ mood: string; en: string; rw: string } | null>(null);
  const lastMoodTipIndex = useRef<Record<string, number>>({});
  const [welcomeQuote] = useState(() => AFFIRM[Math.floor(Math.random() * AFFIRM.length)]);
  const bottomRef = useRef<HTMLDivElement>(null);
  const sid = useRef("");
  const hydrated = useRef(false);

  useEffect(() => {
    sid.current = sessionId();
    const { threads: loaded, currentId: cid } = loadThreads();
    if (loaded.length) {
      setThreads(loaded);
      setCurrentId(cid);
    } else {
      const t = newThread();
      setDraftThread(t);
      setCurrentId(t.id);
    }
    if (loaded.some((t) => t.msgs.length > 1)) setConsented(true);
    hydrated.current = true;
    try { setMoodHistory(JSON.parse(localStorage.getItem("umubyeyi_moods_v1") || "[]")); } catch { /* ignore */ }
  }, []);

  useEffect(() => {
    if (!hydrated.current) return;
    saveThreads(threads, currentId);
  }, [threads, currentId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [threads, typing, currentId]);

  const current = threads.find((t) => t.id === currentId)
    ?? (draftThread?.id === currentId ? draftThread : threads[0]);
  const isRated = current ? ratedThreads[current.id] ?? false : true;
  const checkinReady = checkin.Age !== "" && CHECKIN_FIELDS.every(([key]) => checkin[key] !== "");

  const setCurrent = useCallback((id: string) => {
    setCurrentId(id);
    setMenuThreadId(null);
    setPanelOpen(false);
  }, []);

  const updateThread = useCallback((updated: Thread) => {
    const touched = touchThread(updated);
    setThreads((prev) => sortThreads([touched, ...prev.filter((t) => t.id !== touched.id)]));
  }, []);

  const handleSend = async (text: string) => {
    if (!text.trim() || typing || !current) return;
    const userMsg = text.trim();
    const isFirstMessage = !current.title;
    const t = { ...current, msgs: [...current.msgs, { role: "user" as const, text: userMsg }] };
    if (!t.title) t.title = userMsg.slice(0, 40);
    updateThread(t);
    if (draftThread?.id === t.id) setDraftThread(null);
    setInput("");
    setTyping(true);
    setRatedThreads((r) => ({ ...r, [t.id]: true }));

    try {
      const res = await sendChat(userMsg, null, current.msgs);
      const botMsg = { role: "bot" as const, text: res.answer, danger: res.danger, mode: res.mode };
      updateThread({ ...t, msgs: [...t.msgs, botMsg] });
      setLastMeta({ lang: res.language, mode: res.mode });
      setRatedThreads((r) => ({ ...r, [t.id]: false }));
      if (sid.current) await logEvent(sid.current, res);
      if (res.concern_signal) {
        try {
          const prev = JSON.parse(localStorage.getItem("umubyeyi_concern_v1") || "[]");
          const next = [{ date: new Date().toISOString(), score: res.concern_signal.score, level: res.concern_signal.level },
            ...(Array.isArray(prev) ? prev : [])].slice(0, 30);
          localStorage.setItem("umubyeyi_concern_v1", JSON.stringify(next));
        } catch { /* ignore */ }
      }
      if (isFirstMessage) {
        generateTitle(userMsg, res.answer, res.language).then((title) => {
          if (!title) return;
          setThreads((prev) => prev.map((th) => (th.id === t.id ? { ...th, title } : th)));
        });
      }
    } catch {
      const fallbackText = lastMeta.lang === "en"
        ? "Sorry, something went wrong. Please try again."
        : lastMeta.lang === "rw"
          ? "Mbabarira, hari ikibazo. Ongera ugerageze."
          : "Sorry, something went wrong. Mbabarira, hari ikibazo. Ongera ugerageze.";
      updateThread({
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

  const renameThread = (id: string, name: string) => {
    const trimmed = name.trim().slice(0, 40);
    if (!trimmed) return;
    setThreads((prev) => sortThreads(prev.map((t) => (t.id === id ? touchThread({ ...t, title: trimmed }) : t))));
    setMenuThreadId(null);
  };

  const confirmDelete = () => {
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
    setDeleteTarget(null);
    setMenuThreadId(null);
  };

  const openMenu = (t: Thread, e: React.MouseEvent) => {
    e.stopPropagation();
    setMenuThreadId(menuThreadId === t.id ? null : t.id);
    setRenameDraft(t.title);
  };

  if (!consented) {
    return (
      <div className="hero">
        <div className="hero-illustration"><MotherBabyMark /></div>
        <div className="logo"><Mark size={44} /></div>
        <h1>Muraho, mama.</h1>
        <div className="tag">Ntabwo uri wenyine · you&apos;re not alone</div>
        <p className="lead">Ndi hano kukwitaho uko wiyumva. Vugana nanjye mu Kinyarwanda cyangwa Icyongereza.</p>
        <p className="leadEn">I&apos;m here to care for how you feel. Talk with me in Kinyarwanda or English.</p>
        <div className="wcard">
          <div className="wrow">
            <b>Umufasha w&apos;imibereho myiza yo mu mutima gusa.</b><br />
            <span>A wellness companion for your mental wellbeing only — not for medical, baby-care, or other challenges.</span>
          </div>
          <div className="wrow">
            <b>Ku bibazo by&apos;umubiri cyangwa umwana, reba umuganga. Mu kaga, hamagara {CRISIS_LINE}.</b><br />
            <span>For physical or baby concerns, see a health worker; in a crisis call {CRISIS_LINE} · chats stay on this device.</span>
          </div>
        </div>
        <div style={{ marginTop: 20 }}>
          <button className="btn btn-primary" onClick={() => setConsented(true)}>
            Tangira ikiganiro · Start →
          </button>
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
          <button className="sidebar-close" onClick={() => setPanelOpen(false)} aria-label="Close menu">✕</button>
        </div>

        <nav className="sidebar-nav">
          {NAV.map(({ id, label }) => (
            <button
              key={id}
              type="button"
              className={`sidebar-nav-btn ${view === id ? "active" : ""}`}
              onClick={() => goToView(id)}
            >
              {label}
            </button>
          ))}
        </nav>

        <button className="btn btn-primary sidebar-new" onClick={startNewChat}>
          ＋ Ikiganiro gishya · New chat
        </button>

        <div className="sblbl">Ibiganiro · Recent</div>
        <div className="thread-list">
          {threads.map((t) => {
            const label = t.title || "Ikiganiro gishya · New chat";
            const active = t.id === currentId;
            return (
              <div key={t.id} className={`thread-row ${active ? "active" : ""}`}>
                <button className="thread-btn" onClick={() => { setCurrent(t.id); setView("chat"); }}>
                  {active ? "• " : ""}{label}
                </button>
                <button
                  className="thread-menu-btn"
                  onClick={(e) => openMenu(t, e)}
                  aria-label="Chat options"
                >
                  ⋯
                </button>
                {menuThreadId === t.id && (
                  <div className="thread-menu" onClick={(e) => e.stopPropagation()}>
                    <label className="thread-menu-label">Guhindura izina · Rename</label>
                    <input
                      className="thread-rename-input"
                      value={renameDraft}
                      onChange={(e) => setRenameDraft(e.target.value)}
                      placeholder="Izina · name"
                      maxLength={40}
                    />
                    <div className="thread-menu-actions">
                      <button
                        type="button"
                        className="btn btn-sm"
                        onClick={() => renameThread(t.id, renameDraft)}
                      >
                        Hindura izina · Rename
                      </button>
                      <button
                        type="button"
                        className="btn btn-sm btn-danger"
                        onClick={() => setDeleteTarget({ id: t.id, title: label })}
                      >
                        Siba · Delete
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
                <div className="s">Umufasha w&apos;imibereho myiza yo mu mutima · a mental-wellbeing companion</div>
              </div>
              <div className="actions">
                <button className="btn btn-sm" onClick={() => setModal("breathe")}>Guhumeka · Breathe</button>
                <button className="btn btn-sm" onClick={() => setModal("help")}>Ubufasha · Help</button>
              </div>
            </div>

            <div className="chat-area">
              {current.msgs.length === 0 && (
                <div className="chat-welcome">
                  <div className="quote">
                    &ldquo;{welcomeQuote[0]}&rdquo;
                    <span>{welcomeQuote[1]}</span>
                  </div>
                  <div className="prompts">
                    {EXAMPLE_PROMPTS.map((p) => (
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
              {typing && <div className="typing">Umubyeyi arimo yandika… · Umubyeyi is typing…</div>}
              <div ref={bottomRef} />
            </div>

            {!isRated && current.msgs.length > 1 && current.msgs.at(-1)?.role === "bot" && (
              <div className="feedback">
                Iki gisubizo cyagufashije? · Was this helpful?{" "}
                <button className="btn btn-sm" onClick={() => {
                  sendFeedback(sid.current, 1, lastMeta.lang, lastMeta.mode);
                  setRatedThreads((r) => ({ ...r, [current.id]: true }));
                }}>Byoroheje · Helpful</button>{" "}
                <button className="btn btn-sm" onClick={() => {
                  sendFeedback(sid.current, -1, lastMeta.lang, lastMeta.mode);
                  setRatedThreads((r) => ({ ...r, [current.id]: true }));
                }}>Ntibyanfashije · Not really</button>
              </div>
            )}

          </>
        )}

        {view === "selfcare" && (
          <>
            <div className="topbar">
              <div className="av"><Mark /></div>
              <div>
                <div className="t">Kwiyitaho · Self-care</div>
                <div className="s">Wowe wanitaye ku mwana - noneho niwiyiteho</div>
              </div>
              <div className="actions">
                <button className="btn btn-sm" onClick={() => setModal("help")}>Ubufasha · Help</button>
              </div>
            </div>
            <div className="section-h">Uko wiyumva · Mood check</div>
            <div className="card">
              <div className="tt">Uyu munsi wiyumva ute? · How are you today?</div>
              <div className="mood-grid">
                {["Great", "Okay", "Low", "Anxious", "Exhausted"].map((mood) => (
                  <button key={mood} onClick={() => {
                    const next = [{ mood, date: new Date().toISOString() }, ...moodHistory].slice(0, 30);
                    setMoodHistory(next);
                    localStorage.setItem("umubyeyi_moods_v1", JSON.stringify(next));

                    const pool = MOOD_TIPS[mood] ?? [];
                    if (pool.length > 0) {
                      const last = lastMoodTipIndex.current[mood];
                      let index = Math.floor(Math.random() * pool.length);
                      if (pool.length > 1 && index === last) index = (index + 1) % pool.length;
                      lastMoodTipIndex.current[mood] = index;
                      const [en, rw] = pool[index];
                      setMoodTip({ mood, en, rw });
                    }
                  }}>{mood}</button>
                ))}
              </div>
              {moodTip && (
                <div className="tip mood-tip">
                  <div className="tt">For feeling {moodTip.mood.toLowerCase()}</div>
                  <div className="td">{moodTip.en}<br /><span>{moodTip.rw}</span></div>
                </div>
              )}
              {moodHistory.length > 0 && (
                <div className="disc">
                  <div>Recent:</div>
                  <div className="mood-history">
                    {moodHistory.slice(0, 7).map((entry, i) => (
                      <span key={`${entry.date}-${i}`} className="mood-pill" style={{ animationDelay: `${i * 45}ms` }}>
                        {entry.mood}
                      </span>
                    ))}
                  </div>
                  <div style={{ marginTop: 8 }}>Stored only on this device. Discuss persistent distress with a health worker.</div>
                </div>
              )}
            </div>
            <div className="section-h">Inama zo kwita ku mutima · Self-care tips</div>
            <div className="tipgrid">
              {TIPS.map(([e, rw, en, drw, den]) => (
                <div key={rw} className="tip">
                  <div className="emo">{e}</div>
                  <div className="tt">{rw} · <span>{en}</span></div>
                  <div className="td">{drw}<br /><span>{den}</span></div>
                </div>
              ))}
            </div>
            <div className="section-h" style={{ marginTop: 20 }}>Amagambo yo kongera imbaraga · Gentle reminders</div>
            <div className="tipgrid">
              {AFFIRM.map(([en, rw]) => (
                <div key={en} className="aff">💗 {en}<div className="affrw">{rw}</div></div>
              ))}
            </div>
          </>
        )}

        {view === "checkin" && (
          <section className="view-section">
            <div className="topbar"><div className="av"><Mark /></div><div>
              <div className="t">Isuzuma ryoroheje · Guided check-in</div>
              <div className="s">Optional screening support · not a diagnosis · answers are not stored</div>
            </div>
              <div className="actions">
                <button className="btn btn-sm" onClick={() => setModal("help")}>Ubufasha · Help</button>
              </div>
            </div>
            <div className="card">
              <p>
                Subiza buri kibazo hakurikijwe uko byifashe mu byumweru bishize, hanyuma ukande &quot;Reba ibisubizo.&quot;
                <br />
                <span className="subtext">
                  Answer every question below based on how things have actually been recently, then press &quot;Check result.&quot;
                  This research check-in estimates whether your answers resemble the dataset&apos;s elevated screening-risk
                  group — it cannot diagnose postpartum depression, and nothing you enter is stored.
                </span>
              </p>
              <label className="thread-menu-label">Age</label>
              <input className="thread-rename-input" type="number" min={18} max={60}
                placeholder="Urugero: 25 · e.g. 25"
                value={checkin.Age} onChange={(e) => setCheckin({ ...checkin, Age: e.target.value })} />
              <div className="tipgrid" style={{ marginTop: 14 }}>
                {CHECKIN_FIELDS.map(([key, label, options]) => (
                  <label className="tip" key={key}>
                    <span className="tt">{label}</span>
                    <select
                      className="thread-rename-input"
                      value={String(checkin[key])}
                      style={checkin[key] === "" ? { color: "#A08E97" } : undefined}
                      onChange={(e) => setCheckin({ ...checkin, [key]: e.target.value })}
                    >
                      <option value="" disabled hidden>Hitamo · Select</option>
                      {options.map((option) => (
                        <option key={optionValue(option)} value={optionValue(option)}>{optionLabel(option)}</option>
                      ))}
                    </select>
                  </label>
                ))}
              </div>
              <label className="subtext" style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 12 }}>
                <input type="checkbox" checked={saveCheckinHistory}
                  onChange={(e) => setSaveCheckinHistory(e.target.checked)} />
                Save this result on this device only, to see your trend — nothing leaves your phone.
              </label>
              <button className="btn btn-primary" style={{ marginTop: 10 }} disabled={screening || !checkinReady} onClick={async () => {
                setScreening(true); setScreenError(""); setScreenResult(null);
                try {
                  const result = await sendScreen(checkin);
                  setScreenResult(result);
                  if (saveCheckinHistory) {
                    try {
                      const prev = JSON.parse(localStorage.getItem(CHECKIN_HISTORY_KEY) || "[]");
                      const next = [{ date: new Date().toISOString(), risk: result.risk, elevated: result.elevated },
                        ...(Array.isArray(prev) ? prev : [])].slice(0, 30);
                      localStorage.setItem(CHECKIN_HISTORY_KEY, JSON.stringify(next));
                    } catch { /* ignore */ }
                  }
                }
                catch (e) { setScreenError(e instanceof Error ? e.message : "Unable to complete check-in"); }
                finally { setScreening(false); }
              }}>{screening ? "Checking…" : "Reba ibisubizo · Check result"}</button>
              {!checkinReady && (
                <div className="subtext" style={{ marginTop: 8 }}>
                  Subiza ibibazo byose hejuru kugira ngo ubone ibisubizo. · Answer all the questions above to see your result.
                </div>
              )}
              {screenError && <div className="card danger">{screenError}</div>}
              {screenResult && <div className={`card ${screenResult.elevated ? "danger" : ""}`}>
                <b style={{ fontSize: 16 }}>
                  {screenResult.elevated
                    ? "Ushobora gukenera ubufasha bwinyongera · You may benefit from some extra support"
                    : "Nta bimenyetso bikomeye byagaragaye · Nothing concerning stood out today"}
                </b>
                <p style={{ marginTop: 10 }}>{screenResult.message_en}</p>
                <p style={{ marginTop: 8 }}>{screenResult.message_rw}</p>
                <div className="disc" style={{ marginTop: 12 }}>{screenResult.disclaimer}</div>
                {screenResult.explainability_available && screenResult.explanation && (
                  <>
                    <div className="section-h" style={{ marginTop: 22 }}>What played the biggest role in this result</div>
                    <HorizontalBarChart data={screenResult.explanation} />
                    <div className="subtext" style={{ marginTop: 6 }}>
                      This comes straight from your own answers, not a fixed rule — every mother&apos;s chart looks different.
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
              <div className="t">Ikizamini cy&apos;imibereho · Wellness test</div>
              <div className="s">Based on the Edinburgh Postnatal Depression Scale (EPDS-10) · not a diagnosis</div>
            </div>
              <div className="actions">
                <button className="btn btn-sm" onClick={() => setModal("help")}>Ubufasha · Help</button>
              </div>
            </div>
            <EpdsAssessment onCrisis={() => setModal("help")} />
          </section>
        )}

        {view === "progress" && (
          <section className="view-section">
            <div className="topbar"><div className="av"><Mark /></div><div>
              <div className="t">Aho ngeze · Your progress</div>
              <div className="s">Trends from your wellness test, mood check-ins, and guided check-in</div>
            </div>
              <div className="actions">
                <button className="btn btn-sm" onClick={() => setModal("help")}>Ubufasha · Help</button>
              </div>
            </div>
            <ProgressDashboard />
          </section>
        )}

        {view === "about" && (
          <>
            <div className="topbar">
              <div className="av"><Mark /></div>
              <div><div className="t">Ibyerekeye Umubyeyi</div><div className="s">About</div></div>
              <div className="actions">
                <button className="btn btn-sm" onClick={() => setModal("help")}>Ubufasha · Help</button>
              </div>
            </div>
            <div className="card">
              <b>Umubyeyi</b> ni umufasha uvuga Ikinyarwanda n&apos;Icyongereza, witeguye kugufasha uko wiyumva mu mezi 6 ya mbere nyuma yo kubyara.
              Ntiyita ku bibazo by&apos;umubiri cyangwa byo kwita ku mwana.
              <br /><br />
              <i>Umubyeyi is a bilingual companion for the emotional wellbeing of first-time mothers in the first 6 months after birth.</i>
              <div className="subtext" style={{ marginTop: 12 }}>
                Si serivisi y&apos;ubuvuzi · niba uri mu kaga, hamagara {CRISIS_LINE}.
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
              placeholder="Andika uko wiyumva... · Type how you feel..."
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
            Umufasha w&apos;imibereho myiza gusa · si uw&apos;ibindi bibazo · mu kaga hamagara {CRISIS_LINE}
          </div>
        </div>
      )}

      {modal && (
        <div className="modal-overlay" onClick={() => setModal(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h3>{modal === "breathe" ? "Guhumeka · Breathe" : "Ubufasha · Help"}</h3>
            {modal === "breathe" ? (
              <div className="card">
                Fata akanya gato uhumeke. Injiza umwuka mu mazuru ubara kugeza kuri <b>4</b>, uwushikire kugeza kuri <b>4</b>, hanyuma uwusohore buhoro kugeza kuri <b>6</b>.
                <br /><br />
                <i>Take a slow moment. Breathe in for 4, hold for 4, out gently for 6. Repeat five times.</i>
              </div>
            ) : (
              <div className="card">
                Niba uri mu kaga, hamagara <b>{CRISIS_LINE}</b> nonaha.
                <br /><br />
                <i>If you are in danger, call <b>{CRISIS_LINE}</b> now. Umubyeyi is emotional support, not a doctor.</i>
              </div>
            )}
            <button className="btn btn-primary" style={{ marginTop: 16, width: "100%" }} onClick={() => setModal(null)}>OK</button>
          </div>
        </div>
      )}

      {deleteTarget && (
        <div className="modal-overlay" onClick={() => setDeleteTarget(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h3>Siba iki kiganiro? · Delete this chat?</h3>
            <div className="card">
              Uragiye gusiba <b>&quot;{deleteTarget.title}&quot;</b>. Iki gikorwa ntigisubirwaho.
              <br /><br />
              <i>This cannot be undone.</i>
            </div>
            <div className="modal-actions">
              <button className="btn" onClick={() => setDeleteTarget(null)}>Reka · Cancel</button>
              <button className="btn btn-primary btn-danger-solid" onClick={confirmDelete}>Yego, siba · Delete</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
