"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Sparkles } from "lucide-react";
import { api, RecipeCardData } from "@/lib/nlp";

type Rec = { recipe: RecipeCardData; reason: string };

export default function Recommendations() {
  const [recs, setRecs] = useState<Rec[] | null>(null);
  const [recent, setRecent] = useState<RecipeCardData[]>([]);

  useEffect(() => {
    api<Rec[]>("/me/recommendations?k=6").then(setRecs).catch(() => setRecs([]));
    api<RecipeCardData[]>("/me/recently-viewed").then(setRecent).catch(() => setRecent([]));
  }, []);

  return (
    <section className="recommendations grid lg:grid-cols-3 gap-4">
      <div className="lg:col-span-2 p-5 rounded-lg bg-white/80 border border-emerald-100 shadow-stamp-sm">
        <h2 className="font-semibold text-emerald-800 flex items-center gap-2 mb-3">
          <Sparkles size={18} /> Recommended for you
        </h2>
        {recs === null ? (
          <p className="text-sm text-slate-500">Loading…</p>
        ) : recs.length === 0 ? (
          <p className="text-sm text-slate-600">
            Favourite or rate a few recipes, or set liked cuisines in{" "}
            <Link href="/preferences" className="underline text-teal-700">Preferences</Link>, and recommendations will appear here.
          </p>
        ) : (
          <ul className="grid sm:grid-cols-2 gap-2">
            {recs.map((r) => (
              <li key={r.recipe.id} className="p-3 rounded-xl border border-slate-100 bg-white">
                <Link href={`/recipes/${r.recipe.id}`} className="font-medium text-teal-800 hover:underline text-sm">
                  {r.recipe.title}
                </Link>
                <p className="text-xs text-slate-500 mt-0.5">{r.reason}</p>
              </li>
            ))}
          </ul>
        )}
      </div>
      <div className="p-5 rounded-lg bg-white/80 border border-emerald-100 shadow-stamp-sm">
        <h2 className="font-semibold text-emerald-800 mb-3">Recently viewed</h2>
        {recent.length === 0 ? (
          <p className="text-sm text-slate-600">
            Nothing yet — try <Link href="/search" className="underline text-teal-700">Smart Search</Link>.
          </p>
        ) : (
          <ul className="space-y-1.5 text-sm">
            {recent.map((r) => (
              <li key={r.id}>
                <Link href={`/recipes/${r.id}`} className="text-teal-800 hover:underline">{r.title}</Link>
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}
