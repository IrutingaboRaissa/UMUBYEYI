import type { Metadata } from "next";
import PrivacyContent from "./PrivacyContent";

export const metadata: Metadata = {
  title: "Privacy Policy · Umubyeyi",
  description: "How Umubyeyi handles your data",
};

export default function PrivacyPolicy() {
  return <PrivacyContent />;
}
