// Typed client for the local FastAPI NLP service (proxied by Next.js under /backend).
export const API = "/backend";

export type Role = "available" | "required" | "preferred" | "excluded" | "unavailable";

export interface IngredientConstraint {
  name: string;
  display: string;
  role: Role;
  quantity?: number | null;
  unit?: string | null;
  quantity_text?: string | null;
}

export interface NutritionFilter {
  nutrient: "calories" | "protein_g" | "carbs_g" | "fat_g" | "fiber_g";
  op: "<=" | ">=";
  value: number;
  text: string;
}

export interface Understanding {
  original: string;
  corrected: string;
  corrections: [string, string][];
  language: string;
  intent: string;
  ingredients: IngredientConstraint[];
  excluded_groups: string[];
  diets: string[];
  cuisines: string[];
  meal_types: string[];
  max_time_min: number | null;
  nutrition: NutritionFilter[];
  qualities: string[];
  servings: number | null;
  similar_to: string | null;
  free_text: string;
  notes: string[];
  conflicts: string[];
  clarification: string | null;
}

export interface Derived {
  diet: Record<string, boolean>;
  diet_uncertain: string[];
  allergens: string[];
  cuisine_guess: string | null;
  meal_type_guess: string[];
  estimated_time_min: number | null;
  time_basis: string | null;
  difficulty: string | null;
  spice_level: string | null;
}

export interface RecipeCardData {
  id: number;
  title: string;
  source: string;
  ingredient_count: number;
  ingredients_preview: string[];
  derived: Derived;
  has_nutrition: boolean;
}

export interface Check {
  constraint: string;
  status: "pass" | "estimated" | "unknown";
  detail: string;
}

export interface SearchHit {
  recipe: RecipeCardData;
  score: number;
  score_breakdown: Record<string, number>;
  used_ingredients: string[];
  missing_ingredients: string[];
  pantry_match_pct: number | null;
  explanation: string[];
  warnings: string[];
  checks: Check[];
}

export interface SearchResponse {
  understanding: Understanding;
  results: SearchHit[];
  total: number;
  excluded_counts: Record<string, number>;
  notes: string[];
  relaxations: { key: string; label: string; results: number }[];
  suggestions: string[];
  add_ingredient_suggestions: string[];
  mode: string;
  timing_ms: Record<string, number>;
}

export interface Nutrition {
  calories?: number | null;
  protein_g?: number | null;
  carbs_g?: number | null;
  fat_g?: number | null;
  fiber_g?: number | null;
}

export interface ParsedIngredient {
  raw: string;
  name: string | null;
  display?: string | null;
  quantity?: number | null;
  quantity_text?: string | null;
  unit?: string | null;
  preparation?: string | null;
  optional: boolean;
  category?: string | null;
  is_staple: boolean;
}

export interface Recipe {
  id: number;
  source: string;
  title: string;
  ingredients: string[];
  instructions: string;
  cuisine: string | null;
  meal_type: string | null;
  total_time_min: number | null;
  servings: number | null;
  nutrition: Nutrition | null;
  nutrition_source: string | null;
  diet_tags: string[];
  owner_id: string | null;
  created_at: number;
  updated_at: number;
  version: number;
  parsed_ingredients?: ParsedIngredient[] | null;
  derived?: Derived | null;
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export async function api<T>(path: string, init?: RequestInit & { json?: unknown }): Promise<T> {
  const { json, ...rest } = init || {};
  const res = await fetch(API + path, {
    ...rest,
    headers: { ...(json !== undefined ? { "Content-Type": "application/json" } : {}), ...(rest.headers || {}) },
    body: json !== undefined ? JSON.stringify(json) : rest.body,
    credentials: "same-origin",
  });
  if (res.status === 204) return undefined as T;
  let data: unknown = null;
  try {
    data = await res.json();
  } catch {
    /* non-JSON error page */
  }
  if (!res.ok) {
    const detail = (data as { detail?: unknown })?.detail;
    const msg =
      typeof detail === "string"
        ? detail
        : Array.isArray(detail)
        ? detail.map((d: { msg?: string }) => d.msg).join("; ")
        : res.status === 503
        ? "The NLP engine is still starting up — try again in a few seconds."
        : `Request failed (${res.status})`;
    throw new ApiError(res.status, msg);
  }
  return data as T;
}

export const ROLE_LABEL: Record<Role, string> = {
  available: "have",
  required: "must include",
  preferred: "prefer",
  excluded: "exclude",
  unavailable: "don't have",
};

export const GROUP_LABEL: Record<string, string> = {
  meat: "meat, poultry & seafood",
  nuts: "nuts & peanuts",
  tree_nut: "tree nuts",
  onion_garlic: "onion & garlic",
  animal: "animal products",
  egg: "eggs",
};

export function titleCase(s: string) {
  return s.replace(/\b\w/g, (c) => c.toUpperCase());
}
