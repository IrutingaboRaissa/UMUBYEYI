import ChatApp from "@/components/ChatApp";
import { LanguageProvider } from "@/lib/language";

export default function Home() {
  return (
    <LanguageProvider>
      <ChatApp />
    </LanguageProvider>
  );
}
