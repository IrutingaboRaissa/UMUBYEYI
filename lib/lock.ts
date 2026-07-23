// Local-only privacy lock: a PIN gates the whole app in the browser. Nothing here is sent
// anywhere -- consistent with the rest of Umubyeyi's client-side-only storage. The PIN itself
// is never stored, only its SHA-256 hash, so reading localStorage doesn't reveal it.
const PIN_HASH_KEY = "umubyeyi_pin_hash_v1";

// Every key that holds anything personal (threads, mood, EPDS, check-in, concern trend).
// A "forgot PIN" reset wipes exactly these, matching the app's "nothing survives off-device,
// and if you can't get back in there's nothing left to protect" privacy model.
const PERSONAL_DATA_KEYS = [
  "umubyeyi_threads_v3",
  "umubyeyi_current_v3",
  "umubyeyi_moods_v1",
  "umubyeyi_concern_v1",
  "umubyeyi_checkin_v1",
  "umubyeyi_epds_v1",
  "umubyeyi_epds_streak_v1",
  "umubyeyi_sid",
  PIN_HASH_KEY,
];

async function sha256Hex(text: string): Promise<string> {
  const bytes = new TextEncoder().encode(text);
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  return Array.from(new Uint8Array(digest)).map((b) => b.toString(16).padStart(2, "0")).join("");
}

export function hasPin(): boolean {
  if (typeof window === "undefined") return false;
  return !!localStorage.getItem(PIN_HASH_KEY);
}

export async function setPin(pin: string): Promise<void> {
  localStorage.setItem(PIN_HASH_KEY, await sha256Hex(pin));
}

export async function verifyPin(pin: string): Promise<boolean> {
  const stored = localStorage.getItem(PIN_HASH_KEY);
  if (!stored) return true;
  return (await sha256Hex(pin)) === stored;
}

export function removePin(): void {
  localStorage.removeItem(PIN_HASH_KEY);
}

/** "Forgot PIN" path: wipes all locked local data and the PIN itself. Nothing is recoverable
 * beyond this, by design -- there is no server copy to restore from. */
export function resetAllData(): void {
  for (const key of PERSONAL_DATA_KEYS) localStorage.removeItem(key);
}
