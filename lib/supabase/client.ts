import { createBrowserClient } from "@supabase/ssr";

// One browser client per call site is fine -- @supabase/ssr's browser client
// is a thin wrapper that reads the session from cookies each time, not a
// heavyweight connection.
export function createClient() {
  return createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
  );
}
