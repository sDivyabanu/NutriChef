"use client";

import { useState, useEffect } from "react";

export default function TrackPage() {
  const [water, setWater] = useState(0);
  const [weightLogs, setWeightLogs] = useState<number[]>([]);
  const [weightInput, setWeightInput] = useState("");

  const dailyGoal = 8; // glasses per day

  const addWater = () => setWater(water + 1);

  const addWeight = (e: React.FormEvent) => {
    e.preventDefault();
    if (!weightInput.trim()) return;
    setWeightLogs([...weightLogs, parseFloat(weightInput)]);
    setWeightInput("");
  };

  // Hydration reminder notification
  useEffect(() => {
    const reminder = setInterval(() => {
      if (Notification.permission === "granted") {
        new Notification("💧 Time to hydrate!", {
          body: "Drink a glass of water and log it in NutriChef 💙",
        });
      }
    }, 1000 * 60 * 60); // every 1 hour

    return () => clearInterval(reminder);
  }, []);

  // Ask for notification permission
  useEffect(() => {
    if (
      typeof window !== "undefined" &&
      Notification.permission === "default"
    ) {
      Notification.requestPermission();
    }
  }, []);

  return (
    <div className="max-w-3xl mx-auto">
      <h1 className="text-3xl font-bold text-slate-800 mb-8">Track</h1>

      {/* Hydration Section */}
      <section className="mb-12 p-6 rounded-2xl bg-gradient-to-br from-emerald-50 to-white border border-slate-200 shadow-sm">
        <h2 className="text-2xl font-semibold text-emerald-600 mb-4">Hydration</h2>
        <p className="text-slate-600 mb-4">
          Track your daily water intake. Each click = 1 glass.
        </p>

        {/* Progress bar */}
        <div className="w-full bg-slate-200 rounded-full h-4 mb-4">
          <div
            className={`bg-emerald-500 h-4 rounded-full transition-all`}
            style={{ width: `${Math.min((water / dailyGoal) * 100, 100)}%` }}
          />
        </div>
        <p className="text-slate-700 mb-4">
          {water}/{dailyGoal} glasses today
        </p>

        <button
          onClick={addWater}
          className="px-6 py-3 rounded-xl bg-emerald-500 text-white font-semibold hover:bg-sky-600 transition"
        >
          + Add Glass
        </button>

        {water >= dailyGoal && (
          <p className="mt-4 text-green-600 font-semibold">
            🎉 Goal achieved! Stay hydrated, champ!
          </p>
        )}
      </section>

      {/* Weight Section */}
      <section className="p-6 rounded-2xl bg-gradient-to-br from-emerald-50 to-white border border-slate-200 shadow-sm">
        <h2 className="text-2xl font-semibold text-emerald-600 mb-4">Weight</h2>
        <p className="text-slate-600 mb-4">
          Log your weight to monitor progress over time.
        </p>

        <form onSubmit={addWeight} className="flex gap-3 mb-6">
          <input
            type="number"
            placeholder="Enter weight (kg)"
            value={weightInput}
            onChange={(e) => setWeightInput(e.target.value)}
            className="flex-1 rounded-xl border border-slate-300 px-4 py-3 focus:outline-none focus:ring-2 focus:ring-emerald-400"
          />
          <button
            type="submit"
            className="px-6 py-3 rounded-xl bg-emerald-500 text-white font-semibold hover:bg-sky-600 transition"
          >
            Log
          </button>
        </form>

        {weightLogs.length > 0 ? (
          <ul className="space-y-3">
            {weightLogs.map((w, idx) => (
              <li
                key={idx}
                className="p-3 rounded-xl bg-white border border-slate-200 text-slate-700 shadow-sm"
              >
                {w} kg
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-slate-500 italic">No weight logs yet.</p>
        )}
      </section>

      {/* Motivation Section */}
      <section className="mt-12 text-center">
        <h3 className="text-xl font-semibold text-emerald-600 mb-3">
          Daily Wellness Tip 🌱
        </h3>
        <p className="text-slate-600">
          Consistency is key — small healthy habits every day lead to big
          results tomorrow. Keep going 💙 
        </p>
      </section>
    </div>
  );
}
