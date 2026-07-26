"use client";

import { useState } from "react";
import { motion } from "framer-motion";

export default function SettingsPage() {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [diet, setDiet] = useState("None");
  const [dailyWater, setDailyWater] = useState(8);
  const [calorieGoal, setCalorieGoal] = useState(2000);
  const [weightGoal, setWeightGoal] = useState("");
  const [notifications, setNotifications] = useState({
    water: true,
    meals: false,
    progress: true,
  });
  const [theme, setTheme] = useState("light");
  const [units, setUnits] = useState("kg");

  const saveSettings = (e: React.FormEvent) => {
    e.preventDefault();
    alert(`✅ Settings saved successfully!`);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-emerald-50 via-white to-green-50 px-6 md:px-10 py-10 md:ml-64 transition-all">
      <motion.h1
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        className="text-3xl font-extrabold text-emerald-700 mb-3 text-center md:text-left"
      >
        ⚙️ Settings
      </motion.h1>

      <p className="text-slate-600 mb-8 text-center md:text-left">
        Customize your profile, health goals, and preferences to match your
        wellness journey.
      </p>

      <motion.form
        onSubmit={saveSettings}
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="space-y-10 max-w-3xl bg-white/80 backdrop-blur-sm p-6 md:p-10 rounded-3xl border border-emerald-100 shadow-md mx-auto"
      >
        {/* Profile Info */}
        <section>
          <h2 className="text-xl font-semibold text-emerald-700 mb-4">
            👤 Profile Information
          </h2>
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <label htmlFor="name" className="block text-slate-700 font-medium mb-2">
                Name
              </label>
              <input
                id="name"
                type="text"
                placeholder="Enter your name"
                title="Full name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full rounded-xl border border-slate-300 px-4 py-3 focus:outline-none focus:ring-2 focus:ring-emerald-400"
              />
            </div>
            <div>
              <label htmlFor="email" className="block text-slate-700 font-medium mb-2">
                Email
              </label>
              <input
                id="email"
                type="email"
                placeholder="Enter your email"
                title="Email address"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full rounded-xl border border-slate-300 px-4 py-3 focus:outline-none focus:ring-2 focus:ring-emerald-400"
              />
            </div>
          </div>
        </section>

        {/* Health Goals */}
        <section>
          <h2 className="text-xl font-semibold text-emerald-700 mb-4">
            💪 Health Goals
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label htmlFor="dailyWater" className="block text-slate-700 font-medium mb-2">
                Daily Water Goal (glasses)
              </label>
              <input
                id="dailyWater"
                type="number"
                min={1}
                placeholder="Enter daily water goal"
                title="Daily water goal in glasses"
                value={dailyWater}
                onChange={(e) => setDailyWater(Number(e.target.value))}
                className="w-full rounded-xl border border-slate-300 px-4 py-3 focus:ring-2 focus:ring-emerald-400"
              />
            </div>
            <div>
              <label htmlFor="calorieGoal" className="block text-slate-700 font-medium mb-2">
                Daily Calorie Goal
              </label>
              <input
                id="calorieGoal"
                type="number"
                min={500}
                placeholder="Enter daily calorie goal"
                title="Daily calorie goal"
                value={calorieGoal}
                onChange={(e) => setCalorieGoal(Number(e.target.value))}
                className="w-full rounded-xl border border-slate-300 px-4 py-3 focus:ring-2 focus:ring-emerald-400"
              />
            </div>
            <div>
              <label htmlFor="weightGoal" className="block text-slate-700 font-medium mb-2">
                Target Weight ({units})
              </label>
              <input
                id="weightGoal"
                type="number"
                placeholder={`Enter target weight (${units})`}
                title="Target weight"
                value={weightGoal}
                onChange={(e) => setWeightGoal(e.target.value)}
                className="w-full rounded-xl border border-slate-300 px-4 py-3 focus:ring-2 focus:ring-emerald-400"
              />
            </div>
          </div>
        </section>

        {/* Diet Preference */}
        <section>
          <h2 className="text-xl font-semibold text-emerald-700 mb-4">
            🥗 Dietary Preferences
          </h2>
          <label htmlFor="diet" className="block text-slate-700 font-medium mb-2">
            Diet Type
          </label>
          <select
            id="diet"
            title="Select diet preference"
            value={diet}
            onChange={(e) => setDiet(e.target.value)}
            className="w-full rounded-xl border border-slate-300 px-4 py-3 focus:ring-2 focus:ring-emerald-400"
          >
            <option value="None">None</option>
            <option value="Vegetarian">Vegetarian</option>
            <option value="Vegan">Vegan</option>
            <option value="Keto">Keto</option>
            <option value="High-Protein">High-Protein</option>
            <option value="Mediterranean">Mediterranean</option>
          </select>
        </section>

        {/* Notifications */}
        <section>
          <h2 className="text-xl font-semibold text-emerald-700 mb-4">
            🔔 Notifications
          </h2>
          <div className="space-y-2">
            {Object.entries(notifications).map(([key, value]) => (
              <label key={key} htmlFor={key} className="flex items-center gap-3">
                <input
                  id={key}
                  type="checkbox"
                  title={`${key} reminder`}
                  checked={value}
                  onChange={() =>
                    setNotifications({ ...notifications, [key]: !value })
                  }
                  className="accent-emerald-500 w-5 h-5"
                />
                <span className="capitalize text-slate-700">{key} reminders</span>
              </label>
            ))}
          </div>
        </section>

        {/* App Preferences */}
        <section>
          <h2 className="text-xl font-semibold text-emerald-700 mb-4">
            🎨 App Preferences
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label htmlFor="theme" className="block text-slate-700 mb-2">
                Theme
              </label>
              <select
                id="theme"
                title="Select theme"
                value={theme}
                onChange={(e) => setTheme(e.target.value)}
                className="w-full rounded-xl border border-slate-300 px-4 py-3 focus:ring-2 focus:ring-emerald-400"
              >
                <option value="light">Light</option>
                <option value="dark">Dark</option>
              </select>
            </div>
            <div>
              <label htmlFor="units" className="block text-slate-700 mb-2">
                Units
              </label>
              <select
                id="units"
                title="Select units of measurement"
                value={units}
                onChange={(e) => setUnits(e.target.value)}
                className="w-full rounded-xl border border-slate-300 px-4 py-3 focus:ring-2 focus:ring-emerald-400"
              >
                <option value="kg">Kg / Liters</option>
                <option value="lbs">Lbs / Ounces</option>
              </select>
            </div>
          </div>
        </section>

        {/* Save Button */}
        <div className="pt-4 text-center">
          <button
            type="submit"
            title="Save your settings"
            className="px-6 py-3 rounded-xl bg-emerald-500 text-white font-semibold hover:bg-emerald-600 transition"
          >
            Save Settings
          </button>
        </div>
      </motion.form>
    </div>
  );
}
