import { NextResponse } from "next/server";
import { forward } from "@/lib/backend";

// Legacy endpoint kept for compatibility: { ingredients: string[] } -> recipes that use them.
// Previously scanned the CSV and attached RANDOM nutrition/diet values; it now uses the local NLP
// search and returns only real data (nutrition is null when unknown).
export async function POST(req: Request) {
  try {
    const { ingredients } = await req.json();
    if (!Array.isArray(ingredients) || ingredients.length === 0) {
      return NextResponse.json({ error: "No ingredients provided" }, { status: 400 });
    }
    const res = await forward("/api/nlp/search", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: `I have ${ingredients.map(String).join(", ")}`, k: 12, apply_profile: false }),
    });
    const data = await res.json();
    if (!res.ok) return NextResponse.json({ error: data.detail || "Search failed" }, { status: res.status });
    const recipes = data.results.map((h: { recipe: { id: number; title: string }; missing_ingredients: string[]; used_ingredients: string[]; pantry_match_pct: number | null }) => ({
      id: h.recipe.id,
      name: h.recipe.title,
      link: `/recipes/${h.recipe.id}`,
      nutrition: null,
      used: h.used_ingredients,
      missing: h.missing_ingredients,
      pantry_match_pct: h.pantry_match_pct,
    }));
    return NextResponse.json({ recipes });
  } catch (error) {
    console.error("Error fetching recipes:", error);
    return NextResponse.json({ error: "Failed to fetch recipes" }, { status: 500 });
  }
}
