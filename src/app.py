"""
Umubyeyi - Streamlit frontend (grounded generation).
A gentle postpartum (0-6mo) companion for first-time mothers in Rwanda.

Type a question in Kinyarwanda or English -> answered in the same language, grounded on
validated maternal knowledge (see src/rag.py). Run:  streamlit run src/app.py
"""
import csv
import datetime
import json
import os

import streamlit as st

import rag  # src/ is on sys.path when run via `streamlit run src/app.py`

# On Streamlit Community Cloud secrets live in st.secrets, not env vars -> bridge them so
# rag.py (which reads os.environ) picks up the Gemini key and feedback credentials.
try:
    for _k in ("GEMINI_API_KEY", "GEMINI_MODEL", "GCP_SERVICE_ACCOUNT", "FEEDBACK_SHEET_ID"):
        if _k in st.secrets:
            os.environ[_k] = str(st.secrets[_k])
except Exception:
    pass

st.set_page_config(page_title="Umubyeyi", layout="centered")

# ----------------------------------------------------------------- theme (CSS)
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Quicksand:wght@400;500;600;700&display=swap');
[data-testid="stAppViewContainer"]{background:linear-gradient(160deg,#FBEFFb 0%,#F6F2FB 45%,#FFF1EA 100%);}
[data-testid="stHeader"]{background:transparent;} #MainMenu, footer{visibility:hidden;}
.block-container{max-width:560px;padding-top:1.2rem;padding-bottom:6rem;font-family:'Quicksand',Segoe UI,sans-serif;}
.umu-header{background:linear-gradient(120deg,#FFB59E 0%,#E6A6D9 55%,#C9B6F2 100%);color:#fff;
  border-radius:26px;padding:20px 24px;margin-bottom:18px;box-shadow:0 10px 28px rgba(201,182,242,.45);}
.umu-header .title{font-size:23px;font-weight:700;} .umu-header .sub{font-size:13.5px;font-weight:500;opacity:.95;margin-top:2px;}
.row{display:flex;margin-bottom:13px;} .row.me{justify-content:flex-end;}
.bubble{max-width:84%;padding:12px 16px;font-size:14.5px;line-height:1.55;font-family:'Quicksand',sans-serif;
  box-shadow:0 3px 12px rgba(150,120,180,.14);white-space:pre-wrap;}
.bubble.bot{background:#fff;color:#4A3B57;border-radius:20px 20px 20px 7px;}
.bubble.me{background:linear-gradient(120deg,#FFCBB0,#FFB59E);color:#5B3A52;font-weight:500;border-radius:20px 20px 7px 20px;}
.danger{background:#FFE9EC;border-left:4px solid #F2839A;border-radius:12px;padding:12px 15px;color:#A33D54;font-weight:500;}
.stButton button,[data-testid="stButton"] button,button[data-testid^="stBaseButton"]{
  background:linear-gradient(120deg,#FFB59E 0%,#E6A6D9 55%,#C9B6F2 100%) !important;border:none !important;
  border-radius:18px !important;font-weight:600;font-family:'Quicksand',sans-serif;padding:12px 18px;}
.stButton button,.stButton button *,button[data-testid^="stBaseButton"],button[data-testid^="stBaseButton"] *{
  color:#fff !important;-webkit-text-fill-color:#fff !important;}
[data-testid="stChatInput"] > div{border-radius:24px !important;border:1.5px solid #C9B6F2 !important;
  background:#4A3B57 !important;box-shadow:0 4px 16px rgba(201,182,242,.25);}
textarea{color:#fff !important;-webkit-text-fill-color:#fff !important;caret-color:#FFD9C2 !important;opacity:1 !important;}
[data-testid="stChatInput"] textarea::placeholder{color:#D9C9F2 !important;-webkit-text-fill-color:#D9C9F2 !important;opacity:1 !important;}
[data-testid="stChatInputSubmitButton"],[data-testid="stChatInputSubmitButton"] svg{color:#FFC9B0 !important;fill:#FFC9B0 !important;}
[data-testid="stSpinner"],[data-testid="stSpinner"] p{color:#7A5AA8 !important;font-weight:600;}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="umu-header"><div class="title">Umubyeyi</div>'
            '<div class="sub">umufasha wawe nyuma yo kubyara · a companion for the first 6 months</div></div>',
            unsafe_allow_html=True)

GREETING = ("Muraho, mama. Ndi hano kugufasha mu mezi 6 ya mbere nyuma yo kubyara. "
            "Wambaza icyo ushaka ku buzima bwawe cyangwa ubw'umwana — mu Kinyarwanda cyangwa Icyongereza.")

# ----------------------------------------------------------------- consent gate
if not st.session_state.get("consented"):
    st.markdown(
        '<div class="bubble bot" style="max-width:100%">'
        '<div style="color:#8A5A86;font-weight:600;margin-bottom:6px;">Mbere yo gutangira</div>'
        "<div>Iyi ni porogaramu y'ubushakashatsi bw'umunyeshuri, si serivisi y'ubuvuzi cyangwa "
        "iy'ubutabazi bwihutirwa. Amakuru itanga ni rusange, ntabwo asimbura inama y'umuganga.</div>"
        f'<div style="background:#FFF0E8;border-left:3px solid #FFB59E;border-radius:10px;padding:9px 13px;margin-top:10px;color:#9A5C44;">'
        f"Niba ufite ibitekerezo byo kwigirira nabi cyangwa kwangiza umwana, hamagara ako kanya: <b>{rag.CRISIS_LINE}</b>.</div>"
        "<div style=\"margin-top:10px\">Ntukandike amazina cyangwa amakuru akuranga.</div></div>",
        unsafe_allow_html=True)
    if st.button("Ndabyumvise kandi ndabyemeye — Komeza", use_container_width=True):
        st.session_state.consented = True
        st.rerun()
    st.stop()

# ----------------------------------------------------------------- state
if "msgs" not in st.session_state:
    st.session_state.msgs = [{"role": "bot", "text": GREETING, "danger": False}]
if "logged" not in st.session_state:
    st.session_state.logged = set()


# ----------------------------------------------------------------- feedback -> Google Sheet (CSV fallback)
@st.cache_resource(show_spinner=False)
def _sheet():
    raw, sid = os.environ.get("GCP_SERVICE_ACCOUNT"), os.environ.get("FEEDBACK_SHEET_ID")
    if not raw or not sid:
        return None
    try:
        import gspread
        from google.oauth2.service_account import Credentials
        creds = Credentials.from_service_account_info(
            json.loads(raw), scopes=["https://www.googleapis.com/auth/spreadsheets"])
        return gspread.authorize(creds).open_by_key(sid).sheet1
    except Exception:
        return None


def log_feedback(user_text, bot, score):
    row = [datetime.datetime.utcnow().isoformat(timespec="seconds"), user_text,
           bot.get("language", ""), "danger" if bot.get("danger") else "answer",
           "up" if score == 1 else "down"]
    sh = _sheet()
    if sh is not None:
        try:
            sh.append_row(row); return
        except Exception:
            pass
    from pathlib import Path
    p = Path(__file__).resolve().parents[1] / "feedback_local.csv"
    new = not p.exists()
    with open(p, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["timestamp", "message", "language", "kind", "vote"])
        w.writerow(row)


def render(m):
    if m["role"] == "user":
        return f'<div class="row me"><div class="bubble me">{m["text"]}</div></div>'
    inner = f'<div class="danger">{m["text"]}</div>' if m.get("danger") else m["text"]
    return f'<div class="row"><div class="bubble bot">{inner}</div></div>'


# ----------------------------------------------------------------- chat
if prompt := st.chat_input("Andika hano... / Type here..."):
    st.session_state.msgs.append({"role": "user", "text": prompt})
    with st.spinner("Tegereza gato, ndategura igisubizo..."):
        try:
            res = rag.answer(prompt)
            st.session_state.msgs.append({"role": "bot", "text": res["answer"],
                                          "danger": res.get("danger", False),
                                          "language": res.get("language", "en")})
        except Exception as e:
            st.session_state.msgs.append({"role": "bot",
                "text": f"Mbabarira, hari ikibazo cya tekiniki. ({e})", "danger": False})

for i, m in enumerate(st.session_state.msgs):
    st.markdown(render(m), unsafe_allow_html=True)
    if i > 0 and m["role"] == "bot" and not m.get("danger"):
        score = st.feedback("thumbs", key=f"fb_{i}")
        if score is not None and i not in st.session_state.logged:
            log_feedback(st.session_state.msgs[i - 1].get("text", ""), m, score)
            st.session_state.logged.add(i)
