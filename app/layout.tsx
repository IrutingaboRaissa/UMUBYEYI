import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Umubyeyi",
  description: "A bilingual wellness companion for first-time mothers in Rwanda",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
