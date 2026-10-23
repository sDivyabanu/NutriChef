"use client";

import { Suspense, useCallback, useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { AlertCircle, Bookmark, Info, Loader2, SlidersHorizontal } from "lucide-react";
import SearchBox from "@/components/nlp/SearchBox";
import UnderstandingChips from "@/components/nlp/UnderstandingChips";
import RecipeResultCard from "@/components/nlp/RecipeResultCard";
import { api, ApiError, SearchResponse, Understanding } from "@/lib/nlp";

const EXAMPLES = [
  "I have tomatoes, rice and onions. What can I cook?",
  "Suggest a spicy vegetarian dinner under 30 minutes",
  "Something filling without meat",
  "High-protein breakfast under 350 calories",
  "South Indian recipes without peanuts",
  "What can I prepare using paneer and capsicum?",
  "Similar to fried rice but with more vegetables",
  "Kathirikai vechu enna cook pannalam?",
];
const PAGE = 12;

function SearchInner() {
  const params = useSearchParams();
  const router = useRouter();
  const [text, setText] = useState(params.get("q") || "");
  const [query, setQuery] = useState("");
  const [data, setData] = useState<SearchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [applyProfile, setApplyProfile] = useState(true);
  const [saved, setSaved] = useState<string | null>(null);
  const lastBody = useRef<Record<string, unknown> | null>(null);

  const run = useCallback(
    async (body: Record<string, unknown>, append = false) => {
      append ? setLoadingMore(true) : setLoading(true);
      setError(null);
      try {
        const res = await api<SearchResponse>("/nlp/search", { method: "POST", json: { k: PAGE, apply_profile: applyProfile, ...body } });
        lastBody.current = body;
        setData((prev) => (append && prev ? { ...res, results: [...prev.results, ...res.results] } : res));
      } catch (e) {
        setError(e instanceof ApiError ? e.message : "Search failed — is the NLP backend running on port 8000?");
        if (!append) setData(null);
      } finally {
        setLoading(false);
        setLoadingMore(false);
      }
    },
    [applyProfile]
  );

  const searchText = (q: string) => {
    setQuery(q);
    setSaved(null);
    router.replace(`/search?q=${encodeURIComponent(q)}`, { scroll: false });
    run({ query: q });
  };

  const searchUnderstanding = (u: Understanding) => run({ understanding: u });

  useEffect(() => {
    const q = params.get("q");
    if (q) {
      setQuery(q);
      run({ query: q });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [applyProfile]);

  const relax = (key: string) => {
    if (!data) return;
    const u = { ...data.understanding };
    if (key === "remove_time") u.max_time_min = null;
    else if (key === "remove_cuisine") u.cuisines = [];
    else if (key === "remove_meal") u.meal_types = [];
    else if (key.startsWith("optional:")) {
      const name = key.slice(9);
      u.ingredients = u.ingredients.map((i) => (i.name === name && i.role === "required" ? { ...i, role: "preferred" } : i));
    }
    searchUnderstanding(u);
  };

  const addIngredient = (name: string) => {
    if (!data) return;
    const u = { ...data.understanding, ingredients: [...data.understanding.ingredients, { name, display: name, role: "available" as const }] };
    searchUnderstanding(u);
  };

  const saveSearch = async () => {
    try {
      await api("/me/saved-searches", { method: "POST", json: { query } });
      setSaved("Saved to your searches.");
    } catch (e) {
      setSaved(e instanceof ApiError && e.status === 401 ? "Log in to save searches." : "Couldn't save.");
    }
  };

  const u = data?.understanding;
  const excluded = data ? Object.entries(data.excluded_counts).sort((a, b) => b[1] - a[1]) : [];

  return (
    <div className="max-w-6xl mx-auto px-1 sm:px-4 py-4 sm:py-8 space-y-6">
      <header className="kitchen-banner p-6 sm:p-10 space-y-3">
        <h1 className="display text-4xl sm:text-5xl">Smart Recipe Search</h1>
        <p className="text-slate-600">
          Ask in plain English (or Tamil-English). NutriChef understands ingredients, exclusions, diets, cuisines,
          time limits and more — all processed locally on this computer.
        </p>
      </header>

      <SearchBox value={text} onChange={setText} onSubmit={searchText} loading={loading} autoFocus />

      <div className="flex flex-wrap items-center gap-2">
        {EXAMPLES.map((ex) => (
          <button
            key={ex}
            onClick={() => {
              setText(ex);
              searchText(ex);
            }}
            className="text-xs sm:text-sm px-3 py-1.5 rounded-full bg-white border border-slate-200 text-slate-700 hover:bg-emerald-50 hover:border-emerald-200"
          >
            {ex}
          </button>
        ))}
      </div>

      <label className="inline-flex items-center gap-2 text-sm text-slate-600 cursor-pointer">
        <input type="checkbox" checked={applyProfile} onChange={(e) => setApplyProfile(e.target.checked)} className="accent-emerald-600" />
        Apply my saved diet & allergies (<a href="/preferences" className="underline">edit</a>)
      </label>

      {error && (
        <div role="alert" className="flex items-start gap-2 p-4 rounded-xl bg-rose-50 text-rose-800 border border-rose-200">
          <AlertCircle size={18} className="mt-0.5 shrink-0" /> {error}
        </div>
      )}

      {loading && !data && (
        <div className="flex items-center gap-2 text-slate-500" aria-live="polite">
          <Loader2 className="animate-spin" size={18} /> Understanding your request…
        </div>
      )}

      {data && u && (
        <section className="space-y-4" aria-live="polite">
          <div className="p-4 kitchen-card bg-white border border-slate-200 space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center gap-2 text-sm text-slate-600">
                <SlidersHorizontal size={16} className="text-emerald-600" />
                Understood as <span className="font-medium text-slate-800">{u.intent.replace(/_/g, " ")}</span>
                {u.language !== "en" && <span className="text-xs px-2 py-0.5 rounded bg-slate-100">mixed Tamil-English</span>}
              </div>
              <button onClick={saveSearch} className="text-sm inline-flex items-center gap-1 text-teal-700 hover:text-teal-900" disabled={!query}>
                <Bookmark size={15} /> Save search
              </button>
            </div>
            {saved && <p className="text-xs text-slate-500">{saved}</p>}
            {u.corrections.length > 0 && (
              <p className="text-sm text-slate-600">
                Spelling corrected:{" "}
                {u.corrections.map(([a, b]) => (
                  <span key={a} className="mr-2">
                    <s className="text-slate-400">{a}</s> → <b>{b}</b>
                  </span>
                ))}
              </p>
            )}
            <UnderstandingChips u={u} onChange={searchUnderstanding} />
            {u.clarification && <p className="text-sm text-sky-800 bg-sky-50 rounded-lg p-2">{u.clarification}</p>}
            {data.notes.map((n) => (
              <p key={n} className="text-sm text-slate-700 flex gap-2">
                <Info size={15} className="text-sky-600 mt-0.5 shrink-0" /> {n}
              </p>
            ))}
          </div>

          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <h2 className="text-lg font-semibold text-slate-800">
              {data.total.toLocaleString()} matching recipe{data.total === 1 ? "" : "s"}
            </h2>
            <span className="text-xs text-slate-500">
              {data.timing_ms.total_ms != null ? `${Math.round(data.timing_ms.total_ms)} ms · ` : ""}local hybrid search
            </span>
          </div>

          {excluded.length > 0 && (
            <details className="text-sm text-slate-600">
              <summary className="cursor-pointer">Why other recipes were filtered out</summary>
              <ul className="mt-2 space-y-0.5">
                {excluded.map(([reason, n]) => (
                  <li key={reason}>
                    {n.toLocaleString()} — {reason}
                  </li>
                ))}
              </ul>
            </details>
          )}

          {data.add_ingredient_suggestions.length > 0 && (
            <div className="flex flex-wrap items-center gap-2 text-sm">
              <span className="text-slate-600">Have any of these? Many top results need them:</span>
              {data.add_ingredient_suggestions.map((s) => (
                <button key={s} onClick={() => addIngredient(s)} className="px-2.5 py-1 rounded-full border border-emerald-300 text-emerald-800 hover:bg-emerald-50">
                  + {s}
                </button>
              ))}
            </div>
          )}

          {data.results.length === 0 ? (
            <div className="p-6 rounded-lg bg-white border border-slate-200 space-y-3">
              <p className="font-medium text-slate-800">No recipes satisfy every constraint.</p>
              {u.conflicts.length > 0 ? (
                <p className="text-sm text-slate-600">Your request contains conflicting requirements — please change one of them.</p>
              ) : data.relaxations.length > 0 ? (
                <>
                  <p className="text-sm text-slate-600">
                    Your exclusions and diet are always kept. You could relax one of these instead:
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {data.relaxations.map((r) => (
                      <button key={r.key} onClick={() => relax(r.key)} className="px-3 py-1.5 rounded-xl bg-emerald-600 text-white text-sm hover:bg-emerald-700">
                        {r.label} ({r.results})
                      </button>
                    ))}
                  </div>
                </>
              ) : (
                <p className="text-sm text-slate-600">Try fewer constraints, or describe the dish differently.</p>
              )}
            </div>
          ) : (
            <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
              {data.results.map((h, i) => (
                <RecipeResultCard key={h.recipe.id} hit={h} query={query} rank={i + 1} />
              ))}
            </div>
          )}

          {data.results.length > 0 && data.results.length < data.total && (
            <div className="text-center">
              <button
                onClick={() => lastBody.current && run({ ...lastBody.current, offset: data.results.length }, true)}
                disabled={loadingMore}
                className="px-5 py-2 rounded-xl border border-emerald-300 text-emerald-800 hover:bg-emerald-50 disabled:opacity-50"
              >
                {loadingMore ? "Loading…" : "Show more"}
              </button>
            </div>
          )}
        </section>
      )}
    </div>
  );
}

export default function SearchPage() {
  return (
    <Suspense fallback={null}>
      <SearchInner />
    </Suspense>
  );
}
