"""
Umubyeyi - Streamlit frontend (clean, mother-facing, chat-app style).
Bilingual grounded-generation postpartum emotional-wellbeing assistant for mothers in Rwanda.
Run:  streamlit run src/app.py
"""
import os
import json
import time
import uuid
import streamlit as st

import rag  # src/ is on sys.path when run via `streamlit run src/app.py`

try:
    import db  # anonymous analytics/feedback store (Postgres in prod, SQLite locally); guarded internally
except Exception:
    db = None

# On-device memory: the conversation is kept ONLY in the user's browser (localStorage),
# never on a server. Degrades gracefully to session-only memory if the component is absent.
try:
    from streamlit_local_storage import LocalStorage
    PERSIST = True
except Exception:
    PERSIST = False

try:
    for _k in ("GEMINI_API_KEY", "GEMINI_MODEL"):
        if _k in st.secrets:
            os.environ[_k] = str(st.secrets[_k])
except Exception:
    pass

st.set_page_config(page_title="Umubyeyi", page_icon="🌿", layout="centered",
                   initial_sidebar_state="expanded")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

/* modern sans-serif everywhere (kills the "document" look) — but keep the icon font on icons */
html, body, [class*="css"], [data-testid="stAppViewContainer"] *, [data-testid="stSidebar"] *,
.stChatInput textarea, .stTextInput input, .stButton button{
  font-family:'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif !important;}
[data-testid="stIconMaterial"], span.material-icons, span.material-icons-outlined,
.material-symbols-outlined, [class*="material-icons"], [class*="material-symbols"], i.material-icons{
  font-family:'Material Symbols Outlined','Material Symbols Rounded','Material Icons' !important;}

[data-testid="stAppViewContainer"]{background:radial-gradient(1200px 600px at 50% -10%, #1a3325 0%, #13211a 55%);}
.block-container{max-width:700px;padding-top:5rem;padding-bottom:6.5rem;}
[data-testid="stSidebar"]{background:#0f1d15;border-right:1px solid #1d3528;}
[data-testid="stSidebar"] *{color:#DCEFE3 !important;}
#MainMenu, footer, [data-testid="stToolbar"], [data-testid="stDecoration"]{display:none !important;}

/* centered welcome (consent screen) — warm, minimal, human */
.hero{text-align:center;padding:14px 0 6px;}
.hero .logo{width:64px;height:64px;border-radius:20px;margin:0 auto 16px;
  background:linear-gradient(135deg,#E9C46A,#d8a83f);color:#102017;display:flex;align-items:center;
  justify-content:center;font-size:30px;font-weight:800;box-shadow:0 8px 24px rgba(233,196,106,.28);}
.hero h1{font-size:28px;font-weight:700;color:#F3EFE3;margin:0 0 4px;letter-spacing:.2px;}
.hero .tag{font-size:15px;color:#9FBCA8;margin-bottom:20px;}
.hero .lead{font-size:16.5px;line-height:1.65;color:#E7F2EB;max-width:440px;margin:0 auto 18px;}
.hero .fine{font-size:12.5px;line-height:1.6;color:#7FA090;max-width:440px;margin:0 auto;}
.hero .fine b{color:#E9C46A;}

/* sidebar brand */
.brand{display:flex;align-items:center;gap:11px;margin:2px 0 4px;}
.brand .mono{background:linear-gradient(135deg,#E9C46A,#d8a83f);color:#102017;width:42px;height:42px;
  border-radius:13px;display:flex;align-items:center;justify-content:center;font-size:22px;font-weight:800;
  box-shadow:0 4px 12px rgba(233,196,106,.25);}
.brand .nm{font-size:20px;font-weight:700;color:#fff;line-height:1.1;}
.brand .sub{font-size:12px;color:#8FB09C;}
.sblbl{color:#7FA090 !important;font-size:11px;font-weight:600;letter-spacing:1px;text-transform:uppercase;margin:4px 0 2px;}

/* header (app bar) */
.apphead{display:flex;align-items:center;gap:12px;padding:6px 2px 16px;border-bottom:1px solid #1e3527;margin-bottom:18px;}
.apphead .logo{background:linear-gradient(135deg,#E9C46A,#d8a83f);color:#102017;width:44px;height:44px;border-radius:14px;
  display:flex;align-items:center;justify-content:center;font-size:22px;font-weight:800;flex-shrink:0;}
.apphead .t{font-size:20px;font-weight:700;color:#F3EFE3;line-height:1.15;}
.apphead .s{font-size:12.5px;color:#8FB09C;display:flex;align-items:center;gap:6px;}
.apphead .dot{width:7px;height:7px;border-radius:50%;background:#4ADE80;box-shadow:0 0 6px #4ADE80;display:inline-block;}

/* chat rows + avatars */
.row{display:flex;align-items:flex-end;gap:9px;margin-bottom:15px;animation:fade .25s ease;}
.row.me{justify-content:flex-end;}
@keyframes fade{from{opacity:0;transform:translateY(6px);}to{opacity:1;transform:none;}}
.av{width:30px;height:30px;border-radius:50%;flex-shrink:0;display:flex;align-items:center;justify-content:center;
  font-weight:800;font-size:13px;background:linear-gradient(135deg,#E9C46A,#d8a83f);color:#102017;}
.bubble{max-width:78%;padding:12px 16px;font-size:15.5px;line-height:1.6;border-radius:20px;white-space:pre-wrap;
  box-shadow:0 3px 14px rgba(0,0,0,.16);}
.bubble.bot{background:#F6F1E7;color:#26221b;border-bottom-left-radius:6px;}
.bubble.me{background:linear-gradient(135deg,#2E7D52,#276b45);color:#fff;border-bottom-right-radius:6px;}
.bubble.danger{background:#F7E6E1;color:#7A2E22;border-left:4px solid #C75B45;}
.disc{margin-top:9px;padding-top:8px;border-top:1px dashed #d9cfa8;font-size:12px;color:#9a8f6f;}
/* translation shown under the answer, in a distinct colour so either-language speakers follow */
.trans{margin-top:10px;padding-top:9px;border-top:1px solid #e3d9c4;color:#2f6d80;font-size:14px;line-height:1.55;}
.trans .tl{display:block;font-size:10px;letter-spacing:1px;text-transform:uppercase;color:#9aa79b;
  margin-bottom:3px;font-weight:700;}
/* wellness-scope note under the header */
.scopebar{background:#16261d;border:1px solid #243c2d;border-radius:12px;padding:9px 13px;margin:-4px 0 16px;
  font-size:12.5px;line-height:1.5;color:#9FBCA8;}

/* suggestion chips */
.exhint{color:#8FB09C;font-size:13.5px;margin:4px 0 10px;font-weight:500;}
.stButton button{background:#18291f !important;color:#E7F2EB !important;border:1px solid #2c4636 !important;
  border-radius:22px !important;font-size:14px !important;font-weight:500 !important;padding:9px 16px !important;
  text-align:left !important;transition:all .15s ease;}
.stButton button:hover{border-color:#3a6b4c !important;transform:translateY(-1px);background:#22392b !important;}
/* primary CTA (Start) — prominent, centered, green */
.stButton button[kind="primary"], [data-testid="stBaseButton-primary"]{
  background:linear-gradient(135deg,#2E7D52,#2a744c) !important;color:#fff !important;border:none !important;
  text-align:center !important;font-size:15.5px !important;font-weight:600 !important;padding:13px 18px !important;
  box-shadow:0 8px 22px rgba(46,125,82,.32) !important;}
.stButton button[kind="primary"]:hover, [data-testid="stBaseButton-primary"]:hover{
  background:linear-gradient(135deg,#33885a,#2E7D52) !important;transform:translateY(-1px);}

/* sticky chat input */
[data-testid="stChatInput"]{background:#18291f !important;border:1px solid #2c4636 !important;border-radius:26px !important;}
[data-testid="stChatInput"] textarea{color:#fff !important;font-size:15.5px !important;}
[data-testid="stChatInput"] textarea::placeholder{color:#7f9a8a !important;}
[data-testid="stBottomBlockContainer"]{background:transparent !important;}

/* selects */
[data-baseweb="select"] > div{background:#18291f !important;border-color:#2c4636 !important;color:#fff !important;
  border-radius:12px !important;}

/* cards (examples / about) */
.card{background:#16261d;border:1px solid #233a2c;border-radius:16px;padding:18px 20px;color:#D8E6DD;
  font-size:15px;line-height:1.7;}
.card b{color:#fff;} .card .h{color:#E9C46A;font-size:12px;letter-spacing:1px;text-transform:uppercase;
  margin:2px 0 8px;font-weight:600;}
.qpill{display:inline-block;background:#1c2f24;border:1px solid #2c4636;border-radius:12px;padding:8px 12px;
  margin:4px 6px 4px 0;font-size:14px;color:#DCEFE3;}

@media (max-width:640px){
  .block-container{max-width:100%;padding-top:4rem;padding-left:0.8rem;padding-right:0.8rem;padding-bottom:5.5rem;}
  .apphead{gap:10px;padding-bottom:12px;margin-bottom:14px;}
  .apphead .logo{width:38px;height:38px;font-size:19px;}
  .apphead .t{font-size:17px;} .apphead .s{font-size:11.5px;}
  .bubble{max-width:90%;font-size:15px;padding:11px 14px;}
  .av{width:26px;height:26px;font-size:12px;}
  .card{font-size:14px;padding:15px 16px;}
  .hero .logo{width:56px;height:56px;font-size:26px;}
  .hero h1{font-size:24px;} .hero .lead{font-size:15.5px;} .hero .tag{font-size:14px;}
  [data-testid="stChatInput"] textarea{font-size:16px !important;}  /* >=16px stops iOS zoom */
}
@media (max-width:380px){
  .hero h1{font-size:21px;} .bubble{font-size:14.5px;}
}
</style>
""", unsafe_allow_html=True)

GREETING = ("Muraho, mama. Ndi hano kugufasha ku byo wiyumva mu mezi 6 ya mbere nyuma yo kubyara — "
            "agahinda, guhangayika, kunanirwa, cyangwa kumva uri wenyine. Wambwira uko umeze uyu munsi, "
            "mu Kinyarwanda cyangwa Icyongereza.")

EXAMPLES = [
    ("Agahinda", "Numva mfite agahinda kuva nabyaye."),
    ("Guhangayika", "Mfite ubwoba n'guhangayika ku kuba mama bushya."),
    ("Kunanirwa", "Numva nananiwe cyane kandi ndi wenyine."),
    ("Kudasinzira", "Sinshobora gusinzira nubwo umwana asinziriye."),
]

# ---------------- welcome / consent (minimal, human) ----------------
if not st.session_state.get("consented"):
    st.markdown(
        '<div class="hero">'
        '<div class="logo">U</div>'
        '<h1>Muraho, mama</h1>'
        '<div class="tag">Umufasha wawe nyuma yo kubyara · a companion after birth</div>'
        '<div class="lead">Ndi hano kukwitaho ku byo wiyumva — agahinda, guhangayika cyangwa kunanirwa. '
        'Vugana nanjye mu Kinyarwanda cyangwa Icyongereza.</div>'
        f'<div class="fine">Si serivisi y\'ubuvuzi. Niba uri mu kaga, hamagara <b>{rag.CRISIS_LINE}</b>.<br>'
        'Ibiganiro bibikwa kuri iyi telefone yawe gusa · your chats stay on your device.</div>'
        '</div>', unsafe_allow_html=True)
    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
    _, mid, _ = st.columns([1, 2.4, 1])
    if mid.button("Tangira ikiganiro  ·  Start  →", use_container_width=True, type="primary"):
        st.session_state.consented = True; st.rerun()
    st.stop()

# ---------- on-device history (browser localStorage only; nothing leaves the device) ----------
STORE_KEY = "umubyeyi_threads_v1"
GREETING_MSG = {"role": "bot", "text": GREETING, "danger": False}
_localS = None
if PERSIST:
    try:
        _localS = LocalStorage()
    except Exception:
        _localS = None


def _new_thread():
    return {"id": uuid.uuid4().hex[:12], "title": "", "ts": int(time.time()), "msgs": [dict(GREETING_MSG)]}


def _persist():
    """Write all chats to the browser, only when they changed (nothing goes to a server)."""
    if not _localS:
        return
    try:
        payload = json.dumps(st.session_state.threads, ensure_ascii=False)
        if st.session_state.get("_saved") != payload:
            _localS.setItem(STORE_KEY, payload, key="ls_set")
            st.session_state._saved = payload
    except Exception:
        pass


if "threads" not in st.session_state:
    st.session_state.threads = [_new_thread()]
    st.session_state.current_id = st.session_state.threads[0]["id"]
    st.session_state._hydrated = not bool(_localS)

# a returning user's saved chats load once (the browser resolves them on the first rerun)
if _localS and not st.session_state.get("_hydrated"):
    try:
        raw = _localS.getItem(STORE_KEY)
        if raw is not None:
            data = json.loads(raw)
            if isinstance(data, list) and data:
                st.session_state.threads = data
                st.session_state.current_id = data[0]["id"]
            st.session_state._hydrated = True
    except Exception:
        st.session_state._hydrated = True

if "sid" not in st.session_state:
    st.session_state.sid = uuid.uuid4().hex[:16]   # anonymous per-session id (not tied to any identity)


def _cur():
    for t in st.session_state.threads:
        if t["id"] == st.session_state.current_id:
            return t
    return st.session_state.threads[0]


def ask(text):
    t = _cur()
    msgs = t["msgs"]
    history = [{"role": m["role"], "text": m["text"]} for m in msgs]   # prior turns for context
    msgs.append({"role": "user", "text": text})
    if not t["title"]:
        t["title"] = text.strip()[:36]
    try:
        t0 = time.time()
        r = rag.answer(text, history=history)
        latency = int((time.time() - t0) * 1000)
        msgs.append({"role": "bot", "text": r["answer"], "danger": r.get("danger", False)})
        if db:   # anonymous analytics only — NO message text is stored
            top = r.get("sources") or []
            db.log_event(st.session_state.sid, r.get("language"), r.get("mode"),
                         r.get("grounded"), (top[0]["sim"] if top else 0.0), latency)
        st.session_state._last = {"lang": r.get("language"), "mode": r.get("mode")}
        st.session_state._rated = False
    except Exception as e:
        msgs.append({"role": "bot", "text": f"Mbabarira, hari ikibazo. ({e})", "danger": False})
    # bring the active chat to the top of the recent list
    st.session_state.threads = [t] + [x for x in st.session_state.threads if x["id"] != t["id"]]


def bubble(m):
    if m["role"] == "user":
        return f'<div class="row me"><div class="bubble me">{m["text"]}</div></div>'
    cls = "bubble bot danger" if m.get("danger") else "bubble bot"
    return f'<div class="row"><div class="av">U</div><div class="{cls}">{m["text"]}</div></div>'


with st.sidebar:
    st.markdown('<div class="brand"><div class="mono">U</div><div>'
                '<div class="nm">Umubyeyi</div><div class="sub">Umufasha wawe</div></div></div>',
                unsafe_allow_html=True)
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    admin = st.query_params.get("admin") == "1"   # ?admin=1 reveals the analytics dashboard (kept off the mother UI)
    nav_items = ["Ikiganiro · Chat", "Ingero · Examples", "Ibyerekeye · About"]
    if admin:
        nav_items.append("Imibare · Insights")
    view = st.radio("nav", nav_items, label_visibility="collapsed")
    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
    if st.button("＋ Ikiganiro gishya · New chat", use_container_width=True):
        nt = _new_thread()
        st.session_state.threads = [nt] + st.session_state.threads
        st.session_state.current_id = nt["id"]
        st.session_state._saved = None      # force the store to be rewritten
        st.rerun()
    # recent chats (on-device history) — click one to reopen it
    _has_history = len(st.session_state.threads) > 1 or bool(st.session_state.threads[0]["title"])
    if _has_history:
        st.markdown('<div class="sblbl">Ibiganiro · Recent</div>', unsafe_allow_html=True)
        for t in st.session_state.threads[:25]:
            title = t["title"] or "Ikiganiro gishya · New chat"
            mark = "•  " if t["id"] == st.session_state.current_id else ""
            if st.button(mark + title, key=f"th_{t['id']}", use_container_width=True):
                st.session_state.current_id = t["id"]; st.rerun()

# ---------------- views ----------------
if view.startswith("Ikiganiro"):
    st.markdown('<div class="apphead"><div class="logo">U</div><div>'
                '<div class="t">Umubyeyi</div>'
                '<div class="s"><span class="dot"></span>Wellness chat · Kinyarwanda / English</div></div></div>',
                unsafe_allow_html=True)
    st.markdown('<div class="scopebar">Umufasha ku byo wiyumva. Ku kuva amaraso, umwana, cyangwa ibibazo '
                "by'umubiri — ganira n'umukozi w'ubuzima. · A wellness companion for how you feel — for "
                'bleeding, the baby, or physical concerns, please see a health worker.</div>',
                unsafe_allow_html=True)
    msgs = _cur()["msgs"]
    for m in msgs:
        st.markdown(bubble(m), unsafe_allow_html=True)

    # subtle thumbs feedback on the latest answer (feeds anonymous analytics; no text stored)
    if db and msgs[-1]["role"] == "bot" and len(msgs) > 1 and not st.session_state.get("_rated"):
        st.markdown('<div class="exhint">Iki gisubizo cyagufashije? · Was this helpful?</div>', unsafe_allow_html=True)
        fc1, fc2, _ = st.columns([1.3, 1.6, 3])
        meta = st.session_state.get("_last", {})
        if fc1.button("Byoroheje · Helpful", key="fb_up"):
            db.log_feedback(st.session_state.sid, 1, meta.get("lang"), meta.get("mode"))
            st.session_state._rated = True; st.rerun()
        if fc2.button("Ntibyanfashije · Not really", key="fb_down"):
            db.log_feedback(st.session_state.sid, -1, meta.get("lang"), meta.get("mode"))
            st.session_state._rated = True; st.rerun()

    if len(msgs) <= 1:   # suggestion chips on a fresh chat
        st.markdown('<div class="exhint">Wagerageza kubaza · You could ask:</div>', unsafe_allow_html=True)
        cols = st.columns(2)
        for i, (lbl, q) in enumerate(EXAMPLES):
            if cols[i % 2].button(q, key=f"ex{i}", use_container_width=True):
                ask(q); st.rerun()

    prompt = st.chat_input("Andika uko wiyumva... · Type how you feel...")
    if prompt and prompt.strip():
        ask(prompt.strip()); st.rerun()

elif view.startswith("Ingero"):
    st.markdown('<div class="apphead"><div class="logo">U</div><div>'
                '<div class="t">Ingero z\'ibibazo</div>'
                '<div class="s">Example questions you can ask</div></div></div>', unsafe_allow_html=True)
    groups = {
        "Agahinda · Sadness & low mood": [
            "Numva mfite agahinda kuva nabyaye.",
            "Sinkunda ibyo nakundaga, kandi ndarira kenshi."],
        "Guhangayika · Anxiety & worry": [
            "Mfite ubwoba n'guhangayika ku kuba mama bushya.",
            "Ntekereza cyane ko ntazabasha kwita ku mwana."],
        "Kunanirwa · Feeling overwhelmed": [
            "Numva nananiwe cyane kandi ndi wenyine.",
            "Byose biranyemera, sinzi aho ngomba gutangirira."],
        "Kudasinzira · Exhaustion & sleep": [
            "Sinshobora gusinzira nubwo umwana asinziriye.",
            "Kubura ibitotsi biri kunyangiza umutwe."],
        "Guhangana · Coping & support": [
            "Nakora iki ngo niyumve neza gato?",
            "Numva ndi wenyine, nta wundi mfite."],
    }
    html = '<div class="card">'
    for g, qs in groups.items():
        html += f'<div class="h" style="margin-top:8px">{g}</div>' + "".join(f'<span class="qpill">{q}</span>' for q in qs)
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)

elif view.startswith("Imibare"):   # Insights dashboard (admin only)
    st.markdown('<div class="apphead"><div class="logo">U</div><div>'
                '<div class="t">Imibare · Insights</div>'
                '<div class="s">Anonymous usage & feedback · no message text stored</div></div></div>',
                unsafe_allow_html=True)
    ins = db.insights() if db else None
    if not ins:
        st.markdown('<div class="card">The analytics database is not configured yet. '
                    'Set <b>DATABASE_URL</b> to a Postgres instance (production) — otherwise a local '
                    'SQLite file is used. No data has been recorded yet, or the store is unavailable.</div>',
                    unsafe_allow_html=True)
    else:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Answers", ins["answers"])
        c2.metric("Sessions", ins["sessions"])
        c3.metric("Grounded", f"{ins['grounded_rate']*100:.0f}%")
        c4.metric("Avg latency", f"{ins['avg_latency_ms']} ms")
        c5, c6 = st.columns(2)
        c5.metric("Feedback", ins["feedback_total"])
        c6.metric("Positive", "—" if ins["feedback_positive_rate"] is None
                  else f"{ins['feedback_positive_rate']*100:.0f}%")
        st.markdown(f'<div class="card"><div class="h">By language</div>{ins["by_language"]}'
                    f'<div class="h" style="margin-top:10px">By mode</div>{ins["by_mode"]}'
                    f'<div class="disc" style="color:#8FB09C;border-color:#2c4636">Backend: '
                    f'<b>{ins["backend"]}</b> · Stored fields: language, mode, grounded, similarity, latency, '
                    f'rating, timestamps — <b>never message text or identity</b>.</div></div>',
                    unsafe_allow_html=True)

else:  # About
    st.markdown('<div class="apphead"><div class="logo">U</div><div>'
                '<div class="t">Ibyerekeye Umubyeyi</div>'
                '<div class="s">About</div></div></div>', unsafe_allow_html=True)
    st.markdown('<div class="card">'
                '<b>Umubyeyi</b> ni umufasha uvuga Ikinyarwanda n\'Icyongereza, witeguye kugufasha ku byo '
                'wiyumva mu mezi 6 ya mbere nyuma yo kubyara — agahinda, guhangayika, kunanirwa, kumva uri '
                'wenyine, no guhangana. Ntiyita ku bibazo by\'umubiri cyangwa byo kwita ku mwana.<br><br>'
                '<i>Umubyeyi is a bilingual (Kinyarwanda / English) companion for the emotional wellbeing of '
                'first-time mothers in the first 6 months after birth — sadness, anxiety, feeling overwhelmed, '
                'loneliness, and coping. It does not cover medical or baby-care questions, and always reminds '
                'you to see a health worker when needed.</i>'
                f'<div class="disc" style="color:#8FB09C;border-color:#2c4636">Si serivisi y\'ubuvuzi. '
                f'Niba uri mu kaga, hamagara {rag.CRISIS_LINE}. · Not medical care; in a crisis call {rag.CRISIS_LINE}.</div>'
                '</div>', unsafe_allow_html=True)

# persist the thread to the browser at the end of the run (writes only when it changed)
_persist()
