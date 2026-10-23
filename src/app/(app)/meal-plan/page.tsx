"use client";

import { useState } from "react";
import Link from "next/link";
import { CalendarDays, Loader2, ShoppingBasket } from "lucide-react";
import { api, ApiError } from "@/lib/nlp";

type Meal = { meal: string; recipe_id: number | null; title: string | null; why: string; warnings: string[] };
type Plan = {
  days: number;
  meals_per_day: string[];
  plan: { day: number; meals: Meal[] }[];
  shopping_list: Record<string, { name: string; recipes: number }[]>;
  constraints: { diets: string[]; excluded: string[]; max_time_min: number | null; cuisines: string[]; qualities: string[] };
  note: string;
};

const EXAMPLES = [
  "Plan 5 vegetarian dinners under 40 minutes without mushrooms",
  "3-day plan with breakfast and dinner, high protein, no peanuts",
  "Weekly Indian dinner plan, vegan",
];

export default function MealPlanPage() {
  const [req, setReq] = useState(EXAMPLES[0]);
  const [plan, setPlan] = useState<Plan | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = async (text = req) => {
    setBusy(true);
    setError(null);
    try {
      setPlan(await api<Plan>("/nlp/meal-plan", { method: "POST", json: { request: text } }));
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not build a plan.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="meal-board max-w-6xl mx-auto px-1 sm:px-4 py-4 sm:py-8 space-y-6">
      <header className="kitchen-banner p-6 sm:p-10 space-y-2">
        <h1 className="display text-4xl sm:text-5xl">A week of good food.</h1>
        <p className="text-slate-600">Describe the plan you want. NutriChef picks varied recipes that satisfy every constraint and builds a shopping list.</p>
      </header>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          run();
        }}
        className="flex flex-col sm:flex-row gap-2"
      >
        <label htmlFor="plan-req" className="sr-only">Plan request</label>
        <input id="plan-req" value={req} onChange={(e) => setReq(e.target.value)} maxLength={500} className="flex-1 rounded-xl border border-slate-300 px-3 py-2.5 bg-white focus:outline-none focus:ring-2 focus:ring-teal-400" />
        <button type="submit" disabled={busy || req.trim().length < 3} className="px-5 py-2.5 rounded-xl bg-teal-600 text-white font-semibold disabled:opacity-50 inline-flex items-center gap-2 justify-center">
          {busy ? <Loader2 size={16} className="animate-spin" /> : <CalendarDays size={16} />} Plan it
        </button>
      </form>
      <div className="flex flex-wrap gap-2">
        {EXAMPLES.map((ex) => (
          <button key={ex} onClick={() => { setReq(ex); run(ex); }} className="text-xs px-2.5 py-1 rounded-full border border-slate-200 bg-white hover:bg-teal-50">
            {ex}
          </button>
        ))}
      </div>
      {error && <p role="alert" className="text-rose-700">{error}</p>}
      {plan && (
        <div className="grid lg:grid-cols-3 gap-6">
          <section className="lg:col-span-2 space-y-3">
            <p className="text-sm text-slate-600">
              {plan.days} day{plan.days > 1 ? "s" : ""} · {plan.meals_per_day.join(" + ")}
              {plan.constraints.diets.length ? ` · ${plan.constraints.diets.join(", ")}` : ""}
              {plan.constraints.excluded.length ? ` · without ${plan.constraints.excluded.join(", ")}` : ""}
              {plan.constraints.max_time_min ? ` · ≤ ${plan.constraints.max_time_min} min` : ""}
            </p>
            {plan.plan.map((d) => (
              <div key={d.day} className="day-card p-4 kitchen-card bg-white border border-slate-200">
                <h2 className="font-semibold text-slate-800 mb-2">Day {d.day}</h2>
                <ul className="space-y-2">
                  {d.meals.map((m, i) => (
                    <li key={i} className="meal-slot text-sm">
                      <span className="inline-block w-20 text-slate-500 capitalize">{m.meal}</span>
                      {m.recipe_id ? (
                        <Link href={`/recipes/${m.recipe_id}`} className="font-medium text-teal-800 hover:underline">
                          {m.title}
                        </Link>
                      ) : (
                        <span className="text-rose-700">{m.why}</span>
                      )}
                      {m.recipe_id && m.why && <span className="block ml-20 text-xs text-slate-500">{m.why}</span>}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </section>
          <aside className="p-4 rounded-2xl bg-emerald-50/70 border border-emerald-100 h-fit space-y-3">
            <h2 className="font-semibold text-emerald-900 flex items-center gap-2">
              <ShoppingBasket size={18} /> Shopping list
            </h2>
            {Object.entries(plan.shopping_list).map(([cat, items]) => (
              <div key={cat}>
                <h3 className="text-xs uppercase tracking-wide text-slate-500">{cat.replace("_", " ")}</h3>
                <ul className="text-sm">
                  {items.map((it) => (
                    <li key={it.name}>
                      {it.name}
                      {it.recipes > 1 ? <span className="text-slate-500"> ×{it.recipes} recipes</span> : null}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
            <p className="text-xs text-slate-500">{plan.note}</p>
          </aside>
        </div>
      )}
    </div>
  );
}
