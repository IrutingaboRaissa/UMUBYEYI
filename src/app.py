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
.block-container{max-width:720px;padding-top:1.4rem;padding-bottom:6.5rem;}
[data-testid="stSidebar"]{background:#0f1d15;border-right:1px solid #1d3528;}
[data-testid="stSidebar"] *{color:#DCEFE3 !important;}
#MainMenu, footer, [data-testid="stToolbar"]{visibility:hidden;}

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

/* suggestion chips */
.exhint{color:#8FB09C;font-size:13.5px;margin:4px 0 10px;font-weight:500;}
.stButton button{background:#18291f !important;color:#E7F2EB !important;border:1px solid #2c4636 !important;
  border-radius:22px !important;font-size:14px !important;font-weight:500 !important;padding:9px 16px !important;
  text-align:left !important;transition:all .15s ease;}
.stButton button:hover{border-color:#3a6b4c !important;transform:translateY(-1px);background:#22392b !important;}

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
  .block-container{max-width:100%;padding-left:0.7rem;padding-right:0.7rem;padding-bottom:6rem;}
  .apphead .t{font-size:18px;} .bubble{max-width:88%;font-size:15px;} .card{font-size:14px;}
  [data-testid="stChatInput"] textarea{font-size:16px !important;}  /* >=16px stops iOS zoom */
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

# ---------------- consent gate ----------------
if not st.session_state.get("consented"):
    st.markdown('<div class="apphead"><div class="logo">U</div><div>'
                '<div class="t">Umubyeyi</div>'
                '<div class="s">Umufasha wawe nyuma yo kubyara · a companion after birth</div></div></div>',
                unsafe_allow_html=True)
    st.markdown('<div class="card"><div class="h">Mbere yo gutangira · Before you start</div>'
                'Umubyeyi akugufasha ku byo wiyumva nyuma yo kubyara (agahinda, guhangayika, kunanirwa). '
                'Si serivisi y\'ubuvuzi, kandi ntiyita ku bibazo by\'umubiri cyangwa byo kwita ku mwana — '
                'ku byo, ganira n\'umukozi w\'ubuzima. <i>Umubyeyi supports how you feel after birth. It is '
                'not medical care and does not cover physical or baby-care questions — please see a health '
                'worker for those.</i><br><br>'
                f'Niba uri mu kaga, hamagara: <b style="color:#E9C46A">{rag.CRISIS_LINE}</b>. '
                'Ntukandike amazina cyangwa amakuru akuranga.<br><br>'
                '<span style="color:#8FB09C;font-size:13px">Ikiganiro cyawe kibikwa gusa muri iyi telefone/mudasobwa '
                '(muri iyi browser), ntikibikwa ku byuma byacu. Koresha “Ikiganiro gishya” kugira usibe. '
                '<i>Your conversation is saved only on this device (in your browser), never on our servers. '
                'Use “New chat” to clear it.</i></span></div>', unsafe_allow_html=True)
    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
    if st.button("Ndabyumvise, ngwino dutangire  →", use_container_width=True):
        st.session_state.consented = True; st.rerun()
    st.stop()

# ---------- on-device memory (browser localStorage only; nothing leaves the device) ----------
STORE_KEY = "umubyeyi_thread_v1"
GREETING_MSG = {"role": "bot", "text": GREETING, "danger": False}
_localS = None
if PERSIST:
    try:
        _localS = LocalStorage()
    except Exception:
        _localS = None


def _persist():
    """Write the current thread to the browser, only when it changed."""
    if not _localS:
        return
    try:
        payload = json.dumps(st.session_state.msgs, ensure_ascii=False)
        if st.session_state.get("_saved") != payload:
            _localS.setItem(STORE_KEY, payload, key="ls_set")
            st.session_state._saved = payload
    except Exception:
        pass


if "msgs" not in st.session_state:
    st.session_state.msgs = [GREETING_MSG]
    st.session_state._restored = not bool(_localS)   # nothing to restore without persistence

# a returning user's saved thread loads once (the browser resolves it on the first rerun)
if _localS and not st.session_state.get("_restored"):
    try:
        raw = _localS.getItem(STORE_KEY)
        if raw is not None:
            data = json.loads(raw)
            if isinstance(data, list) and data:
                st.session_state.msgs = data
            st.session_state._restored = True
    except Exception:
        st.session_state._restored = True


if "sid" not in st.session_state:
    st.session_state.sid = uuid.uuid4().hex[:16]   # anonymous per-session id (not tied to any identity)


def ask(text, force=None):
    st.session_state._restored = True   # once she interacts, stop trying to restore old state
    history = [{"role": m["role"], "text": m["text"]} for m in st.session_state.msgs]  # prior turns for context
    st.session_state.msgs.append({"role": "user", "text": text})
    try:
        t0 = time.time()
        r = rag.answer(text, force_lang=force, history=history)
        latency = int((time.time() - t0) * 1000)
        st.session_state.msgs.append({"role": "bot", "text": r["answer"], "danger": r.get("danger", False)})
        # anonymous analytics only — NO message text is stored
        if db:
            top = r.get("sources") or []
            db.log_event(st.session_state.sid, r.get("language"), r.get("mode"),
                         r.get("grounded"), (top[0]["sim"] if top else 0.0), latency)
        st.session_state._last = {"lang": r.get("language"), "mode": r.get("mode")}
        st.session_state._rated = False
    except Exception as e:
        st.session_state.msgs.append({"role": "bot", "text": f"Mbabarira, hari ikibazo. ({e})", "danger": False})


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
    st.markdown('<div class="sblbl">Ururimi · Language</div>', unsafe_allow_html=True)
    pref = st.selectbox("lang", ["Auto", "RW", "EN"], label_visibility="collapsed")
    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
    if st.button("＋ Ikiganiro gishya · New chat", use_container_width=True):
        st.session_state.msgs = [GREETING_MSG]
        st.session_state._restored = True
        st.session_state._saved = None      # force the stored thread to be overwritten
        st.rerun()

# ---------------- views ----------------
if view.startswith("Ikiganiro"):
    st.markdown('<div class="apphead"><div class="logo">U</div><div>'
                '<div class="t">Umubyeyi</div>'
                '<div class="s"><span class="dot"></span>Wellness chat · Kinyarwanda / English</div></div></div>',
                unsafe_allow_html=True)
    for m in st.session_state.msgs:
        st.markdown(bubble(m), unsafe_allow_html=True)

    # subtle thumbs feedback on the latest answer (feeds anonymous analytics; no text stored)
    last = st.session_state.msgs[-1]
    if db and last["role"] == "bot" and len(st.session_state.msgs) > 1 and not st.session_state.get("_rated"):
        st.markdown('<div class="exhint">Iki gisubizo cyagufashije? · Was this helpful?</div>', unsafe_allow_html=True)
        fc1, fc2, _ = st.columns([1.3, 1.6, 3])
        meta = st.session_state.get("_last", {})
        if fc1.button("Byoroheje · Helpful", key="fb_up"):
            db.log_feedback(st.session_state.sid, 1, meta.get("lang"), meta.get("mode"))
            st.session_state._rated = True; st.rerun()
        if fc2.button("Ntibyanfashije · Not really", key="fb_down"):
            db.log_feedback(st.session_state.sid, -1, meta.get("lang"), meta.get("mode"))
            st.session_state._rated = True; st.rerun()

    if len(st.session_state.msgs) <= 1:   # suggestion chips on a fresh chat
        st.markdown('<div class="exhint">Wagerageza kubaza · You could ask:</div>', unsafe_allow_html=True)
        cols = st.columns(2)
        for i, (lbl, q) in enumerate(EXAMPLES):
            if cols[i % 2].button(q, key=f"ex{i}", use_container_width=True):
                ask(q, {"RW": "rw", "EN": "en"}.get(pref)); st.rerun()

    prompt = st.chat_input("Andika uko wiyumva... · Type how you feel...")
    if prompt and prompt.strip():
        ask(prompt.strip(), {"RW": "rw", "EN": "en"}.get(pref)); st.rerun()

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
