// Local-only privacy lock: a PIN gates the whole app in the browser, on top of the real
// account sign-in (see components/AuthGate.tsx). Nothing here is sent anywhere. The PIN
// itself is never stored, only its SHA-256 hash, so reading localStorage doesn't reveal it.
//
// This is deliberately just a per-device quick-lock now, not the only line of defense --
// the mother's actual data lives in her Supabase account, so forgetting this PIN signs her
// out rather than destroying anything (see ChatApp.tsx's handleForgotPin).
const PIN_HASH_KEY = "umubyeyi_pin_hash_v1";

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
