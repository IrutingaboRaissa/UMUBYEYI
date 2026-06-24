"""
Umubyeyi - Streamlit dashboard frontend (sidebar · chat · analysis panel).
Bilingual grounded-generation postpartum assistant for first-time mothers in Rwanda.
Run:  streamlit run src/app.py
"""
import os
import streamlit as st

import rag  # src/ is on sys.path when run via `streamlit run src/app.py`

# Streamlit Cloud secrets -> env (so rag.py picks up the Gemini key)
try:
    for _k in ("GEMINI_API_KEY", "GEMINI_MODEL"):
        if _k in st.secrets:
            os.environ[_k] = str(st.secrets[_k])
except Exception:
    pass

st.set_page_config(page_title="Umubyeyi · Maternal Wellness AI", layout="wide", initial_sidebar_state="expanded")

# model comparison + degradation (from the analysis; see the notebook)
MODELS = [("Random Forest", 0.71, True), ("Linear SVM", 0.66, False),
          ("Logistic Regression", 0.64, False), ("AfriBERTa (fine-tuned)", 0.45, False),
          ("ComplementNB (baseline)", 0.45, False)]
DEG_EN, DEG_RW = 0.72, 0.56

st.markdown("""
<style>
html, body, [class*="css"], [data-testid="stAppViewContainer"] *, [data-testid="stSidebar"] *{
  font-family:'Times New Roman', Times, serif !important;}
[data-testid="stAppViewContainer"]{background:#141310;}
[data-testid="stSidebar"]{background:#15241c;border-right:1px solid #21382c;}
[data-testid="stSidebar"] *{color:#DCEFE3 !important;}
.block-container{padding-top:1.2rem;max-width:1500px;}
h1,h2,h3,h4{font-family:'Times New Roman',serif !important;}

/* sidebar brand + badge */
.brand{display:flex;align-items:center;gap:10px;margin-bottom:4px;}
.brand .logo{background:#E9C46A;color:#15241c;width:34px;height:34px;border-radius:9px;
  display:flex;align-items:center;justify-content:center;font-size:18px;}
.brand .nm{font-size:19px;font-weight:700;color:#fff;}
.brand .sub{font-size:12px;color:#9FBCA8;}
.badge{background:#1c2f24;border:1px solid #2c4a39;border-radius:10px;padding:9px 12px;
  font-size:12.5px;color:#BFE3CE;margin-top:14px;}
.badge b{color:#fff;font-size:13.5px;}

/* cards */
.card{background:#1f1d18;border:1px solid #2a2820;border-radius:12px;padding:13px 15px;margin-bottom:14px;}
.eyebrow{font-size:11px;letter-spacing:1.2px;color:#8C8676;text-transform:uppercase;margin-bottom:8px;}
.card h4{margin:0 0 4px 0;font-size:15px;color:#fff;}
.muted{color:#A39E8E;font-size:12.5px;}

/* model bars */
.bar-row{display:flex;align-items:center;justify-content:space-between;font-size:13px;margin:6px 0;color:#D8D3C5;}
.bar-name{width:54%;}
.bar-track{flex:1;height:7px;background:#2a2820;border-radius:6px;margin:0 8px;overflow:hidden;}
.bar-fill{height:7px;background:#3FA66A;border-radius:6px;}
.bar-val{width:34px;text-align:right;color:#fff;}
.best{background:#2e7d52;color:#fff;font-size:10px;padding:1px 6px;border-radius:6px;margin-left:6px;}

/* degradation */
.deg{display:flex;gap:10px;}
.deg .cell{flex:1;background:#1c2f24;border:1px solid #2c4a39;border-radius:10px;padding:10px;text-align:center;}
.deg .cell .l{font-size:11px;color:#9FBCA8;} .deg .cell .v{font-size:22px;font-weight:700;color:#fff;}
.deg .cell.rw .v{color:#E07A5F;}

/* chat bubbles */
.chead{display:flex;align-items:center;gap:10px;border-bottom:1px solid #2a2820;padding-bottom:10px;margin-bottom:12px;}
.chead .t{font-size:18px;font-weight:700;color:#fff;}
.chead .meta{font-size:12px;color:#8C8676;}
.dot{color:#3FA66A;}
.row{display:flex;margin-bottom:12px;} .row.me{justify-content:flex-end;}
.bubble{max-width:82%;padding:11px 15px;font-size:15px;line-height:1.55;border-radius:14px;white-space:pre-wrap;}
.bubble.bot{background:#F5F0E6;color:#2A2620;}
.bubble.me{background:#2e7d52;color:#fff;}
.bubble.danger{background:#3a1f22;border:1px solid #E07A5F;color:#F2C7BD;}
.disc{background:#2a2412;border:1px solid #5c4d1f;border-radius:10px;padding:11px 13px;font-size:12.5px;color:#E9C46A;}

[data-testid="stForm"]{border:none;padding:0;}
.stTextInput input{background:#1f1d18 !important;color:#fff !important;border:1px solid #2a2820 !important;
  font-family:'Times New Roman',serif !important;font-size:15px !important;}
[data-testid="stForm"] button{background:#2e7d52 !important;color:#fff !important;border:none !important;}
</style>
""", unsafe_allow_html=True)

# ---------------- consent gate ----------------
if not st.session_state.get("consented"):
    st.markdown('<div class="card" style="max-width:640px;margin:6vh auto;">'
        '<div class="eyebrow">Mbere yo gutangira · Before you start</div>'
        '<div class="muted" style="font-size:14px;line-height:1.6;">Iyi ni porogaramu y\'ubushakashatsi '
        'bw\'umunyeshuri, si serivisi y\'ubuvuzi. Amakuru ni rusange. / This is a student research '
        'prototype, not medical care. Information is general.<br><br>'
        f'Niba uri mu kaga / In a crisis, call: <b style="color:#E07A5F">{rag.CRISIS_LINE}</b>.<br>'
        'Ntukandike amazina cyangwa amakuru akuranga · Do not enter identifying information.</div></div>',
        unsafe_allow_html=True)
    if st.button("Ndabyumvise — I understand & agree"):
        st.session_state.consented = True; st.rerun()
    st.stop()

if "msgs" not in st.session_state:
    st.session_state.msgs = [{"role": "bot", "text": rag.GREETING_REPLY if hasattr(rag, "GREETING_REPLY")
                              else "Muraho, mama! Mbaza ikibazo cyawe ku buzima bwawe nyuma yo kubyara.",
                              "danger": False, "language": "rw"}]

# ---------------- sidebar ----------------
with st.sidebar:
    st.markdown('<div class="brand"><div class="logo">🌷</div><div>'
                '<div class="nm">Umubyeyi</div><div class="sub">Maternal Wellness AI</div></div></div>',
                unsafe_allow_html=True)
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    view = st.radio("menu", ["Chat", "Model results", "Knowledge base", "Safety layer", "About"],
                    label_visibility="collapsed")
    st.markdown('<div class="badge">Grounded RAG · retrieval + Gemini<br><b>Recall@3 0.94 · deployed</b></div>',
                unsafe_allow_html=True)

last_lang = next((m.get("language", "rw") for m in reversed(st.session_state.msgs) if m["role"] == "bot"), "rw")


def model_bars():
    rows = ""
    for name, f1, best in MODELS:
        tag = '<span class="best">best</span>' if best else ""
        rows += (f'<div class="bar-row"><div class="bar-name">{name}{tag}</div>'
                 f'<div class="bar-track"><div class="bar-fill" style="width:{f1/0.8*100:.0f}%"></div></div>'
                 f'<div class="bar-val">{f1:.2f}</div></div>')
    return rows


def info_panel():
    lang_label = "Kinyarwanda" if last_lang == "rw" else "English"
    st.markdown(f'<div class="card"><div class="eyebrow">Detected language</div>'
                f'<h4>{lang_label}</h4><div class="muted">Reply is generated in this language.</div></div>',
                unsafe_allow_html=True)
    st.markdown(f'<div class="card"><div class="eyebrow">Model comparison · macro-F1</div>{model_bars()}</div>',
                unsafe_allow_html=True)
    st.markdown('<div class="card"><div class="eyebrow">Cross-lingual degradation</div>'
                f'<div class="deg"><div class="cell"><div class="l">English</div><div class="v">{DEG_EN:.2f}</div></div>'
                f'<div class="cell rw"><div class="l">Kinyarwanda</div><div class="v">{DEG_RW:.2f}</div></div></div>'
                '<div class="muted" style="margin-top:8px">NLLB-200 translation introduces a ~0.16 F1 drop (22%) — '
                'a measured benchmark for Kinyarwanda maternal-wellness classification.</div></div>',
                unsafe_allow_html=True)
    st.markdown('<div class="disc"><b>Disclaimer:</b> General information only — not a diagnostic tool. '
                'Always consult a healthcare provider.</div>', unsafe_allow_html=True)


def bubble(m):
    if m["role"] == "user":
        return f'<div class="row me"><div class="bubble me">{m["text"]}</div></div>'
    cls = "bubble bot danger" if m.get("danger") else "bubble bot"
    return f'<div class="row"><div class="{cls}">{m["text"]}</div></div>'


# ---------------- main views ----------------
if view == "Chat":
    chat, info = st.columns([2, 1], gap="large")
    with chat:
        st.markdown(f'<div class="chead"><div class="t">Wellness Chat</div>'
                    f'<div class="meta">· {"Kinyarwanda" if last_lang=="rw" else "English"} '
                    f'<span class="dot">● Online</span></div></div>', unsafe_allow_html=True)
        for m in st.session_state.msgs:
            st.markdown(bubble(m), unsafe_allow_html=True)
        with st.form("chat", clear_on_submit=True):
            c1, c2, c3 = st.columns([5, 1, 1])
            txt = c1.text_input("msg", label_visibility="collapsed", placeholder="Andika hano... / Type here...")
            pref = c2.selectbox("lang", ["Auto", "RW", "EN"], label_visibility="collapsed")
            send = c3.form_submit_button("➤ Andika")
        if send and txt.strip():
            st.session_state.msgs.append({"role": "user", "text": txt})
            force = {"RW": "rw", "EN": "en"}.get(pref)
            with st.spinner("Tegereza gato..."):
                try:
                    r = rag.answer(txt, force_lang=force)
                    st.session_state.msgs.append({"role": "bot", "text": r["answer"],
                                                  "danger": r.get("danger", False), "language": r.get("language", "rw")})
                except Exception as e:
                    st.session_state.msgs.append({"role": "bot", "text": f"Mbabarira, hari ikibazo. ({e})", "danger": False})
            st.rerun()
    with info:
        info_panel()

elif view == "Model results":
    st.markdown("### Model results")
    st.markdown(f'<div class="card"><div class="eyebrow">Classification — held-out macro-F1</div>{model_bars()}'
                '<div class="muted" style="margin-top:8px">Classical models beat fine-tuned transformers in this '
                'low-resource setting; this analysis motivated the retrieval design.</div></div>', unsafe_allow_html=True)
    st.markdown('<div class="card"><div class="eyebrow">Product retrieval (deployed)</div>'
                '<div class="deg"><div class="cell"><div class="l">Recall@3</div><div class="v">0.94</div></div>'
                '<div class="cell"><div class="l">MRR</div><div class="v">0.91</div></div>'
                '<div class="cell"><div class="l">Lang. detect</div><div class="v">99.9%</div></div></div>'
                '<div class="muted" style="margin-top:8px">The product-level metric: the assistant fetches the '
                'correct validated answer ~94% of the time (top-3).</div></div>', unsafe_allow_html=True)

elif view == "Knowledge base":
    st.markdown("### Knowledge base")
    st.markdown(f'<div class="card"><h4>{len(rag.BANK)} validated postpartum Q&A</h4>'
                '<div class="muted">Source: the MOTHER dataset (medically validated; Uganda), filtered to the '
                '0–6 month postpartum window. Answers are grounded on this bank; nothing is invented.</div></div>',
                unsafe_allow_html=True)
    for b in rag.BANK[:6]:
        st.markdown(f'<div class="card"><b style="color:#fff">{b["question_en"]}</b>'
                    f'<div class="muted" style="margin-top:6px">{b["answer_en"][:200]}…</div></div>', unsafe_allow_html=True)

elif view == "Safety layer":
    st.markdown("### Safety layer")
    for t, d in [("Consent gate", "Shown once before any chat; states this is a research prototype, not medical care."),
                 ("Danger-sign override", "Self-harm / emergency keywords bypass the model and show a crisis referral."),
                 ("Grounded answers", "Clinical answers use only validated content — controls hallucination."),
                 ("Domain bounding", "Off-topic questions (malaria, COVID, farming) are politely declined."),
                 ("Disclaimer", "Every answer carries an informational disclaimer."),
                 ("Privacy", "No names or identifying information are requested or stored.")]:
        st.markdown(f'<div class="card"><h4>{t}</h4><div class="muted">{d}</div></div>', unsafe_allow_html=True)

else:  # About
    st.markdown("### About")
    st.markdown('<div class="card"><div class="muted" style="font-size:14px;line-height:1.7">'
                '<b style="color:#fff">Umubyeyi</b> is a bilingual (Kinyarwanda / English) chatbot supporting '
                'first-time mothers in Rwanda during the 0–6 month postpartum window. It detects the question\'s '
                'language, retrieves a medically-validated answer, and generates a warm, on-domain reply in that '
                'language — wrapped in safety mechanisms.<br><br>'
                'Author: Raissa IRUTINGABO · Supervisor: Samiratu Ntohsi · BSc Software Engineering, ALU.</div></div>',
                unsafe_allow_html=True)
