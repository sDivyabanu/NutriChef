"use client";

import { useEffect } from "react";
import { OPEN_CHAT_EVENT } from "@/components/chat/FloatingChat";

// The assistant now lives in the floating chat panel (mounted once in the app layout).
// This route stays for old links and simply opens that panel.
export default function AssistantPage() {
  useEffect(() => {
    window.dispatchEvent(new Event(OPEN_CHAT_EVENT));
  }, []);
  return (
    <div className="max-w-3xl mx-auto px-1 sm:px-4 py-8">
      <h1 className="display text-2xl font-bold text-teal-800">Recipe Assistant</h1>
      <p className="text-slate-600 mt-2">
        The assistant is available on every page from the chat button in the bottom-right corner.{" "}
        <button onClick={() => window.dispatchEvent(new Event(OPEN_CHAT_EVENT))} className="underline text-teal-700">
          Open it
        </button>
        .
      </p>
    </div>
  );
}
