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
/* keep Streamlit's icon font on icon elements, or icon names render as raw text (e.g. "keyboard_double_arrow_right") */
[data-testid="stIconMaterial"], span.material-icons, span.material-icons-outlined,
.material-symbols-outlined, [class*="material-icons"], [class*="material-symbols"], i.material-icons{
  font-family:'Material Symbols Outlined','Material Symbols Rounded','Material Icons' !important;}
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

/* ---- responsive: phones & small screens ---- */
@media (max-width:640px){
  .block-container{max-width:100%;padding-left:0.8rem;padding-right:0.8rem;padding-top:1rem;padding-bottom:4rem;}
  .apphead{margin-bottom:14px;}
  .apphead .t{font-size:23px;}
  .apphead .s{font-size:13px;}
  .bubble{max-width:92%;font-size:15px;padding:11px 14px;line-height:1.55;}
  .about{padding:14px 15px;font-size:14px;line-height:1.6;}
  .exhint{font-size:13px;}
  .stTextInput input{font-size:16px !important;}  /* >=16px stops iOS Safari auto-zoom on focus */
}
@media (max-width:380px){
  .apphead .t{font-size:20px;}
  .bubble{font-size:14.5px;}
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
    st.markdown('<div class="apphead"><div class="t">Umubyeyi</div>'
                '<div class="s">Umufasha wawe nyuma yo kubyara · a companion after birth</div></div>', unsafe_allow_html=True)
    st.markdown('<div class="about"><div class="h">Mbere yo gutangira · Before you start</div>'
                'Umubyeyi akugufasha ku byo wiyumva nyuma yo kubyara (agahinda, guhangayika, kunanirwa). '
                'Si serivisi y\'ubuvuzi, kandi ntiyita ku bibazo by\'umubiri cyangwa byo kwita ku mwana — '
                'ku byo, ganira n\'umukozi w\'ubuzima. <i>Umubyeyi supports how you feel after birth. It is '
                'not medical care and does not cover physical or baby-care questions — please see a health '
                'worker for those.</i><br><br>'
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
    html = '<div class="about">'
    for g, qs in groups.items():
        html += f'<div class="h" style="margin-top:6px">{g}</div>' + "".join(f"• {q}<br>" for q in qs)
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)

else:  # About
    st.markdown('<div class="apphead"><div class="t">Ibyerekeye Umubyeyi</div>'
                '<div class="s">About</div></div>', unsafe_allow_html=True)
    st.markdown('<div class="about">'
                '<b>Umubyeyi</b> ni umufasha uvuga Ikinyarwanda n\'Icyongereza, witeguye kugufasha ku byo '
                'wiyumva mu mezi 6 ya mbere nyuma yo kubyara — agahinda, guhangayika, kunanirwa, kumva uri '
                'wenyine, no guhangana. Ntiyita ku bibazo by\'umubiri cyangwa byo kwita ku mwana.<br><br>'
                '<i>Umubyeyi is a bilingual (Kinyarwanda / English) companion for the emotional wellbeing of '
                'first-time mothers in the first 6 months after birth — sadness, anxiety, feeling overwhelmed, '
                'loneliness, and coping. It does not cover medical or baby-care questions, and always reminds '
                'you to see a health worker when needed.</i>'
                f'<div class="disc" style="color:#9FBCA8;border-color:#29412f">Si serivisi y\'ubuvuzi. '
                f'Niba uri mu kaga, hamagara {rag.CRISIS_LINE}. · Not medical care; in a crisis call {rag.CRISIS_LINE}.</div>'
                '</div>', unsafe_allow_html=True)
