# Deploying Umubyeyi for the feedback pilot

Goal: a phone-friendly public URL you can share with 5-10 new mothers, running the
full Kinyarwanda -> English -> classify -> Kinyarwanda pipeline, with in-app
thumbs feedback saved to a Google Sheet.

Host: **Hugging Face Spaces (free CPU tier, ~16GB RAM)** — it can load NLLB, so no
model change and no accuracy loss.

---

## Before you launch (must-have)

1. **Crisis helpline.** Open [src/app.py](src/app.py), find `CRISIS_LINE`, and replace the
   placeholder with a **verified** Rwandan crisis/helpline number. It is shown on the consent
   screen and in the danger override. Do not launch without a real number.
2. **Proofread the 8 Kinyarwanda responses** in
   [data/knowledge_base/mental_wellness_kb.json](data/knowledge_base/mental_wellness_kb.json)
   (the `empathy_rw`, `guidance_rw`, `when_to_seek_help_rw` fields). These are machine-translated;
   testers will read them, so fix any awkward or wrong Kinyarwanda.

---

## Step 1 - Google Sheet for feedback

1. Create a Google Sheet (e.g. "Umubyeyi feedback"). Copy its **id** from the URL:
   `https://docs.google.com/spreadsheets/d/THIS_IS_THE_ID/edit`
2. In [Google Cloud Console](https://console.cloud.google.com/): create a project ->
   enable the **Google Sheets API** -> create a **Service Account** -> create a **JSON key**
   and download it.
3. Open the downloaded JSON, copy the `client_email`, and **share the Sheet** with that email
   (Editor access).

## Step 2 - Create the Space

1. On https://huggingface.co create a new **Space** -> SDK: **Streamlit**.
2. Push this repo to the Space (its own git remote):
   ```bash
   git remote add space https://huggingface.co/spaces/<your-username>/umubyeyi
   git push space main
   ```
   (The HF config block at the top of [README.md](README.md) tells the Space to run `src/app.py`.)

## Step 3 - Add the secrets

In the Space: **Settings -> Variables and secrets**, add two **secrets**:

| Name | Value |
|---|---|
| `FEEDBACK_SHEET_ID` | the Sheet id from Step 1 |
| `GCP_SERVICE_ACCOUNT` | the **entire** contents of the service-account JSON file |

The app reads these at runtime. If they are missing it still runs, but feedback falls back to a
local CSV that is wiped when the Space restarts — so set them before the pilot.

## Step 4 - First run

- The first message is slow (~30-60s) while NLLB downloads and loads; it is cached after that.
- Open the Space URL on a phone, tap through the consent screen, and send a test message.
- Confirm a 👍/👎 appears under the reply and a new row lands in your Google Sheet.

---

## What gets logged per feedback

`timestamp, message, intent, confidence, vote` — no names. The consent screen also asks
testers not to enter identifying information.

## Pilot readiness checklist

- [ ] `CRISIS_LINE` set to a verified number
- [ ] 8 Kinyarwanda responses proofread
- [ ] Google Sheet shared with the service account
- [ ] `FEEDBACK_SHEET_ID` + `GCP_SERVICE_ACCOUNT` secrets set on the Space
- [ ] Tested end-to-end on a phone (consent -> chat -> feedback row appears)
