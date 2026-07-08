"""
Umubyeyi - Streamlit frontend (light "cream & plum" theme).
Bilingual grounded-generation postpartum emotional-wellbeing companion for mothers in Rwanda.
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

# On-device history: conversations are kept ONLY in the browser (localStorage), never on a server.
try:
    from streamlit_local_storage import LocalStorage
    PERSIST = True
except Exception:
    PERSIST = False

st.set_page_config(page_title="Umubyeyi", page_icon="🌿", layout="centered",
                   initial_sidebar_state="expanded")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"], [data-testid="stAppViewContainer"] *, [data-testid="stSidebar"] *,
.stChatInput textarea, .stButton button{
  font-family:'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;}
[data-testid="stIconMaterial"], .material-symbols-outlined, [class*="material-icons"], [class*="material-symbols"]{
  font-family:'Material Symbols Outlined','Material Icons' !important;}

[data-testid="stAppViewContainer"]{background:linear-gradient(180deg,#F6EFE5 0%,#F1E7E5 100%);}
.block-container{max-width:840px;padding-top:4.5rem;padding-bottom:8.5rem;}
#MainMenu, footer, [data-testid="stToolbar"], [data-testid="stDecoration"]{display:none !important;}
[data-testid="stSidebar"]{background:#FBF5EC;border-right:1px solid #EADFCF;}
[data-testid="stSidebar"] *{color:#4A3F47 !important;}
/* hide Streamlit's native collapse control (its Material icon renders as "keyboard..." text in the
   HF mobile iframe). We provide our own ☰ toggle instead. */
[data-testid="stSidebarCollapseButton"], [data-testid="stSidebarCollapsedControl"],
[data-testid="collapsedControl"], [data-testid="stSidebarHeader"]{display:none !important;}
.sblbl{color:#A08E97 !important;font-size:11px;font-weight:700;letter-spacing:1px;text-transform:uppercase;margin:10px 0 2px;}
.sbrand{font-size:19px;font-weight:700;color:#3B2E39;padding:2px 0 2px;}

/* ---- top bar ---- */
.topbar{display:flex;align-items:center;gap:12px;padding:2px 2px 16px;border-bottom:1px solid #EADFCF;margin-bottom:20px;}
.topbar .av{width:44px;height:44px;border-radius:50%;flex-shrink:0;display:flex;align-items:center;
  justify-content:center;background:radial-gradient(circle at 32% 30%, #9A7C9D 0%, #5E4A5E 75%);
  box-shadow:0 4px 12px rgba(94,74,94,.25);}
.topbar .av::after{content:"U";color:#fff;font-weight:800;font-size:22px;line-height:1;letter-spacing:-.5px;}
.topbar .t{font-size:20px;font-weight:700;color:#3B2E39;line-height:1.15;}
.topbar .s{font-size:12.5px;color:#A08E97;}

/* ---- chat bubbles ---- */
.row{display:flex;margin-bottom:16px;animation:fade .25s ease;}
.row.me{justify-content:flex-end;}
@keyframes fade{from{opacity:0;transform:translateY(6px);}to{opacity:1;transform:none;}}
.bubble{max-width:80%;padding:13px 18px;font-size:15.5px;line-height:1.62;border-radius:20px;white-space:pre-wrap;}
.bubble.bot{background:#FCF8F2;color:#356B7D;border:1px solid #EFE6D8;border-bottom-left-radius:6px;
  box-shadow:0 3px 16px rgba(90,70,80,.06);}
.bubble.me{background:linear-gradient(135deg,#6E5668,#57445A);color:#F7F1F4;border-bottom-right-radius:6px;
  box-shadow:0 4px 14px rgba(87,68,90,.22);}
.bubble.danger{background:#FBEDE9;color:#8A4030;border:1px solid #F0D4CB;border-left:4px solid #C9705A;}
.disc{margin-top:9px;padding-top:8px;border-top:1px dashed #E3D9C6;font-size:12px;color:#9aa79b;font-style:italic;}

/* ---- scope note above the input ---- */
.scopebar{text-align:center;font-size:13px;line-height:1.55;color:#6b5560;font-weight:500;margin:2px 0 4px;}
.scopebar b{color:#5E4A5E;}
.foot{text-align:center;font-size:11.5px;color:#B0A2A9;margin-top:2px;}

/* ---- buttons -> soft pills ---- */
.stButton button{background:#FFFFFF !important;color:#4A3F47 !important;border:1px solid #E7DDCF !important;
  border-radius:22px !important;font-size:13.5px !important;font-weight:500 !important;padding:8px 15px !important;
  box-shadow:0 2px 6px rgba(90,70,80,.05);transition:all .15s ease;}
.stButton button:hover{border-color:#C9B9C2 !important;transform:translateY(-1px);background:#FCF8F2 !important;}
.stButton button[kind="primary"], [data-testid="stBaseButton-primary"]{
  background:linear-gradient(135deg,#6E5668,#57445A) !important;color:#fff !important;border:none !important;
  text-align:center !important;font-weight:600 !important;font-size:15px !important;padding:12px 18px !important;
  box-shadow:0 8px 20px rgba(87,68,90,.28) !important;}

/* language segmented control -> plum active */
[data-testid="stSegmentedControl"] button{border-radius:20px !important;font-size:13px !important;color:#6b5c64 !important;}
[data-testid="stSegmentedControl"] button[aria-checked="true"],
[data-testid="stSegmentedControl"] button[data-selected="true"]{
  background:#5E4A5E !important;color:#fff !important;}
/* full-width menu bar: segmented controls fill the width with equal buttons (great on mobile) */
[data-testid="stSegmentedControl"]{width:100% !important;}
[data-testid="stSegmentedControl"] > div{display:flex !important;width:100% !important;gap:5px;}
[data-testid="stSegmentedControl"] button{flex:1 1 0 !important;}

/* kill every dark background: the whole app + the bottom input band must be cream */
.stApp, body, [data-testid="stMain"], [data-testid="stBottom"], [data-testid="stBottom"] > div,
[data-testid="stBottomBlockContainer"]{background:#F2E8E4 !important;}

/* chat input -> rounded white pill with plum send, dark visible text */
[data-testid="stChatInput"]{background:#FFFFFF !important;border:1px solid #E0D3C4 !important;border-radius:26px !important;
  box-shadow:0 4px 18px rgba(90,70,80,.10);}
[data-testid="stChatInput"] textarea, [data-testid="stChatInput"] [contenteditable]{color:#3B2E39 !important;
  font-size:15.5px !important;-webkit-text-fill-color:#3B2E39 !important;}
[data-testid="stChatInput"] textarea::placeholder{color:#A99BA3 !important;-webkit-text-fill-color:#A99BA3 !important;}
[data-testid="stChatInput"] button{background:#5E4A5E !important;border-radius:50% !important;}
[data-testid="stChatInput"] button svg{color:#fff !important;fill:#fff !important;}

/* cards (examples / about / dialogs) */
.card{background:#FCF8F2;border:1px solid #EFE6D8;border-radius:16px;padding:18px 20px;color:#5b4f56;
  font-size:15px;line-height:1.7;}
.card b{color:#3B2E39;} .card .h{color:#5E4A5E;font-size:12px;letter-spacing:1px;text-transform:uppercase;
  margin:2px 0 8px;font-weight:700;}
.qpill{display:inline-block;background:#F4ECDF;border:1px solid #EADFCF;border-radius:12px;padding:8px 12px;
  margin:4px 6px 4px 0;font-size:14px;color:#5b4f56;}
/* self-care tip cards */
.tipgrid{display:grid;grid-template-columns:repeat(2,1fr);gap:11px;margin-top:8px;}
.tip{background:#FBF5EC;border:1px solid #EADFCF;border-radius:15px;padding:13px 15px;}
.tip .emo{font-size:22px;line-height:1;}
.tip .tt{font-weight:700;color:#5E4A5E;font-size:13.5px;margin:6px 0 3px;}
.tip .tt span{color:#A08E97;font-weight:600;}
.tip .td{font-size:12px;color:#6b5560;line-height:1.45;}
.tip .td span{color:#A99BA3;}
.aff{background:linear-gradient(135deg,#F6EBF0,#F3EFE6);border:1px solid #EFD9E2;border-radius:15px;
  padding:13px 15px;font-size:13.5px;color:#5E4A5E;font-weight:600;line-height:1.45;}
.aff .affrw{color:#A08E97;font-weight:500;font-size:12px;margin-top:5px;font-style:italic;}
@media(max-width:640px){.tipgrid{grid-template-columns:1fr;}}

/* welcome / consent */
.hero{text-align:center;padding:4px 0 2px;}
.hero .ill{width:132px;height:132px;margin:0 auto 8px;border-radius:50%;display:flex;align-items:center;
  justify-content:center;font-size:66px;background:radial-gradient(circle at 50% 35%,#EFE1E7 0%,#F6EFE5 72%);
  box-shadow:0 14px 34px rgba(94,74,94,.14);}
.hero .ill img{width:100%;height:100%;object-fit:cover;border-radius:50%;}
.hero .ill.logo{background:radial-gradient(circle at 34% 28%,#9A7C9D 0%,#5E4A5E 72%);box-shadow:0 12px 30px rgba(94,74,94,.32);}
.hero .ill.logo span{font-weight:800;font-size:74px;color:#fff;line-height:1;letter-spacing:-2px;}
.hero h1{font-size:27px;font-weight:700;color:#3B2E39;margin:0 0 3px;}
.hero .tag{font-size:14.5px;color:#A08E97;margin-bottom:12px;}
.hero .lead{font-size:15.5px;line-height:1.6;color:#5b4f56;max-width:440px;margin:0 auto 2px;}
.hero .leadEn{font-size:13px;line-height:1.5;color:#A99BA3;max-width:420px;margin:0 auto 12px;}
.subtext{margin-top:7px;color:#8FA0A6;font-size:13.5px;line-height:1.5;}
.hero .fine{font-size:12.5px;line-height:1.6;color:#A08E97;max-width:440px;margin:0 auto;}
.hero .fine b{color:#5E4A5E;}
.wcard{max-width:460px;margin:4px auto 0;text-align:left;background:#FCF8F2;border:1px solid #EFE6D8;
  border-radius:16px;padding:4px 20px;}
.wrow{padding:11px 0;border-bottom:1px solid #F1E8DA;}
.wrow:last-child{border-bottom:none;}
.wrow b{color:#3B2E39;font-weight:600;font-size:14.5px;} .wrow span{color:#9B8A93;font-size:12.5px;}

@media (max-width:640px){
  .block-container{max-width:100%;padding-top:3.4rem;padding-left:0.8rem;padding-right:0.8rem;padding-bottom:7rem;}
  .topbar .t{font-size:18px;} .topbar .av{width:38px;height:38px;}
  .bubble{max-width:90%;font-size:15px;padding:11px 15px;}
  .hero h1{font-size:24px;} .hero .lead{font-size:15.5px;}
  [data-testid="stChatInput"] textarea{font-size:16px !important;}
}
</style>
""", unsafe_allow_html=True)

GREETING = "Muraho, mama. Wambwira uko umeze uyu munsi?"
GREETING_SUB = "Hello, mama. Tell me how you're feeling today."

# mood shortcuts: (emoji, Kinyarwanda · English, message sent on tap)
MOODS = [
    ("😔", "Agahinda · Sad", "Numva mfite agahinda."),
    ("😟", "Guhangayika · Anxious", "Mfite guhangayika kwinshi."),
    ("😩", "Nananiwe · Tired", "Numva nananiwe cyane."),
    ("🌧️", "Ndi ngenyine · Alone", "Numva ndi ngenyine, nta wundi mfite."),
    ("🙂", "Meze neza · Okay", "Numva meze neza uyu munsi."),
]
GREETING_MSG = {"role": "bot", "text": GREETING, "sub": GREETING_SUB, "danger": False}

# ---------------- Breathe & Help dialogs ----------------
@st.dialog("Guhumeka · Breathe")
def _breathe():
    st.markdown('<div class="card">Fata akanya gato uhumeke. Injiza umwuka mu mazuru ubara kugeza kuri <b>4</b>, '
                'uwushikire kugeza kuri <b>4</b>, hanyuma uwusohore buhoro kugeza kuri <b>6</b>. Bisubiremo inshuro '
                'eshanu.<br><br><i>Take a slow moment. Breathe in through your nose for <b>4</b>, hold for <b>4</b>, '
                'and out gently for <b>6</b>. Repeat five times. You are safe right now.</i></div>',
                unsafe_allow_html=True)

@st.dialog("Siba iki kiganiro? · Delete this chat?")
def _confirm_delete(tid, title):
    st.markdown(f'<div class="card">Uragiye gusiba <b>"{title}"</b>. '
                'Iki gikorwa ntigisubirwaho — ikiganiro nticyakongera kuboneka.<br><br>'
                '<i>You are about to delete this chat. This cannot be undone.</i></div>', unsafe_allow_html=True)
    d1, d2 = st.columns(2)
    if d1.button("Reka · Cancel", use_container_width=True):
        st.session_state.pop("confirm_delete", None); st.rerun()
    if d2.button("Yego, siba · Delete", type="primary", use_container_width=True):
        st.session_state.threads = [x for x in st.session_state.threads if x["id"] != tid]
        if not st.session_state.threads:
            st.session_state.threads = [_new_thread()]
        if st.session_state.current_id == tid:
            st.session_state.current_id = st.session_state.threads[0]["id"]
        if db:
            db.log_action(st.session_state.sid, "delete")
        st.session_state._saved = None
        st.session_state.pop("confirm_delete", None); st.rerun()

@st.dialog("Ubufasha · Help")
def _help():
    st.markdown(f'<div class="card">Niba uri mu kaga cyangwa utekereza kwikomeretsa, hamagara '
                f'<b>{rag.CRISIS_LINE}</b> nonaha, cyangwa uganire n\'umuntu wizeye cyangwa umukozi w\'ubuzima.'
                f'<br><br><i>If you are in danger or thinking of harming yourself, call <b>{rag.CRISIS_LINE}</b> now, '
                'or talk to someone you trust or a health worker. Umubyeyi is emotional support, not a doctor.</i></div>',
                unsafe_allow_html=True)

# ---------------- welcome / consent ----------------
if not st.session_state.get("consented"):
    st.markdown('<style>.block-container{padding-top:1.8rem !important;}</style>', unsafe_allow_html=True)
    # illustration: drop a picture at assets/welcome.png (or .jpg) to use it; otherwise a placeholder shows
    import base64
    _ill = '<div class="ill logo"><span>U</span></div>'
    _adir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets")
    for _n in ("welcome.png", "welcome.jpg", "hero.png"):
        _p = os.path.join(_adir, _n)
        if os.path.exists(_p):
            _mime = "jpeg" if _n.endswith("jpg") else "png"
            _b64 = base64.b64encode(open(_p, "rb").read()).decode()
            _ill = f'<div class="ill"><img src="data:image/{_mime};base64,{_b64}"></div>'
            break
    st.markdown(
        f'<div class="hero">{_ill}'
        '<h1>Muraho, mama.</h1>'
        '<div class="tag">Ntabwo uri wenyine · you\'re not alone</div>'
        '<div class="lead">Ndi hano kukwitaho uko wiyumva. Vugana nanjye mu Kinyarwanda cyangwa Icyongereza.</div>'
        '<div class="leadEn">I\'m here to care for how you feel. Talk with me in Kinyarwanda or English.</div></div>',
        unsafe_allow_html=True)
    st.markdown(
        '<div class="wcard">'
        '<div class="wrow"><b>Umufasha w\'imibereho myiza yo mu mutima gusa.</b><br>'
        '<span>A wellness companion for your mental wellbeing only — not for medical, baby-care, '
        'or other challenges.</span></div>'
        '<div class="wrow"><b>Ku bibazo by\'umubiri cyangwa umwana, reba umuganga. Mu kaga, hamagara '
        f'{rag.CRISIS_LINE}.</b><br>'
        f'<span>For physical or baby concerns, see a health worker; in a crisis call {rag.CRISIS_LINE} '
        '· chats stay on this device.</span></div></div>',
        unsafe_allow_html=True)
    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
    _, mid, _ = st.columns([1, 2.4, 1])
    if mid.button("Tangira ikiganiro  ·  Start  →", use_container_width=True, type="primary"):
        st.session_state.consented = True; st.rerun()
    st.stop()

# ---------------- on-device history (browser localStorage only) ----------------
STORE_KEY = "umubyeyi_threads_v2"
_localS = None
if PERSIST:
    try:
        _localS = LocalStorage()
    except Exception:
        _localS = None

def _new_thread():
    return {"id": uuid.uuid4().hex[:12], "title": "", "ts": int(time.time()), "msgs": [dict(GREETING_MSG)]}

def _persist():
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

# keep the opening greeting in sync with the current wording, even in saved chats
for _t in st.session_state.threads:
    if _t.get("msgs") and _t["msgs"][0]["role"] == "bot":
        _t["msgs"][0]["text"] = GREETING
        _t["msgs"][0]["sub"] = GREETING_SUB

if "sid" not in st.session_state:
    st.session_state.sid = uuid.uuid4().hex[:16]   # anonymous per-session id (not tied to any identity)

def _cur():
    for t in st.session_state.threads:
        if t["id"] == st.session_state.current_id:
            return t
    return st.session_state.threads[0]


def _send(text, force=None):
    """Show the user's message immediately, then generate on the next run so a 'typing' indicator shows."""
    t = _cur()
    t["msgs"].append({"role": "user", "text": text})
    if not t["title"]:
        t["title"] = text.strip()[:36]
    st.session_state.threads = [t] + [x for x in st.session_state.threads if x["id"] != t["id"]]
    st.session_state._awaiting = True
    st.session_state._awaiting_force = force
    st.rerun()


def _respond(force=None):
    """Generate the bot reply for the last user message already in the thread."""
    t = _cur(); msgs = t["msgs"]
    if not msgs or msgs[-1]["role"] != "user":
        return
    text = msgs[-1]["text"]
    history = [{"role": m["role"], "text": m["text"]} for m in msgs[:-1]]
    try:
        t0 = time.time()
        r = rag.answer(text, force_lang=force, history=history)
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

def bubble(m):
    if m["role"] == "user":
        return f'<div class="row me"><div class="bubble me">{m["text"]}</div></div>'
    cls = "bubble bot danger" if m.get("danger") else "bubble bot"
    inner = m["text"]
    if m.get("sub"):   # a fixed English rendering under the Kinyarwanda (used for the greeting)
        inner += f'<div class="subtext">{m["sub"]}</div>'
    return f'<div class="row"><div class="{cls}">{inner}</div></div>'

# ---------------- sidebar (Claude-style: brand + collapse, New chat, nav, Recents) ----------------
with st.sidebar:
    st.markdown('<div class="sbrand">Umubyeyi</div>', unsafe_allow_html=True)
    if st.button("＋  Ikiganiro gishya · New chat", use_container_width=True, key="newchat"):
        nt = _new_thread()
        st.session_state.threads = [nt] + st.session_state.threads
        st.session_state.current_id = nt["id"]
        st.session_state._saved = None
        if db:
            db.log_action(st.session_state.sid, "new_chat")
        st.rerun()
    admin = st.query_params.get("admin") == "1"
    nav_items = ["Ikiganiro", "Kwiyitaho", "Ibyerekeye"]   # Chat · Self-care · About (compact for the top menu bar)
    if admin:
        nav_items.append("Imibare")
    if len(st.session_state.threads) > 1 or bool(st.session_state.threads[0]["title"]):
        st.markdown('<div class="sblbl">Ibiganiro · Recent</div>', unsafe_allow_html=True)
        for t in st.session_state.threads[:25]:
            title = t["title"] or "Ikiganiro gishya · New chat"
            mark = "•  " if t["id"] == st.session_state.current_id else ""
            rc1, rc2 = st.columns([5, 1.25])
            if rc1.button(mark + title, key=f"th_{t['id']}", use_container_width=True):
                st.session_state.current_id = t["id"]; st.rerun()
            with rc2.popover("⋯", use_container_width=True):
                new_name = st.text_input("Guhindura izina · Rename", value=t["title"],
                                         key=f"rn_{t['id']}", placeholder="Izina · name")
                pc1, pc2 = st.columns(2)
                if pc1.button("Bika · Save", key=f"sv_{t['id']}", use_container_width=True):
                    if new_name.strip():
                        t["title"] = new_name.strip()[:40]
                        if db:
                            db.log_action(st.session_state.sid, "rename")
                        st.session_state._saved = None; st.rerun()
                if pc2.button("Siba · Delete", key=f"del_{t['id']}", use_container_width=True):
                    st.session_state.confirm_delete = {"id": t["id"], "title": title}
                    st.rerun()

# a delete only happens after explicit confirmation (no undo) — targets the exact chat chosen
_cd = st.session_state.get("confirm_delete")
if _cd:
    _confirm_delete(_cd["id"], _cd["title"])

# ---------------- top bar: ☰ history toggle + navigation menu (mobile-friendly) ----------------
st.session_state.setdefault("panel", False)          # left history panel collapsed by default
if not st.session_state.panel:
    st.markdown('<style>[data-testid="stSidebar"]{display:none !important;}</style>', unsafe_allow_html=True)
_mc, _nc = st.columns([1, 6.5])
if _mc.button("✕" if st.session_state.panel else "☰", key="panel_toggle", help="Ibiganiro · your chats"):
    st.session_state.panel = not st.session_state.panel; st.rerun()
with _nc:
    view = st.segmented_control("nav", nav_items, default=nav_items[0],
                                label_visibility="collapsed", key="topnav") or nav_items[0]

# ---------------- views ----------------
if view.startswith("Ikiganiro"):
    hc1, hc2, hc3 = st.columns([5.2, 1.6, 1.4])
    hc1.markdown('<div class="topbar"><div class="av"></div><div>'
                 '<div class="t">Umubyeyi</div>'
                 '<div class="s">Umufasha w\'imibereho myiza yo mu mutima · a mental-wellbeing companion</div>'
                 '</div></div>', unsafe_allow_html=True)
    if hc2.button("Guhumeka · Breathe", use_container_width=True):
        _breathe()
    if hc3.button("Ubufasha · Help", use_container_width=True):
        _help()

    msgs = _cur()["msgs"]
    for m in msgs:
        st.markdown(bubble(m), unsafe_allow_html=True)

    # after the user's message is on screen, generate the reply while showing ONE typing indicator
    if st.session_state.get("_awaiting"):
        with st.spinner("Umubyeyi arimo yandika… · Umubyeyi is typing…"):
            _respond(st.session_state.get("_awaiting_force"))
        st.session_state._awaiting = False
        st.rerun()

    if db and msgs[-1]["role"] == "bot" and len(msgs) > 1 and not st.session_state.get("_rated"):
        st.markdown('<div style="font-size:13px;color:#A08E97;margin:2px 0 6px">Iki gisubizo cyagufashije? · Was this helpful?</div>',
                    unsafe_allow_html=True)
        fc1, fc2, _ = st.columns([1.3, 1.6, 3])
        meta = st.session_state.get("_last", {})
        if fc1.button("Byoroheje · Helpful", key="fb_up"):
            db.log_feedback(st.session_state.sid, 1, meta.get("lang"), meta.get("mode"))
            st.session_state._rated = True; st.rerun()
        if fc2.button("Ntibyanfashije · Not really", key="fb_down"):
            db.log_feedback(st.session_state.sid, -1, meta.get("lang"), meta.get("mode"))
            st.session_state._rated = True; st.rerun()

    if len(msgs) <= 1:   # mood shortcuts on a fresh chat
        cols = st.columns(3)
        for i, (emo, lbl, q) in enumerate(MOODS):
            if cols[i % 3].button(f"{emo}  {lbl}", key=f"mood{i}", use_container_width=True):
                _send(q)

    st.markdown('<div class="foot">Umufasha w\'imibereho myiza gusa · si uw\'ibindi bibazo · '
                'mu kaga hamagara 114  ·  a wellness companion only — not for other challenges · '
                'in a crisis call 114</div>', unsafe_allow_html=True)
    prompt = st.chat_input("Andika uko wiyumva... · Type how you feel...")
    if prompt and prompt.strip():
        _send(prompt.strip())

elif view.startswith("Kwiyitaho"):
    st.markdown('<div class="topbar"><div class="av"></div><div>'
                '<div class="t">Kwiyitaho · Self-care</div>'
                '<div class="s">Wowe wanitaye ku mwana - noneho niwiyiteho · you cared for your baby, now care for you</div>'
                '</div></div>', unsafe_allow_html=True)

    # gentle self-care tips for the mother (general wellbeing guidance, bilingual)
    TIPS = [
        ("🤝", "Shaka ubufasha", "Reach out", "Ganira n'umuntu wizeye cyangwa umukozi w'ubuzima.", "Talk to someone you trust or a health worker."),
        ("👪", "Wubake abagufasha", "Build support", "Egera uwo mwashakanye, umuryango n'incuti.", "Lean on your partner, family, and friends."),
        ("🌸", "Wite ku mutima wawe", "Self-care", "Fata udukanya duto wiyibagiza, ushake ibikunezeza bito.", "Take small moments for yourself; small joys matter."),
        ("😴", "Ruhuka bihagije", "Rest", "Sinzira igihe umwana asinziriye, usabe ubufasha nijoro.", "Sleep when the baby sleeps; ask for help at night."),
        ("🚶", "Imyitozo yoroheje", "Gentle movement", "Genda urugendo rugufi cyangwa unyeganyege gato.", "A short walk or light stretching lifts your mood."),
        ("🥗", "Kurya indyo yuzuye", "Nourish", "Fata indyo yuzuye kugira ngo ugire imbaraga.", "Balanced meals help your energy and mood."),
        ("🧘", "Humeka utuze", "Breathe", "Guhumeka gahoro bishobora gutuza umutima.", "A few slow breaths can calm a hard moment."),
        ("💬", "Vuga uko wiyumva", "Share openly", "Vuga ibyiyumvo byawe utagira ipfunwe.", "Speak your feelings without guilt; it's a strength."),
    ]
    cards = "".join(
        f'<div class="tip"><div class="emo">{e}</div>'
        f'<div class="tt">{rw} · <span>{en}</span></div>'
        f'<div class="td">{drw}<br><span>{den}</span></div></div>'
        for e, rw, en, drw, den in TIPS)
    st.markdown(
        '<div class="h" style="margin:6px 0 2px;color:#5E4A5E;font-size:12px;letter-spacing:1px;'
        'text-transform:uppercase;font-weight:700">Inama zo kwita ku mutima · Self-care tips</div>'
        f'<div class="tipgrid">{cards}</div>', unsafe_allow_html=True)

    # gentle affirmations / reminders for hard days (bilingual)
    AFFIRM = [
        ("You are not failing - you are learning.", "Ntabwo unaniwe - uriga."),
        ("It's okay not to be okay - this is a huge change.", "Biremewe kutamererwa neza - iyi ni impinduka ikomeye."),
        ("The house can wait; you and your baby cannot.", "Inzu irashobora gutegereza; wowe n'umwana oya."),
        ("Rest is productive - your healing is the priority.", "Kuruhuka ni ingirakamaro - gukira kwawe ni ingenzi."),
        ("Tears are okay; they don't erase the joy.", "Amarira aremewe; ntahindura ibyishimo."),
        ("Your body is a miracle - be gentle with it.", "Umubiri wawe ni igitangaza - wugwize neza."),
        ("Asking for help is a sign of strength, not weakness.", "Gusaba ubufasha ni ubutwari, si intege nke."),
        ("You are exactly what your baby needs.", "Uri ibyo umwana wawe akeneye byuzuye."),
        ("You are an amazing parent - even on the hard days.", "Uri umubyeyi mwiza - ndetse no ku minsi igoye."),
    ]
    affcards = "".join(f'<div class="aff">💗 {en}<div class="affrw">{rw}</div></div>' for en, rw in AFFIRM)
    st.markdown(
        '<div class="h" style="margin:20px 0 2px;color:#5E4A5E;font-size:12px;letter-spacing:1px;'
        'text-transform:uppercase;font-weight:700">Amagambo yo kongera imbaraga · Gentle reminders</div>'
        f'<div class="tipgrid">{affcards}</div>'
        '<div class="scopebar" style="margin-top:14px">Ntabwo uri wenyine · you are not alone. '
        'Wihangane, gukira bisaba igihe · be patient, recovery takes time.</div>',
        unsafe_allow_html=True)

elif view.startswith("Imibare"):
    st.markdown('<div class="topbar"><div class="av"></div><div><div class="t">Imibare · Insights</div>'
                '<div class="s">Anonymous usage & feedback · no message text stored</div></div></div>',
                unsafe_allow_html=True)
    ins = db.insights() if db else None
    if not ins:
        st.markdown('<div class="card">Analytics not configured yet. Set <b>DATABASE_URL</b> to a Postgres '
                    'instance (production); otherwise a local SQLite file is used.</div>', unsafe_allow_html=True)
    else:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Answers", ins["answers"]); c2.metric("Sessions", ins["sessions"])
        c3.metric("Grounded", f"{ins['grounded_rate']*100:.0f}%"); c4.metric("Avg latency", f"{ins['avg_latency_ms']} ms")
        c5, c6 = st.columns(2)
        c5.metric("Feedback", ins["feedback_total"])
        c6.metric("Positive", "—" if ins["feedback_positive_rate"] is None else f"{ins['feedback_positive_rate']*100:.0f}%")
        st.markdown(f'<div class="card"><div class="h">By language</div>{ins["by_language"]}'
                    f'<div class="h" style="margin-top:10px">By mode</div>{ins["by_mode"]}'
                    f'<div class="h" style="margin-top:10px">Chat actions</div>{ins.get("by_action", {})}'
                    f'<div class="disc">Backend: <b>{ins["backend"]}</b> · never stores message text or identity.</div></div>',
                    unsafe_allow_html=True)

else:  # About
    st.markdown('<div class="topbar"><div class="av"></div><div><div class="t">Ibyerekeye Umubyeyi</div>'
                '<div class="s">About</div></div></div>', unsafe_allow_html=True)
    st.markdown('<div class="card"><b>Umubyeyi</b> ni umufasha uvuga Ikinyarwanda n\'Icyongereza, witeguye kugufasha '
                'uko wiyumva mu mezi 6 ya mbere nyuma yo kubyara — agahinda, guhangayika, kunanirwa, no guhangana. '
                'Ntiyita ku bibazo by\'umubiri cyangwa byo kwita ku mwana.<br><br>'
                '<i>Umubyeyi is a bilingual companion for the emotional wellbeing of first-time mothers in the first '
                '6 months after birth. It does not cover medical or baby-care questions, and always reminds you to '
                'see a health worker when needed.</i>'
                f'<div class="disc">Si serivisi y\'ubuvuzi · niba uri mu kaga, hamagara {rag.CRISIS_LINE}. '
                f'Not medical care; in a crisis call {rag.CRISIS_LINE}.</div></div>', unsafe_allow_html=True)

_persist()
