"use client";

import { useEffect, useId, useRef, useState } from "react";
import { Search, Loader2 } from "lucide-react";
import { api } from "@/lib/nlp";

type Props = {
  value: string;
  onChange: (v: string) => void;
  onSubmit: (v: string) => void;
  loading?: boolean;
  placeholder?: string;
  autoFocus?: boolean;
};

export default function SearchBox({ value, onChange, onSubmit, loading, placeholder, autoFocus }: Props) {
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(-1);
  const listId = useId();
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (timer.current) clearTimeout(timer.current);
    const q = value.trim();
    if (q.length < 2) {
      setSuggestions([]);
      return;
    }
    timer.current = setTimeout(async () => {
      try {
        const s = await api<string[]>(`/nlp/suggest?q=${encodeURIComponent(q)}&limit=8`);
        setSuggestions(s);
      } catch {
        setSuggestions([]);
      }
    }, 180);
  }, [value]);

  const submit = (v: string) => {
    setOpen(false);
    setActive(-1);
    if (v.trim()) onSubmit(v.trim());
  };

  return (
    <form
      role="search"
      onSubmit={(e) => {
        e.preventDefault();
        submit(active >= 0 && open ? suggestions[active] : value);
      }}
      className="relative"
    >
      <label htmlFor={listId + "-input"} className="sr-only">
        Search recipes in plain language
      </label>
      <div className="discovery-input flex items-center gap-2 bg-white rounded-lg border border-emerald-200 shadow-stamp-sm focus-within:ring-2 focus-within:ring-emerald-400 px-4">
        <Search className="text-emerald-500 shrink-0" size={20} aria-hidden />
        <input
          id={listId + "-input"}
          autoFocus={autoFocus}
          value={value}
          onChange={(e) => {
            onChange(e.target.value);
            setOpen(true);
            setActive(-1);
          }}
          onFocus={() => setOpen(true)}
          onBlur={() => setTimeout(() => setOpen(false), 150)}
          onKeyDown={(e) => {
            if (!open || !suggestions.length) return;
            if (e.key === "ArrowDown") {
              e.preventDefault();
              setActive((a) => (a + 1) % suggestions.length);
            } else if (e.key === "ArrowUp") {
              e.preventDefault();
              setActive((a) => (a <= 0 ? suggestions.length - 1 : a - 1));
            } else if (e.key === "Escape") {
              setOpen(false);
            }
          }}
          placeholder={placeholder || "e.g. I have tomatoes, rice and onions — what can I cook?"}
          className="flex-1 py-3.5 bg-transparent outline-none text-slate-800 placeholder:text-slate-400 min-w-0"
          role="combobox"
          aria-expanded={open && suggestions.length > 0}
          aria-controls={listId}
          aria-autocomplete="list"
          aria-activedescendant={active >= 0 ? `${listId}-${active}` : undefined}
          maxLength={500}
        />
        <button
          type="submit"
          disabled={loading || !value.trim()}
          className="shrink-0 px-4 py-2 rounded-xl bg-emerald-600 text-white font-medium hover:bg-emerald-700 disabled:opacity-50 flex items-center gap-2"
        >
          {loading ? <Loader2 className="animate-spin" size={16} aria-hidden /> : null}
          Search
        </button>
      </div>
      {open && suggestions.length > 0 && (
        <ul
          id={listId}
          role="listbox"
          className="absolute z-30 mt-2 w-full bg-white border border-emerald-100 rounded-xl shadow-lg overflow-hidden"
        >
          {suggestions.map((s, i) => (
            <li
              key={s}
              id={`${listId}-${i}`}
              role="option"
              aria-selected={i === active}
              onMouseDown={(e) => {
                e.preventDefault();
                onChange(s);
                submit(s);
              }}
              className={`px-4 py-2 cursor-pointer text-sm ${i === active ? "bg-emerald-50 text-emerald-800" : "text-slate-700 hover:bg-slate-50"}`}
            >
              {s}
            </li>
          ))}
        </ul>
      )}
    </form>
  );
}
