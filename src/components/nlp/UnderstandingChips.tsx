"use client";

import { X } from "lucide-react";
import { GROUP_LABEL, ROLE_LABEL, Understanding } from "@/lib/nlp";

const ROLE_STYLE: Record<string, string> = {
  available: "bg-emerald-50 text-emerald-800 border-emerald-200",
  required: "bg-teal-50 text-teal-800 border-teal-300",
  preferred: "bg-sky-50 text-sky-800 border-sky-200",
  excluded: "bg-rose-50 text-rose-800 border-rose-200",
  unavailable: "bg-amber-50 text-amber-800 border-amber-200",
};

type Chip = { key: string; label: string; style: string; remove: (u: Understanding) => Understanding };

export function chipsFor(u: Understanding): Chip[] {
  const chips: Chip[] = [];
  u.ingredients.forEach((ing, idx) =>
    chips.push({
      key: `ing-${idx}`,
      label: `${ROLE_LABEL[ing.role]}: ${ing.display}${ing.display.toLowerCase() !== ing.name ? ` (${ing.name})` : ""}${
        ing.quantity_text ? ` · ${ing.quantity_text}` : ""
      }`,
      style: ROLE_STYLE[ing.role],
      remove: (x) => ({ ...x, ingredients: x.ingredients.filter((_, i) => i !== idx) }),
    })
  );
  u.excluded_groups.forEach((g) =>
    chips.push({
      key: `grp-${g}`,
      label: `exclude: ${GROUP_LABEL[g] || g}`,
      style: ROLE_STYLE.excluded,
      remove: (x) => ({
        ...x,
        excluded_groups: x.excluded_groups.filter((y) => y !== g),
        // removing the group also removes the ingredient chip that produced it
        ingredients: x.ingredients.filter((i) => !(i.role === "excluded" && groupOf(i.name) === g)),
      }),
    })
  );
  u.diets.forEach((d) =>
    chips.push({ key: `diet-${d}`, label: `diet: ${d}`, style: "bg-lime-50 text-lime-800 border-lime-300", remove: (x) => ({ ...x, diets: x.diets.filter((y) => y !== d) }) })
  );
  u.cuisines.forEach((c) =>
    chips.push({ key: `cui-${c}`, label: `cuisine: ${c}`, style: "bg-violet-50 text-violet-800 border-violet-200", remove: (x) => ({ ...x, cuisines: x.cuisines.filter((y) => y !== c) }) })
  );
  u.meal_types.forEach((m) =>
    chips.push({ key: `meal-${m}`, label: `meal: ${m}`, style: "bg-orange-50 text-orange-800 border-orange-200", remove: (x) => ({ ...x, meal_types: x.meal_types.filter((y) => y !== m) }) })
  );
  if (u.max_time_min != null)
    chips.push({ key: "time", label: `≤ ${u.max_time_min} min`, style: "bg-slate-50 text-slate-800 border-slate-300", remove: (x) => ({ ...x, max_time_min: null }) });
  u.nutrition.forEach((n, idx) =>
    chips.push({
      key: `nut-${idx}`,
      label: `${n.nutrient.replace("_g", "")} ${n.op} ${n.value}${n.nutrient === "calories" ? " kcal" : " g"}`,
      style: "bg-yellow-50 text-yellow-800 border-yellow-300",
      remove: (x) => ({ ...x, nutrition: x.nutrition.filter((_, i) => i !== idx) }),
    })
  );
  u.qualities.forEach((q) =>
    chips.push({ key: `q-${q}`, label: q, style: "bg-white text-slate-700 border-slate-200", remove: (x) => ({ ...x, qualities: x.qualities.filter((y) => y !== q) }) })
  );
  if (u.similar_to)
    chips.push({ key: "sim", label: `similar to: ${u.similar_to}`, style: "bg-indigo-50 text-indigo-800 border-indigo-200", remove: (x) => ({ ...x, similar_to: null }) });
  return chips;
}

function groupOf(name: string) {
  return ({ dairy: "dairy", egg: "egg", nut: "nuts", peanut: "peanut", fish: "fish", shellfish: "shellfish", seafood: "seafood", meat: "meat", alcohol: "alcohol" } as Record<string, string>)[name];
}

export default function UnderstandingChips({ u, onChange }: { u: Understanding; onChange?: (u: Understanding) => void }) {
  const chips = chipsFor(u);
  if (!chips.length) return null;
  return (
    <div className="flex flex-wrap gap-2" aria-label="How your request was understood">
      {chips.map((c) => (
        <span key={c.key} className={`inline-flex items-center gap-1 text-xs sm:text-sm px-3 py-1 rounded-full border ${c.style}`}>
          {c.label}
          {onChange && (
            <button
              type="button"
              onClick={() => onChange(c.remove(u))}
              aria-label={`Remove filter ${c.label}`}
              className="ml-0.5 rounded-full hover:bg-black/10 p-0.5"
            >
              <X size={12} aria-hidden />
            </button>
          )}
        </span>
      ))}
    </div>
  );
}
