import type { Metadata } from "next";
import EulaContent from "./EulaContent";

export const metadata: Metadata = {
  title: "End User License Agreement · Umubyeyi",
  description: "Terms of use for Umubyeyi",
};

export default function Eula() {
  return <EulaContent />;
}
