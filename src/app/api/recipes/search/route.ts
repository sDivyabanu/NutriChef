// src/app/api/recipes/search/route.ts
import { NextResponse } from "next/server";
import prisma from "@/lib/prisma";
import { normalizeIngredient } from "@/lib/normalizeIngredient";

type Body = {
  ingredients: string[];
  limit?: number;
};

export async function POST(req: Request) {
  const body: Body = await req.json().catch(() => ({ ingredients: [] }));
  const limit = body.limit ?? 20;

  if (!body.ingredients || !Array.isArray(body.ingredients) || body.ingredients.length === 0) {
    return NextResponse.json({ error: "Provide ingredients array" }, { status: 400 });
  }

  // Normalize user ingredients -> canonical names
  const normalized = Array.from(new Set(body.ingredients.map(normalizeIngredient).filter(Boolean)));

  // Fetch matching ingredients from DB
  const ingredientRows = await prisma.ingredient.findMany({
    where: { name: { in: normalized } },
  });

  // Map names -> ids for the ones found
  const nameToId = new Map<string, number>();
  for (const row of ingredientRows) nameToId.set(row.name, row.id);

  // For normalized names not found, we'll still try fuzzy match by partial name search
  const missingNames = normalized.filter((n) => !nameToId.has(n));
  if (missingNames.length > 0) {
    // attempt partial matches (e.g., 'tomato' might match 'roma tomato')
    const partialMatches = await prisma.ingredient.findMany({
      where: { OR: missingNames.map((nm) => ({ name: { contains: nm } })) },
    });
    for (const p of partialMatches) {
      if (!nameToId.has(p.name)) nameToId.set(p.name, p.id);
    }
  }

  const ingredientIds = Array.from(nameToId.values());
  if (ingredientIds.length === 0) {
    // no known ingredients in DB -> return empty
    return NextResponse.json({ recipes: [] });
  }

  // Query recipes that use any of these ingredients and compute match counts
  // We'll fetch recipe ids and counts
  const recMatches = await prisma.$queryRaw<
    Array<{ recipeId: number; matchCount: number; totalCount: number }>
  >`SELECT ri."recipeId" AS "recipeId",
        COUNT(*) FILTER (WHERE ri."ingredientId" = ANY(${ingredientIds}::int[])) AS "matchCount",
        COUNT(*) AS "totalCount"
    FROM "RecipeIngredient" ri
    WHERE ri."recipeId" IN (
      SELECT DISTINCT "recipeId" FROM "RecipeIngredient" WHERE ri."ingredientId" = ri."ingredientId" OR TRUE
    )
    GROUP BY ri."recipeId"
    ORDER BY "matchCount" DESC
    LIMIT ${limit}`;

  // The above raw query is a bit complex — simpler approach: load candidate recipes that have at least one of the ingredientIds
  const candidateRecipeIdsRes = await prisma.recipeIngredient.findMany({
    where: { ingredientId: { in: ingredientIds } },
    select: { recipeId: true },
    distinct: ["recipeId"],
    take: 200,
  });
  const candidateRecipeIds = candidateRecipeIdsRes.map((r: { recipeId: number }) => r.recipeId);

  // For each candidate recipe compute match stats
  const recipesWithStats = await Promise.all(
    candidateRecipeIds.map(async (recipeId: number) => {
      const total = await prisma.recipeIngredient.count({ where: { recipeId } });
      const match = await prisma.recipeIngredient.count({
        where: { recipeId, ingredientId: { in: ingredientIds } },
      });
      const recipe = await prisma.recipe.findUnique({ where: { id: recipeId }, select: { id: true, title: true, imageUrl: true, instructions: true, sourceUrl: true } });
      const missingIngredientRows = await prisma.recipeIngredient.findMany({
        where: { recipeId, ingredientId: { notIn: ingredientIds } },
        include: { ingredient: true },
        take: 10,
      });

      return {
        recipe,
        total,
        match,
        matchRatio: total ? match / total : 0,
        missing: missingIngredientRows.map((r: { ingredient: { name: string } }) => r.ingredient.name),
      };
    })
  );

  // sort by matchRatio desc, then match count desc
  recipesWithStats.sort((a, b) => {
    if (b.matchRatio !== a.matchRatio) return b.matchRatio - a.matchRatio;
    return b.match - a.match;
  });

  return NextResponse.json({
    ingredients: normalized,
    foundIngredientCount: ingredientIds.length,
    recipes: recipesWithStats.slice(0, limit).map((r) => ({
      id: r.recipe?.id,
      title: r.recipe?.title,
      imageUrl: r.recipe?.imageUrl,
      instructionsSnippet: (r.recipe?.instructions || "").slice(0, 200),
      match: r.match,
      total: r.total,
      matchRatio: r.matchRatio,
      missing: r.missing,
      sourceUrl: r.recipe?.sourceUrl,
    })),
  });
}
