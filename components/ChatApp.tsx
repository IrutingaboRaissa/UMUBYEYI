"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  AFFIRM, CHECKIN_FIELDS, CRISIS_LINE, MOODS, TIPS,
  Thread, loadThreads, newThread, saveThreads, sendChat, sendFeedback,
  logEvent, sendScreen, sessionId, sortThreads, touchThread, ScreenResponse,
} from "@/lib/chat";

type View = "chat" | "checkin" | "selfcare" | "about";

const NAV: { id: View; label: string }[] = [
  { id: "chat", label: "Ikiganiro" },
  { id: "checkin", label: "Isuzuma · Check-in" },
  { id: "selfcare", label: "Kwiyitaho" },
  { id: "about", label: "Ibyerekeye" },
];

export default function ChatApp() {
  const [consented, setConsented] = useState(false);
  const [threads, setThreads] = useState<Thread[]>([]);
  const [currentId, setCurrentId] = useState("");
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
    const initial: Record<string, string | number> = { Age: 25 };
    for (const [key, , options] of CHECKIN_FIELDS) initial[key] = options[0];
    return initial;
  });
  const [screenResult, setScreenResult] = useState<ScreenResponse | null>(null);
  const [screening, setScreening] = useState(false);
  const [screenError, setScreenError] = useState("");
  const [moodHistory, setMoodHistory] = useState<{ mood: string; date: string }[]>([]);
  const bottomRef = useRef<HTMLDivElement>(null);
  const sid = useRef("");
  const hydrated = useRef(false);

  useEffect(() => {
    sid.current = sessionId();
    const { threads: loaded, currentId: cid } = loadThreads();
    setThreads(loaded);
    setCurrentId(cid);
    if (loaded.some((t) => t.msgs.length > 1)) setConsented(true);
    hydrated.current = true;
    try { setMoodHistory(JSON.parse(localStorage.getItem("umubyeyi_moods_v1") || "[]")); } catch { /* ignore */ }
  }, []);

  useEffect(() => {
    if (!hydrated.current || !threads.length) return;
    saveThreads(threads, currentId);
  }, [threads, currentId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [threads, typing, currentId]);

  const current = threads.find((t) => t.id === currentId) ?? threads[0];
  const isRated = current ? ratedThreads[current.id] ?? false : true;

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
    const t = { ...current, msgs: [...current.msgs, { role: "user" as const, text: userMsg }] };
    if (!t.title) t.title = userMsg.slice(0, 40);
    updateThread(t);
    setInput("");
    setTyping(true);
    setRatedThreads((r) => ({ ...r, [t.id]: true }));

    try {
      const res = await sendChat(userMsg);
      const botMsg = { role: "bot" as const, text: res.answer, danger: res.danger };
      updateThread({ ...t, msgs: [...t.msgs, botMsg] });
      setLastMeta({ lang: res.language, mode: res.mode });
      setRatedThreads((r) => ({ ...r, [t.id]: false }));
      if (sid.current) await logEvent(sid.current, res);
    } catch (e) {
      updateThread({
        ...t,
        msgs: [...t.msgs, { role: "bot", text: `Mbabarira, hari ikibazo. (${e instanceof Error ? e.message : "error"})` }],
      });
    } finally {
      setTyping(false);
    }
  };

  const startNewChat = () => {
    const t = newThread();
    setThreads((prev) => sortThreads([t, ...prev]));
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
    let next = remaining;
    if (!next.length) next = [newThread()];
    setThreads(sortThreads(next));
    if (currentId === deleteTarget.id) setCurrentId(next[0].id);
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
        <div className="logo">U</div>
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
      {panelOpen && <div className="sidebar-backdrop" onClick={() => setPanelOpen(false)} aria-hidden />}

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
          <div className="topnav desktop-topnav">
            {NAV.map(({ id, label }) => (
              <button key={id} type="button" className={view === id ? "active" : ""} onClick={() => setView(id)}>
                {label}
              </button>
            ))}
          </div>
        </div>

        {view === "chat" && current && (
          <>
            <div className="topbar">
              <div className="av">U</div>
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

            {current.msgs.length <= 1 && (
              <div className="mood-grid">
                {MOODS.map(([emo, lbl, q]) => (
                  <button key={lbl} onClick={() => handleSend(q)} disabled={typing}>
                    {emo} {lbl}
                  </button>
                ))}
              </div>
            )}
          </>
        )}

        {view === "selfcare" && (
          <>
            <div className="topbar">
              <div className="av">U</div>
              <div>
                <div className="t">Kwiyitaho · Self-care</div>
                <div className="s">Wowe wanitaye ku mwana - noneho niwiyiteho</div>
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
                  }}>{mood}</button>
                ))}
              </div>
              {moodHistory.length > 0 && <div className="disc">
                Recent: {moodHistory.slice(0, 7).map((entry) => entry.mood).join(" · ")}
                <br />Stored only on this device. Discuss persistent distress with a health worker.
              </div>}
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
            <div className="topbar"><div className="av" /><div>
              <div className="t">Isuzuma ryoroheje · Guided check-in</div>
              <div className="s">Optional screening support · not a diagnosis · answers are not stored</div>
            </div></div>
            <div className="card">
              <p>This research check-in estimates whether your answers resemble the dataset&apos;s elevated screening-risk group. It cannot diagnose postpartum depression.</p>
              <label className="thread-menu-label">Age</label>
              <input className="thread-rename-input" type="number" min={18} max={60}
                value={checkin.Age} onChange={(e) => setCheckin({ ...checkin, Age: Number(e.target.value) })} />
              <div className="tipgrid" style={{ marginTop: 14 }}>
                {CHECKIN_FIELDS.map(([key, label, options]) => (
                  <label className="tip" key={key}>
                    <span className="tt">{label}</span>
                    <select className="thread-rename-input" value={String(checkin[key])}
                      onChange={(e) => setCheckin({ ...checkin, [key]: e.target.value })}>
                      {options.map((option) => <option key={option} value={option}>{option}</option>)}
                    </select>
                  </label>
                ))}
              </div>
              <button className="btn btn-primary" disabled={screening} onClick={async () => {
                setScreening(true); setScreenError(""); setScreenResult(null);
                try { setScreenResult(await sendScreen(checkin)); }
                catch (e) { setScreenError(e instanceof Error ? e.message : "Unable to complete check-in"); }
                finally { setScreening(false); }
              }}>{screening ? "Checking…" : "Reba ibisubizo · Check result"}</button>
              {screenError && <div className="card danger">{screenError}</div>}
              {screenResult && <div className={`card ${screenResult.elevated ? "danger" : ""}`}>
                <b>{screenResult.elevated ? "Additional support recommended" : "No elevated risk classified"}</b>
                <p>{screenResult.message_en}</p><p>{screenResult.message_rw}</p>
                <div className="disc">{screenResult.disclaimer}</div>
              </div>}
            </div>
          </section>
        )}

        {view === "about" && (
          <>
            <div className="topbar">
              <div className="av">U</div>
              <div><div className="t">Ibyerekeye Umubyeyi</div><div className="s">About</div></div>
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
            <button type="submit" disabled={typing || !input.trim()} aria-label="Send">➤</button>
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
