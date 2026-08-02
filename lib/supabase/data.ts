import { createClient } from "@/lib/supabase/client";
import { RAW_HISTORY_CAP, STORE_CURRENT_KEY, Thread } from "@/lib/chat";

// Reads the cached local session rather than auth.getUser() -- getUser() re-validates
// against Supabase's server on every call, so any transient network hiccup made every
// save fail with a misleading "Not signed in". Row Level Security re-checks the real JWT
// server-side regardless of what user_id the client sends, so there's no security reason
// to make this a network round trip.
async function requireUserId(): Promise<string> {
  const { data, error } = await createClient().auth.getSession();
  if (error) throw new Error(`Could not read session: ${error.message}`);
  if (!data.session) throw new Error("Not signed in");
  return data.session.user.id;
}

type ThreadRow = {
  id: string;
  title: string;
  title_source: Thread["titleSource"] | null;
  ts: number;
  msgs: Thread["msgs"];
  locked: boolean;
};

function rowToThread(row: ThreadRow): Thread {
  return {
    id: row.id,
    title: row.title,
    titleSource: row.title_source ?? undefined,
    ts: row.ts,
    msgs: row.msgs,
    locked: row.locked,
  };
}

export async function loadThreads(): Promise<{ threads: Thread[]; currentId: string }> {
  const supabase = createClient();
  const { data, error } = await supabase
    .from("threads")
    .select("id, title, title_source, ts, msgs, locked")
    .order("ts", { ascending: false });
  if (error) throw error;

  const threads = (data ?? []).map(rowToThread);
  if (!threads.length) return { threads: [], currentId: "" };

  let savedCurrent = "";
  try { savedCurrent = localStorage.getItem(STORE_CURRENT_KEY) || ""; } catch { /* ignore */ }
  const currentId = savedCurrent && threads.some((t) => t.id === savedCurrent)
    ? savedCurrent
    : threads[0].id;
  return { threads, currentId };
}

export async function saveThread(thread: Thread): Promise<Thread> {
  const userId = await requireUserId();
  const { data, error } = await createClient()
    .from("threads")
    .upsert({
      id: thread.id,
      user_id: userId,
      title: thread.title,
      title_source: thread.titleSource ?? null,
      ts: thread.ts,
      msgs: thread.msgs,
      locked: !!thread.locked,
      updated_at: new Date().toISOString(),
    })
    .select("id, title, title_source, ts, msgs, locked")
    .single();
  if (error) throw error;
  return rowToThread(data);
}

export async function deleteThread(id: string): Promise<void> {
  const { error } = await createClient().from("threads").delete().eq("id", id);
  if (error) throw error;
}

export type MoodEntry = { mood: string; date: string };

export async function loadMoodHistory(): Promise<MoodEntry[]> {
  const { data, error } = await createClient()
    .from("mood_checkins")
    .select("mood, occurred_at")
    .order("occurred_at", { ascending: false })
    .limit(RAW_HISTORY_CAP);
  if (error) throw error;
  return (data ?? []).map((row) => ({ mood: row.mood, date: row.occurred_at }));
}

export async function saveMoodEntry(mood: string): Promise<MoodEntry[]> {
  const userId = await requireUserId();
  const { error } = await createClient().from("mood_checkins").insert({ user_id: userId, mood });
  if (error) throw error;
  return loadMoodHistory();
}

export type CheckinEntry = { date: string; risk: string; elevated: boolean };

export async function loadCheckinHistory(): Promise<CheckinEntry[]> {
  const { data, error } = await createClient()
    .from("guided_checkins")
    .select("occurred_at, risk, elevated")
    .order("occurred_at", { ascending: false })
    .limit(RAW_HISTORY_CAP);
  if (error) throw error;
  return (data ?? []).map((row) => ({ date: row.occurred_at, risk: row.risk, elevated: row.elevated }));
}

export async function saveCheckinEntry(entry: { risk: string; elevated: boolean }): Promise<CheckinEntry[]> {
  const userId = await requireUserId();
  const { error } = await createClient().from("guided_checkins").insert({ user_id: userId, ...entry });
  if (error) throw error;
  return loadCheckinHistory();
}

export type ConcernEntry = { date: string; score: number; level: string };

export async function loadConcernHistory(): Promise<ConcernEntry[]> {
  const { data, error } = await createClient()
    .from("concern_history")
    .select("occurred_at, score, level")
    .order("occurred_at", { ascending: false })
    .limit(RAW_HISTORY_CAP);
  if (error) throw error;
  return (data ?? []).map((row) => ({ date: row.occurred_at, score: row.score, level: row.level }));
}

export async function saveConcernEntry(entry: { score: number; level: string }): Promise<ConcernEntry[]> {
  const userId = await requireUserId();
  const { error } = await createClient().from("concern_history").insert({ user_id: userId, ...entry });
  if (error) throw error;
  return loadConcernHistory();
}
