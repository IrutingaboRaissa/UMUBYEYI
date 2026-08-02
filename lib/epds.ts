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
// The 10 item questions and the response scale are English-sourced from the published
// scale/licensed dataset (see above). The Kinyarwanda text on each (textRw / the RW half of
// RESPONSE_LABELS) is this project's own translation, authored the same way as the rest of
// the app's Kinyarwanda copy -- it has NOT been reviewed by a clinician or a native-speaker
// translator, and is not a claim of official equivalence with the validated English EPDS-10.
// The disclaimer shown in EpdsAssessment.tsx states this plainly; see also
// UMUBYEYI project docs for the open item to source/commission a validated RW translation.

import { createClient } from "@/lib/supabase/client";

export type EpdsItem = {
  id: string;
  text: string;
  textRw: string;
  /** true if a higher-frequency answer means FEWER symptoms (score is flipped). */
  reverseScored: boolean;
};

export const RESPONSE_LABELS = [
  ["Not at all", "Rwose ntabwo"],
  ["Several days", "Iminsi mike"],
  ["More than half the days", "Birenze kimwe cya kabiri cy'iminsi"],
  ["Nearly every day", "Hafi buri munsi"],
] as const;

export const EPDS_ITEMS: EpdsItem[] = [
  { id: "epds_1", text: "I have been able to laugh and see the funny side of things",
    textRw: "Narashoboye guseka no kubona uruhande rushimishije rw'ibintu", reverseScored: true },
  { id: "epds_2", text: "I have looked forward with enjoyment to things",
    textRw: "Nari niteze kunezerwa n'ibintu byari bigiye kuba", reverseScored: true },
  { id: "epds_3", text: "I have blamed myself unnecessarily when things went wrong",
    textRw: "Nariyibazaga nta mpamvu igihe ibintu byifashe nabi", reverseScored: false },
  { id: "epds_4", text: "I have been anxious or worried for no good reason",
    textRw: "Nagize impungenge cyangwa guhangayika nta mpamvu ihagije", reverseScored: false },
  { id: "epds_5", text: "I have felt scared or panicky for no very good reason",
    textRw: "Nagize ubwoba cyangwa guhahamuka nta mpamvu ihagije", reverseScored: false },
  { id: "epds_6", text: "Things have been getting on top of me",
    textRw: "Numvaga ibintu byose binyikubiseho", reverseScored: false },
  { id: "epds_7", text: "I have been so unhappy that I have had difficulty sleeping",
    textRw: "Nababaye cyane ku buryo byangoye gusinzira", reverseScored: false },
  { id: "epds_8", text: "I have felt sad or miserable",
    textRw: "Numvaga mbabaye cyangwa ntishimye", reverseScored: false },
  { id: "epds_9", text: "I have been so unhappy that I have been crying",
    textRw: "Nababaye cyane ku buryo narize", reverseScored: false },
  { id: "epds_10", text: "The thought of harming myself has occurred to me",
    textRw: "Nagize igitekerezo cyo kwihutaza", reverseScored: false },
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

// There's no real cost to keeping a long history -- 500 entries is years of even weekly
// use. The old cap of 30 was silently deleting a mother's own past results once she'd
// taken the test 31 times, with no way to get them back.
const HISTORY_CAP = 500;

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

export async function loadEpdsHistory(): Promise<EpdsEntry[]> {
  const { data, error } = await createClient()
    .from("epds_results")
    .select("occurred_at, total, band, item10_flag")
    .order("occurred_at", { ascending: false })
    .limit(HISTORY_CAP);
  if (error) throw error;
  return (data ?? []).map((row) => ({
    date: row.occurred_at,
    total: row.total,
    band: row.band as EpdsBand,
    item10Flag: row.item10_flag,
  }));
}

export async function saveEpdsEntry(entry: EpdsEntry): Promise<EpdsEntry[]> {
  const { data: userData, error: userError } = await createClient().auth.getUser();
  if (userError || !userData.user) throw new Error("Not signed in");
  const { error } = await createClient().from("epds_results").insert({
    user_id: userData.user.id,
    total: entry.total,
    band: entry.band,
    item10_flag: entry.item10Flag,
  });
  if (error) throw error;
  return loadEpdsHistory();
}

/** Derived from history rather than stored separately -- it was always incremented 1:1
 * with each saved entry, so a separate counter could only drift once writes go over the
 * network (e.g. a failed insert would still have bumped a locally-stored streak). */
export function deriveStreak(history: EpdsEntry[]): EpdsStreak {
  return { count: history.length, lastDate: history[0]?.date ?? "" };
}
