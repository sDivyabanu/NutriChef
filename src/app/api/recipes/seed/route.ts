// src/app/api/recipes/seed/route.ts
import { NextResponse } from "next/server";
import prisma from "@/lib/prisma";
import fetch from "node-fetch";
import { normalizeIngredient } from "@/lib/normalizeIngredient";

// THEMEALDB API examples:
// Search by first letter: https://www.themealdb.com/api/json/v1/1/search.php?f=a
// Random: https://www.themealdb.com/api/json/v1/1/random.php
// Or list all meals by category then lookup details.

const THEMEALDB_BASE = process.env.THEMEALDB_BASE ?? "https://www.themealdb.com/api/json/v1/1";

async function upsertIngredient(name: string) {
  name = name.trim();
  if (!name) return null;
  const existing = await prisma.ingredient.findUnique({ where: { name } });
  if (existing) return existing;
  return prisma.ingredient.create({ data: { name } });
}

export async function POST(req: Request) {
  // simple auth guard (dev) - require SEED_KEY to be set and passed as header
  const seedKey = process.env.SEED_KEY;
  const secret = req.headers.get("x-seed-key") ?? "";
  if (seedKey && seedKey !== secret) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  // We'll fetch meals by letters a..z and upsert them
  const letters = "abcdefghijklmnopqrstuvwxyz".split("");
  let imported = 0;

  for (const l of letters) {
    const res = await fetch(`${THEMEALDB_BASE}/search.php?f=${l}`);
    if (!res.ok) continue;
    const data = await res.json();
    if (!data.meals) continue;

    for (const meal of data.meals) {
      // meal fields: idMeal, strMeal, strInstructions, strSource, strMealThumb
      const externalId = meal.idMeal;
      const title = meal.strMeal;
      const instructions = meal.strInstructions || "";
      const imageUrl = meal.strMealThumb || null;
      const sourceUrl = meal.strSource || null;

      // upsert recipe
      const recipe = await prisma.recipe.upsert({
        where: { externalId },
        update: {
          title,
          instructions,
          imageUrl,
          sourceUrl,
        },
        create: {
          externalId,
          title,
          instructions,
          imageUrl,
          sourceUrl,
        },
      });

      // TheMealDB returns ingredient1..20 and measure1..20
      for (let i = 1; i <= 20; i++) {
        const ingRaw = meal[`strIngredient${i}`];
        const measure = meal[`strMeasure${i}`] || "";
        if (ingRaw && ingRaw.trim()) {
          const normalized = normalizeIngredient(ingRaw);
          if (!normalized) continue;
          // find or create ingredient
          let ing = await prisma.ingredient.findUnique({ where: { name: normalized } });
          if (!ing) {
            ing = await prisma.ingredient.create({ data: { name: normalized } });
          }

          // link to recipe (avoid duplicates)
          await prisma.recipeIngredient.upsert({
            where: {
              recipeId_ingredientId: {
                recipeId: recipe.id,
                ingredientId: ing.id,
              },
            },
            update: { rawText: `${measure} ${ingRaw}`.trim() },
            create: {
              recipeId: recipe.id,
              ingredientId: ing.id,
              rawText: `${measure} ${ingRaw}`.trim(),
            },
          });
        }
      }

      imported++;
    }
  }

  return NextResponse.json({ ok: true, imported });
}
