"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Loader2, Plus, Search } from "lucide-react";
import { api, ApiError, Recipe } from "@/lib/nlp";
import FoodArt from "@/components/bento/FoodArt";

type Page = { items: Recipe[]; total: number; offset: number; limit: number };
const LIMIT = 24;

export default function RecipesPage() {
  const [tab, setTab] = useState<"all" | "mine">("all");
  const [q, setQ] = useState("");
  const [term, setTerm] = useState("");
  const [offset, setOffset] = useState(0);
  const [data, setData] = useState<Page | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    setLoading(true);
    setError(null);
    const params = new URLSearchParams({ offset: String(offset), limit: String(LIMIT) });
    if (term) params.set("q", term);
    if (tab === "mine") params.set("mine", "true");
    api<Page>(`/recipes?${params}`)
      .then((d) => alive && setData(d))
      .catch((e) => alive && setError(e instanceof ApiError ? e.message : "Could not load recipes. Is the backend running?"))
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, [tab, term, offset]);

  return (
    <div className="max-w-6xl mx-auto px-1 sm:px-4 py-4 sm:py-8 space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="display text-4xl sm:text-5xl">Recipes</h1>
          <p className="text-slate-600">
            Browse {data && tab === "all" ? data.total.toLocaleString() : ""} recipes, or use{" "}
            <Link href="/search" className="underline text-teal-700">
              Smart Search
            </Link>{" "}
            to ask in plain language.
          </p>
        </div>
        <Link href="/recipes/new" className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-emerald-600 text-white font-medium hover:bg-emerald-700">
          <Plus size={18} /> New recipe
        </Link>
      </header>

      <div className="flex flex-wrap items-center gap-3">
        <div role="tablist" className="inline-flex rounded-xl border border-slate-200 bg-white p-1">
          {(["all", "mine"] as const).map((t) => (
            <button
              key={t}
              role="tab"
              aria-selected={tab === t}
              onClick={() => {
                setTab(t);
                setOffset(0);
              }}
              className={`px-4 py-1.5 rounded-lg text-sm ${tab === t ? "bg-emerald-600 text-white" : "text-slate-700 hover:bg-slate-50"}`}
            >
              {t === "all" ? "All recipes" : "My recipes"}
            </button>
          ))}
        </div>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            setOffset(0);
            setTerm(q.trim());
          }}
          className="flex items-center gap-2 bg-white border border-slate-200 rounded-xl px-3"
        >
          <Search size={16} className="text-slate-400" aria-hidden />
          <label htmlFor="title-filter" className="sr-only">
            Filter by title
          </label>
          <input id="title-filter" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Filter by title" className="py-2 outline-none bg-transparent text-sm" />
        </form>
      </div>

      {error && <p role="alert" className="text-rose-700">{error}</p>}
      {loading && (
        <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3" aria-label="Loading recipes">
          {Array.from({ length: 6 }).map((_, i) => (
            <li key={i} className="skeleton h-56" />
          ))}
        </ul>
      )}
      {!loading && data && data.items.length === 0 && (
        <div className="p-6 rounded-lg bg-white border border-slate-200 text-slate-600">
          {tab === "mine" ? (
            <>
              You haven&apos;t created any recipes yet.{" "}
              <Link href="/recipes/new" className="underline text-teal-700">
                Create one
              </Link>{" "}
              or{" "}
              <Link href="/generate" className="underline text-teal-700">
                generate one
              </Link>
              .
            </>
          ) : (
            "No recipes match that title."
          )}
        </div>
      )}

      <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {data?.items.map((r) => (
          <li key={r.id}>
            <Link href={`/recipes/${r.id}`} className="group block h-full kitchen-card bg-white border border-slate-200 overflow-hidden transition duration-300 hover:-translate-y-1 hover:border-emerald-300">
              <FoodArt title={r.title} hints={r.ingredients} size="md" className="h-36" />
              <div className="p-5">
              <div className="flex items-start justify-between gap-2">
                <h2 className="font-bold text-ink leading-snug">{r.title}</h2>
                {r.source !== "epicurious-13k" && (
                  <span className="shrink-0 text-[10px] uppercase tracking-wide px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800">
                    {r.source === "generated" ? "generated" : "yours"}
                  </span>
                )}
              </div>
              <p className="text-sm text-slate-500 mt-2 line-clamp-2">{r.ingredients.slice(0, 6).join(" · ")}</p>
              </div>
            </Link>
          </li>
        ))}
      </ul>

      {data && data.total > LIMIT && (
        <nav className="flex items-center justify-center gap-3" aria-label="Pagination">
          <button disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - LIMIT))} className="px-4 py-2 rounded-xl border border-slate-300 disabled:opacity-40">
            Previous
          </button>
          <span className="text-sm text-slate-600">
            {offset + 1}–{Math.min(offset + LIMIT, data.total)} of {data.total.toLocaleString()}
          </span>
          <button disabled={offset + LIMIT >= data.total} onClick={() => setOffset(offset + LIMIT)} className="px-4 py-2 rounded-xl border border-slate-300 disabled:opacity-40">
            Next
          </button>
        </nav>
      )}
    </div>
  );
}
