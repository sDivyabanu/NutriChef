"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";
import { useRouter } from "next/navigation";

export default function OnboardingPage() {
  const router = useRouter();
  const [step, setStep] = useState(0);
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState({
    height: "",
    weight: "",
    age: "",
    dietType: "",
    allergies: "",
    conditions: [] as string[],
    otherInfo: "",
  });

  const conditionsList = ["Diabetes", "Blood Pressure", "Thyroid", "PCOS", "Heart Disease"];
  const dietOptions = ["Vegetarian", "Non-Vegetarian", "Vegan", "Eggetarian"];

  const handleSubmit = async () => {
  setLoading(true);

  try {
    const userId = document.cookie
      .split("; ")
      .find((row) => row.startsWith("userId="))
      ?.split("=")[1];

    if (!userId) throw new Error("User not logged in");

    const res = await fetch("/api/profile", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...data, userId }), // send userId to backend
    });

    if (res.ok) {
      router.push("/dashboard"); // ✅ done
    } else {
      const err = await res.json();
      alert(err.error || "Something went wrong!");
    }
  } catch (error) {
    console.error("Error saving profile:", error);
    alert("Failed to save profile!");
  } finally {
    setLoading(false);
  }
};

  return (
    <div className="min-h-screen flex flex-col items-center justify-center p-6">
      <div className="w-full max-w-lg bg-white shadow-xl rounded-2xl p-6 relative overflow-hidden">
        <button
          onClick={() => router.push("/profile")}
          className="absolute top-4 right-6 text-gray-400 hover:text-emerald-500 text-sm"
        >
          Skip →
        </button>

        <motion.div
          key={step}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
        >
          {step === 0 && (
            <>
              <h2 className="text-xl font-bold mb-4 text-emerald-600">
                Let’s personalize your experience ✨
              </h2>
              <Input
                placeholder="Height (cm)"
                value={data.height}
                onChange={(e) => setData({ ...data, height: e.target.value })}
                className="mb-3"
              />
              <Input
                placeholder="Weight (kg)"
                value={data.weight}
                onChange={(e) => setData({ ...data, weight: e.target.value })}
                className="mb-3"
              />
              <Input
                placeholder="Age"
                value={data.age}
                onChange={(e) => setData({ ...data, age: e.target.value })}
              />
              <div className="flex justify-end mt-5">
                <Button onClick={() => setStep(1)}>Next</Button>
              </div>
            </>
          )}

          {step === 1 && (
            <>
              <h2 className="text-xl font-bold mb-4 text-emerald-600">Diet Preferences 🍽️</h2>
              <div className="space-y-3">
                {dietOptions.map((opt) => (
                  <label key={opt} className="flex items-center space-x-2">
                    <input
                      type="radio"
                      name="diet"
                      value={opt}
                      checked={data.dietType === opt}
                      onChange={(e) => setData({ ...data, dietType: e.target.value })}
                    />
                    <span>{opt}</span>
                  </label>
                ))}
              </div>
              <div className="flex justify-between mt-5">
                <Button variant="outline" onClick={() => setStep(0)}>Back</Button>
                <Button onClick={() => setStep(2)}>Next</Button>
              </div>
            </>
          )}

          {step === 2 && (
            <>
              <h2 className="text-xl font-bold mb-4 text-emerald-600">Health Conditions 💊</h2>
              <div className="grid grid-cols-2 gap-3">
                {conditionsList.map((cond) => (
                  <label key={cond} className="flex items-center space-x-2">
                    <Checkbox
                      checked={data.conditions.includes(cond)}
                      onCheckedChange={(checked: boolean) =>
                        setData({
                          ...data,
                          conditions: checked
                            ? [...data.conditions, cond]
                            : data.conditions.filter((c) => c !== cond),
                        })
                      }
                    />
                    <span>{cond}</span>
                  </label>
                ))}
              </div>
              <Input
                placeholder="Any allergies? (optional)"
                value={data.allergies}
                onChange={(e) => setData({ ...data, allergies: e.target.value })}
                className="mt-3"
              />
              <div className="flex justify-between mt-5">
                <Button variant="outline" onClick={() => setStep(1)}>Back</Button>
                <Button onClick={() => setStep(3)}>Next</Button>
              </div>
            </>
          )}

          {step === 3 && (
            <>
              <h2 className="text-xl font-bold mb-4 text-emerald-600">Anything else? ✍️</h2>
              <Input
                placeholder="Other details (optional)"
                value={data.otherInfo}
                onChange={(e) => setData({ ...data, otherInfo: e.target.value })}
              />
              <div className="flex justify-between mt-5">
                <Button variant="outline" onClick={() => setStep(2)}>Back</Button>
                <Button disabled={loading} onClick={handleSubmit}>
                  {loading ? "Saving..." : "Finish 🎉"}
                </Button>
              </div>
            </>
          )}
        </motion.div>
      </div>
    </div>
  );
}
