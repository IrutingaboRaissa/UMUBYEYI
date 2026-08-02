import ChatApp from "@/components/ChatApp";
import AuthGate from "@/components/AuthGate";

export default function Home() {
  return (
    <AuthGate>
      <ChatApp />
    </AuthGate>
  );
}
