"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Upload, Plus, Heart, X, Leaf, Flame, Utensils } from "lucide-react";

export default function IngredientsPage() {
  const [ingredients, setIngredients] = useState<string[]>([]);
  const [input, setInput] = useState("");
  const [suggestedRecipes, setSuggestedRecipes] = useState<any[]>([]);
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [selectedRecipe, setSelectedRecipe] = useState<any | null>(null);
  const [dietFilter, setDietFilter] = useState("All");

  const getRandomFoodEmoji = () => {
    const emojis = ["🍕", "🍜", "🥗", "🍝", "🍱", "🍛", "🥘", "🍣", "🍰", "🍩"];
    return emojis[Math.floor(Math.random() * emojis.length)];
  };

  const addIngredient = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;
    setIngredients([...ingredients, input.trim()]);
    setInput("");
  };

  const handleUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) setImageFile(e.target.files[0]);
  };

  const getRecipesFromImage = async () => {
    if (!imageFile) return alert("Please upload an image first.");
    const formData = new FormData();
    formData.append("file", imageFile);

    try {
      const res = await fetch("http://localhost:8000/detect", {
        method: "POST",
        body: formData,
      });
      const data = await res.json();
      if (data.ingredients?.length > 0) {
        setIngredients([...ingredients, ...data.ingredients]);
      } else alert("No ingredients detected. Try another image.");
    } catch {
      alert("Error detecting ingredients.");
    }
  };

  const getRecipes = async () => {
    if (ingredients.length === 0) return alert("Add at least one ingredient!");
    setLoading(true);
    try {
      const res = await fetch("/api/recipes", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ingredients }),
      });
      const data = await res.json();
      setSuggestedRecipes(
        data.recipes.map((r: any) => ({
          id: r.id,
          name: r.name,
          image: r.image,
          link: r.link,
          nutrition: r.nutrition,
          instructions: r.instructions || "No instructions available.",
          diet:
            r.diet ||
            ["Vegan", "Vegetarian", "High-Protein"][
              Math.floor(Math.random() * 3)
            ],
        }))
      );
    } catch {
      alert("Error fetching recipes.");
    } finally {
      setLoading(false);
    }
  };

  const addToFavorites = async (recipe: any) => {
  try {
    // ✅ Get logged-in user from profile API
    const profileRes = await fetch("/api/profile");
    const profileData = await profileRes.json();
    const userId = profileData.id;

    if (!userId) {
      alert("Not logged in!");
      return;
    }

    // ✅ Send favorite recipe to API
    const res = await fetch("/api/favorites", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        userId,
        recipe: {
          recipe_name: recipe.name, // ✅ FIXED FIELD NAME
          calories: recipe.nutrition?.calories ?? null,
          protein: recipe.nutrition?.protein ?? null,
          fat: recipe.nutrition?.fat ?? null,
          carbs: recipe.nutrition?.carbs ?? null,
          instructions: recipe.instructions ?? null,
        },
      }),
    });

    const data = await res.json();

    if (!res.ok) {
      console.error("Add favorite failed:", data.error);
      alert("❌ Failed to add to favorites!");
      return;
    }

    alert("❤️ Added to favorites!");
  } catch (err) {
    console.error("Add favorite error:", err);
    alert("Something went wrong while adding to favorites!");
  }
};

  const filteredRecipes =
    dietFilter === "All"
      ? suggestedRecipes
      : suggestedRecipes.filter((r) => r.diet === dietFilter);

  return (
    <div className="relative min-h-screen md:ml-64 bg-gradient-to-br from-sky-50 via-emerald-50 to-teal-100 text-slate-800 px-6 md:px-12 lg:px-16 py-10 transition-colors">
      <motion.h1
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        className="text-4xl font-extrabold text-teal-700 mb-2"
      >
        🥦 Ingredients
      </motion.h1>
      <p className="text-slate-600 mb-8">
        Enter ingredients manually or upload a photo — NutriChef will suggest recipes just for you!
      </p>

      {/* Input */}
      <form onSubmit={addIngredient} className="flex gap-3 mb-6">
        <input
          type="text"
          placeholder="e.g. Tomato"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          className="flex-1 rounded-xl border border-teal-300 px-4 py-3 bg-white/80 backdrop-blur-md focus:outline-none focus:ring-2 focus:ring-teal-400 transition"
        />
        <button
          type="submit"
          className="px-6 py-3 flex items-center gap-2 rounded-xl bg-gradient-to-r from-teal-500 to-emerald-500 text-white font-semibold hover:scale-105 transition-all shadow-md"
        >
          <Plus size={18} /> Add
        </button>
      </form>

      {/* Upload */}
      <div className="mb-6">
        <label className="flex items-center justify-center w-full p-5 border-2 border-dashed border-teal-400 rounded-2xl text-teal-600 cursor-pointer hover:bg-white/50 backdrop-blur-md transition">
          <Upload className="mr-2" size={20} /> Upload Ingredients Photo
          <input
            type="file"
            accept="image/*"
            onChange={handleUpload}
            className="hidden"
          />
        </label>
      </div>

      {imageFile && (
        <button
          onClick={getRecipesFromImage}
          className="mb-8 px-6 py-3 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-500 text-white font-semibold hover:scale-105 transition-all shadow-md"
        >
          Detect Ingredients from Image
        </button>
      )}

      {/* Ingredient List */}
      {ingredients.length > 0 && (
        <ul className="space-y-3 mb-6">
          {ingredients.map((item, idx) => (
            <li
              key={idx}
              className="p-3 rounded-xl bg-white/70 border border-teal-200 text-teal-800 shadow-sm backdrop-blur-md"
            >
              <motion.div
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                className="flex justify-between items-center"
              >
                <span>{item}</span>
                <button
                  onClick={() =>
                    setIngredients(ingredients.filter((_, i) => i !== idx))
                  }
                  className="text-red-500 hover:text-red-700"
                  aria-label={`Remove ${item}`}
                >
                  ✕
                </button>
              </motion.div>
            </li>
          ))}
        </ul>
      )}

      {/* Get Recipes */}
      {ingredients.length > 0 && (
        <button
          onClick={getRecipes}
          className="mb-10 px-6 py-3 rounded-xl bg-gradient-to-r from-teal-600 to-emerald-600 text-white font-semibold hover:scale-105 transition-all shadow-md"
        >
          {loading ? "Loading Recipes..." : "Get Recipes 🍳"}
        </button>
      )}

      {/* Diet Filters */}
      {suggestedRecipes.length > 0 && (
        <>
          <div className="flex flex-wrap gap-3 mb-8">
            {["All", "High-Protein", "Vegan", "Vegetarian"].map((diet) => (
              <button
                key={diet}
                onClick={() => setDietFilter(diet)}
                className={`px-4 py-2.5 rounded-full border text-sm font-medium backdrop-blur-md shadow-sm transition-all ${
                  dietFilter === diet
                    ? "bg-gradient-to-r from-teal-500 to-emerald-500 text-white border-transparent shadow-md scale-105"
                    : "bg-white/80 text-slate-700 border-slate-300 hover:bg-slate-100"
                }`}
              >
                {diet}
              </button>
            ))}
          </div>

          {/* Recipes Grid */}
          <div className="grid gap-8 md:grid-cols-2 lg:grid-cols-3">
            {filteredRecipes.map((r, idx) => (
              <motion.div
                key={idx}
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                whileHover={{ y: -6 }}
                transition={{ duration: 0.3 }}
                className="relative p-6 rounded-3xl bg-white/80 border border-slate-200 shadow-md hover:shadow-xl backdrop-blur-md"
              >
                <button
                  onClick={() => addToFavorites(r)}
                  aria-label={`Add ${r.name} to favorites`}
                  title={`Add ${r.name} to favorites`}
                  className="absolute top-3 right-3 text-red-500 hover:text-red-600 transition"
                >
                  <Heart size={20} />
                </button>

                <h2 className="text-xl font-semibold text-teal-700 mb-2 flex items-center gap-2">
                  {r.name} <span>{getRandomFoodEmoji()}</span>
                </h2>

                <p className="text-slate-700 mb-4 line-clamp-3">
                  {r.instructions?.slice(0, 120) || "No description available"}...
                </p>

                <span
                  className={`inline-flex items-center gap-1 text-sm px-3 py-1.5 rounded-full font-medium mb-3 ${
                    r.diet === "Vegan"
                      ? "bg-green-100 text-green-700"
                      : r.diet === "High-Protein"
                      ? "bg-orange-100 text-orange-700"
                      : "bg-sky-100 text-sky-700"
                  }`}
                >
                  {r.diet === "Vegan" && <Leaf size={14} />}
                  {r.diet === "High-Protein" && <Flame size={14} />}
                  {r.diet === "Vegetarian" && <Utensils size={14} />}
                  {r.diet}
                </span>

                <button
                  onClick={() => setSelectedRecipe(r)}
                  className="text-teal-600 font-semibold hover:text-teal-800 transition-colors"
                >
                  View Recipe →
                </button>
              </motion.div>
            ))}
          </div>
        </>
      )}

      {/* Modal */}
      <AnimatePresence>
        {selectedRecipe && (
          <motion.div
            className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            <motion.div
              className="relative bg-gradient-to-br from-white via-teal-50 to-emerald-50 rounded-3xl shadow-2xl p-8 max-w-lg w-full max-h-[80vh] overflow-y-auto"
              initial={{ scale: 0.9 }}
              animate={{ scale: 1 }}
              exit={{ scale: 0.9 }}
            >
              <button
                onClick={() => setSelectedRecipe(null)}
                aria-label="Close recipe details"
                title="Close recipe details"
                className="absolute top-4 right-4 text-slate-500 hover:text-slate-700 transition"
              >
                <X size={26} />
              </button>

              <h2 className="text-3xl font-bold text-teal-700 mb-3 flex items-center gap-2">
                {selectedRecipe.name} <span>{getRandomFoodEmoji()}</span>
              </h2>

              {selectedRecipe.nutrition && (
                <div className="text-sm text-slate-600 mb-3">
                  <p>
                    <strong>Calories:</strong>{" "}
                    {selectedRecipe.nutrition.calories} kcal
                  </p>
                  <p>
                    <strong>Protein:</strong>{" "}
                    {selectedRecipe.nutrition.protein} g
                  </p>
                  <p>
                    <strong>Fat:</strong> {selectedRecipe.nutrition.fat} g
                  </p>
                  <p>
                    <strong>Carbs:</strong> {selectedRecipe.nutrition.carbs} g
                  </p>
                </div>
              )}

              <h3 className="font-semibold text-teal-700 mb-2">Instructions:</h3>
              <p className="text-slate-700 whitespace-pre-line leading-relaxed text-sm">
                {selectedRecipe.instructions}
              </p>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
