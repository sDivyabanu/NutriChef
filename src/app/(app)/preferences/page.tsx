"use client";

import { useEffect, useState } from "react";
import { Loader2, Save } from "lucide-react";
import { api, ApiError } from "@/lib/nlp";

type Prefs = {
  diet: string | null;
  vegetarian_includes_eggs: boolean;
  allergies: string[];
  disliked_ingredients: string[];
  liked_ingredients: string[];
  liked_cuisines: string[];
  staples: string[];
  apply_profile: boolean;
  unrecognised?: string[];
};

const DIETS = ["", "vegetarian", "eggetarian", "vegan", "pescatarian", "non-vegetarian", "jain"];
const ALLERGENS = ["peanut", "nuts", "dairy", "egg", "gluten", "soy", "sesame", "fish", "shellfish", "mustard"];
const CUISINES = ["south indian", "north indian", "indian", "italian", "mexican", "chinese", "thai", "japanese", "korean", "middle eastern", "greek", "french", "american", "spanish"];

const toList = (s: string) => s.split(",").map((x) => x.trim()).filter(Boolean);

export default function PreferencesPage() {
  const [p, setP] = useState<Prefs | null>(null);
  const [text, setText] = useState({ disliked: "", liked: "", staples: "" });
  const [status, setStatus] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [importMsg, setImportMsg] = useState<string | null>(null);

  useEffect(() => {
    api<Prefs>("/me/preferences")
      .then((d) => {
        setP(d);
        setText({ disliked: d.disliked_ingredients.join(", "), liked: d.liked_ingredients.join(", "), staples: d.staples.join(", ") });
      })
      .catch((e) => setStatus(e instanceof ApiError && e.status === 401 ? "Please log in to manage preferences." : "Could not load preferences."));
  }, []);

  const importProfile = async () => {
    try {
      const res = await fetch("/api/profile");
      if (!res.ok) throw new Error();
      const prof = await res.json();
      setP((x) =>
        x
          ? {
              ...x,
              diet: prof.diet_type ? String(prof.diet_type).toLowerCase() : x.diet,
              allergies: Array.from(new Set([...(x.allergies || []), ...((prof.allergies as string[]) || []).map((a) => a.toLowerCase())])),
            }
          : x
      );
      setImportMsg("Imported diet and allergies from your profile — review and save.");
    } catch {
      setImportMsg("No profile found to import.");
    }
  };

  const save = async () => {
    if (!p) return;
    setSaving(true);
    setStatus(null);
    try {
      const out = await api<Prefs>("/me/preferences", {
        method: "PUT",
        json: {
          diet: p.diet || null,
          vegetarian_includes_eggs: p.vegetarian_includes_eggs,
          allergies: p.allergies,
          disliked_ingredients: toList(text.disliked),
          liked_ingredients: toList(text.liked),
          liked_cuisines: p.liked_cuisines,
          staples: toList(text.staples),
          apply_profile: p.apply_profile,
        },
      });
      setP(out);
      setStatus(out.unrecognised?.length ? `Saved. Not recognised (ignored in matching): ${out.unrecognised.join(", ")}` : "Saved.");
    } catch (e) {
      setStatus(e instanceof ApiError ? e.message : "Save failed.");
    } finally {
      setSaving(false);
    }
  };

  const toggle = (key: "allergies" | "liked_cuisines", v: string) =>
    setP((x) => (x ? { ...x, [key]: x[key].includes(v) ? x[key].filter((y) => y !== v) : [...x[key], v] } : x));

  const field = "w-full rounded-xl border border-slate-300 bg-white px-3 py-2 focus:outline-none focus:ring-2 focus:ring-emerald-400";

  return (
    <div className="max-w-3xl mx-auto px-1 sm:px-4 py-4 sm:py-8 space-y-6">
      <header className="kitchen-banner p-6 sm:p-10 space-y-2">
        <h1 className="display text-4xl sm:text-5xl">Preferences</h1>
        <p className="text-slate-600">Used to personalise search, the assistant, recommendations and generation. Diet and allergies are hard filters; likes are gentle boosts.</p>
      </header>
      {!p && !status && (
        <p className="flex items-center gap-2 text-slate-500">
          <Loader2 size={16} className="animate-spin" /> Loading…
        </p>
      )}
      {status && !p && <p role="alert" className="text-rose-700">{status}</p>}
      {p && (
        <div className="space-y-5 bg-white/90 rounded-lg border border-slate-200 p-5">
          <button onClick={importProfile} className="text-sm underline text-teal-700">Import diet & allergies from my profile</button>
          {importMsg && <p className="text-xs text-slate-500">{importMsg}</p>}
          <label className="block">
            <span className="text-sm font-medium text-slate-700">Diet</span>
            <select value={p.diet || ""} onChange={(e) => setP({ ...p, diet: e.target.value || null })} className={field}>
              {DIETS.map((d) => (
                <option key={d} value={d}>{d || "No restriction"}</option>
              ))}
            </select>
          </label>
          <label className="flex items-center gap-2 text-sm text-slate-700">
            <input type="checkbox" checked={p.vegetarian_includes_eggs} onChange={(e) => setP({ ...p, vegetarian_includes_eggs: e.target.checked })} className="accent-emerald-600" />
            When I say “vegetarian”, eggs are fine
          </label>
          <fieldset>
            <legend className="text-sm font-medium text-slate-700 mb-1">Allergies & intolerances (always excluded, including “may contain”)</legend>
            <div className="flex flex-wrap gap-2">
              {ALLERGENS.map((a) => (
                <button key={a} type="button" aria-pressed={p.allergies.includes(a)} onClick={() => toggle("allergies", a)}
                  className={`px-3 py-1 rounded-full border text-sm ${p.allergies.includes(a) ? "bg-rose-600 text-white border-rose-600" : "bg-white border-slate-300"}`}>
                  {a}
                </button>
              ))}
            </div>
            <p className="text-xs text-slate-500 mt-1">NutriChef checks ingredient text only. It cannot guarantee a recipe is allergy-safe.</p>
          </fieldset>
          <fieldset>
            <legend className="text-sm font-medium text-slate-700 mb-1">Cuisines I like</legend>
            <div className="flex flex-wrap gap-2">
              {CUISINES.map((c) => (
                <button key={c} type="button" aria-pressed={p.liked_cuisines.includes(c)} onClick={() => toggle("liked_cuisines", c)}
                  className={`px-3 py-1 rounded-full border text-sm ${p.liked_cuisines.includes(c) ? "bg-emerald-600 text-white border-emerald-600" : "bg-white border-slate-300"}`}>
                  {c}
                </button>
              ))}
            </div>
          </fieldset>
          <label className="block">
            <span className="text-sm font-medium text-slate-700">Ingredients I like (comma separated)</span>
            <input value={text.liked} onChange={(e) => setText({ ...text, liked: e.target.value })} className={field} placeholder="paneer, spinach, chickpeas" />
          </label>
          <label className="block">
            <span className="text-sm font-medium text-slate-700">Ingredients I dislike (ranked lower, not excluded)</span>
            <input value={text.disliked} onChange={(e) => setText({ ...text, disliked: e.target.value })} className={field} placeholder="mushrooms, olives" />
          </label>
          <label className="block">
            <span className="text-sm font-medium text-slate-700">Pantry staples I always have (not counted as “missing”)</span>
            <input value={text.staples} onChange={(e) => setText({ ...text, staples: e.target.value })} className={field} placeholder="sugar, cumin, turmeric, rice" />
            <span className="text-xs text-slate-500">Salt, pepper, water and cooking oils are always assumed.</span>
          </label>
          <label className="flex items-center gap-2 text-sm text-slate-700">
            <input type="checkbox" checked={p.apply_profile} onChange={(e) => setP({ ...p, apply_profile: e.target.checked })} className="accent-emerald-600" />
            Apply these preferences by default
          </label>
          <button onClick={save} disabled={saving} className="px-5 py-2 rounded-xl bg-emerald-600 text-white font-medium inline-flex items-center gap-2 disabled:opacity-50">
            {saving ? <Loader2 size={16} className="animate-spin" /> : <Save size={16} />} Save preferences
          </button>
          {status && <p className="text-sm text-slate-700">{status}</p>}
        </div>
      )}
    </div>
  );
}
