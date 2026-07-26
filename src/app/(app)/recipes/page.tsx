"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { Leaf, Utensils, Flame, X } from "lucide-react";

type Recipe = {
  id: number;
  title: string;
  description: string;
  diet: string;
  instructions: string[];
};

export default function RecipesPage() {
  const [dietFilter, setDietFilter] = useState("All");
  const [selectedRecipe, setSelectedRecipe] = useState<Recipe | null>(null);

  const sampleRecipes: Recipe[] = [
  { id: 1, title: "Grilled Soya Salad 🥗", description: "A light, protein-rich salad with fresh greens and olive oil.", diet: "High-Protein", instructions: ["Grill soya chunks until golden brown.", "Mix with fresh greens, cherry tomatoes, and cucumber.", "Drizzle with olive oil and lemon juice before serving."] },
  { id: 2, title: "Vegan Buddha Bowl 🥙", description: "Colorful veggies, quinoa, and creamy tahini dressing.", diet: "Vegan", instructions: ["Cook quinoa according to package instructions.", "Roast assorted vegetables in olive oil and spices.", "Assemble bowl with quinoa, veggies, and drizzle with tahini."] },
  { id: 3, title: "Oatmeal with Berries 🫐", description: "Quick breakfast rich in fiber, antioxidants, and natural sweetness.", diet: "Vegetarian", instructions: ["Cook oats with milk or water until soft.", "Top with fresh berries and a drizzle of honey.", "Sprinkle some chia seeds for extra nutrition."] },
  { id: 4, title: "Spicy Chickpea Curry 🌶️", description: "Protein-packed chickpea curry with aromatic spices.", diet: "Vegan", instructions: ["Sauté onions, garlic, and ginger.", "Add tomatoes and spices, cook until oil separates.", "Add chickpeas and simmer for 15 minutes."] },
  { id: 5, title: "Eggplant Parmesan 🍆🧀", description: "Layered eggplant baked with marinara sauce and cheese.", diet: "Vegetarian", instructions: ["Slice and roast eggplant until tender.", "Layer with marinara sauce and mozzarella.", "Bake at 180°C for 25 minutes."] },
  { id: 6, title: "Protein Pancakes 🥞", description: "Fluffy pancakes packed with protein and flavor.", diet: "High-Protein", instructions: ["Mix oats, protein powder, eggs, and milk to form batter.", "Cook pancakes on non-stick pan until golden.", "Serve with fresh fruit or nut butter."] },
  { id: 7, title: "Vegan Tacos 🌮", description: "Soft tortillas with spiced beans, avocado, and salsa.", diet: "Vegan", instructions: ["Warm tortillas.", "Fill with cooked beans, avocado slices, and salsa.", "Serve with lime wedges."] },
  { id: 8, title: "Mushroom Risotto 🍄", description: "Creamy risotto with mushrooms and parmesan.", diet: "Vegetarian", instructions: ["Sauté onions and garlic.", "Add arborio rice and gradually add broth while stirring.", "Mix in mushrooms and parmesan before serving."] },
  { id: 9, title: "Grilled Salmon 🐟", description: "Salmon fillet grilled with herbs and lemon.", diet: "High-Protein", instructions: ["Season salmon with salt, pepper, and herbs.", "Grill for 4-5 minutes each side.", "Serve with lemon wedges."] },
  { id: 10, title: "Vegan Pad Thai 🍜", description: "Rice noodles stir-fried with tofu, veggies, and peanut sauce.", diet: "Vegan", instructions: ["Cook rice noodles.", "Stir-fry tofu and vegetables.", "Mix with noodles and peanut sauce."] },
  { id: 11, title: "Quinoa Salad 🥗", description: "Refreshing salad with quinoa, cucumber, tomato, and lemon dressing.", diet: "Vegan", instructions: ["Cook quinoa.", "Mix with chopped vegetables and dressing.", "Serve chilled."] },
  { id: 12, title: "Chicken Stir Fry 🍗", description: "Quick stir fry with chicken, bell peppers, and soy sauce.", diet: "High-Protein", instructions: ["Slice chicken and vegetables.", "Stir fry chicken until cooked.", "Add vegetables and soy sauce, cook until tender."] },
  { id: 13, title: "Vegetable Soup 🥣", description: "Warm soup with assorted vegetables and herbs.", diet: "Vegetarian", instructions: ["Chop vegetables.", "Simmer in vegetable broth until tender.", "Season with herbs and salt."] },
  { id: 14, title: "Vegan Lentil Curry 🍛", description: "Hearty curry with red lentils and spices.", diet: "Vegan", instructions: ["Sauté onions, garlic, and ginger.", "Add lentils and spices.", "Simmer until lentils are soft."] },
  { id: 15, title: "Greek Salad 🥗", description: "Salad with cucumber, tomato, feta, and olives.", diet: "Vegetarian", instructions: ["Chop vegetables.", "Mix with feta and olives.", "Drizzle olive oil and lemon juice."] },
  { id: 16, title: "Tofu Scramble 🍳", description: "Vegan scramble with tofu, turmeric, and vegetables.", diet: "Vegan", instructions: ["Crumble tofu.", "Cook with vegetables and turmeric.", "Serve warm."] },
  { id: 17, title: "High-Protein Smoothie 🥤", description: "Smoothie with protein powder, banana, and spinach.", diet: "High-Protein", instructions: ["Blend protein powder, banana, spinach, and almond milk.", "Serve chilled."] },
  { id: 18, title: "Vegetarian Pizza 🍕", description: "Homemade pizza with tomato, cheese, and vegetables.", diet: "Vegetarian", instructions: ["Prepare pizza dough.", "Top with sauce, cheese, and vegetables.", "Bake at 200°C for 15-20 minutes."] },
  { id: 19, title: "Vegan Burger 🍔", description: "Plant-based burger with lentil patty and vegan mayo.", diet: "Vegan", instructions: ["Cook lentil patties.", "Assemble burger with buns and toppings.", "Serve with fries."] },
  { id: 20, title: "Chicken Caesar Salad 🥗", description: "Grilled chicken salad with Caesar dressing and croutons.", diet: "High-Protein", instructions: ["Grill chicken.", "Mix lettuce, croutons, and dressing.", "Top with sliced chicken."] },
  { id: 21, title: "Vegetable Stir Fry 🥦", description: "Quick stir fry with assorted vegetables and soy sauce.", diet: "Vegan", instructions: ["Chop vegetables.", "Stir fry in soy sauce and garlic.", "Serve hot."] },
  { id: 22, title: "Protein Oatmeal 🥣", description: "Oatmeal with protein powder, nuts, and berries.", diet: "High-Protein", instructions: ["Cook oats.", "Mix in protein powder, berries, and nuts.", "Serve warm."] },
  { id: 23, title: "Stuffed Bell Peppers 🌶️", description: "Bell peppers stuffed with rice, beans, and vegetables.", diet: "Vegetarian", instructions: ["Prepare bell peppers.", "Cook filling with rice, beans, and spices.", "Bake until peppers are tender."] },
  { id: 24, title: "Vegan Chili 🌶️", description: "Spicy chili with beans, tomatoes, and corn.", diet: "Vegan", instructions: ["Cook beans and vegetables with spices.", "Simmer until thick.", "Serve hot."] },
  { id: 25, title: "High-Protein Salad 🥗", description: "Salad with chicken, boiled eggs, and avocado.", diet: "High-Protein", instructions: ["Boil eggs and grill chicken.", "Mix with greens and avocado.", "Dress with olive oil and lemon."] },
  { id: 26, title: "Vegetarian Tacos 🌮", description: "Soft tacos with beans, corn, and vegetables.", diet: "Vegetarian", instructions: ["Warm tortillas.", "Fill with beans, corn, and vegetables.", "Top with salsa."] },
  { id: 27, title: "Vegan Sushi 🍣", description: "Rice rolls with avocado, cucumber, and carrots.", diet: "Vegan", instructions: ["Prepare sushi rice.", "Roll with nori and vegetables.", "Slice and serve."] },
  { id: 28, title: "Grilled Turkey 🦃", description: "Lean turkey breast grilled with herbs.", diet: "High-Protein", instructions: ["Season turkey.", "Grill until cooked through.", "Serve with steamed vegetables."] },
  { id: 29, title: "Vegetable Lasagna 🍝", description: "Layered lasagna with vegetables and cheese.", diet: "Vegetarian", instructions: ["Prepare lasagna sheets.", "Layer with vegetables, sauce, and cheese.", "Bake for 30-35 minutes."] },
  { id: 30, title: "Vegan Curry 🥘", description: "Mixed vegetable curry with coconut milk.", diet: "Vegan", instructions: ["Cook vegetables with spices.", "Add coconut milk and simmer.", "Serve with rice."] },
  { id: 31, title: "High-Protein Wrap 🌯", description: "Whole wheat wrap with chicken, veggies, and hummus.", diet: "High-Protein", instructions: ["Grill chicken.", "Assemble wrap with veggies and hummus.", "Serve warm."] },
  { id: 32, title: "Vegetarian Quiche 🥧", description: "Savory quiche with spinach, cheese, and eggs.", diet: "Vegetarian", instructions: ["Prepare pastry base.", "Mix filling with eggs, spinach, and cheese.", "Bake for 30 minutes."] },
  { id: 33, title: "Vegan Stir Fry 🍜", description: "Tofu and vegetable stir fry with soy sauce.", diet: "Vegan", instructions: ["Cube tofu and fry until golden.", "Stir fry vegetables.", "Combine with tofu and sauce."] },
  { id: 34, title: "High-Protein Smoothie Bowl 🥣", description: "Smoothie bowl with protein powder, fruits, and granola.", diet: "High-Protein", instructions: ["Blend fruits with protein powder.", "Pour into bowl.", "Top with granola and seeds."] },
  { id: 35, title: "Vegetarian Pasta 🍝", description: "Pasta with tomato sauce, vegetables, and cheese.", diet: "Vegetarian", instructions: ["Cook pasta.", "Prepare vegetable sauce.", "Mix pasta with sauce and top with cheese."] },
  { id: 36, title: "Vegan Burger Bowl 🍔", description: "Deconstructed vegan burger in a bowl with quinoa and veggies.", diet: "Vegan", instructions: ["Cook quinoa.", "Cook vegan patties.", "Assemble bowl with quinoa, patties, and veggies."] },
  { id: 37, title: "Grilled Shrimp 🦐", description: "Shrimp grilled with garlic and herbs.", diet: "High-Protein", instructions: ["Season shrimp.", "Grill for 2-3 minutes per side.", "Serve with lemon wedges."] },
  { id: 38, title: "Vegetarian Chili 🌶️", description: "Chili with beans, vegetables, and spices.", diet: "Vegetarian", instructions: ["Cook beans and vegetables with spices.", "Simmer until thick.", "Serve hot."] },
  { id: 39, title: "Vegan Pancakes 🥞", description: "Fluffy pancakes made with plant-based ingredients.", diet: "Vegan", instructions: ["Mix flour, plant milk, and baking powder.", "Cook pancakes on non-stick pan.", "Serve with syrup or fruit."] },
  { id: 40, title: "High-Protein Omelette 🍳", description: "Omelette with eggs, spinach, and cheese.", diet: "High-Protein", instructions: ["Beat eggs and pour into pan.", "Add spinach and cheese.", "Cook until done."] },
  { id: 41, title: "Vegetarian Curry 🥘", description: "Mixed vegetable curry with aromatic spices.", diet: "Vegetarian", instructions: ["Cook vegetables with spices.", "Simmer with tomato sauce.", "Serve with rice."] },
  { id: 42, title: "Vegan Smoothie 🥤", description: "Smoothie with banana, spinach, and almond milk.", diet: "Vegan", instructions: ["Blend all ingredients until smooth.", "Serve chilled."] },
  { id: 43, title: "Grilled Steak 🥩", description: "Juicy steak grilled to perfection.", diet: "High-Protein", instructions: ["Season steak.", "Grill for desired doneness.", "Serve with vegetables."] },
  { id: 44, title: "Vegetarian Burrito 🌯", description: "Burrito with rice, beans, and vegetables.", diet: "Vegetarian", instructions: ["Cook rice and beans.", "Assemble burrito with veggies and sauce.", "Serve warm."] },
  { id: 45, title: "Vegan Mac & Cheese 🧀", description: "Creamy mac and cheese made with plant-based ingredients.", diet: "Vegan", instructions: ["Cook pasta.", "Prepare vegan cheese sauce.", "Mix pasta with sauce and serve."] },
  { id: 46, title: "High-Protein Chicken Bowl 🍗", description: "Bowl with grilled chicken, quinoa, and veggies.", diet: "High-Protein", instructions: ["Grill chicken.", "Cook quinoa.", "Assemble bowl with veggies."] },
  { id: 47, title: "Vegetarian Stuffed Mushrooms 🍄", description: "Mushrooms stuffed with cheese and herbs.", diet: "Vegetarian", instructions: ["Remove mushroom stems.", "Mix cheese with herbs.", "Fill mushrooms and bake for 15 minutes."] },
  { id: 48, title: "Vegan Falafel 🥙", description: "Crispy falafel balls with tahini sauce.", diet: "Vegan", instructions: ["Blend chickpeas with spices.", "Form balls and fry until golden.", "Serve with tahini sauce."] },
  { id: 49, title: "High-Protein Fish Bowl 🐟", description: "Bowl with grilled fish, rice, and vegetables.", diet: "High-Protein", instructions: ["Grill fish.", "Cook rice.", "Assemble bowl with vegetables and sauce."] },
  { id: 50, title: "Vegetarian Frittata 🍳", description: "Baked frittata with vegetables and cheese.", diet: "Vegetarian", instructions: ["Beat eggs and mix with vegetables and cheese.", "Bake until set.", "Serve warm."] },
  { id: 51, title: "Vegan Coconut Curry 🥘", description: "Curry with vegetables and coconut milk.", diet: "Vegan", instructions: ["Cook vegetables with spices.", "Add coconut milk and simmer.", "Serve with rice."] },
  { id: 52, title: "High-Protein Beef Stir Fry 🥩", description: "Beef stir fry with vegetables and soy sauce.", diet: "High-Protein", instructions: ["Slice beef and vegetables.", "Stir fry beef until cooked.", "Add vegetables and sauce, cook until tender."] },
  { id: 53, title: "Vegetarian Shepherd’s Pie 🥧", description: "Layered pie with mashed potatoes and vegetables.", diet: "Vegetarian", instructions: ["Cook vegetables.", "Layer with mashed potatoes.", "Bake at 180°C for 25 minutes."] },
  { id: 54, title: "Zucchini Noodles with Pesto 🍝", description: "Low-carb noodles with basil pesto and cherry tomatoes.", diet: "Vegetarian", instructions: ["Spiralize zucchini.", "Toss with pesto and cherry tomatoes.", "Serve immediately."] },
  { id: 55, title: "Vegan Jackfruit Tacos 🌮", description: "Pulled jackfruit tacos with avocado and salsa.", diet: "Vegan", instructions: ["Cook jackfruit with spices.", "Fill tortillas with jackfruit, avocado, and salsa.", "Serve warm."] },
  { id: 56, title: "High-Protein Turkey Meatballs 🥩", description: "Lean turkey meatballs baked and served with tomato sauce.", diet: "High-Protein", instructions: ["Mix turkey with spices.", "Form meatballs and bake.", "Serve with tomato sauce."] },
  { id: 57, title: "Vegetarian Stuffed Zucchini 🌿", description: "Zucchini boats stuffed with quinoa, tomatoes, and cheese.", diet: "Vegetarian", instructions: ["Halve zucchini.", "Fill with quinoa mixture.", "Bake until tender."] },
  { id: 58, title: "Vegan Mushroom Stroganoff 🍄", description: "Creamy mushroom stroganoff with plant-based cream.", diet: "Vegan", instructions: ["Sauté mushrooms and onions.", "Add plant cream and spices.", "Serve with noodles or rice."] },
  { id: 59, title: "High-Protein Shrimp Skewers 🦐", description: "Grilled shrimp skewers with herbs and spices.", diet: "High-Protein", instructions: ["Marinate shrimp.", "Grill on skewers until cooked.", "Serve with lemon wedges."] },
  { id: 60, title: "Vegetarian Cauliflower Steaks 🥦", description: "Roasted cauliflower steaks with herbs and olive oil.", diet: "Vegetarian", instructions: ["Slice cauliflower into thick steaks.", "Brush with olive oil and herbs.", "Roast until golden.", "Serve hot."] },
];

  const filteredRecipes =
    dietFilter === "All"
      ? sampleRecipes
      : sampleRecipes.filter((r) => r.diet === dietFilter);

  return (
    <div className="relative min-h-screen md:ml-64 bg-gradient-to-br from-sky-50 via-emerald-50 to-teal-100 text-slate-800 px-6 md:px-12 lg:px-16 py-10 transition-colors">
      <motion.h1
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        className="text-4xl font-extrabold text-teal-700 mb-2"
      >
        🍽️ Explore Recipes
      </motion.h1>
      <p className="text-slate-600 mb-8">
        Discover delicious dishes tailored to your diet and preferences.
      </p>

      {/* Diet Filter Buttons */}
      <div className="flex flex-wrap gap-3 mb-10">
        {["All", "High-Protein", "Vegan", "Vegetarian"].map((diet) => (
          <button
            key={diet}
            onClick={() => setDietFilter(diet)}
            aria-label={`Filter recipes by ${diet}`}
            className={`px-5 py-2.5 rounded-full font-medium text-sm backdrop-blur-md border transition-all shadow-sm
              ${
                dietFilter === diet
                  ? "bg-gradient-to-r from-teal-500 to-emerald-500 text-white border-transparent shadow-lg scale-105"
                  : "bg-white/80 text-slate-700 border-slate-300 hover:bg-slate-100 hover:shadow-md"
              }`}
          >
            {diet}
          </button>
        ))}
      </div>

      {/* Recipe Cards Grid */}
      <div className="grid gap-8 md:grid-cols-2 lg:grid-cols-3">
        {filteredRecipes.map((recipe) => (
          <motion.div
            key={recipe.id}
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            whileHover={{ y: -6 }}
            transition={{ duration: 0.3 }}
            className="relative p-6 rounded-3xl bg-white/80 border border-slate-200 shadow-md hover:shadow-xl backdrop-blur-md"
          >
            <h2 className="text-xl font-semibold text-teal-700 mb-2">
              {recipe.title}
            </h2>
            <p className="text-slate-600 mb-4 leading-relaxed">{recipe.description}</p>

            <span
              className={`inline-flex items-center gap-1 text-sm px-3 py-1.5 rounded-full font-medium mb-5 ${
                recipe.diet === "Vegan"
                  ? "bg-green-100 text-green-700"
                  : recipe.diet === "High-Protein"
                  ? "bg-orange-100 text-orange-700"
                  : "bg-sky-100 text-sky-700"
              }`}
            >
              {recipe.diet === "Vegan" && <Leaf size={15} />}
              {recipe.diet === "High-Protein" && <Flame size={15} />}
              {recipe.diet === "Vegetarian" && <Utensils size={15} />}
              {recipe.diet}
            </span>

            <button
              onClick={() => setSelectedRecipe(recipe)}
              aria-label={`View recipe for ${recipe.title}`}
              className="text-teal-600 font-semibold hover:text-teal-800 transition-colors"
            >
              View Recipe →
            </button>
          </motion.div>
        ))}
      </div>

      {filteredRecipes.length === 0 && (
        <p className="text-slate-500 italic mt-6">No recipes match your filter.</p>
      )}

      {/* Modal Popup */}
      {selectedRecipe && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <motion.div
            initial={{ opacity: 0, scale: 0.8, y: 30 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.9 }}
            className="relative bg-gradient-to-br from-white via-teal-50 to-emerald-50 rounded-3xl shadow-2xl p-8 max-w-lg w-full"
          >
            <button
              type="button"
              onClick={() => setSelectedRecipe(null)}
              aria-label="Close recipe modal"
              title="Close"
              className="absolute top-5 right-5 text-slate-500 hover:text-slate-700 transition"
            >
              <X size={26} />
            </button>

            <h2 className="text-3xl font-bold text-teal-700 mb-3">{selectedRecipe.title}</h2>

            <span
              className={`inline-flex items-center gap-1 text-sm px-3 py-1.5 rounded-full font-medium mb-4 ${
                selectedRecipe.diet === "Vegan"
                  ? "bg-green-100 text-green-700"
                  : selectedRecipe.diet === "High-Protein"
                  ? "bg-orange-100 text-orange-700"
                  : "bg-sky-100 text-sky-700"
              }`}
            >
              {selectedRecipe.diet === "Vegan" && <Leaf size={15} />}
              {selectedRecipe.diet === "High-Protein" && <Flame size={15} />}
              {selectedRecipe.diet === "Vegetarian" && <Utensils size={15} />}
              {selectedRecipe.diet}
            </span>

            <p className="text-slate-700 mb-5">{selectedRecipe.description}</p>

            <h3 className="font-semibold text-teal-700 mb-2">Instructions:</h3>
            <ol className="list-decimal list-inside space-y-2 text-slate-700">
              {selectedRecipe.instructions.map((step, idx) => (
                <li key={idx}>{step}</li>
              ))}
            </ol>
          </motion.div>
        </div>
      )}
    </div>
  );
}


