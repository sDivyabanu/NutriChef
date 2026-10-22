"use client";

import { KeyboardEvent, useCallback, useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ChefHat, Loader2, MessageCircle, RotateCcw, Send, X } from "lucide-react";
import { api, ApiError, SearchHit, Understanding } from "@/lib/nlp";
import UnderstandingChips from "@/components/nlp/UnderstandingChips";

// Same contract, state shape and storage key as the former /assistant page, so history carries over.
type ChatState = { understanding: Understanding | null; shown_ids: number[]; focus_recipe_id: number | null; turns: number };
type ChatOut = { reply: string; action: string; state: ChatState; results: SearchHit[]; total: number | null; focus_recipe_id: number | null; suggestions: string[] };
type Msg = { role: "user" | "bot"; text: string; results?: SearchHit[]; total?: number | null; action?: string };

const STARTERS = ["Find a high-protein vegetarian dinner", "I have rice, tomatoes and onions", "Something spicy without peanuts", "Paneer vechu spicy dinner suggest pannu"];
const STORAGE_KEY = "nutrichef-chat-v1";
export const OPEN_CHAT_EVENT = "nutrichef:open-chat";

export default function FloatingChat() {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [state, setState] = useState<ChatState | null>(null);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const endRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);
  const loaded = useRef(false);

  useEffect(() => {
    try {
      const saved = sessionStorage.getItem(STORAGE_KEY);
      if (saved) {
        const d = JSON.parse(saved);
        setMsgs(d.msgs || []);
        setState(d.state || null);
      }
    } catch {
      /* storage unavailable */
    }
    loaded.current = true;
    const openHandler = () => setOpen(true);
    window.addEventListener(OPEN_CHAT_EVENT, openHandler);
    return () => window.removeEventListener(OPEN_CHAT_EVENT, openHandler);
  }, []);

  useEffect(() => {
    if (!loaded.current) return;
    try {
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify({ msgs: msgs.slice(-40), state }));
    } catch {
      /* ignore */
    }
  }, [msgs, state]);

  useEffect(() => {
    if (open) endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [msgs, busy, open]);

  const close = useCallback(() => {
    setOpen(false);
    buttonRef.current?.focus();
  }, []);

  useEffect(() => {
    if (!open) return;
    const t = setTimeout(() => inputRef.current?.focus(), 250);
    const onKey = (e: globalThis.KeyboardEvent) => {
      if (e.key === "Escape") close();
    };
    window.addEventListener("keydown", onKey);
    return () => {
      clearTimeout(t);
      window.removeEventListener("keydown", onKey);
    };
  }, [open, close]);

  const send = async (message: string) => {
    if (!message.trim() || busy) return;
    setMsgs((m) => [...m, { role: "user", text: message }]);
    setText("");
    setBusy(true);
    setError(null);
    try {
      const r = await api<ChatOut>("/nlp/chat", { method: "POST", json: { message, state } });
      setState(r.state);
      setMsgs((m) => [...m, { role: "bot", text: r.reply, results: r.results, total: r.total, action: r.action }]);
      if (r.action === "generate" && r.suggestions[0]) {
        setMsgs((m) => [...m, { role: "bot", text: "", action: "generate-link" }]);
        sessionStorage.setItem("nutrichef-generate-prefill", r.suggestions[0]);
      }
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "The assistant is unavailable — is the backend running?");
    } finally {
      setBusy(false);
    }
  };

  const reset = () => {
    setMsgs([]);
    setState(null);
    setError(null);
    try {
      sessionStorage.removeItem(STORAGE_KEY);
    } catch {
      /* ignore */
    }
    inputRef.current?.focus();
  };

  const onInputKey = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault();
      send(text);
    }
  };

  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  if (!mounted) return null;

  // Portalled to <body> so no transformed/animated ancestor can turn position:fixed into page-relative.
  return createPortal(
    <>
      <button
        ref={buttonRef}
        onClick={() => setOpen((o) => !o)}
        aria-label={open ? "Close recipe assistant" : "Open recipe assistant"}
        aria-expanded={open}
        aria-controls="nutrichef-chat-panel"
        className={`chat-launcher fixed bottom-5 right-5 z-[60] h-14 w-14 rounded-full bg-gradient-to-br from-emerald-500 to-teal-600 text-white shadow-lg shadow-emerald-600/30 flex items-center justify-center transition-all duration-200 hover:scale-105 hover:shadow-xl focus:outline-none focus-visible:ring-4 focus-visible:ring-emerald-300 ${
          open ? "opacity-0 pointer-events-none scale-90" : "opacity-100"
        }`}
      >
        <MessageCircle size={26} aria-hidden />
        <ChefHat size={14} className="absolute top-2.5 right-2.5" aria-hidden />
        {msgs.length > 0 && !open && <span className="absolute -top-0.5 -right-0.5 h-3.5 w-3.5 rounded-full bg-amber-400 ring-2 ring-white" aria-hidden />}
      </button>

      {/* Clipping layer: keeps the off-screen panel from adding horizontal scroll width */}
      <div className="fixed inset-0 z-[70] overflow-hidden pointer-events-none">
      <aside
        id="nutrichef-chat-panel"
        role="dialog"
        aria-modal="false"
        aria-labelledby="nutrichef-chat-title"
        aria-hidden={!open}
        inert={!open}
        className={`chat-panel pointer-events-auto absolute top-0 right-0 h-[100dvh] w-full sm:w-[85vw] md:w-[50vw] lg:w-[38vw] max-w-[640px] lg:min-w-[440px] bg-white/95 backdrop-blur-md border-l border-emerald-100 flex flex-col transition-[translate,box-shadow,visibility] duration-300 ease-out ${
          open ? "translate-x-0 shadow-2xl visible" : "translate-x-full shadow-none invisible"
        }`}
      >
        <header className="chat-header flex items-center justify-between gap-3 px-4 sm:px-5 py-3.5 border-b border-emerald-100 bg-gradient-to-r from-emerald-50 to-white shrink-0">
          <div className="flex items-center gap-2.5 min-w-0">
            <span className="h-9 w-9 shrink-0 rounded-full bg-gradient-to-br from-emerald-500 to-teal-600 text-white flex items-center justify-center" aria-hidden>
              <ChefHat size={18} />
            </span>
            <div className="min-w-0">
              <h2 id="nutrichef-chat-title" className="font-bold text-emerald-800 leading-tight">THE KITCHEN SIDEKICK</h2>
              <p className="text-xs text-slate-500 truncate">Refine step by step — answers come from the recipe database</p>
            </div>
          </div>
          <div className="flex items-center gap-1 shrink-0">
            <button onClick={reset} className="inline-flex items-center gap-1 text-xs px-2.5 py-1.5 rounded-lg border border-slate-200 text-slate-600 hover:bg-white" aria-label="Reset conversation">
              <RotateCcw size={14} aria-hidden /> Reset
            </button>
            <button onClick={close} className="p-2 rounded-lg text-slate-600 hover:bg-emerald-100" aria-label="Close recipe assistant">
              <X size={20} aria-hidden />
            </button>
          </div>
        </header>

        {state?.understanding && (
          <div className="px-4 sm:px-5 py-2.5 border-b border-slate-100 bg-white shrink-0">
            <p className="text-[11px] uppercase tracking-wide text-slate-400 mb-1.5">Remembered filters</p>
            <UnderstandingChips u={state.understanding} />
          </div>
        )}

        <div className="flex-1 overflow-y-auto overflow-x-hidden px-4 sm:px-5 py-4 space-y-4" aria-live="polite">
          {msgs.length === 0 && (
            <div className="p-4 rounded-2xl bg-emerald-50/60 border border-emerald-100 space-y-3">
              <p className="text-slate-700 text-sm">Ask about recipes in plain English or Tamil-English. Try:</p>
              <div className="flex flex-wrap gap-2">
                {STARTERS.map((s) => (
                  <button key={s} onClick={() => send(s)} className="text-sm px-3 py-1.5 rounded-full border border-emerald-200 bg-white text-emerald-800 hover:bg-emerald-100 text-left">
                    {s}
                  </button>
                ))}
              </div>
              <p className="text-xs text-slate-500">Then refine: “only paneer recipes”, “under 20 minutes”, “how long does the first one take?”, “eggs are fine”, “start over”.</p>
            </div>
          )}
          {msgs.map((m, i) =>
            m.action === "generate-link" ? (
              <div key={i}>
                <button onClick={() => router.push("/generate")} className="px-4 py-2 rounded-xl bg-teal-600 text-white text-sm">
                  Open the recipe generator →
                </button>
              </div>
            ) : (
              <div key={i} className={m.role === "user" ? "flex justify-end" : "space-y-2"}>
                <div
                  className={`max-w-[88%] rounded-2xl px-4 py-2.5 whitespace-pre-wrap break-words text-sm ${
                    m.role === "user" ? "bg-emerald-600 text-white rounded-br-md" : "bg-white border border-slate-200 text-slate-800 rounded-bl-md shadow-stamp-sm"
                  }`}
                >
                  {m.text}
                </div>
                {m.results && m.results.length > 0 && (
                  <ol className="grid gap-2">
                    {m.results.map((h, j) => (
                      <li key={h.recipe.id} className="p-3 rounded-xl bg-white border border-slate-200 text-sm">
                        <span className="text-xs text-slate-400 mr-1">{j + 1}.</span>
                        <Link href={`/recipes/${h.recipe.id}`} className="font-medium text-teal-800 hover:underline break-words">
                          {h.recipe.title}
                        </Link>
                        <p className="text-xs text-slate-500 mt-1">{h.explanation[0]}</p>
                        {h.recipe.derived.estimated_time_min != null && <p className="text-xs text-slate-400">~{h.recipe.derived.estimated_time_min} min (estimated)</p>}
                      </li>
                    ))}
                  </ol>
                )}
              </div>
            )
          )}
          {busy && (
            <p className="flex items-center gap-2 text-slate-500 text-sm">
              <Loader2 size={15} className="animate-spin" /> Thinking…
            </p>
          )}
          {error && (
            <p role="alert" className="text-rose-700 text-sm">
              {error}
            </p>
          )}
          <div ref={endRef} />
        </div>

        <form
          onSubmit={(e) => {
            e.preventDefault();
            send(text);
          }}
          className="shrink-0 border-t border-emerald-100 bg-white p-3 pb-[max(0.75rem,env(safe-area-inset-bottom))]"
        >
          <label htmlFor="chat-input" className="sr-only">
            Message the recipe assistant
          </label>
          <div className="flex items-end gap-2 rounded-lg border border-emerald-200 bg-white p-1.5 focus-within:ring-2 focus-within:ring-emerald-400">
            <textarea
              id="chat-input"
              ref={inputRef}
              value={text}
              onChange={(e) => setText(e.target.value)}
              onKeyDown={onInputKey}
              placeholder="Ask or refine…"
              aria-describedby="chat-input-hint"
              rows={1}
              className="flex-1 resize-none max-h-32 px-2.5 py-2 outline-none bg-transparent text-sm"
              maxLength={500}
              autoComplete="off"
            />
            <button type="submit" disabled={busy || !text.trim()} className="shrink-0 px-3.5 py-2 rounded-xl bg-emerald-600 text-white disabled:opacity-50 inline-flex items-center gap-1 text-sm" aria-label="Send message">
              <Send size={16} aria-hidden /> Send
            </button>
          </div>
          <p id="chat-input-hint" className="mt-1.5 px-1 text-[11px] text-slate-400">Enter to send · Shift+Enter for a new line · Esc to close</p>
        </form>
      </aside>
      </div>
    </>,
    document.body
  );
}
