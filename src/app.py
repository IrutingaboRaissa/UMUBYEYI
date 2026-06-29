"""
Umubyeyi - Streamlit frontend (clean, mother-facing).
Bilingual grounded-generation postpartum assistant for first-time mothers in Rwanda.
Run:  streamlit run src/app.py
"""
import os
import streamlit as st

import rag  # src/ is on sys.path when run via `streamlit run src/app.py`

try:
    for _k in ("GEMINI_API_KEY", "GEMINI_MODEL"):
        if _k in st.secrets:
            os.environ[_k] = str(st.secrets[_k])
except Exception:
    pass

st.set_page_config(page_title="Umubyeyi", layout="centered", initial_sidebar_state="expanded")

st.markdown("""
<style>
html, body, [class*="css"], [data-testid="stAppViewContainer"] *, [data-testid="stSidebar"] *{
  font-family:'Times New Roman', Times, serif !important;}
[data-testid="stAppViewContainer"]{background:#13211a;}
.block-container{max-width:760px;padding-top:2rem;padding-bottom:5rem;}
[data-testid="stSidebar"]{background:#102017;border-right:1px solid #1d3528;}
[data-testid="stSidebar"] *{color:#DCEFE3 !important;}

/* sidebar brand */
.brand{display:flex;align-items:center;gap:11px;margin:2px 0 6px;}
.brand .mono{background:#E9C46A;color:#102017;width:40px;height:40px;border-radius:12px;
  display:flex;align-items:center;justify-content:center;font-size:22px;font-weight:700;}
.brand .nm{font-size:21px;font-weight:700;color:#fff;line-height:1.1;}
.brand .sub{font-size:12px;color:#9FBCA8;}

/* header */
.apphead{text-align:center;margin-bottom:22px;}
.apphead .t{font-size:30px;font-weight:700;color:#F3EFE3;letter-spacing:.3px;}
.apphead .s{font-size:15px;color:#9FBCA8;margin-top:2px;}

/* chat bubbles */
.row{display:flex;margin-bottom:14px;} .row.me{justify-content:flex-end;}
.bubble{max-width:80%;padding:13px 17px;font-size:16px;line-height:1.6;border-radius:16px;white-space:pre-wrap;
  box-shadow:0 2px 10px rgba(0,0,0,.18);}
.bubble.bot{background:#F5F0E6;color:#2A2620;border-bottom-left-radius:6px;}
.bubble.me{background:#2E7D52;color:#fff;border-bottom-right-radius:6px;}
.bubble.danger{background:#F5E3DF;color:#7A2E22;border-left:4px solid #C75B45;}
.disc{margin-top:9px;padding-top:8px;border-top:1px dashed #d9cfa8;font-size:12.5px;color:#8a7f5f;}

/* example chips */
.exhint{color:#9FBCA8;font-size:14px;margin:6px 0 10px;}
[data-testid="stForm"]{border:none;padding:0;}
.stTextInput input{background:#19281f !important;color:#fff !important;border:1px solid #29412f !important;
  font-family:'Times New Roman',serif !important;font-size:16px !important;border-radius:12px !important;padding:11px 14px !important;}
.stTextInput input::placeholder{color:#7f9a8a !important;}
[data-testid="stForm"] button, .stButton button{background:#2E7D52 !important;color:#fff !important;border:none !important;
  border-radius:12px !important;font-family:'Times New Roman',serif !important;font-weight:600;}
.stButton button:hover{background:#27693f !important;}
[data-baseweb="select"] > div{background:#19281f !important;border-color:#29412f !important;color:#fff !important;}
.about{background:#19281f;border:1px solid #29412f;border-radius:14px;padding:18px 20px;color:#D8E6DD;
  font-size:15px;line-height:1.7;}
.about b{color:#fff;} .about .h{color:#E9C46A;font-size:13px;letter-spacing:1px;text-transform:uppercase;margin-bottom:8px;}
</style>
""", unsafe_allow_html=True)

GREETING = ("Muraho, mama. Ndi hano kugufasha mu mezi 6 ya mbere nyuma yo kubyara — "
            "ku buzima bwawe n'ubw'umwana. Wambaza icyo ushaka, mu Kinyarwanda cyangwa Icyongereza.")

EXAMPLES = [
    ("Umwana", "Umwana wanjye ararira cyane nijoro, nakora iki?"),
    ("Konsa", "Nkonsa umwana wanjye inshuro zingahe?"),
    ("Gukira", "Nshobora gutangira kugenda ryari nyuma yo kubagwa?"),
    ("Iyumva", "Numva mfite agahinda kuva nabyaye."),
]

# ---------------- consent gate ----------------
if not st.session_state.get("consented"):
    st.markdown('<div class="apphead"><div class="t">Umubyeyi</div>'
                '<div class="s">Umufasha wawe nyuma yo kubyara · a companion after birth</div></div>', unsafe_allow_html=True)
    st.markdown('<div class="about"><div class="h">Mbere yo gutangira · Before you start</div>'
                'Iyi ni porogaramu y\'ubushakashatsi, si serivisi y\'ubuvuzi. Amakuru ni rusange. '
                '<i>This is a research prototype, not medical care; information is general.</i><br><br>'
                f'Niba uri mu kaga, hamagara: <b style="color:#E9C46A">{rag.CRISIS_LINE}</b>. '
                'Ntukandike amazina cyangwa amakuru akuranga.</div>', unsafe_allow_html=True)
    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
    if st.button("Ndabyumvise, ngwino dutangire", use_container_width=True):
        st.session_state.consented = True; st.rerun()
    st.stop()

if "msgs" not in st.session_state:
    st.session_state.msgs = [{"role": "bot", "text": GREETING, "danger": False}]


def ask(text, force=None):
    history = [{"role": m["role"], "text": m["text"]} for m in st.session_state.msgs]  # prior turns for context
    st.session_state.msgs.append({"role": "user", "text": text})
    try:
        r = rag.answer(text, force_lang=force, history=history)
        st.session_state.msgs.append({"role": "bot", "text": r["answer"], "danger": r.get("danger", False)})
    except Exception as e:
        st.session_state.msgs.append({"role": "bot", "text": f"Mbabarira, hari ikibazo. ({e})", "danger": False})


def bubble(m):
    if m["role"] == "user":
        return f'<div class="row me"><div class="bubble me">{m["text"]}</div></div>'
    cls = "bubble bot danger" if m.get("danger") else "bubble bot"
    return f'<div class="row"><div class="{cls}">{m["text"]}</div></div>'


with st.sidebar:
    st.markdown('<div class="brand"><div class="mono">U</div><div>'
                '<div class="nm">Umubyeyi</div><div class="sub">Umufasha wawe</div></div></div>', unsafe_allow_html=True)
    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
    view = st.radio("nav", ["Ikiganiro · Chat", "Ingero · Examples", "Ibyerekeye · About"], label_visibility="collapsed")

    # --- TEMPORARY diagnostics (remove before final submission) ---
    with st.expander("Diagnostics"):
        in_secrets = False
        try:
            in_secrets = "GEMINI_API_KEY" in st.secrets
        except Exception as _e:
            st.write(f"st.secrets error: {_e}")
        key = os.environ.get("GEMINI_API_KEY", "")
        st.write("key in st.secrets:", in_secrets)
        st.write("key in environment:", bool(key))
        if key:
            st.write("key length:", len(key), "· starts:", key[:4])
        try:
            from google import genai  # noqa: F401
            st.write("google-genai import: OK")
        except Exception as _e:
            st.write("google-genai import FAILED:", str(_e)[:120])
        if st.button("Test generation"):
            try:
                out = rag.answer("hello")
                st.write("mode:", out.get("mode"))
                st.write(out.get("answer", "")[:200])
            except Exception as _e:
                st.write("test FAILED:", str(_e)[:200])

# ---------------- views ----------------
if view.startswith("Ikiganiro"):
    st.markdown('<div class="apphead"><div class="t">Umubyeyi</div>'
                '<div class="s">Wellness chat · Kinyarwanda / English</div></div>', unsafe_allow_html=True)
    for m in st.session_state.msgs:
        st.markdown(bubble(m), unsafe_allow_html=True)

    if len(st.session_state.msgs) <= 1:   # show example chips on a fresh chat
        st.markdown('<div class="exhint">Wagerageza kubaza · You could ask:</div>', unsafe_allow_html=True)
        cols = st.columns(2)
        for i, (lbl, q) in enumerate(EXAMPLES):
            if cols[i % 2].button(q, key=f"ex{i}", use_container_width=True):
                ask(q); st.rerun()

    with st.form("chat", clear_on_submit=True):
        c1, c2, c3 = st.columns([6, 1.1, 1.4])
        txt = c1.text_input("msg", label_visibility="collapsed", placeholder="Andika hano... / Type here...")
        pref = c2.selectbox("lang", ["Auto", "RW", "EN"], label_visibility="collapsed")
        send = c3.form_submit_button("Ohereza", use_container_width=True)
    if send and txt.strip():
        ask(txt, {"RW": "rw", "EN": "en"}.get(pref)); st.rerun()

elif view.startswith("Ingero"):
    st.markdown('<div class="apphead"><div class="t">Ingero z\'ibibazo</div>'
                '<div class="s">Example questions you can ask</div></div>', unsafe_allow_html=True)
    groups = {
        "Kwita ku mwana · Newborn care": [
            "Umwana wanjye ararira cyane nijoro, nakora iki?",
            "Umwana wanjye afite umuriro, nkore iki?",
            "Nita nte ku rugingo rw'umwana (cord)?"],
        "Konsa · Breastfeeding": [
            "Nkonsa umwana inshuro zingahe ku munsi?",
            "Numva amata yanjye ntahagije, nakora iki?"],
        "Gukira kwawe · Your recovery": [
            "Kuva nyuma yo kubyara bisanzwe ni bingahe?",
            "Nshobora gutangira imyitozo ryari nyuma yo kubagwa?"],
        "Uko wiyumva · How you feel": [
            "Numva mfite agahinda kuva nabyaye.",
            "Numva ndushye cyane kandi ndi wenyine."],
        "Kuboneza urubyaro · Family planning": [
            "Nshobora gutangira kuboneza urubyaro ryari nyuma yo kubyara?"],
    }
    html = '<div class="about">'
    for g, qs in groups.items():
        html += f'<div class="h" style="margin-top:6px">{g}</div>' + "".join(f"• {q}<br>" for q in qs)
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)

else:  # About
    st.markdown('<div class="apphead"><div class="t">Ibyerekeye Umubyeyi</div>'
                '<div class="s">About</div></div>', unsafe_allow_html=True)
    st.markdown('<div class="about">'
                '<b>Umubyeyi</b> ni umufasha uvuga Ikinyarwanda n\'Icyongereza, ufasha ababyeyi '
                'mu mezi 6 ya mbere nyuma yo kubyara — ku buzima bwabo n\'ubw\'abana babo.<br><br>'
                '<i>Umubyeyi is a bilingual (Kinyarwanda / English) companion for first-time mothers during '
                'the first 6 months after birth. It answers your questions with safe, general information and '
                'always reminds you to see a health worker when needed.</i>'
                f'<div class="disc" style="color:#9FBCA8;border-color:#29412f">Si serivisi y\'ubuvuzi. '
                f'Niba uri mu kaga, hamagara {rag.CRISIS_LINE}. · Not medical care; in a crisis call {rag.CRISIS_LINE}.</div>'
                '</div>', unsafe_allow_html=True)
