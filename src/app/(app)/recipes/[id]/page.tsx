"use client";

import { use, useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { AlertTriangle, Copy, GitCompare, Heart, Loader2, Pencil, Star, Trash2 } from "lucide-react";
import { api, ApiError, Recipe, RecipeCardData } from "@/lib/nlp";
import { DerivedBadges } from "@/components/nlp/RecipeResultCard";
import ModifyPanel from "@/components/recipes/ModifyPanel";
import FoodArt from "@/components/bento/FoodArt";
import { useMe } from "@/lib/useMe";

type Similar = { recipe: RecipeCardData; score: number; ingredient_overlap: number; shared: string[]; reason: string };
type Compare = {
  first: { id: number; title: string };
  second: { id: number; title: string };
  shared_ingredients: string[];
  only_in_first: string[];
  only_in_second: string[];
  ingredient_overlap: number;
  semantic_similarity: number | null;
  rows: { field: string; first: unknown; second: unknown }[];
};

const NUTRIENT_LABEL: Record<string, string> = { calories: "Calories", protein_g: "Protein (g)", carbs_g: "Carbs (g)", fat_g: "Fat (g)", fiber_g: "Fibre (g)" };

function steps(text: string) {
  const parts = text.split(/\n+/).map((s) => s.trim()).filter(Boolean);
  if (parts.length > 1) return parts;
  return text.split(/(?<=[.!?])\s+(?=[A-Z])/).map((s) => s.trim()).filter(Boolean);
}

export default function RecipeDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const rid = Number(id);
  const router = useRouter();
  const me = useMe();
  const [recipe, setRecipe] = useState<Recipe | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [similar, setSimilar] = useState<Similar[] | null>(null);
  const [fav, setFav] = useState(false);
  const [rating, setRating] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const [cmp, setCmp] = useState<Compare | null>(null);
  const [confirmDelete, setConfirmDelete] = useState(false);

  const load = useCallback(() => {
    setError(null);
    api<Recipe>(`/recipes/${rid}`)
      .then(setRecipe)
      .catch((e) => setError(e instanceof ApiError ? e.message : "Could not load the recipe."));
    api<Similar[]>(`/recipes/${rid}/similar?k=6`).then(setSimilar).catch(() => setSimilar([]));
  }, [rid]);

  useEffect(() => {
    load();
    setCmp(null);
  }, [load]);

  useEffect(() => {
    if (!me) return;
    api("/interactions", { method: "POST", json: { recipe_id: rid, kind: "view" } }).catch(() => {});
    api<{ favorite: boolean; rating: number | null }>(`/interactions/${rid}`)
      .then((s) => {
        setFav(s.favorite);
        setRating(s.rating);
      })
      .catch(() => {});
  }, [me, rid]);

  const toggleFav = async () => {
    if (!recipe) return;
    setBusy(true);
    try {
      if (!fav) {
        const res = await fetch("/api/favorites", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            recipe: {
              recipe_name: recipe.title,
              recipe_ref: String(recipe.id),
              instructions: recipe.instructions,
              calories: recipe.nutrition?.calories ?? null,
              protein: recipe.nutrition?.protein_g ?? null,
              fat: recipe.nutrition?.fat_g ?? null,
              carbs: recipe.nutrition?.carbs_g ?? null,
            },
          }),
        });
        if (!res.ok) throw new Error();
        await api("/interactions", { method: "POST", json: { recipe_id: rid, kind: "favorite" } });
        setFav(true);
      } else {
        const list = await (await fetch("/api/favorites")).json();
        const row = (list.recipes || []).find((x: { recipe_ref?: string }) => x.recipe_ref === String(rid));
        if (row) await fetch("/api/favorites", { method: "DELETE", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ id: row.id }) });
        await api("/interactions", { method: "POST", json: { recipe_id: rid, kind: "unfavorite" } });
        setFav(false);
      }
    } catch {
      setMsg("Couldn't update favourites — are you logged in?");
    } finally {
      setBusy(false);
    }
  };

  const rate = async (v: number) => {
    setRating(v);
    try {
      await api("/interactions", { method: "POST", json: { recipe_id: rid, kind: "rating", value: v } });
    } catch {
      setMsg("Couldn't save rating.");
    }
  };

  const saveCopy = async () => {
    if (!recipe) return;
    setBusy(true);
    try {
      const copy = await api<Recipe>("/recipes", {
        method: "POST",
        json: { title: `${recipe.title} (my copy)`, ingredients: recipe.ingredients, instructions: recipe.instructions },
      });
      router.push(`/recipes/${copy.id}/edit`);
    } catch (e) {
      setMsg(e instanceof ApiError && e.status === 401 ? "Log in to save a copy." : "Couldn't save a copy.");
    } finally {
      setBusy(false);
    }
  };

  const del = async () => {
    setBusy(true);
    try {
      await api(`/recipes/${rid}`, { method: "DELETE" });
      router.push("/recipes");
    } catch (e) {
      setMsg(e instanceof ApiError ? e.message : "Delete failed.");
      setBusy(false);
    }
  };

  const compareWith = async (other: number) => {
    try {
      setCmp(await api<Compare>(`/recipes/${rid}/compare/${other}`));
    } catch {
      setMsg("Comparison failed.");
    }
  };

  if (error)
    return (
      <div className="p-6">
        <p role="alert" className="text-rose-700">{error}</p>
        <Link href="/recipes" className="underline text-teal-700">Back to recipes</Link>
      </div>
    );
  if (!recipe)
    return (
      <div className="p-6 flex items-center gap-2 text-slate-500">
        <Loader2 className="animate-spin" size={18} /> Loading recipe…
      </div>
    );

  const own = me && recipe.owner_id === me.id && recipe.source !== "epicurious-13k";
  const d = recipe.derived;
  const sourceLabel =
    recipe.source === "epicurious-13k"
      ? "From the Epicurious recipe dataset (read-only)"
      : recipe.source === "generated"
      ? "Generated with a local AI model and saved by you — a suggestion, check it with your own cooking judgement"
      : "Your recipe";

  return (
    <div className="max-w-6xl mx-auto px-1 sm:px-4 py-4 sm:py-8 space-y-6">
      <header className="grid gap-4 lg:grid-cols-12">
        <div className="lg:col-span-8 kitchen-banner p-6 sm:p-9 space-y-3">
        <p className="pill bg-cream/80 text-ink/70 text-xs py-1">{sourceLabel}</p>
        <h1 className="display text-4xl sm:text-6xl">{recipe.title}</h1>
        {d && <DerivedBadges d={d} />}
        <div className="flex flex-wrap gap-2 pt-1">
          {me && (
            <button onClick={toggleFav} disabled={busy} aria-pressed={fav} className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-rose-200 text-rose-700 hover:bg-rose-50">
              <Heart size={16} fill={fav ? "currentColor" : "none"} /> {fav ? "Favourited" : "Favourite"}
            </button>
          )}
          {me && recipe.source === "epicurious-13k" && (
            <button onClick={saveCopy} disabled={busy} className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-slate-300 hover:bg-slate-50">
              <Copy size={16} /> Save a copy to edit
            </button>
          )}
          {own && (
            <>
              <Link href={`/recipes/${rid}/edit`} className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-slate-300 hover:bg-slate-50">
                <Pencil size={16} /> Edit
              </Link>
              {confirmDelete ? (
                <span className="inline-flex items-center gap-2 text-sm">
                  Delete this recipe?
                  <button onClick={del} disabled={busy} className="px-3 py-1.5 rounded-xl bg-rose-600 text-white">Yes, delete</button>
                  <button onClick={() => setConfirmDelete(false)} className="px-3 py-1.5 rounded-xl border">Cancel</button>
                </span>
              ) : (
                <button onClick={() => setConfirmDelete(true)} className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-rose-200 text-rose-700 hover:bg-rose-50">
                  <Trash2 size={16} /> Delete
                </button>
              )}
            </>
          )}
          {me && (
            <div className="inline-flex items-center gap-0.5 ml-1" role="group" aria-label="Rate this recipe">
              {[1, 2, 3, 4, 5].map((v) => (
                <button key={v} onClick={() => rate(v)} aria-label={`Rate ${v} star${v > 1 ? "s" : ""}`} className="p-0.5 text-amber-500">
                  <Star size={18} fill={rating != null && v <= rating ? "currentColor" : "none"} />
                </button>
              ))}
            </div>
          )}
        </div>
        {msg && <p className="text-sm text-amber-800">{msg}</p>}
        </div>
        <FoodArt title={recipe.title} hints={recipe.ingredients} size="xl" className="lg:col-span-4 kitchen-card min-h-[220px]" />
      </header>

      <div className="grid lg:grid-cols-3 gap-6">
        <section className="lg:col-span-1 bg-white/90 rounded-lg border border-slate-200 p-5 space-y-3 h-fit">
          <h2 className="font-semibold text-slate-800">Ingredients ({recipe.ingredients.length})</h2>
          <ul className="space-y-2 text-sm">
            {recipe.ingredients.map((line, i) => {
              const parsed = recipe.parsed_ingredients?.filter((p) => p.raw === line) || [];
              return (
                <li key={i} className="leading-snug">
                  <span className="text-slate-800">{line}</span>
                  {parsed.length > 0 && (
                    <span className="block text-xs text-slate-500">
                      {parsed.map((p) => (p.name ? `${p.name}${p.optional ? " (optional)" : ""}${p.is_staple ? " · staple" : ""}` : "unrecognised")).join(", ")}
                    </span>
                  )}
                </li>
              );
            })}
          </ul>
          {d && (
            <div className="text-xs text-slate-600 border-t border-slate-100 pt-3 space-y-1">
              <p>
                <b>Allergens found in ingredient text:</b> {d.allergens.length ? d.allergens.join(", ") : "none recognised"}
              </p>
              {d.diet_uncertain.length > 0 && (
                <p className="text-amber-800 flex gap-1">
                  <AlertTriangle size={13} className="shrink-0 mt-0.5" /> Uncertain: {d.diet_uncertain.slice(0, 4).join("; ")}
                </p>
              )}
              <p className="text-slate-500">Diet and allergen information is derived from the ingredient text by NLP and is not a guarantee of allergy safety.</p>
            </div>
          )}
        </section>

        <section className="lg:col-span-2 space-y-6">
          <div className="bg-white/90 rounded-lg border border-slate-200 p-5">
            <h2 className="font-semibold text-slate-800 mb-3">Instructions</h2>
            {recipe.instructions ? (
              <ol className="list-decimal ml-5 space-y-2 text-slate-700">
                {steps(recipe.instructions).map((s, i) => (
                  <li key={i}>{s}</li>
                ))}
              </ol>
            ) : (
              <p className="text-slate-500">No instructions provided.</p>
            )}
            <dl className="mt-4 grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm">
              <div>
                <dt className="text-slate-500">Time</dt>
                <dd>
                  {recipe.total_time_min ? `${recipe.total_time_min} min (stated)` : d?.estimated_time_min != null ? `~${d.estimated_time_min} min (estimated)` : "unknown"}
                </dd>
              </div>
              <div>
                <dt className="text-slate-500">Servings</dt>
                <dd>{recipe.servings ?? "not stated"}</dd>
              </div>
              <div>
                <dt className="text-slate-500">Cuisine</dt>
                <dd>{recipe.cuisine || (d?.cuisine_guess ? `${d.cuisine_guess} (inferred)` : "unlabelled")}</dd>
              </div>
              <div>
                <dt className="text-slate-500">Difficulty</dt>
                <dd>{d?.difficulty ? `${d.difficulty} (estimated)` : "—"}</dd>
              </div>
            </dl>
          </div>

          <div className="bg-white/90 rounded-lg border border-slate-200 p-5">
            <h2 className="font-semibold text-slate-800 mb-2">Nutrition</h2>
            {recipe.nutrition && Object.values(recipe.nutrition).some((v) => v != null) ? (
              <>
                <dl className="grid grid-cols-2 sm:grid-cols-5 gap-3 text-sm">
                  {Object.entries(NUTRIENT_LABEL).map(([k, label]) => (
                    <div key={k}>
                      <dt className="text-slate-500">{label}</dt>
                      <dd>{(recipe.nutrition as Record<string, number | null>)[k] ?? "unknown"}</dd>
                    </div>
                  ))}
                </dl>
                <p className="text-xs text-slate-500 mt-2">Per serving · source: {recipe.nutrition_source || "unknown"}</p>
              </>
            ) : (
              <p className="text-sm text-slate-600">
                No nutrition data for this recipe. NutriChef does not estimate or invent calories or macros — unknown values stay unknown.
              </p>
            )}
          </div>

          <ModifyPanel recipe={recipe} canOverwrite={!!own} loggedIn={!!me} onSaved={(r) => router.push(`/recipes/${r.id}`)} onReplaced={load} />
        </section>
      </div>

      <section className="space-y-3">
        <h2 className="text-xl font-semibold text-slate-800">Similar recipes</h2>
        {similar === null ? (
          <p className="text-slate-500 text-sm">Finding similar recipes…</p>
        ) : similar.length === 0 ? (
          <p className="text-slate-500 text-sm">No similar recipes found.</p>
        ) : (
          <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {similar.map((s) => (
              <li key={s.recipe.id} className="p-4 kitchen-card bg-white border border-slate-200 space-y-1.5">
                <Link href={`/recipes/${s.recipe.id}`} className="font-medium text-teal-800 hover:underline">
                  {s.recipe.title}
                </Link>
                <p className="text-xs text-slate-600">{s.reason}</p>
                <button onClick={() => compareWith(s.recipe.id)} className="text-xs inline-flex items-center gap-1 text-teal-700 underline">
                  <GitCompare size={13} /> Compare
                </button>
              </li>
            ))}
          </ul>
        )}
        {cmp && (
          <div className="bg-white rounded-lg border border-slate-200 p-5 overflow-x-auto">
            <h3 className="font-semibold mb-2">
              {cmp.first.title} vs {cmp.second.title}
            </h3>
            <table className="text-sm w-full">
              <thead>
                <tr className="text-left text-slate-500">
                  <th className="py-1 pr-3"></th>
                  <th className="py-1 pr-3">This recipe</th>
                  <th className="py-1">Other</th>
                </tr>
              </thead>
              <tbody>
                {cmp.rows.map((r) => (
                  <tr key={r.field} className="border-t border-slate-100">
                    <td className="py-1 pr-3 text-slate-500">{r.field}</td>
                    <td className="py-1 pr-3">{String(r.first ?? "—")}</td>
                    <td className="py-1">{String(r.second ?? "—")}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="text-sm mt-3">
              <b>Shared:</b> {cmp.shared_ingredients.join(", ") || "none"}
            </p>
            <p className="text-sm">
              <b>Only here:</b> {cmp.only_in_first.join(", ") || "none"} · <b>Only in other:</b> {cmp.only_in_second.join(", ") || "none"}
            </p>
            <p className="text-xs text-slate-500 mt-1">
              Ingredient overlap {Math.round(cmp.ingredient_overlap * 100)}%{cmp.semantic_similarity != null ? ` · text similarity ${cmp.semantic_similarity}` : ""}
            </p>
          </div>
        )}
      </section>
    </div>
  );
}
