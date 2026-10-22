"use client";

import { useState } from "react";
import Link from "next/link";
import { AlertTriangle, ClipboardPaste, Loader2, Wand2 } from "lucide-react";
import { api, ApiError, Nutrition, Recipe } from "@/lib/nlp";

export type RecipeDraft = {
  title: string;
  ingredients: string;
  instructions: string;
  cuisine: string;
  meal_type: string;
  total_time_min: string;
  servings: string;
  diet_tags: string;
  nutrition: Record<keyof Nutrition, string>;
};

const EMPTY_NUTRITION = { calories: "", protein_g: "", carbs_g: "", fat_g: "", fiber_g: "" };

export function draftFromRecipe(r?: Partial<Recipe> | null): RecipeDraft {
  return {
    title: r?.title || "",
    ingredients: (r?.ingredients || []).join("\n"),
    instructions: r?.instructions || "",
    cuisine: r?.cuisine || "",
    meal_type: r?.meal_type || "",
    total_time_min: r?.total_time_min ? String(r.total_time_min) : "",
    servings: r?.servings ? String(r.servings) : "",
    diet_tags: (r?.diet_tags || []).join(", "),
    nutrition: {
      calories: r?.nutrition?.calories != null ? String(r.nutrition.calories) : "",
      protein_g: r?.nutrition?.protein_g != null ? String(r.nutrition.protein_g) : "",
      carbs_g: r?.nutrition?.carbs_g != null ? String(r.nutrition.carbs_g) : "",
      fat_g: r?.nutrition?.fat_g != null ? String(r.nutrition.fat_g) : "",
      fiber_g: r?.nutrition?.fiber_g != null ? String(r.nutrition.fiber_g) : "",
    },
  };
}

type ParseResult = {
  title: string | null;
  ingredients: string[];
  instructions: string[];
  total_time_min: number | null;
  time_source: string | null;
  servings: number | null;
  cuisine_guess: string | null;
  meal_type_guess: string[];
  diet: Record<string, boolean>;
  allergens: string[];
  confidence: Record<string, number>;
  warnings: string[];
  parsed_ingredients: { raw: string; name: string | null; quantity?: number | null; unit?: string | null }[];
};

type Dup = { recipe_id: number; title: string; same_title: boolean; ingredient_overlap: number };

const num = (s: string) => (s.trim() === "" ? null : Number(s));

export default function RecipeForm({
  initial,
  recipeId,
  onSaved,
}: {
  initial: RecipeDraft;
  recipeId?: number;
  onSaved: (r: Recipe) => void;
}) {
  const [d, setD] = useState<RecipeDraft>(initial);
  const [paste, setPaste] = useState("");
  const [parsing, setParsing] = useState(false);
  const [parsed, setParsed] = useState<ParseResult | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dups, setDups] = useState<Dup[] | null>(null);
  const [confirmDup, setConfirmDup] = useState(false);

  const set = (k: keyof RecipeDraft, v: string) => setD((x) => ({ ...x, [k]: v }));

  const runParse = async () => {
    setParsing(true);
    setError(null);
    try {
      setParsed(await api<ParseResult>("/nlp/parse-recipe", { method: "POST", json: { text: paste } }));
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not parse the text.");
    } finally {
      setParsing(false);
    }
  };

  // Extracted values only fill EMPTY fields; non-empty fields need an explicit "replace" click.
  const extracted: { key: keyof RecipeDraft; label: string; value: string }[] = parsed
    ? ([
        { key: "title", label: "Title", value: parsed.title || "" },
        { key: "ingredients", label: "Ingredients", value: parsed.ingredients.join("\n") },
        { key: "instructions", label: "Instructions", value: parsed.instructions.join("\n") },
        { key: "total_time_min", label: `Total time${parsed.time_source ? ` (${parsed.time_source})` : ""}`, value: parsed.total_time_min ? String(parsed.total_time_min) : "" },
        { key: "servings", label: "Servings", value: parsed.servings ? String(parsed.servings) : "" },
        { key: "cuisine", label: "Cuisine (inferred)", value: parsed.cuisine_guess || "" },
        { key: "meal_type", label: "Meal type (inferred)", value: parsed.meal_type_guess.filter((m) => m !== "component").join(", ") },
      ] as { key: keyof RecipeDraft; label: string; value: string }[]).filter((x) => x.value)
    : [];

  const fillEmpty = () => {
    setD((x) => {
      const next = { ...x };
      for (const e of extracted) {
        if (!String(next[e.key] || "").trim()) (next as Record<string, unknown>)[e.key] = e.value;
      }
      return next;
    });
  };

  const body = () => {
    const nutrition = Object.fromEntries(Object.entries(d.nutrition).map(([k, v]) => [k, num(v)]));
    const hasNutrition = Object.values(nutrition).some((v) => v != null);
    return {
      title: d.title.trim(),
      ingredients: d.ingredients.split("\n").map((s) => s.trim()).filter(Boolean),
      instructions: d.instructions.trim(),
      cuisine: d.cuisine.trim() || null,
      meal_type: d.meal_type.trim() || null,
      total_time_min: num(d.total_time_min),
      servings: num(d.servings),
      diet_tags: d.diet_tags.split(",").map((s) => s.trim()).filter(Boolean),
      nutrition: hasNutrition ? nutrition : null,
    };
  };

  const save = async () => {
    setError(null);
    const b = body();
    if (!b.title || !b.ingredients.length) {
      setError("A title and at least one ingredient line are required.");
      return;
    }
    if (!confirmDup) {
      try {
        const res = await api<{ duplicates: Dup[] }>("/recipes/check-duplicates", {
          method: "POST",
          json: { title: b.title, ingredients: b.ingredients, exclude_id: recipeId ?? null },
        });
        if (res.duplicates.length) {
          setDups(res.duplicates);
          setConfirmDup(true);
          return;
        }
      } catch {
        /* duplicate check is advisory */
      }
    }
    setSaving(true);
    try {
      const r = recipeId
        ? await api<Recipe>(`/recipes/${recipeId}`, { method: "PUT", json: b })
        : await api<Recipe>("/recipes", { method: "POST", json: b });
      onSaved(r);
    } catch (e) {
      setError(e instanceof ApiError ? (e.status === 401 ? "Please log in to save recipes." : e.message) : "Save failed.");
    } finally {
      setSaving(false);
    }
  };

  const field = "w-full rounded-xl border border-slate-300 bg-white px-3 py-2 focus:outline-none focus:ring-2 focus:ring-emerald-400";

  return (
    <div className="grid lg:grid-cols-5 gap-6">
      <section className="lg:col-span-3 space-y-4 bg-white/90 rounded-lg border border-slate-200 p-5">
        <label className="block">
          <span className="text-sm font-medium text-slate-700">Title *</span>
          <input className={field} value={d.title} onChange={(e) => set("title", e.target.value)} maxLength={200} />
        </label>
        <label className="block">
          <span className="text-sm font-medium text-slate-700">Ingredients * (one per line, with quantities)</span>
          <textarea className={field + " font-mono text-sm"} rows={8} value={d.ingredients} onChange={(e) => set("ingredients", e.target.value)} />
        </label>
        <label className="block">
          <span className="text-sm font-medium text-slate-700">Instructions (one step per line)</span>
          <textarea className={field} rows={7} value={d.instructions} onChange={(e) => set("instructions", e.target.value)} />
        </label>
        <div className="grid sm:grid-cols-2 gap-3">
          <label className="block">
            <span className="text-sm text-slate-700">Cuisine</span>
            <input className={field} value={d.cuisine} onChange={(e) => set("cuisine", e.target.value)} placeholder="e.g. south indian" />
          </label>
          <label className="block">
            <span className="text-sm text-slate-700">Meal type</span>
            <input className={field} value={d.meal_type} onChange={(e) => set("meal_type", e.target.value)} placeholder="e.g. dinner" />
          </label>
          <label className="block">
            <span className="text-sm text-slate-700">Total time (minutes)</span>
            <input className={field} type="number" min={1} value={d.total_time_min} onChange={(e) => set("total_time_min", e.target.value)} />
          </label>
          <label className="block">
            <span className="text-sm text-slate-700">Servings</span>
            <input className={field} type="number" min={1} step="0.5" value={d.servings} onChange={(e) => set("servings", e.target.value)} />
          </label>
        </div>
        <label className="block">
          <span className="text-sm text-slate-700">Your diet tags (comma separated)</span>
          <input className={field} value={d.diet_tags} onChange={(e) => set("diet_tags", e.target.value)} placeholder="e.g. vegetarian, gluten-free" />
        </label>
        <fieldset className="border border-slate-200 rounded-xl p-3">
          <legend className="text-sm text-slate-700 px-1">Nutrition per serving (optional — only if you know it)</legend>
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-2">
            {(Object.keys(EMPTY_NUTRITION) as (keyof Nutrition)[]).map((k) => (
              <label key={k} className="block text-xs text-slate-600">
                {k.replace("_g", " (g)").replace("calories", "kcal")}
                <input
                  className={field}
                  type="number"
                  min={0}
                  value={d.nutrition[k]}
                  onChange={(e) => setD((x) => ({ ...x, nutrition: { ...x.nutrition, [k]: e.target.value } }))}
                />
              </label>
            ))}
          </div>
          <p className="text-xs text-slate-500 mt-2">Leave blank if unknown. NutriChef never guesses nutrition values.</p>
        </fieldset>

        {dups && dups.length > 0 && (
          <div role="alert" className="p-3 rounded-xl bg-amber-50 border border-amber-200 text-sm text-amber-900 space-y-1">
            <p className="font-medium flex items-center gap-1">
              <AlertTriangle size={15} /> This looks similar to existing recipes:
            </p>
            <ul className="list-disc ml-5">
              {dups.map((x) => (
                <li key={x.recipe_id}>
                  <Link href={`/recipes/${x.recipe_id}`} className="underline" target="_blank">
                    {x.title}
                  </Link>{" "}
                  ({Math.round(x.ingredient_overlap * 100)}% ingredient overlap{x.same_title ? ", same title" : ""})
                </li>
              ))}
            </ul>
            <p>Click save again to keep yours anyway.</p>
          </div>
        )}
        {error && (
          <p role="alert" className="text-sm text-rose-700">
            {error}
          </p>
        )}
        <button
          onClick={save}
          disabled={saving}
          className="px-5 py-2.5 rounded-xl bg-emerald-600 text-white font-semibold hover:bg-emerald-700 disabled:opacity-50 inline-flex items-center gap-2"
        >
          {saving && <Loader2 size={16} className="animate-spin" />}
          {recipeId ? "Save changes" : "Save recipe"}
        </button>
      </section>

      <aside className="lg:col-span-2 space-y-3 bg-emerald-50/60 rounded-lg border border-emerald-100 p-5 h-fit">
        <h2 className="font-semibold text-emerald-900 flex items-center gap-2">
          <ClipboardPaste size={18} /> Paste a recipe (optional)
        </h2>
        <p className="text-sm text-slate-600">
          Paste any recipe text. NutriChef extracts the title, ingredients with quantities, steps, time and servings
          locally. You review everything before it is saved.
        </p>
        <textarea className={field + " text-sm"} rows={8} value={paste} onChange={(e) => setPaste(e.target.value)} placeholder="Paste recipe text here…" />
        <button
          onClick={runParse}
          disabled={parsing || paste.trim().length < 10}
          className="px-4 py-2 rounded-xl bg-teal-600 text-white text-sm font-medium hover:bg-teal-700 disabled:opacity-50 inline-flex items-center gap-2"
        >
          {parsing ? <Loader2 size={15} className="animate-spin" /> : <Wand2 size={15} />} Extract fields
        </button>
        {parsed && (
          <div className="space-y-3 text-sm">
            {parsed.warnings.map((w) => (
              <p key={w} className="text-amber-800 flex gap-1">
                <AlertTriangle size={14} className="mt-0.5 shrink-0" /> {w}
              </p>
            ))}
            <ul className="space-y-2">
              {extracted.map((e) => {
                const current = String(d[e.key] || "").trim();
                return (
                  <li key={e.key} className="bg-white rounded-lg p-2 border border-slate-200">
                    <div className="flex justify-between gap-2">
                      <span className="font-medium text-slate-700">{e.label}</span>
                      {current && current !== e.value && (
                        <button className="text-xs text-teal-700 underline" onClick={() => set(e.key, e.value)}>
                          replace yours
                        </button>
                      )}
                    </div>
                    <pre className="whitespace-pre-wrap text-xs text-slate-600 max-h-28 overflow-auto font-sans">{e.value}</pre>
                  </li>
                );
              })}
            </ul>
            {parsed.parsed_ingredients.length > 0 && (
              <div>
                <p className="font-medium text-slate-700 mb-1">Recognised ingredients</p>
                <div className="flex flex-wrap gap-1">
                  {parsed.parsed_ingredients.map((p, i) => (
                    <span key={i} className={`px-2 py-0.5 rounded-full text-xs border ${p.name ? "bg-white border-emerald-200 text-emerald-800" : "bg-rose-50 border-rose-200 text-rose-700"}`}>
                      {p.name || `? ${p.raw}`}
                      {p.quantity != null ? ` · ${p.quantity}${p.unit ? " " + p.unit : ""}` : ""}
                    </span>
                  ))}
                </div>
                <p className="text-xs text-slate-500 mt-1">
                  Diet check from ingredients: {parsed.diet.vegan ? "vegan" : parsed.diet.vegetarian ? "vegetarian" : parsed.diet.eggetarian ? "eggetarian" : "contains meat/fish"}
                  {parsed.allergens.length ? ` · allergens: ${parsed.allergens.join(", ")}` : ""} (not a guarantee)
                </p>
              </div>
            )}
            <button onClick={fillEmpty} className="px-4 py-2 rounded-xl border border-teal-400 text-teal-800 hover:bg-white">
              Fill empty fields with these
            </button>
          </div>
        )}
      </aside>
    </div>
  );
}
