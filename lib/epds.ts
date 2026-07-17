// Edinburgh Postnatal Depression Scale (EPDS-10) — a real, validated postpartum
// screening instrument (Cox, Holden & Sagovsky, 1987), not an invented test.
//
// Item wording follows the published scale. The 4-point response scale, the
// 0-3 per-item scoring, and which items are reverse-scored follow this
// project's own licensed source dataset — Raisa & Kaiser, "Data for Postpartum
// Depression Prediction in Bangladesh", Mendeley Data v3, CC BY 4.0 — which
// adapts the original item-specific response wording to a uniform 4-point
// frequency scale (see data/postpartum_depression/PPD_Data_Dictionary_v3.csv,
// rows 48-57 for item text/scoring, row 68 for the Low/Medium/High cutoffs
// used below). This is a documented methodological choice, not a claim that
// every response option is verbatim from the 1987 paper.
//
// English only for now — no validated Kinyarwanda translation of this
// instrument exists yet; presenting an unverified one as equivalent would be
// dishonest. Ship bilingual once a validated RW translation is sourced.

export type EpdsItem = {
  id: string;
  text: string;
  /** true if a higher-frequency answer means FEWER symptoms (score is flipped). */
  reverseScored: boolean;
};

export const RESPONSE_LABELS = [
  "Not at all",
  "Several days",
  "More than half the days",
  "Nearly every day",
] as const;

export const EPDS_ITEMS: EpdsItem[] = [
  { id: "epds_1", text: "I have been able to laugh and see the funny side of things", reverseScored: true },
  { id: "epds_2", text: "I have looked forward with enjoyment to things", reverseScored: true },
  { id: "epds_3", text: "I have blamed myself unnecessarily when things went wrong", reverseScored: false },
  { id: "epds_4", text: "I have been anxious or worried for no good reason", reverseScored: false },
  { id: "epds_5", text: "I have felt scared or panicky for no very good reason", reverseScored: false },
  { id: "epds_6", text: "Things have been getting on top of me", reverseScored: false },
  { id: "epds_7", text: "I have been so unhappy that I have had difficulty sleeping", reverseScored: false },
  { id: "epds_8", text: "I have felt sad or miserable", reverseScored: false },
  { id: "epds_9", text: "I have been so unhappy that I have been crying", reverseScored: false },
  { id: "epds_10", text: "The thought of harming myself has occurred to me", reverseScored: false },
];

/** Index of the self-harm item — any non-zero answer routes to the existing crisis modal. */
export const EPDS_ITEM10_INDEX = 9;

export type EpdsBand = "low" | "medium" | "high";

export type EpdsEntry = {
  date: string; // ISO timestamp
  total: number; // 0-30
  band: EpdsBand;
  item10Flag: boolean;
};

export type EpdsStreak = { count: number; lastDate: string };

export const EPDS_STORAGE_KEY = "umubyeyi_epds_v1";
export const EPDS_STREAK_KEY = "umubyeyi_epds_streak_v1";
const HISTORY_CAP = 30;

export function scoreOption(item: EpdsItem, optionIndex: number): number {
  return item.reverseScored ? 3 - optionIndex : optionIndex;
}

export function computeTotal(optionIndices: number[]): number {
  return EPDS_ITEMS.reduce((sum, item, i) => sum + scoreOption(item, optionIndices[i] ?? 0), 0);
}

/** Bands and the 13-point "high" cutoff come from the licensed dataset's own
 * data dictionary and match the standard cited EPDS threshold in the
 * literature — not derived from this app's separate ML classifier. */
export function classifyBand(total: number): EpdsBand {
  if (total >= 13) return "high";
  if (total >= 9) return "medium";
  return "low";
}

export function isItem10Flagged(optionIndices: number[]): boolean {
  return (optionIndices[EPDS_ITEM10_INDEX] ?? 0) > 0;
}

export function loadEpdsHistory(): EpdsEntry[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = JSON.parse(localStorage.getItem(EPDS_STORAGE_KEY) || "[]");
    return Array.isArray(raw) ? raw : [];
  } catch {
    return [];
  }
}

export function saveEpdsEntry(entry: EpdsEntry): EpdsEntry[] {
  const next = [entry, ...loadEpdsHistory()].slice(0, HISTORY_CAP);
  if (typeof window !== "undefined") localStorage.setItem(EPDS_STORAGE_KEY, JSON.stringify(next));
  return next;
}

export function loadStreak(): EpdsStreak {
  if (typeof window === "undefined") return { count: 0, lastDate: "" };
  try {
    const raw = JSON.parse(localStorage.getItem(EPDS_STREAK_KEY) || "null");
    if (raw && typeof raw.count === "number") return raw;
  } catch {
    /* ignore */
  }
  return { count: 0, lastDate: "" };
}

/** Rewards taking the assessment regularly — never the score/content of answers. */
export function bumpStreak(): EpdsStreak {
  const next = { count: loadStreak().count + 1, lastDate: new Date().toISOString() };
  if (typeof window !== "undefined") localStorage.setItem(EPDS_STREAK_KEY, JSON.stringify(next));
  return next;
}
