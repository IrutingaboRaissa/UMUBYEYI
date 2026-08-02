import type { Metadata } from "next";
import "./globals.css";
import { LanguageProvider } from "@/lib/language";

export const metadata: Metadata = {
  title: "Umubyeyi",
  description: "A bilingual wellness companion for first-time mothers in Rwanda",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      {/* suppressHydrationWarning here only: browser extensions (Grammarly, password
          managers, etc.) inject attributes like data-gr-ext-installed onto <body> before
          React hydrates, causing a false-positive mismatch warning unrelated to our code. */}
      <body suppressHydrationWarning>
        <LanguageProvider>{children}</LanguageProvider>
      </body>
    </html>
  );
}
