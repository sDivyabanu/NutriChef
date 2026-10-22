"use client";

import { useEffect, useState } from "react";
import { Camera, Loader2, Plus, Refrigerator, Search, X } from "lucide-react";
import { api, ApiError, IngredientConstraint, SearchResponse, Understanding } from "@/lib/nlp";
import RecipeResultCard from "@/components/nlp/RecipeResultCard";

type Chip = { name: string; display: string; quantity_text?: string | null };
type VisionStatus = { available: boolean; model: string | null; classes: string[]; note: string };
type ExtractOut = { corrections: [string, string][]; ingredients: IngredientConstraint[] };

const DIETS = ["", "vegetarian", "eggetarian", "vegan", "gluten-free", "dairy-free", "nut-free"];

export default function IngredientsPage() {
  const [chips, setChips] = useState<Chip[]>([]);
  const [input, setInput] = useState("");
  const [note, setNote] = useState<string | null>(null);
  const [diet, setDiet] = useState("");
  const [maxTime, setMaxTime] = useState("");
  const [data, setData] = useState<SearchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [vision, setVision] = useState<VisionStatus | null>(null);
  const [detecting, setDetecting] = useState(false);

  useEffect(() => {
    api<VisionStatus>("/vision/status").then(setVision).catch(() => setVision(null));
  }, []);

  const addChips = (items: Chip[]) =>
    setChips((cur) => {
      const names = new Set(cur.map((c) => c.name));
      return [...cur, ...items.filter((i) => !names.has(i.name) && names.add(i.name))];
    });

  const parseAndAdd = async (text: string) => {
    if (!text.trim()) return;
    setNote(null);
    try {
      const r = await api<ExtractOut>("/nlp/extract-ingredients", { method: "POST", json: { text } });
      const found = r.ingredients.filter((i) => i.role !== "excluded" && i.role !== "unavailable");
      if (!found.length) {
        setNote(`Couldn't recognise an ingredient in “${text}”.`);
        return;
      }
      addChips(found.map((i) => ({ name: i.name, display: i.display, quantity_text: i.quantity_text })));
      const notes = [];
      if (r.corrections.length) notes.push("Corrected: " + r.corrections.map(([a, b]) => `${a} → ${b}`).join(", "));
      const renamed = found.filter((i) => i.display.toLowerCase() !== i.name);
      if (renamed.length) notes.push("Normalised: " + renamed.map((i) => `${i.display} → ${i.name}`).join(", "));
      setNote(notes.join(" · ") || null);
      setInput("");
    } catch (e) {
      setNote(e instanceof ApiError ? e.message : "Backend unavailable.");
    }
  };

  const fromPantry = async () => {
    try {
      const res = await fetch("/api/pantry");
      if (!res.ok) throw new Error();
      const d = await res.json();
      const names = (d.pantry || []).map((p: { name: string }) => p.name).filter(Boolean);
      if (!names.length) return setNote("Your pantry is empty — add items on the Pantry page.");
      await parseAndAdd(names.join(", "));
    } catch {
      setNote("Couldn't load your pantry (are you logged in?).");
    }
  };

  const detect = async (file: File) => {
    setDetecting(true);
    setNote(null);
    try {
      const form = new FormData();
      form.append("file", file);
      const res = await fetch("/backend/vision/detect", { method: "POST", body: form });
      const d = await res.json();
      if (!res.ok) throw new Error(d.detail || "Detection failed");
      if (!d.ingredients.length) setNote("No supported foods detected in the photo. You can still type ingredients.");
      else {
        addChips(d.ingredients.map((i: { name: string; label: string; confidence: number }) => ({ name: i.name, display: `${i.label} (${Math.round(i.confidence * 100)}%)` })));
        setNote("Detected from photo — please check them; the model only knows a few foods.");
      }
    } catch (e) {
      setNote((e as Error).message);
    } finally {
      setDetecting(false);
    }
  };

  const search = async () => {
    if (!chips.length) return;
    setLoading(true);
    setError(null);
    const u: Partial<Understanding> = {
      original: "I have " + chips.map((c) => c.display).join(", "),
      intent: "find_by_ingredients",
      ingredients: chips.map((c) => ({ name: c.name, display: c.display, role: "available" as const })),
      diets: diet ? [diet] : [],
      max_time_min: maxTime ? Number(maxTime) : null,
      excluded_groups: [],
      cuisines: [],
      meal_types: [],
      nutrition: [],
      qualities: [],
      corrections: [],
      notes: [],
      conflicts: [],
      free_text: "",
    };
    try {
      setData(await api<SearchResponse>("/nlp/search", { method: "POST", json: { understanding: u, k: 12 } }));
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Search failed.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-6xl mx-auto px-1 sm:px-4 py-4 sm:py-8 space-y-6">
      <header className="kitchen-banner p-6 sm:p-10 space-y-2">
        <h1 className="display text-4xl sm:text-5xl">Cook with what I have</h1>
        <p className="text-slate-600">Add what&apos;s in your kitchen — in any form (“2 tomatos, capsicum, curd”). Recipes are ranked by how much of each one you can already make.</p>
      </header>

      <section className="bg-white/90 rounded-lg border border-slate-200 p-5 space-y-4">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            parseAndAdd(input);
          }}
          className="flex gap-2"
        >
          <label htmlFor="ing-input" className="sr-only">Add ingredients</label>
          <input id="ing-input" value={input} onChange={(e) => setInput(e.target.value)} placeholder="e.g. 2 tomatoes, half an onion, paneer" className="flex-1 rounded-xl border border-slate-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-emerald-400" maxLength={500} />
          <button type="submit" className="px-4 py-2 rounded-xl bg-emerald-600 text-white inline-flex items-center gap-1">
            <Plus size={16} /> Add
          </button>
        </form>
        <div className="flex flex-wrap gap-2 text-sm">
          <button onClick={fromPantry} className="inline-flex items-center gap-1 px-3 py-1.5 rounded-xl border border-slate-300 hover:bg-slate-50">
            <Refrigerator size={15} /> Add from my pantry
          </button>
          {vision?.available && (
            <label className="inline-flex items-center gap-1 px-3 py-1.5 rounded-xl border border-slate-300 hover:bg-slate-50 cursor-pointer">
              {detecting ? <Loader2 size={15} className="animate-spin" /> : <Camera size={15} />} Detect from a photo
              <input type="file" accept="image/*" className="sr-only" onChange={(e) => e.target.files?.[0] && detect(e.target.files[0])} />
            </label>
          )}
        </div>
        {vision?.available && <p className="text-xs text-slate-500">{vision.note}</p>}
        {note && <p className="text-sm text-slate-600">{note}</p>}
        {chips.length > 0 && (
          <ul className="flex flex-wrap gap-2" aria-label="Your ingredients">
            {chips.map((c) => (
              <li key={c.name} className="inline-flex items-center gap-1 px-3 py-1 rounded-full bg-emerald-50 border border-emerald-200 text-emerald-800 text-sm">
                {c.name}
                {c.quantity_text ? <span className="text-emerald-600 text-xs">· {c.quantity_text}</span> : null}
                <button onClick={() => setChips(chips.filter((x) => x.name !== c.name))} aria-label={`Remove ${c.name}`} className="rounded-full hover:bg-emerald-100 p-0.5">
                  <X size={12} />
                </button>
              </li>
            ))}
          </ul>
        )}
        <div className="flex flex-wrap gap-3 items-end">
          <label className="text-sm">
            <span className="block text-slate-600">Diet</span>
            <select value={diet} onChange={(e) => setDiet(e.target.value)} className="rounded-xl border border-slate-300 px-3 py-2 bg-white">
              {DIETS.map((d) => (
                <option key={d} value={d}>{d || "Any"}</option>
              ))}
            </select>
          </label>
          <label className="text-sm">
            <span className="block text-slate-600">Max minutes</span>
            <input type="number" min={5} value={maxTime} onChange={(e) => setMaxTime(e.target.value)} className="w-28 rounded-xl border border-slate-300 px-3 py-2" placeholder="any" />
          </label>
          <button onClick={search} disabled={!chips.length || loading} className="px-5 py-2.5 rounded-xl bg-teal-600 text-white font-semibold disabled:opacity-50 inline-flex items-center gap-2">
            {loading ? <Loader2 size={16} className="animate-spin" /> : <Search size={16} />} Find recipes
          </button>
        </div>
      </section>

      {error && <p role="alert" className="text-rose-700">{error}</p>}
      {data && (
        <section className="space-y-4" aria-live="polite">
          <h2 className="text-lg font-semibold text-slate-800">{data.total.toLocaleString()} recipes use at least one of your ingredients</h2>
          {data.add_ingredient_suggestions.length > 0 && (
            <p className="text-sm text-slate-600">
              Often needed by the top matches: {data.add_ingredient_suggestions.map((s) => (
                <button key={s} onClick={() => addChips([{ name: s, display: s }])} className="mx-1 px-2 py-0.5 rounded-full border border-emerald-300 text-emerald-800 hover:bg-emerald-50">+ {s}</button>
              ))}
            </p>
          )}
          {data.results.length === 0 ? (
            <p className="text-slate-600">No recipes match. Try removing the time limit or diet.</p>
          ) : (
            <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
              {data.results.map((h, i) => (
                <RecipeResultCard key={h.recipe.id} hit={h} rank={i + 1} query={data.understanding.original} />
              ))}
            </div>
          )}
        </section>
      )}
    </div>
  );
}
