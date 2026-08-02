import { createServerClient, type CookieOptions } from "@supabase/ssr";
import { cookies } from "next/headers";

// For Server Components / Route Handlers, should any be added later. Next 15's
// cookies() is async, so this factory is async too.
export async function createClient() {
  const cookieStore = await cookies();

  return createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return cookieStore.getAll();
        },
        setAll(cookiesToSet: { name: string; value: string; options: CookieOptions }[]) {
          try {
            cookiesToSet.forEach(({ name, value, options }) =>
              cookieStore.set(name, value, options)
            );
          } catch {
            // Called from a Server Component with no writable response --
            // fine as long as middleware.ts is also refreshing sessions.
          }
        },
      },
    }
  );
}
