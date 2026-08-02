export type Msg = {
  role: "user" | "bot";
  text: string;
  sub?: string;
  danger?: boolean;
  mode?: string;
  lang?: string;
};

export type Thread = {
  id: string;
  title: string;
  // "fallback" = raw truncated first message, shown instantly and meant to be replaced;
  // "generated" = a real Groq-summarized topic title; "manual" = the mother renamed it
  // herself, so it must never be overwritten by a background retitle attempt.
  titleSource?: "fallback" | "generated" | "manual";
  ts: number;
  msgs: Msg[];
  locked?: boolean;
};

export type ConcernSignal = {
  level: "none" | "mild" | "moderate" | "elevated";
  score: number;
  basis: string[];
};

export type ChatResponse = {
  answer: string;
  language: string;
  danger: boolean;
  grounded: boolean;
  mode: string;
  intent: string | null;
  sources: { topic: string; source: string; sim: number }[];
  topic_predictions?: { topic_id: string; topic: string; score: number }[];
  latency_ms?: number;
  concern_signal?: ConcernSignal;
};

export type Explanation = {
  feature: string;
  feature_label: string;
  contribution: number;
  direction: "increases" | "decreases";
};

export type ScreenResponse = {
  risk: "elevated" | "not_elevated";
  elevated: boolean;
  message_en: string;
  message_rw: string;
  disclaimer: string;
  disclaimer_rw?: string;
  explainability_available?: boolean;
  explanation?: Explanation[] | null;
};

// Each option is either a plain string (submitted value === displayed label) or a
// [value, label] pair when the value the trained model expects would be confusing to show
// verbatim -- e.g. the PHQ-2 items must submit clinical "Negative"/"Positive" (matching the
// dataset's own encoding, "Positive" meaning a positive depression screen) while the label
// shown to the mother needs to be an unambiguous yes/no question, since "Positive" reads as
// good news everywhere else in this form.
export type CheckinOption = string | readonly [string, string];

// Display labels and option labels are bilingual ("Kinyarwanda · English"), matching the
// rest of the app's static UI text. The first tuple element (the dataset column name) and
// every option VALUE must stay exactly as the trained model's OneHotEncoder was fit on --
// only the second element and option LABELS (what's actually shown) are translated.
export const CHECKIN_FIELDS: readonly (readonly [string, string, readonly CheckinOption[]])[] = [
  ["Relationship with husband", "Umubano wawe n'uwo mwashakanye · Relationship with partner",
    [["Good", "Mwiza · Good"], ["Neutral", "Uringaniye · Neutral"], ["Bad", "Mubi · Bad"]]],
  ["Relationship with the newborn", "Umubano wawe n'umwana wawe · Connection with your baby",
    [["Good", "Mwiza · Good"], ["Neutral", "Uringaniye · Neutral"], ["Bad", "Mubi · Bad"]]],
  ["Feeling about motherhood", "Uko wiyumva ku byerekeye ubumama · How you feel about motherhood",
    [["Positive", "Byiza · Positive"], ["Neutral", "Uringaniye · Neutral"], ["Negative", "Bibi · Negative"]]],
  ["Recieved Support", "Ubufasha ubu ubona · Support you currently receive",
    [["High", "Bwinshi · High"], ["Medium", "Bugereranyije · Medium"], ["Low", "Buke · Low"]]],
  ["Need for Support", "Ubufasha bwinshi ukeneye · How much more support you need",
    [["High", "Bwinshi · High"], ["Medium", "Bugereranyije · Medium"], ["Low", "Buke · Low"]]],
  ["Abuse", "Waba warigeze ugirirwa nabi? · Have you experienced abuse?", [["No", "Oya · No"], ["Yes", "Yego · Yes"]]],
  ["Trust and share feelings", "Ushobora kubwira umuntu wizeye uko wiyumva? · Can you share feelings with someone you trust?",
    [["Yes", "Yego · Yes"], ["No", "Oya · No"]]],
  ["Worry about newborn", "Uhorana impungenge ku mwana wawe? · Are you constantly worried about your baby?",
    [["No", "Oya · No"], ["Yes", "Yego · Yes"]]],
  ["Relax/sleep when newborn is tended ", "Ushobora kuruhuka igihe undi yitaho umwana? · Can you rest when someone trusted watches the baby?",
    [["Yes", "Yego · Yes"], ["No", "Oya · No"]]],
  ["Relax/sleep when the newborn is asleep", "Ushobora kuruhuka igihe umwana asinziriye? · Can you rest when the baby sleeps?",
    [["Yes", "Yego · Yes"], ["No", "Oya · No"]]],
  ["Angry after latest child birth", "Waba wumva urakaye cyangwa bigoranye kwitonda? · Have you often felt angry or hard to calm?",
    [["No", "Oya · No"], ["Yes", "Yego · Yes"]]],
  ["Feeling for regular activities", "Ibikorwa bisanzwe bikumera bite? · How do ordinary activities feel?",
    [["Nothing (no difficulty)", "Nta kibazo · Nothing (no difficulty)"], ["Tired", "Umunaniro · Tired"],
      ["Anxious", "Impungenge · Anxious"], ["Fearful", "Ubwoba · Fearful"]]],
  ["Depression before pregnancy (PHQ2)",
    "Mbere yo gutwita, wari usanzwe wiyumva ubabaye cyangwa udashishikajwe n'ibintu? · Before this pregnancy, did you often feel down or lose interest in things?",
    [["Negative", "Oya · No"], ["Positive", "Yego · Yes"]]],
  ["Depression during pregnancy (PHQ2)",
    "Mu gihe cyo gutwita, wari usanzwe wiyumva ubabaye cyangwa udashishikajwe n'ibintu? · During this pregnancy, did you often feel down or lose interest in things?",
    [["Negative", "Oya · No"], ["Positive", "Yego · Yes"]]],
] as const;

// Bilingual short axis-style labels for the SHAP explanation chart, keyed by the same raw
// dataset column names as CHECKIN_FIELDS above (the backend's Explanation.feature value) --
// a shorter, noun-phrase style than the check-in form's question-style labels, since these
// are chart categories rather than form prompts. Overrides the backend's English-only
// feature_label on the frontend rather than requiring a Python change.
export const FEATURE_LABEL: Record<string, string> = {
  "Age": "Imyaka · Age",
  "Relationship with husband": "Umubano n'uwo mwashakanye · Relationship with partner",
  "Relationship with the newborn": "Umubano n'umwana · Connection with your baby",
  "Feeling about motherhood": "Uko wiyumva ku bumama · How you feel about motherhood",
  "Recieved Support": "Ubufasha ubona · Support you currently receive",
  "Need for Support": "Ubufasha ukeneye · How much more support you need",
  "Abuse": "Kugirirwa nabi · Experience of abuse",
  "Trust and share feelings": "Kubwira uwizeye uko wiyumva · Can share feelings with someone you trust",
  "Worry about newborn": "Impungenge ku mwana · Constantly worried about your baby",
  "Relax/sleep when newborn is tended ": "Kuruhuka undi yitaho umwana · Can rest when someone trusted watches the baby",
  "Relax/sleep when the newborn is asleep": "Kuruhuka umwana asinziriye · Can rest when the baby sleeps",
  "Angry after latest child birth": "Kwumva urakaye cyangwa bigoye kwitonda · Feeling angry or hard to calm",
  "Feeling for regular activities": "Uko ibikorwa bisanzwe bimeze · Comfort with ordinary daily activities",
  "Depression before pregnancy (PHQ2)": "Uko wiyumva mbere yo gutwita · Low mood before pregnancy (screening)",
  "Depression during pregnancy (PHQ2)": "Uko wiyumva mu gutwita · Low mood during pregnancy (screening)",
};

export function optionValue(option: CheckinOption): string {
  return typeof option === "string" ? option : option[0];
}

export function optionLabel(option: CheckinOption): string {
  return typeof option === "string" ? option : option[1];
}

export const CRISIS_LINE = "114";
// Which thread is currently open -- a pure per-device UI preference, so it stays in
// localStorage rather than syncing to the account; see lib/supabase/data.ts loadThreads().
export const STORE_CURRENT_KEY = "umubyeyi_current_v3";

// Local-only storage, so there's no real cost to a long history -- 500 entries is years of
// even daily use. Used for mood, guided-check-in, and concern-signal history; the previous
// cap of 30 raw entries silently deleted anything older with no way to get it back.
export const RAW_HISTORY_CAP = 500;

export const TIPS = [
  ["Shaka ubufasha", "Reach out", "Ganira n'umuntu wizeye cyangwa umukozi w'ubuzima.", "Talk to someone you trust or a health worker."],
  ["Wubake abagufasha", "Build support", "Egera uwo mwashakanye, umuryango n'incuti.", "Lean on your partner, family, and friends."],
  ["Wite ku mutima wawe", "Self-care", "Fata udukanya duto wiyibagiza, ushake ibikunezeza bito.", "Take small moments for yourself; small joys matter."],
  ["Ruhuka bihagije", "Rest", "Sinzira igihe umwana asinziriye, usabe ubufasha nijoro.", "Sleep when the baby sleeps; ask for help at night."],
  ["Imyitozo yoroheje", "Gentle movement", "Genda urugendo rugufi cyangwa unyeganyege gato.", "A short walk or light stretching lifts your mood."],
  ["Kurya indyo yuzuye", "Nourish", "Fata indyo yuzuye kugira ngo ugire imbaraga.", "Balanced meals help your energy and mood."],
  ["Humeka utuze", "Breathe", "Guhumeka gahoro bishobora gutuza umutima.", "A few slow breaths can calm a hard moment."],
  ["Vuga uko wiyumva", "Share openly", "Vuga ibyiyumvo byawe utagira ipfunwe.", "Speak your feelings without guilt; it's a strength."],
] as const;

// Real, hand-authored supportive copy per mood (same category as TIPS/AFFIRM above, not a
// dataset) so picking the same mood again doesn't always show the identical tip.
export const MOOD_TIPS: Record<string, readonly (readonly [string, string])[]> = {
  Great: [
    ["Write down what helped you feel this way today - it's worth remembering.", "Andika icyagutumye wiyumva utyo uyu munsi - birakwiye kwibukwa."],
    ["Share this good moment with someone who cares about you.", "Sangira uku kwiyumva neza n'umuntu ukwitaho."],
    ["Keep doing what's working - your instincts are guiding you well.", "Komeza ukore ibigufasha - umutima wawe ukuyobora neza."],
  ],
  Okay: [
    ["A steady day is worth noticing - small stability matters.", "Umunsi utuje ukwiye kwitabwaho - gutuza gato birafite agaciro."],
    ["Check in with your body: water, food, and a moment to sit today?", "Reba ku mubiri wawe: wanyoye amazi, urarya, kandi wicaye gato uyu munsi?"],
    ["It's fine to just get through today - you don't need to feel more than okay.", "Birakwiye kunyura uyu munsi utyo - ntugomba kwiyumva neza cyane."],
  ],
  Low: [
    ["Low days pass. Be as gentle with yourself as you would with a friend.", "Iminsi mibi irashira. Wigirire neza nk'uko wagirira incuti yawe."],
    ["Try one small comforting thing - tea, sunlight, a favorite song.", "Gerageza ikintu gito gikuruhura - icyayi, izuba, indirimbo ukunda."],
    ["If low feelings stay for many days, tell someone you trust.", "Niba wiyumva utyo iminsi myinshi, bwira umuntu wizeye."],
  ],
  Anxious: [
    ["Try slow breathing: in for 4, hold for 4, out for 6.", "Gerageza guhumeka gahoro: injiza ubara 4, ushikire 4, sohora ubara 6."],
    ["Write down the one worry that's loudest right now - naming it can loosen its grip.", "Andika impungenge imwe ikomeye cyane ubu - kuyivuga birayoroshya."],
    ["Anxious thoughts are not always facts. Ask: what do I actually know right now?", "Ibitekerezo by'impungenge si ukuri buri gihe. Wibaze: ni iki nzi neza ubu?"],
  ],
  Exhausted: [
    ["Rest when the baby rests, even for ten minutes - it counts.", "Ruhuka igihe umwana aruhutse, n'iminota icumi irafite agaciro."],
    ["Ask for one specific piece of help today instead of managing everything alone.", "Saba ubufasha ku kintu kimwe uyu munsi aho kwikorera byose wenyine."],
    ["Lower the bar today: fed and safe is enough.", "Gabanya icyo witeze uyu munsi: kurya no kuba mu mutekano birahagije."],
  ],
};

// Display-only bilingual labels for the mood-grid buttons/pills -- the English mood name
// (Great/Okay/Low/Anxious/Exhausted) stays the actual stored/lookup key into MOOD_TIPS
// and local storage; only what's shown to the mother changes here.
export const MOOD_LABEL: Record<string, string> = {
  Great: "Byiza cyane · Great",
  Okay: "Ni byiza · Okay",
  Low: "Ntabwo ari byiza · Low",
  Anxious: "Impungenge · Anxious",
  Exhausted: "Umunaniro · Exhausted",
};

export const AFFIRM = [
  ["You are not failing - you are learning.", "Ntabwo unaniwe - uriga."],
  ["It's okay not to be okay - this is a huge change.", "Biremewe kutamererwa neza - iyi ni impinduka ikomeye."],
  ["The house can wait; you and your baby cannot.", "Inzu irashobora gutegereza; wowe n'umwana oya."],
  ["Rest is productive - your healing is the priority.", "Kuruhuka ni ingirakamaro - gukira kwawe ni ingenzi."],
  ["Asking for help is a sign of strength, not weakness.", "Gusaba ubufasha ni ubutwari, si intege nke."],
  ["You are exactly what your baby needs.", "Uri ibyo umwana wawe akeneye byuzuye."],
] as const;

export function newThread(): Thread {
  return {
    id: Math.random().toString(36).slice(2, 14),
    title: "",
    ts: Date.now(),
    msgs: [],
  };
}

export function sortThreads(threads: Thread[]): Thread[] {
  return [...threads].sort((a, b) => b.ts - a.ts);
}

export function touchThread(t: Thread): Thread {
  return { ...t, ts: Date.now() };
}

// Points requests at a separately hosted backend (e.g. Render) when set at
// build time; otherwise every call stays relative, so a bare `/api/...`
// path is served same-origin exactly as before (by Vercel's own api/*.py in
// production, or by local_api.py via the Next.js dev rewrite locally). Must
// only ever hold a public base URL -- never a secret, since NEXT_PUBLIC_*
// values are inlined into the browser bundle.
const API_BASE_URL = (process.env.NEXT_PUBLIC_API_BASE_URL || "").replace(/\/+$/, "");

export function apiUrl(path: string): string {
  const cleanPath = path.startsWith("/") ? path : `/${path}`;
  return API_BASE_URL ? `${API_BASE_URL}${cleanPath}` : cleanPath;
}

// Thrown when the backend looks asleep rather than genuinely broken, so the
// UI can show "still starting up" instead of a generic error. Render's free
// tier can take 50s+ to spin back up after idling -- a plain fetch would
// otherwise just hang with no feedback for that whole window.
export class ApiWakingUpError extends Error {
  constructor() {
    super("The backend is starting up. Please try again in a moment.");
    this.name = "ApiWakingUpError";
  }
}

const WAKE_TIMEOUT_MS = 60_000;

async function apiFetch(path: string, init: RequestInit): Promise<Response> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), WAKE_TIMEOUT_MS);
  try {
    const res = await fetch(apiUrl(path), { ...init, signal: controller.signal });
    if (res.status === 502 || res.status === 503) throw new ApiWakingUpError();
    return res;
  } catch (err) {
    if (err instanceof ApiWakingUpError) throw err;
    if (err instanceof DOMException && err.name === "AbortError") throw new ApiWakingUpError();
    throw err;
  } finally {
    clearTimeout(timeout);
  }
}

export async function sendChat(
  message: string, forceLang?: "en" | "rw" | null, history?: Msg[]
): Promise<ChatResponse> {
  // Last few turns only: enough for the generator to track the current
  // exchange without shipping a mother's whole chat history on every request.
  const recentHistory = (history || []).slice(-6).map((m) => ({ role: m.role, text: m.text }));
  const res = await apiFetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, force_lang: forceLang ?? null, history: recentHistory }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error || `Request failed (${res.status})`);
  }
  return res.json();
}

export async function sendScreen(answers: Record<string, string | number>): Promise<ScreenResponse> {
  const res = await apiFetch("/api/screen", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ answers, explain: true }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error || `Request failed (${res.status})`);
  }
  return res.json();
}

export async function generateTitle(userMessage: string, botReply: string, lang?: string): Promise<string> {
  try {
    const res = await apiFetch("/api/title", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_message: userMessage, bot_reply: botReply, lang: lang ?? "en" }),
    });
    if (!res.ok) return "";
    const data = await res.json();
    return typeof data.title === "string" ? data.title : "";
  } catch {
    return "";
  }
}

