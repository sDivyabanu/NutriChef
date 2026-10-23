"use client";

import { use, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import RecipeForm, { draftFromRecipe } from "@/components/recipes/RecipeForm";
import { api, ApiError, Recipe } from "@/lib/nlp";

export default function EditRecipePage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const router = useRouter();
  const [recipe, setRecipe] = useState<Recipe | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api<Recipe>(`/recipes/${id}`)
      .then(setRecipe)
      .catch((e) => setError(e instanceof ApiError ? e.message : "Could not load recipe."));
  }, [id]);

  return (
    <div className="max-w-6xl mx-auto px-1 sm:px-4 py-4 sm:py-8 space-y-6">
      <h1 className="display text-4xl sm:text-5xl">Edit recipe</h1>
      {error && <p role="alert" className="text-rose-700">{error}</p>}
      {recipe && recipe.source === "epicurious-13k" && (
        <p className="text-amber-800">Dataset recipes are read-only. Use “Save a copy” on the recipe page to edit your own version.</p>
      )}
      {recipe && recipe.source !== "epicurious-13k" && (
        <RecipeForm initial={draftFromRecipe(recipe)} recipeId={recipe.id} onSaved={(r) => router.push(`/recipes/${r.id}`)} />
      )}
    </div>
  );
}
