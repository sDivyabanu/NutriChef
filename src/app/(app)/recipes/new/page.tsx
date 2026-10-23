"use client";

import { useRouter } from "next/navigation";
import RecipeForm, { draftFromRecipe } from "@/components/recipes/RecipeForm";

export default function NewRecipePage() {
  const router = useRouter();
  return (
    <div className="max-w-6xl mx-auto px-1 sm:px-4 py-4 sm:py-8 space-y-6">
      <h1 className="display text-4xl sm:text-5xl">New recipe</h1>
      <RecipeForm initial={draftFromRecipe(null)} onSaved={(r) => router.push(`/recipes/${r.id}`)} />
    </div>
  );
}
