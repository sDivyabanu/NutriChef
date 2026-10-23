// src/app/api/recipes/search/route.ts
// Previously queried Prisma models (Ingredient, RecipeIngredient) that do not exist in the schema.
// Now forwards to the local NLP hybrid search.
import { NextResponse } from "next/server";
import { forward } from "@/lib/backend";

type Body = { ingredients?: string[]; query?: string; limit?: number };

export async function POST(req: Request) {
  const body: Body = await req.json().catch(() => ({}));
  const limit = Math.min(Math.max(body.limit ?? 20, 1), 50);
  const query = body.query?.trim() || (Array.isArray(body.ingredients) && body.ingredients.length ? `I have ${body.ingredients.join(", ")}` : "");
  if (!query) return NextResponse.json({ error: "Provide ingredients array or query" }, { status: 400 });
  const res = await forward("/api/nlp/search", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, k: limit }),
    cookie: req.headers.get("cookie"),
  });
  const data = await res.json();
  return NextResponse.json(data, { status: res.status });
}
