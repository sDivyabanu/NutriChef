export const runtime = "nodejs";

import { NextResponse } from "next/server";
import pool from "@/lib/db";
import { getUser } from "@/lib/getUser";

// Favorites are stored in "UserRecipe" with tag = 'favorite'.
// recipe_ref links to the recipe id in the local NLP recipe store (nullable for older rows).

export async function POST(req: Request) {
  try {
    const user = await getUser();
    if (!user) {
      return NextResponse.json({ success: false, error: "User not logged in" }, { status: 401 });
    }
    const { recipe } = await req.json();
    if (!recipe || !recipe.recipe_name) {
      return NextResponse.json({ success: false, error: "Invalid recipe data" }, { status: 400 });
    }
    const recipeRef = recipe.recipe_ref != null ? String(recipe.recipe_ref) : null;
    if (recipeRef) {
      const dup = await pool.query(
        `SELECT * FROM "UserRecipe" WHERE user_id = $1 AND tag = 'favorite' AND recipe_ref = $2 LIMIT 1`,
        [user.id, recipeRef]
      );
      if (dup.rows[0]) return NextResponse.json({ success: true, recipe: dup.rows[0], existing: true });
    }
    const toInt = (v: unknown) => (typeof v === "number" && Number.isFinite(v) ? Math.round(v) : null);
    const { rows } = await pool.query(
      `INSERT INTO "UserRecipe" (user_id, recipe_name, calories, protein, fat, carbs, instructions, tag, recipe_ref)
       VALUES ($1, $2, $3, $4, $5, $6, $7, 'favorite', $8) RETURNING *`,
      [
        user.id,
        String(recipe.recipe_name).slice(0, 300),
        toInt(recipe.calories),
        toInt(recipe.protein),
        toInt(recipe.fat),
        toInt(recipe.carbs),
        recipe.instructions ?? null,
        recipeRef,
      ]
    );
    return NextResponse.json({ success: true, recipe: rows[0] ?? null });
  } catch (err) {
    console.error("Add favorite error:", err);
    return NextResponse.json({ success: false, error: "Failed to add favorite" }, { status: 500 });
  }
}

export async function GET() {
  try {
    const user = await getUser();
    if (!user) return NextResponse.json({ error: "User not logged in" }, { status: 401 });
    const { rows } = await pool.query(
      `SELECT * FROM "UserRecipe" WHERE user_id = $1 AND tag = 'favorite' ORDER BY created_at DESC`,
      [user.id]
    );
    return NextResponse.json({ recipes: rows });
  } catch (err) {
    console.error("Fetch favorites error:", err);
    return NextResponse.json({ error: "Failed to load favorites" }, { status: 500 });
  }
}

export async function DELETE(req: Request) {
  try {
    const user = await getUser();
    if (!user) return NextResponse.json({ error: "User not logged in" }, { status: 401 });
    const { id } = await req.json();
    if (!id) return NextResponse.json({ error: "Missing recipe ID" }, { status: 400 });
    await pool.query(`DELETE FROM "UserRecipe" WHERE id = $1 AND user_id = $2`, [id, user.id]);
    return NextResponse.json({ success: true });
  } catch (err) {
    console.error("Delete favorite error:", err);
    return NextResponse.json({ success: false, error: "Failed to delete favorite" }, { status: 500 });
  }
}
