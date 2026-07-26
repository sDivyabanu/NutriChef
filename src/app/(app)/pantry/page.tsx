"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Trash2 } from "lucide-react";

export default function PantryPage() {
  const [pantry, setPantry] = useState<any[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  // 🧭 Fetch pantry items when page loads
  useEffect(() => {
    const fetchPantry = async () => {
      try {
        const res = await fetch("/api/pantry");
        const data = await res.json();
        if (res.ok) setPantry(data.pantry || []);
      } catch (err) {
        console.error("Fetch pantry error:", err);
      }
    };
    fetchPantry();
  }, []);

  // 🥫 Add item
  const addItem = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;

    try {
      setLoading(true);
      const res = await fetch("/api/pantry", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: input }),
      });

      const data = await res.json();
      if (res.ok && data.item) {
        setPantry([data.item, ...pantry]);
        setInput("");
      } else {
        alert(data.error || "Failed to add item");
      }
    } catch (err) {
      console.error("Add pantry error:", err);
    } finally {
      setLoading(false);
    }
  };

  // 🗑 Remove item
  const removeItem = async (id: string) => {
    try {
      await fetch("/api/pantry", {
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id }),
      });
      setPantry(pantry.filter((i) => i.id !== id));
    } catch (err) {
      console.error("Delete pantry error:", err);
    }
  };

  return (
    <div className="max-w-2xl mx-auto">
      {/* Heading */}
      <h1 className="text-3xl font-bold text-slate-800 mb-3">Pantry</h1>
      <p className="text-slate-600 mb-6">
        Keep track of your staple ingredients here. Add, remove, and manage your
        pantry like a pro.
      </p>

      {/* Input Form */}
      <form
        onSubmit={addItem}
        className="flex gap-3 mb-8 bg-white p-3 rounded-2xl shadow-sm border border-slate-200"
      >
        <input
          type="text"
          placeholder="e.g. Rice"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          className="flex-1 rounded-xl border border-slate-300 px-4 py-3 focus:outline-none focus:ring-2 focus:ring-emerald-400"
        />
        <button
          type="submit"
          disabled={loading}
          className="px-6 py-3 rounded-xl bg-emerald-500 text-white font-semibold hover:bg-emerald-600 transition disabled:opacity-50"
        >
          {loading ? "Adding..." : "Add"}
        </button>
      </form>

      {/* Pantry List */}
      {pantry.length > 0 ? (
        <ul className="space-y-3">
          <AnimatePresence>
            {pantry.map((item) => (
              <li key={item.id}>
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, x: -20 }}
                  transition={{ duration: 0.2 }}
                  className="flex justify-between items-center p-4 rounded-xl bg-emerald-50 border border-slate-200 text-slate-700 shadow-sm"
                >
                  <span className="font-medium">{item.name}</span>
                  <button
                    onClick={() => removeItem(item.id)}
                    className="flex items-center gap-2 px-3 py-1 text-sm rounded-lg bg-red-100 text-red-600 hover:bg-red-200 transition"
                  >
                    <Trash2 size={16} />
                    Remove
                  </button>
                </motion.div>
              </li>
            ))}
          </AnimatePresence>
        </ul>
      ) : (
        <p className="text-slate-500 italic">
          No pantry items added yet. Start adding your staples!
        </p>
      )}
    </div>
  );
}
