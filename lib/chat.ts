export type Msg = {
  role: "user" | "bot";
  text: string;
  sub?: string;
  danger?: boolean;
  mode?: string;
};

export type Thread = {
  id: string;
  title: string;
  ts: number;
  msgs: Msg[];
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
};

export type ScreenResponse = {
  risk: "elevated" | "not_elevated";
  elevated: boolean;
  message_en: string;
  message_rw: string;
  disclaimer: string;
};

export const CHECKIN_FIELDS = [
  ["Relationship with husband", "Relationship with partner", ["Good", "Neutral", "Bad"]],
  ["Relationship with the newborn", "Connection with your baby", ["Good", "Neutral", "Bad"]],
  ["Feeling about motherhood", "How you feel about motherhood", ["Positive", "Neutral", "Negative"]],
  ["Recieved Support", "Support you currently receive", ["High", "Medium", "Low"]],
  ["Need for Support", "How much more support you need", ["High", "Medium", "Low"]],
  ["Abuse", "Have you experienced abuse?", ["No", "Yes"]],
  ["Trust and share feelings", "Can you share feelings with someone you trust?", ["Yes", "No"]],
  ["Worry about newborn", "Are you constantly worried about your baby?", ["No", "Yes"]],
  ["Relax/sleep when newborn is tended ", "Can you rest when someone trusted watches the baby?", ["Yes", "No"]],
  ["Relax/sleep when the newborn is asleep", "Can you rest when the baby sleeps?", ["Yes", "No"]],
  ["Angry after latest child birth", "Have you often felt angry or hard to calm?", ["No", "Yes"]],
  ["Feeling for regular activities", "How do ordinary activities feel?", ["Nothing (no difficulty)", "Tired", "Anxious", "Fearful"]],
  ["Depression before pregnancy (PHQ2)", "Low mood before pregnancy screening", ["Negative", "Positive"]],
  ["Depression during pregnancy (PHQ2)", "Low mood during pregnancy screening", ["Negative", "Positive"]],
] as const;

export const CRISIS_LINE = "114";
export const STORE_KEY = "umubyeyi_threads_v3";
export const STORE_CURRENT_KEY = "umubyeyi_current_v3";

export const TIPS = [
  ["🤝", "Shaka ubufasha", "Reach out", "Ganira n'umuntu wizeye cyangwa umukozi w'ubuzima.", "Talk to someone you trust or a health worker."],
  ["👪", "Wubake abagufasha", "Build support", "Egera uwo mwashakanye, umuryango n'incuti.", "Lean on your partner, family, and friends."],
  ["🌸", "Wite ku mutima wawe", "Self-care", "Fata udukanya duto wiyibagiza, ushake ibikunezeza bito.", "Take small moments for yourself; small joys matter."],
  ["😴", "Ruhuka bihagije", "Rest", "Sinzira igihe umwana asinziriye, usabe ubufasha nijoro.", "Sleep when the baby sleeps; ask for help at night."],
  ["🚶", "Imyitozo yoroheje", "Gentle movement", "Genda urugendo rugufi cyangwa unyeganyege gato.", "A short walk or light stretching lifts your mood."],
  ["🥗", "Kurya indyo yuzuye", "Nourish", "Fata indyo yuzuye kugira ngo ugire imbaraga.", "Balanced meals help your energy and mood."],
  ["🧘", "Humeka utuze", "Breathe", "Guhumeka gahoro bishobora gutuza umutima.", "A few slow breaths can calm a hard moment."],
  ["💬", "Vuga uko wiyumva", "Share openly", "Vuga ibyiyumvo byawe utagira ipfunwe.", "Speak your feelings without guilt; it's a strength."],
] as const;

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

export function loadThreads(): { threads: Thread[]; currentId: string } {
  if (typeof window === "undefined") {
    const t = newThread();
    return { threads: [t], currentId: t.id };
  }
  let threads: Thread[] = [];
  try {
    const raw = localStorage.getItem(STORE_KEY);
    if (raw) {
      const data = JSON.parse(raw);
      if (Array.isArray(data) && data.length) threads = data;
    }
  } catch { /* ignore */ }
  if (!threads.length) {
    const t = newThread();
    return { threads: [t], currentId: t.id };
  }
  const savedCurrent = localStorage.getItem(STORE_CURRENT_KEY);
  const currentId = savedCurrent && threads.some((t) => t.id === savedCurrent)
    ? savedCurrent
    : threads[0].id;
  return { threads: sortThreads(threads), currentId };
}

export function saveThreads(threads: Thread[], currentId: string) {
  if (typeof window === "undefined") return;
  localStorage.setItem(STORE_KEY, JSON.stringify(sortThreads(threads)));
  localStorage.setItem(STORE_CURRENT_KEY, currentId);
}

export function sortThreads(threads: Thread[]): Thread[] {
  return [...threads].sort((a, b) => b.ts - a.ts);
}

export function touchThread(t: Thread): Thread {
  return { ...t, ts: Date.now() };
}

export function sessionId(): string {
  if (typeof window === "undefined") return "";
  let sid = localStorage.getItem("umubyeyi_sid");
  if (!sid) {
    sid = Math.random().toString(36).slice(2, 18);
    localStorage.setItem("umubyeyi_sid", sid);
  }
  return sid;
}

export async function sendChat(message: string, forceLang?: "en" | "rw" | null): Promise<ChatResponse> {
  const res = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, force_lang: forceLang ?? null }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error || `Request failed (${res.status})`);
  }
  return res.json();
}

export async function sendScreen(answers: Record<string, string | number>): Promise<ScreenResponse> {
  const res = await fetch("/api/screen", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ answers }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error || `Request failed (${res.status})`);
  }
  return res.json();
}

export async function logEvent(sid: string, data: ChatResponse) {
  await fetch("/api/event", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      session_id: sid,
      language: data.language,
      mode: data.mode,
      grounded: data.grounded,
      sources: data.sources,
      latency_ms: data.latency_ms ?? 0,
    }),
  }).catch(() => {});
}

export async function sendFeedback(sid: string, rating: 1 | -1, lang?: string, mode?: string) {
  await fetch("/api/feedback", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sid, rating, language: lang, mode }),
  }).catch(() => {});
}
