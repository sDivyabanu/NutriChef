"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Leaf, Utensils, Flame, X, Trash2 } from "lucide-react";
import { createClient } from "@supabase/supabase-js";

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
);

type Recipe = {
  id: string;
  recipe_name: string;
  calories?: number;
  protein?: number;
  fat?: number;
  carbs?: number;
  instructions?: string;
  tag?: string; // Vegan, Vegetarian, High-Protein, etc.
};

export default function FavoritesPage() {
  const [favorites, setFavorites] = useState<Recipe[]>([]);
  const [selectedRecipe, setSelectedRecipe] = useState<Recipe | null>(null);
  const [loading, setLoading] = useState(true);

  // ✅ Fetch favorites
  const fetchFavorites = async () => {
    try {
      const res = await fetch("/api/favorites");
      const data = await res.json();

      if (res.ok && data.recipes) setFavorites(data.recipes);
      else console.error("Fetch error:", data.error);
    } catch (err) {
      console.error("Fetch failed:", err);
    } finally {
      setLoading(false);
    }
  };

  // ✅ Delete favorite
  const removeFavorite = async (id: string) => {
    try {
      const res = await fetch("/api/favorites", {
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id }),
      });
      const data = await res.json();

      if (res.ok && data.success)
        setFavorites((prev) => prev.filter((r) => r.id !== id));
      else console.error("Delete failed:", data.error);
    } catch (err) {
      console.error("Remove favorite error:", err);
    }
  };

  useEffect(() => {
    fetchFavorites();
  }, []);

  return (
    <div className="relative min-h-screen md:ml-64 bg-gradient-to-br from-sky-50 via-emerald-50 to-teal-100 text-slate-800 px-6 md:px-12 lg:px-16 py-10">
      <motion.h1
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        className="text-4xl font-extrabold text-teal-700 mb-4 text-center"
      >
        ❤️ Your Favorite Recipes
      </motion.h1>

      {loading ? (
        <p className="text-center text-slate-500">Loading favorites...</p>
      ) : favorites.length > 0 ? (
        <div className="grid gap-8 md:grid-cols-2 lg:grid-cols-3">
          {favorites.map((recipe, i) => (
            <motion.div
              key={recipe.id}
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              whileHover={{ y: -5 }}
              transition={{ duration: 0.3, delay: i * 0.05 }}
              className="relative p-6 rounded-3xl bg-white/80 border border-slate-200 shadow-md hover:shadow-xl backdrop-blur-md"
            >
              <h2 className="text-xl font-semibold text-teal-700 mb-2">
                {recipe.recipe_name}
              </h2>

              <div className="text-slate-600 mb-4 space-y-1 text-sm">
                {recipe.calories && <p>🔥 {recipe.calories} kcal</p>}
                {recipe.protein && <p>💪 {recipe.protein} g protein</p>}
                {recipe.fat && <p>🥑 {recipe.fat} g fat</p>}
                {recipe.carbs && <p>🍞 {recipe.carbs} g carbs</p>}
              </div>

              <span
                className={`inline-flex items-center gap-1 text-sm px-3 py-1.5 rounded-full font-medium mb-4 ${
                  recipe.tag === "Vegan"
                    ? "bg-green-100 text-green-700"
                    : recipe.tag === "High-Protein"
                    ? "bg-orange-100 text-orange-700"
                    : "bg-sky-100 text-sky-700"
                }`}
              >
                {recipe.tag === "Vegan" && <Leaf size={15} />}
                {recipe.tag === "High-Protein" && <Flame size={15} />}
                {recipe.tag === "Vegetarian" && <Utensils size={15} />}
                {recipe.tag || "Other"}
              </span>

              <div className="flex justify-between items-center mt-3">
                <button
                  onClick={() => setSelectedRecipe(recipe)}
                  className="text-teal-600 font-semibold hover:text-teal-800 transition-colors"
                >
                  View Recipe →
                </button>
                <button
                  onClick={() => removeFavorite(recipe.id)}
                  className="p-2 rounded-full hover:bg-red-100 text-red-600 transition"
                  title="Remove from favorites"
                >
                  <Trash2 size={18} />
                </button>
              </div>
            </motion.div>
          ))}
        </div>
      ) : (
        <p className="text-center text-slate-500 italic mt-12">
          No favorites yet. Add some tasty dishes! 🍽️
        </p>
      )}

      {/* ✅ Recipe Popup */}
      {/* ✅ Recipe Popup */}
{selectedRecipe && (
  <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm px-4">
    <motion.div
      initial={{ opacity: 0, scale: 0.9, y: 30 }}
      animate={{ opacity: 1, scale: 1, y: 0 }}
      transition={{ duration: 0.25 }}
      className="relative bg-gradient-to-br from-white via-teal-50 to-emerald-50 rounded-3xl shadow-2xl p-6 sm:p-8 max-w-md w-full max-h-[75vh] overflow-hidden"
    >
      {/* ❌ Close button */}
      <button
        onClick={() => setSelectedRecipe(null)}
        className="absolute top-4 right-4 text-slate-500 hover:text-slate-700 transition"
      >
        ✕
      </button>

      {/* Title */}
      <h2 className="text-2xl sm:text-3xl font-bold text-teal-700 mb-3 pr-6">
        {selectedRecipe.recipe_name}
      </h2>

      {/* Tag badge */}
      <span
        className={`inline-flex items-center gap-1 text-sm px-3 py-1.5 rounded-full font-medium mb-4 ${
          selectedRecipe.tag === "Vegan"
            ? "bg-green-100 text-green-700"
            : selectedRecipe.tag === "High-Protein"
            ? "bg-orange-100 text-orange-700"
            : "bg-sky-100 text-sky-700"
        }`}
      >
        {selectedRecipe.tag || "Other"}
      </span>

      {/* Scrollable Instructions */}
      <div className="overflow-y-auto pr-2 max-h-[50vh] text-slate-700 text-sm sm:text-base leading-relaxed custom-scrollbar">
        {selectedRecipe.instructions ? (
          <p className="whitespace-pre-line">{selectedRecipe.instructions}</p>
        ) : (
          <p className="italic text-slate-500">No instructions provided.</p>
        )}
      </div>
    </motion.div>
  </div>
)}
     
    </div>
  );
}
