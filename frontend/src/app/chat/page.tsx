"use client";
import { Suspense } from "react";
import ChatContent from "./ChatContent";

export default function ChatPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin h-8 w-8 border-2 border-patch-accent border-t-transparent rounded-full" />
      </div>
    }>
      <ChatContent />
    </Suspense>
  );
}
