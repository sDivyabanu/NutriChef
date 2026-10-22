"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { AlertTriangle, CheckCircle2, Cpu, Loader2, Sparkles, XCircle } from "lucide-react";
import { api, ApiError, Recipe } from "@/lib/nlp";

type Check = { check: string; passed: boolean; detail: string };
type GenResult = {
  recipe: {
    title: string;
    description: string;
    servings: number | null;
    prep_time_min: number | null;
    cook_time_min: number | null;
    ingredients: { item: string; quantity: string; unit: string; note: string }[];
    steps: string[];
    tips: string[];
  } | null;
  method: string;
  model: string | null;
  valid: boolean;
  checks: Check[];
  warnings: string[];
  grounding: { id: number; title: string }[];
  attempts: number;
  timing: Record<string, number | null>;
  raw_error: string | null;
  adapted_from: { id: number; title: string } | null;
  ingredient_lines: string[];
};
type Job = { id: string; status: string; elapsed_s: number; result: GenResult | null; error: string | null };
type LlmStatus = { model: string | null; backend: string; server_binary: boolean; running: boolean; load_seconds: number | null; error: string | null };

const EXAMPLES = [
  "Create a spicy South Indian vegetarian dinner using rice, tomatoes and onions in under 30 minutes",
  "A quick vegan breakfast with oats and banana for 2",
  "High-protein paneer lunch without onion or garlic",
  "Gluten-free chicken curry for 4 people without dairy",
];
const HARD = /^(vegetarian|vegan|eggetarian|pescatarian|gluten-free|dairy-free|nut-free|egg-free|jain|no )/;

export default function GeneratePage() {
  const router = useRouter();
  const [req, setReq] = useState("");
  const [useLlm, setUseLlm] = useState(true);
  const [status, setStatus] = useState<LlmStatus | null>(null);
  const [job, setJob] = useState<Job | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const poll = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    api<LlmStatus>("/nlp/llm/status").then(setStatus).catch(() => setStatus(null));
    try {
      const pre = sessionStorage.getItem("nutrichef-generate-prefill");
      if (pre) {
        setReq(pre);
        sessionStorage.removeItem("nutrichef-generate-prefill");
      }
    } catch {
      /* ignore */
    }
    return () => {
      if (poll.current) clearInterval(poll.current);
    };
  }, []);

  const start = async () => {
    setError(null);
    setJob(null);
    try {
      const j = await api<Job>("/nlp/generate", { method: "POST", json: { request: req, use_llm: useLlm } });
      setJob(j);
      if (poll.current) clearInterval(poll.current);
      poll.current = setInterval(async () => {
        try {
          const s = await api<Job>(`/nlp/jobs/${j.id}`);
          setJob(s);
          if (s.status === "done" || s.status === "error") {
            if (poll.current) clearInterval(poll.current);
            api<LlmStatus>("/nlp/llm/status").then(setStatus).catch(() => {});
          }
        } catch {
          if (poll.current) clearInterval(poll.current);
          setError("Lost contact with the backend.");
        }
      }, 1000);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not start generation.");
    }
  };

  const r = job?.result;
  const hardFail = r?.checks.filter((c) => !c.passed && HARD.test(c.check)) || [];

  const save = async () => {
    if (!r?.recipe) return;
    setSaving(true);
    setError(null);
    try {
      const saved = await api<Recipe>("/recipes", {
        method: "POST",
        json: {
          title: r.recipe.title,
          ingredients: r.ingredient_lines,
          instructions: r.recipe.steps.join("\n"),
          servings: r.recipe.servings ?? null,
          total_time_min: r.recipe.prep_time_min != null && r.recipe.cook_time_min != null ? r.recipe.prep_time_min + r.recipe.cook_time_min || null : null,
          generated: r.method === "local-llm",
        },
      });
      router.push(`/recipes/${saved.id}`);
    } catch (e) {
      setError(e instanceof ApiError ? (e.status === 401 ? "Log in to save recipes." : e.message) : "Save failed.");
    } finally {
      setSaving(false);
    }
  };

  const running = job && (job.status === "queued" || job.status === "running");

  return (
    <div className="max-w-5xl mx-auto px-1 sm:px-4 py-4 sm:py-8 space-y-6">
      <header className="kitchen-banner p-6 sm:p-10 space-y-2">
        <h1 className="display text-4xl sm:text-5xl">Generate a recipe</h1>
        <p className="text-slate-600">
          Describe what you want. A language model running on this computer writes a recipe, grounded on similar recipes
          from the database, and NutriChef checks it against your constraints.
        </p>
      </header>

      <div className="text-sm flex flex-wrap items-center gap-2 text-slate-600">
        <Cpu size={16} className="text-teal-600" />
        {status?.model ? (
          <span>
            Local model: <b>{status.model}</b> ({status.backend}){status.running ? " · loaded" : " · loads on first use (≈10–30 s)"}
          </span>
        ) : (
          <span>No local language model installed — the fallback adapts an existing recipe instead (clearly labelled).</span>
        )}
      </div>

      <section className="bg-white/90 rounded-lg border border-slate-200 p-5 space-y-3">
        <label htmlFor="gen-req" className="text-sm font-medium text-slate-700">
          Your request
        </label>
        <textarea
          id="gen-req"
          value={req}
          onChange={(e) => setReq(e.target.value)}
          rows={3}
          maxLength={600}
          className="w-full rounded-xl border border-slate-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-teal-400"
          placeholder="e.g. Create a spicy South Indian vegetarian dinner using rice, tomatoes and onions in under 30 minutes"
        />
        <div className="flex flex-wrap gap-2">
          {EXAMPLES.map((ex) => (
            <button key={ex} onClick={() => setReq(ex)} className="text-xs px-2.5 py-1 rounded-full border border-slate-200 hover:bg-teal-50">
              {ex}
            </button>
          ))}
        </div>
        <div className="flex flex-wrap items-center gap-4">
          <button
            onClick={start}
            disabled={!!running || req.trim().length < 3}
            className="px-5 py-2.5 rounded-xl bg-teal-600 text-white font-semibold hover:bg-teal-700 disabled:opacity-50 inline-flex items-center gap-2"
          >
            {running ? <Loader2 size={16} className="animate-spin" /> : <Sparkles size={16} />} Generate
          </button>
          <label className="text-sm text-slate-600 inline-flex items-center gap-2">
            <input type="checkbox" checked={useLlm} onChange={(e) => setUseLlm(e.target.checked)} className="accent-teal-600" />
            Use the local language model (otherwise adapt an existing recipe)
          </label>
        </div>
        {running && (
          <p className="text-sm text-slate-500" aria-live="polite">
            {job?.status === "queued" ? "Queued…" : "Generating on your CPU"} — {job?.elapsed_s.toFixed(0)} s elapsed. This usually takes 20–90 seconds.
          </p>
        )}
        {error && <p role="alert" className="text-sm text-rose-700">{error}</p>}
        {job?.status === "error" && <p role="alert" className="text-sm text-rose-700">Generation failed: {job.error}</p>}
      </section>

      {r && !r.recipe && (
        <div className="p-4 rounded-2xl bg-amber-50 border border-amber-200 text-amber-900 text-sm">
          {r.raw_error || r.warnings.join(" ") || "No recipe could be produced."}
        </div>
      )}

      {r?.recipe && (
        <article className="bg-white/95 rounded-lg border border-slate-200 p-5 sm:p-6 space-y-5">
          <div className="flex flex-wrap items-center gap-2 text-xs">
            {r.method === "local-llm" ? (
              <span className="px-2 py-1 rounded-full bg-teal-100 text-teal-800">Generated locally by {r.model}</span>
            ) : (
              <span className="px-2 py-1 rounded-full bg-amber-100 text-amber-900">
                Adapted from an existing recipe{r.adapted_from ? `: ${r.adapted_from.title}` : ""} — not AI-generated
              </span>
            )}
            <span className="text-slate-500">
              {r.timing.total_s != null ? `${r.timing.total_s}s total` : ""}
              {r.timing.tokens_per_second ? ` · ${r.timing.tokens_per_second} tokens/s` : ""}
              {r.attempts > 1 ? ` · ${r.attempts} attempts (auto-repaired)` : ""}
            </span>
          </div>
          <div>
            <h2 className="text-2xl font-bold text-teal-800">{r.recipe.title}</h2>
            {r.recipe.description && <p className="text-slate-600 mt-1">{r.recipe.description}</p>}
            <p className="text-sm text-slate-500 mt-1">
              {r.recipe.servings ? `Serves ${r.recipe.servings}` : "Servings not stated"}
              {r.recipe.prep_time_min != null ? ` · prep ${r.recipe.prep_time_min} min` : ""}
              {r.recipe.cook_time_min != null ? ` · cook ${r.recipe.cook_time_min} min` : ""} (model-stated)
            </p>
          </div>
          <div className="grid md:grid-cols-5 gap-6">
            <div className="md:col-span-2">
              <h3 className="font-semibold mb-2">Ingredients</h3>
              <ul className="space-y-1 text-sm">
                {r.ingredient_lines.map((l, i) => (
                  <li key={i}>• {l}</li>
                ))}
              </ul>
            </div>
            <div className="md:col-span-3">
              <h3 className="font-semibold mb-2">Steps</h3>
              <ol className="list-decimal ml-5 space-y-1.5 text-sm text-slate-700">
                {r.recipe.steps.map((s, i) => (
                  <li key={i}>{s}</li>
                ))}
              </ol>
              {r.recipe.tips.length > 0 && (
                <ul className="mt-3 text-sm text-slate-600 list-disc ml-5">
                  {r.recipe.tips.map((t) => (
                    <li key={t}>{t}</li>
                  ))}
                </ul>
              )}
            </div>
          </div>
          <div className="border-t border-slate-100 pt-4 space-y-2">
            <h3 className="font-semibold text-sm">Constraint checks (done by NutriChef, not the model)</h3>
            <ul className="text-sm space-y-1">
              {r.checks.map((c) => (
                <li key={c.check} className="flex gap-1.5 items-start">
                  {c.passed ? <CheckCircle2 size={15} className="text-emerald-600 mt-0.5" /> : <XCircle size={15} className="text-rose-600 mt-0.5" />}
                  <span>
                    <b>{c.check}</b>: {c.detail}
                  </span>
                </li>
              ))}
            </ul>
            {r.warnings.map((w) => (
              <p key={w} className="text-sm text-amber-800 flex gap-1.5">
                <AlertTriangle size={14} className="mt-0.5 shrink-0" /> {w}
              </p>
            ))}
            <p className="text-xs text-slate-500">
              A generated recipe is a suggestion — check quantities, doneness and food safety with your own judgement. No nutrition values are generated.
            </p>
          </div>
          {r.grounding.length > 0 && (
            <p className="text-xs text-slate-500">
              Grounded on:{" "}
              {r.grounding.map((g, i) => (
                <span key={g.id}>
                  {i > 0 && ", "}
                  <Link href={`/recipes/${g.id}`} className="underline">
                    {g.title}
                  </Link>
                </span>
              ))}
            </p>
          )}
          <div className="flex flex-wrap gap-2 items-center">
            <button
              onClick={save}
              disabled={saving || hardFail.length > 0}
              className="px-4 py-2 rounded-xl bg-emerald-600 text-white font-medium hover:bg-emerald-700 disabled:opacity-50"
            >
              Save to my recipes
            </button>
            {hardFail.length > 0 && <span className="text-sm text-rose-700">Can’t save: it fails {hardFail.map((c) => c.check).join(", ")}. Try generating again.</span>}
            <button onClick={start} disabled={!!running} className="px-4 py-2 rounded-xl border border-slate-300 hover:bg-slate-50">
              Generate another
            </button>
          </div>
        </article>
      )}
    </div>
  );
}
