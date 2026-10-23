"use client";

import { useState } from "react";
import { AlertTriangle, CheckCircle2, Loader2, Wand2, XCircle } from "lucide-react";
import { api, ApiError, Recipe } from "@/lib/nlp";

type LineChange = { before: string | null; after: string | null; status: string; note?: string | null; alternatives: string[] };
type ModifyResult = {
  understood: string[];
  title: string;
  ingredients: string[];
  instructions: string;
  servings: number | null;
  line_changes: LineChange[];
  step_changes: { before: string; after: string; changed: boolean }[];
  validation: { check: string; passed: boolean; detail: string }[];
  suggestions: string[];
  warnings: string[];
  clarification: string | null;
  method: string;
};

const EXAMPLES = ["Make this vegan", "Replace paneer with tofu", "Reduce the spice level", "Remove mushrooms", "Make it for 2 people", "Suggest an alternative without cream", "Make this quicker"];

export default function ModifyPanel({
  recipe,
  canOverwrite,
  loggedIn,
  onSaved,
  onReplaced,
}: {
  recipe: Recipe;
  canOverwrite: boolean;
  loggedIn: boolean;
  onSaved: (r: Recipe) => void;
  onReplaced: () => void;
}) {
  const [instr, setInstr] = useState("");
  const [servings, setServings] = useState("");
  const [res, setRes] = useState<ModifyResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [confirmReplace, setConfirmReplace] = useState(false);
  const [saving, setSaving] = useState(false);

  const run = async (text = instr) => {
    if (!text.trim()) return;
    setInstr(text);
    setLoading(true);
    setError(null);
    setConfirmReplace(false);
    try {
      setRes(
        await api<ModifyResult>("/nlp/modify", {
          method: "POST",
          json: { recipe_id: recipe.id, instruction: text, original_servings: servings ? Number(servings) : null },
        })
      );
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Modification failed.");
    } finally {
      setLoading(false);
    }
  };

  const save = async (replace: boolean) => {
    if (!res) return;
    setSaving(true);
    setError(null);
    const body = { title: res.title, ingredients: res.ingredients, instructions: res.instructions, servings: res.servings };
    try {
      if (replace) {
        await api(`/recipes/${recipe.id}`, { method: "PUT", json: body });
        setRes(null);
        setInstr("");
        onReplaced();
      } else {
        onSaved(await api<Recipe>("/recipes", { method: "POST", json: body }));
      }
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Save failed.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="bg-white/90 rounded-lg border border-teal-200 p-5 space-y-3">
      <h2 className="font-semibold text-slate-800 flex items-center gap-2">
        <Wand2 size={18} className="text-teal-600" /> Modify this recipe
      </h2>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          run();
        }}
        className="flex flex-col sm:flex-row gap-2"
      >
        <label htmlFor="modify-input" className="sr-only">
          Describe the change
        </label>
        <input
          id="modify-input"
          value={instr}
          onChange={(e) => setInstr(e.target.value)}
          placeholder="e.g. make this vegan, replace paneer with tofu…"
          className="flex-1 rounded-xl border border-slate-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-teal-400"
          maxLength={500}
        />
        <button type="submit" disabled={loading || !instr.trim()} className="px-4 py-2 rounded-xl bg-teal-600 text-white font-medium hover:bg-teal-700 disabled:opacity-50 inline-flex items-center gap-2 justify-center">
          {loading && <Loader2 size={15} className="animate-spin" />} Preview change
        </button>
      </form>
      <div className="flex flex-wrap gap-1.5">
        {EXAMPLES.map((ex) => (
          <button key={ex} onClick={() => run(ex)} className="text-xs px-2.5 py-1 rounded-full border border-slate-200 hover:bg-teal-50">
            {ex}
          </button>
        ))}
      </div>
      {error && <p role="alert" className="text-sm text-rose-700">{error}</p>}

      {res && (
        <div className="space-y-3 border-t border-slate-100 pt-3">
          {res.clarification ? (
            <div className="p-3 rounded-xl bg-sky-50 text-sky-900 text-sm space-y-2">
              <p>{res.clarification}</p>
              {/servings/.test(res.clarification) && (
                <div className="flex gap-2 items-center">
                  <label htmlFor="orig-serv">Original servings</label>
                  <input id="orig-serv" type="number" min={1} value={servings} onChange={(e) => setServings(e.target.value)} className="w-20 rounded-lg border px-2 py-1" />
                  <button onClick={() => run()} className="px-3 py-1 rounded-lg bg-sky-600 text-white">
                    Scale
                  </button>
                </div>
              )}
            </div>
          ) : null}
          {res.understood.length > 0 && (
            <p className="text-sm text-slate-600">
              Understood: <b>{res.understood.join(" · ")}</b> <span className="text-xs text-slate-400">({res.method})</span>
            </p>
          )}
          <p className="text-sm">
            New title: <b>{res.title}</b>
            {res.servings ? ` · serves ${res.servings}` : ""}
          </p>

          <div className="grid sm:grid-cols-2 gap-3 text-sm">
            <div>
              <h3 className="text-xs uppercase tracking-wide text-slate-500 mb-1">Original</h3>
              <ul className="space-y-1">
                {res.line_changes.map((c, i) => (
                  <li key={i} className={c.status === "removed" ? "line-through text-rose-700" : c.status === "changed" ? "text-rose-700" : "text-slate-600"}>
                    {c.before ?? <span className="text-slate-300">—</span>}
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <h3 className="text-xs uppercase tracking-wide text-slate-500 mb-1">Modified</h3>
              <ul className="space-y-1">
                {res.line_changes.map((c, i) => (
                  <li key={i} className={c.status === "unchanged" ? "text-slate-600" : "text-emerald-800 font-medium"}>
                    {c.after ?? <span className="text-slate-400 italic">removed</span>}
                    {c.note && <span className="block text-xs font-normal text-slate-500">{c.note}</span>}
                    {c.alternatives.length > 0 && <span className="block text-xs font-normal text-slate-500">or: {c.alternatives.join(", ")}</span>}
                  </li>
                ))}
              </ul>
            </div>
          </div>

          {res.step_changes.some((s) => s.changed) && (
            <div className="text-sm">
              <h3 className="text-xs uppercase tracking-wide text-slate-500 mb-1">Changed steps</h3>
              <ul className="space-y-1">
                {res.step_changes.filter((s) => s.changed).map((s, i) => (
                  <li key={i} className="text-emerald-800">• {s.after}</li>
                ))}
              </ul>
            </div>
          )}

          {res.validation.length > 0 && (
            <ul className="text-sm space-y-1">
              {res.validation.map((v) => (
                <li key={v.check} className="flex gap-1.5 items-start">
                  {v.passed ? <CheckCircle2 size={15} className="text-emerald-600 mt-0.5" /> : <XCircle size={15} className="text-rose-600 mt-0.5" />}
                  <span>
                    <b>{v.check}</b>: {v.detail}
                  </span>
                </li>
              ))}
            </ul>
          )}
          {res.suggestions.length > 0 && (
            <ul className="text-sm text-slate-700 list-disc ml-5">
              {res.suggestions.map((s) => (
                <li key={s}>{s}</li>
              ))}
            </ul>
          )}
          {res.warnings.map((w) => (
            <p key={w} className="text-sm text-amber-800 flex gap-1.5">
              <AlertTriangle size={14} className="mt-0.5 shrink-0" /> {w}
            </p>
          ))}
          <p className="text-xs text-slate-500">Substitutions are suggestions — they are not always interchangeable; use your cooking judgement.</p>

          {loggedIn && !res.clarification && res.understood.length > 0 && (
            <div className="flex flex-wrap gap-2 items-center">
              <button onClick={() => save(false)} disabled={saving} className="px-4 py-2 rounded-xl bg-emerald-600 text-white text-sm font-medium hover:bg-emerald-700 disabled:opacity-50">
                Save as a new recipe
              </button>
              {canOverwrite &&
                (confirmReplace ? (
                  <span className="text-sm inline-flex items-center gap-2">
                    Replace your saved recipe? The previous version is kept in history.
                    <button onClick={() => save(true)} disabled={saving} className="px-3 py-1.5 rounded-xl bg-rose-600 text-white">
                      Yes, replace
                    </button>
                    <button onClick={() => setConfirmReplace(false)} className="px-3 py-1.5 rounded-xl border">
                      Cancel
                    </button>
                  </span>
                ) : (
                  <button onClick={() => setConfirmReplace(true)} className="px-4 py-2 rounded-xl border border-rose-300 text-rose-700 text-sm hover:bg-rose-50">
                    Replace my recipe…
                  </button>
                ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
