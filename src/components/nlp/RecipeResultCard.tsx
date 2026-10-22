"use client";

import Link from "next/link";
import { useState } from "react";
import { AlertTriangle, CheckCircle2, Clock, Flame, HelpCircle, Leaf, ThumbsDown, ThumbsUp, Waves } from "lucide-react";
import { api, SearchHit, titleCase } from "@/lib/nlp";
import FoodArt from "@/components/bento/FoodArt";

export function DerivedBadges({ d }: { d: SearchHit["recipe"]["derived"] }) {
  return (
    <div className="flex flex-wrap gap-1.5 text-xs">
      {d.diet?.vegan ? (
        <Badge className="bg-green-100 text-green-800" title="No animal ingredients found in the ingredient list">
          <Leaf size={12} aria-hidden /> Vegan
        </Badge>
      ) : d.diet?.vegetarian ? (
        <Badge className="bg-green-50 text-green-800" title="No meat, fish or eggs found in the ingredient list">
          <Leaf size={12} aria-hidden /> Vegetarian
        </Badge>
      ) : d.diet?.eggetarian ? (
        <Badge className="bg-lime-50 text-lime-800" title="No meat or fish found; contains eggs">
          Eggetarian
        </Badge>
      ) : null}
      {d.estimated_time_min != null && (
        <Badge className="bg-slate-100 text-slate-700" title={`Estimated: ${d.time_basis}`}>
          <Clock size={12} aria-hidden /> ~{d.estimated_time_min} min
        </Badge>
      )}
      {d.spice_level && d.spice_level !== "mild" && (
        <Badge className="bg-red-50 text-red-700" title="Estimated from chili ingredients">
          <Flame size={12} aria-hidden /> {d.spice_level}
        </Badge>
      )}
      {d.cuisine_guess && (
        <Badge className="bg-violet-50 text-violet-700" title="Cuisine inferred from title and ingredients">
          {titleCase(d.cuisine_guess)}
        </Badge>
      )}
      {d.difficulty && (
        <Badge className="bg-white border border-slate-200 text-slate-600" title="Estimated from ingredient count, steps and techniques">
          {d.difficulty}
        </Badge>
      )}
    </div>
  );
}

function Badge({ children, className, title }: { children: React.ReactNode; className: string; title?: string }) {
  return (
    <span title={title} className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full ${className}`}>
      {children}
    </span>
  );
}

const STATUS_ICON = {
  pass: <CheckCircle2 size={14} className="text-emerald-600 shrink-0" aria-label="passed" />,
  estimated: <Waves size={14} className="text-amber-600 shrink-0" aria-label="estimated" />,
  unknown: <HelpCircle size={14} className="text-slate-400 shrink-0" aria-label="not verified" />,
};

export default function RecipeResultCard({ hit, query, rank }: { hit: SearchHit; query?: string; rank: number }) {
  const r = hit.recipe;
  const [feedback, setFeedback] = useState<null | boolean>(null);
  const [showWhy, setShowWhy] = useState(false);

  const sendFeedback = async (helpful: boolean) => {
    setFeedback(helpful);
    try {
      await api("/nlp/feedback", { method: "POST", json: { query: query || "", recipe_id: r.id, helpful } });
    } catch {
      /* feedback is best-effort */
    }
  };

  return (
    <article className="recipe-result group kitchen-card bg-white border border-slate-200 overflow-hidden transition duration-300 hover:-translate-y-1 hover:border-emerald-300 hover:shadow-[0_18px_40px_-20px_rgba(25,63,67,0.35)] flex flex-col">
      <Link href={`/recipes/${r.id}`} tabIndex={-1} aria-hidden className="relative block h-40">
        <FoodArt title={r.title} hints={[...r.ingredients_preview, ...(r.derived.meal_type_guess || [])]} size="md" className="absolute inset-0" />
        {hit.pantry_match_pct != null && (
          <span className="pill absolute left-3 top-3 bg-cream/95 text-ink text-xs py-1.5">{hit.pantry_match_pct}% pantry match</span>
        )}
      </Link>
      <div className="p-5 flex flex-col gap-3 flex-1">
      <div className="flex items-start justify-between gap-3">
        <h3 className="text-lg font-bold text-ink leading-snug">
          <span className="sr-only">Result {rank}: </span>
          <Link href={`/recipes/${r.id}`} className="hover:underline">
            {r.title}
          </Link>
        </h3>
        {hit.pantry_match_pct != null && (
          <div
            className="shrink-0 text-right hidden"
            title="Pantry match = share of the recipe's main ingredients (excluding salt, pepper, oil, water and optional items) that you have."
          >
            <div className="text-xl font-bold text-emerald-700">{hit.pantry_match_pct}%</div>
            <div className="text-[10px] uppercase tracking-wide text-slate-500">pantry match</div>
          </div>
        )}
      </div>

      <DerivedBadges d={r.derived} />

      <ul className="text-sm text-slate-700 space-y-1">
        {hit.explanation.map((e) => (
          <li key={e}>• {e}</li>
        ))}
      </ul>

      {(hit.used_ingredients.length > 0 || hit.missing_ingredients.length > 0) && (
        <div className="text-sm space-y-1.5">
          {hit.used_ingredients.length > 0 && (
            <div className="flex flex-wrap gap-1.5 items-center">
              <span className="text-xs text-slate-500 w-14">You have</span>
              {hit.used_ingredients.map((i) => (
                <span key={i} className="px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-800 text-xs border border-emerald-200">
                  {i}
                </span>
              ))}
            </div>
          )}
          {hit.missing_ingredients.length > 0 && (
            <div className="flex flex-wrap gap-1.5 items-center">
              <span className="text-xs text-slate-500 w-14">Missing</span>
              {hit.missing_ingredients.slice(0, 8).map((i) => (
                <span key={i} className="px-2 py-0.5 rounded-full bg-amber-50 text-amber-800 text-xs border border-amber-200">
                  {i}
                </span>
              ))}
              {hit.missing_ingredients.length > 8 && <span className="text-xs text-slate-500">+{hit.missing_ingredients.length - 8} more</span>}
            </div>
          )}
        </div>
      )}

      {hit.checks.length > 0 && (
        <ul className="text-xs text-slate-600 space-y-1 border-t border-slate-100 pt-2">
          {hit.checks.map((c, i) => (
            <li key={i} className="flex items-start gap-1.5">
              {STATUS_ICON[c.status]}
              <span>
                <span className="font-medium">{c.constraint}</span> — {c.detail}
              </span>
            </li>
          ))}
        </ul>
      )}

      {hit.warnings.length > 0 && (
        <ul className="text-xs text-amber-800 bg-amber-50 rounded-lg p-2 space-y-1">
          {hit.warnings.map((w) => (
            <li key={w} className="flex gap-1.5">
              <AlertTriangle size={13} className="shrink-0 mt-0.5" aria-hidden />
              {w}
            </li>
          ))}
        </ul>
      )}

      <div className="mt-auto flex items-center justify-between pt-1">
        <div className="flex items-center gap-1 text-slate-500" role="group" aria-label="Was this result helpful?">
          <button
            onClick={() => sendFeedback(true)}
            aria-pressed={feedback === true}
            aria-label="Helpful result"
            className={`p-1.5 rounded-lg hover:bg-emerald-50 ${feedback === true ? "text-emerald-600" : ""}`}
          >
            <ThumbsUp size={15} />
          </button>
          <button
            onClick={() => sendFeedback(false)}
            aria-pressed={feedback === false}
            aria-label="Not helpful"
            className={`p-1.5 rounded-lg hover:bg-rose-50 ${feedback === false ? "text-rose-600" : ""}`}
          >
            <ThumbsDown size={15} />
          </button>
          <button onClick={() => setShowWhy((s) => !s)} className="text-xs underline ml-2" aria-expanded={showWhy}>
            score details
          </button>
        </div>
        <Link href={`/recipes/${r.id}`} className="text-teal-700 font-semibold text-sm hover:text-teal-900">
          View recipe →
        </Link>
      </div>
      {showWhy && (
        <dl className="text-xs text-slate-600 grid grid-cols-2 gap-x-3 gap-y-0.5 bg-slate-50 rounded-lg p-2">
          {Object.entries(hit.score_breakdown).map(([k, v]) => (
            <div key={k} className="contents">
              <dt>{k.replace("_", " ")}</dt>
              <dd className="text-right font-mono">{v.toFixed(3)}</dd>
            </div>
          ))}
          <dt className="font-semibold">total</dt>
          <dd className="text-right font-mono font-semibold">{hit.score.toFixed(3)}</dd>
        </dl>
      )}
      </div>
    </article>
  );
}
