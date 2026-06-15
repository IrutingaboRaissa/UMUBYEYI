"""
Umubyeyi — Streamlit MVP, "Peach & Lavender" theme.
A soft, warm maternal-wellness chat — made with care, for new mothers.

Run:  streamlit run src/app.py

Pipeline status: intent classification + per-intent response templates are live.
The NLLB Kinyarwanda<->English translation layer is the next hook (responses
below are the English template text until it's wired) — marked TODO inline.
"""
import json
from pathlib import Path

import joblib
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
clf = joblib.load(ROOT / "models" / "intent_classifier.joblib")
tfidf = joblib.load(ROOT / "models" / "tfidf_vectorizer.joblib")
KB = json.loads((ROOT / "data" / "knowledge_base" / "mental_wellness_kb.json").read_text(encoding="utf-8"))
KB_BY_INTENT = {e["intent"]: e for e in KB["entries"]}  # first entry per intent

CONF_GATE = 0.40  # below this -> gentle general fallback (per design §3.5.6)
DISCLAIMER = "Aya ni amakuru rusange, si inama z'ubuvuzi. Vugana n'umuganga niba ufite impungenge."
GREETING = "Muraho, mama. Ndi hano kugufasha. Nshobora kugufasha gute uyu munsi?"

# danger-sign override -> bypass classification, escalate gently (per safety design)
DANGER = ["kill myself", "end my life", "suicide", "hurt myself", "hurt my baby",
          "harm my baby", "kwiyahura", "kwiyica", "guhotora"]

INTENT_META = {
    "sadness_low_mood":     "low mood",
    "anxiety_worry":        "anxiety",
    "sleep":                "sleep",
    "overwhelmed_identity": "feeling overwhelmed",
    "relationship_support": "relationships & support",
    "self_care_coping":     "self-care",
}

st.set_page_config(page_title="Umubyeyi", layout="centered")

# ----------------------------------------------------------------- theme (CSS)
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Quicksand:wght@400;500;600;700&display=swap');

[data-testid="stAppViewContainer"]{
  background: linear-gradient(160deg,#FBEFFb 0%, #F6F2FB 45%, #FFF1EA 100%);
}
[data-testid="stHeader"]{background:transparent;}
#MainMenu, footer{visibility:hidden;}
.block-container{max-width:560px;padding-top:1.2rem;padding-bottom:6rem;
  font-family:'Quicksand',Segoe UI,sans-serif;}

/* header card */
.umu-header{
  background:linear-gradient(120deg,#FFB59E 0%, #E6A6D9 55%, #C9B6F2 100%);
  color:#fff;border-radius:26px;padding:20px 24px;margin-bottom:18px;
  box-shadow:0 10px 28px rgba(201,182,242,.45);}
.umu-header .title{font-size:23px;font-weight:700;letter-spacing:.2px;}
.umu-header .sub{font-size:13.5px;font-weight:500;opacity:.95;margin-top:2px;}

/* bubbles */
.row{display:flex;margin-bottom:13px;}
.row.me{justify-content:flex-end;}
.bubble{max-width:84%;padding:12px 16px;font-size:14.5px;line-height:1.5;
  font-family:'Quicksand',sans-serif;box-shadow:0 3px 12px rgba(150,120,180,.14);}
.bubble.bot{background:#fff;color:#4A3B57;border-radius:20px 20px 20px 7px;}
.bubble.me{background:linear-gradient(120deg,#FFCBB0,#FFB59E);color:#5B3A52;
  font-weight:500;border-radius:20px 20px 7px 20px;}

/* intent pill */
.pill{display:inline-block;background:#ECE3FB;color:#7A5AA8;font-weight:600;
  font-size:12.5px;padding:4px 12px;border-radius:999px;margin-bottom:9px;}

/* answer pieces */
.empathy{color:#8A5A86;font-weight:600;margin-bottom:6px;}
.seek{background:#FFF0E8;border-left:3px solid #FFB59E;border-radius:10px;
  padding:9px 13px;margin-top:10px;font-size:13px;color:#9A5C44;}
.disclaimer{margin-top:11px;padding-top:8px;border-top:1px dashed #E7DBF7;
  font-size:11.5px;color:#A99CB8;}
.danger{background:#FFE9EC;border-left:4px solid #F2839A;border-radius:12px;
  padding:12px 15px;color:#A33D54;font-weight:500;}

/* chat input -> soft peach pill */
[data-testid="stChatInput"]{background:transparent;}
[data-testid="stChatInput"] > div{
  border-radius:24px !important;border:1.5px solid #F0CFE9 !important;
  background:#fff !important;box-shadow:0 4px 16px rgba(201,182,242,.25);}
[data-testid="stChatInput"] textarea{font-family:'Quicksand',sans-serif;}
[data-testid="stChatInputSubmitButton"]{color:#C9719E !important;}
</style>
""", unsafe_allow_html=True)

st.markdown(
    '<div class="umu-header"><div class="title">Umubyeyi</div>'
    '<div class="sub">umufasha wawe · a gentle companion for new mothers</div></div>',
    unsafe_allow_html=True)

# ----------------------------------------------------------------- state
if "msgs" not in st.session_state:
    st.session_state.msgs = [{"role": "bot", "kind": "text", "text": GREETING}]


@st.cache_resource(show_spinner="Gukanura umusemuzi (NLLB)...")
def _translator():
    from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
    tok = AutoTokenizer.from_pretrained("facebook/nllb-200-distilled-600M")
    model = AutoModelForSeq2SeqLM.from_pretrained("facebook/nllb-200-distilled-600M").eval()
    return tok, model


def kin_to_eng(text: str) -> str:
    """Kinyarwanda -> English for the classifier (NLLB). Degrades to raw text if unavailable."""
    try:
        import torch
        tok, model = _translator()
        tok.src_lang = "kin_Latn"
        with torch.no_grad():
            enc = tok(text, return_tensors="pt", truncation=True, max_length=128)
            gen = model.generate(**enc, forced_bos_token_id=tok.convert_tokens_to_ids("eng_Latn"),
                                 max_length=128, num_beams=4)
        return tok.batch_decode(gen, skip_special_tokens=True)[0]
    except Exception:
        return text


def respond(text: str) -> dict:
    """Translate -> classify -> return the intent's response template (safety + confidence gates)."""
    en = kin_to_eng(text)                       # NLLB: Kinyarwanda -> English
    if any(k in f"{text} {en}".lower() for k in DANGER):
        return {"role": "bot", "kind": "danger"}

    proba = clf.predict_proba(tfidf.transform([en]))[0]
    i = proba.argmax()
    intent, conf = clf.classes_[i], float(proba[i])

    gated = conf < CONF_GATE
    if gated:
        intent = "self_care_coping"             # gentle general fallback when unsure
    entry = KB_BY_INTENT.get(intent, KB_BY_INTENT.get("self_care_coping"))
    label = INTENT_META.get(intent, intent)
    return {"role": "bot", "kind": "answer", "label": label,
            "conf": conf, "gated": gated, "entry": entry, "en": en}


def render(m: dict) -> str:
    if m["role"] == "user":
        return f'<div class="row me"><div class="bubble me">{m["text"]}</div></div>'
    if m["kind"] == "text":
        return f'<div class="row"><div class="bubble bot">{m["text"]}</div></div>'
    if m["kind"] == "danger":
        return ('<div class="row"><div class="bubble bot"><div class="danger">'
                "Ndumva ko ubu uri kunyura mu bihe bikomeye cyane. Ntabwo uri wenyine. "
                "Nyamuneka vugana n'umuntu wizeye cyangwa umukozi w'ubuzima nonaha, cyangwa "
                "uhamagare serivisi z'ubutabazi. Ubuzima bwawe burafite agaciro."
                "</div></div></div>")
    e = m["entry"]
    # Pre-translated Kinyarwanda (human-validated); fall back to English if not yet translated.
    empathy = e.get("empathy_rw") or e["empathy"]
    guidance = e.get("guidance_rw") or e["guidance"]
    seek_txt = e.get("when_to_seek_help_rw") or e.get("when_to_seek_help")
    pill = f'<div class="pill">{m["label"]} · {m["conf"]:.2f}</div>'
    note = ('<div class="empathy">Sinabashije kumva neza, ariko ndi hano.</div>'
            if m["gated"] else f'<div class="empathy">{empathy}</div>')
    seek = f'<div class="seek">{seek_txt}</div>' if seek_txt else ""
    return (f'<div class="row"><div class="bubble bot">{pill}{note}'
            f'<div>{guidance}</div>{seek}'
            f'<div class="disclaimer">{DISCLAIMER}</div></div></div>')


# ----------------------------------------------------------------- handle input
if prompt := st.chat_input("Andika hano..."):
    st.session_state.msgs.append({"role": "user", "text": prompt})
    st.session_state.msgs.append(respond(prompt))

# ----------------------------------------------------------------- render chat
st.markdown("".join(render(m) for m in st.session_state.msgs), unsafe_allow_html=True)
