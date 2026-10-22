"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Droplets, Scale, Utensils } from "lucide-react";
import { motion } from "framer-motion";
import Recommendations from "@/components/nlp/Recommendations";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceArea,
  ReferenceLine,
} from "recharts";

export default function DashboardPage() {
  const router = useRouter();
  const [profile, setProfile] = useState<any>(null);
  const [hydrationData, setHydrationData] = useState<any[]>([]);
  const [bmi, setBmi] = useState<number | null>(null);

  useEffect(() => {
    async function fetchData() {
      try {
        const res = await fetch("/api/dashboard");
        const data = await res.json();
        setProfile(data.profile);
        setHydrationData(data.waterLogs);

        if (data.profile?.weight_kg && data.profile?.height_cm) {
          const heightM = data.profile.height_cm / 100;
          const calculatedBmi = data.profile.weight_kg / (heightM * heightM);
          setBmi(parseFloat(calculatedBmi.toFixed(1)));
        }
      } catch (err) {
        console.error(err);
      }
    }
    fetchData();
  }, []);

  const heightM = profile?.height_cm ? profile.height_cm / 100 : 0;
  const minNormalWeight = heightM ? 18.5 * heightM * heightM : 0;
  const maxNormalWeight = heightM ? 24.9 * heightM * heightM : 0;

  const bmiChartData = [
    { category: "Underweight", weight: 0 },
    { category: "Normal", weight: minNormalWeight },
    { category: "Overweight", weight: maxNormalWeight + 5 },
    { category: "Obese", weight: maxNormalWeight + 10 },
    { category: "You", weight: profile?.weight_kg || 0 },
  ];

  const CurrentWeightDot = (props: any) => {
    const { cx, cy, value } = props;
    if (value === profile?.weight_kg) {
      return (
        <circle
          cx={cx}
          cy={cy}
          r={8}
          fill="#FF4D35"
          stroke="#0A0A0A"
          strokeWidth={2}
        />
      );
    }
    return <circle cx={cx} cy={cy} r={3} fill="#FF4D35" />;
  };

  const getBmiCategory = (bmiValue: number) => {
    if (bmiValue < 18.5) return "Underweight";
    if (bmiValue < 25) return "Normal";
    if (bmiValue < 30) return "Overweight";
    return "Obese";
  };

  return (
    <div className="py-4 sm:py-6 space-y-6">
      {/* Header Section */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
      >
        <h1 className="display text-4xl sm:text-5xl mb-2 drop-shadow-stamp-sm">
          Welcome back{profile?.full_name ? `, ${profile.full_name}` : ""}
        </h1>
        <p className="text-lg text-ink/80">
          Here’s your health snapshot — hydration, weight, BMI, and recipe tips.
        </p>
      </motion.div>

      <Recommendations />

      {/* Cards Section */}
      <motion.div
        className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.6, delay: 0.2 }}
      >
        {/* Hydration Card */}
        <Card className="shadow-stamp rounded-lg bg-white/70 backdrop-blur-lg border border-emerald-100">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-emerald-700">
              <Droplets className="text-emerald-500" /> Hydration
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={200}>
              <LineChart
                data={
                  hydrationData.length
                    ? hydrationData
                    : [{ day: "Today", liters: 2 }]
                }
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#d1fae5" />
                <XAxis dataKey="day" stroke="#047857" />
                <YAxis stroke="#047857" />
                <Tooltip contentStyle={{ backgroundColor: "#ecfdf5" }} />
                <Line
                  type="monotone"
                  dataKey="liters"
                  stroke="#FF4D35"
                  strokeWidth={3}
                />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Weight + BMI Card */}
        <Card className="shadow-stamp rounded-lg bg-white/70 backdrop-blur-lg border border-emerald-100">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-emerald-700">
              <Scale className="text-lime-600" /> Weight & BMI
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={bmiChartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#d1fae5" />
                <XAxis dataKey="category" stroke="#047857" />
                <YAxis
                  domain={[
                    0,
                    Math.max(profile?.weight_kg || 0, maxNormalWeight + 10),
                  ]}
                  stroke="#047857"
                />
                <Tooltip contentStyle={{ backgroundColor: "#ecfdf5" }} />

                {heightM && (
                  <ReferenceArea
                    y1={minNormalWeight}
                    y2={maxNormalWeight}
                    fill="#bef264"
                    fillOpacity={0.25}
                    label={{
                      value: "Target Normal",
                      position: "insideTop",
                      fill: "#3f6212",
                    }}
                  />
                )}

                {profile?.weight_kg && heightM && (
                  <ReferenceLine
                    y={profile.weight_kg}
                    stroke="#FF4D35"
                    strokeDasharray="3 3"
                    label={{
                      value: "You",
                      position: "right",
                      fill: "#0A0A0A",
                    }}
                  />
                )}

                <Line
                  type="monotone"
                  dataKey="weight"
                  stroke="#FF4D35"
                  strokeWidth={3}
                  dot={<CurrentWeightDot />}
                />
              </LineChart>
            </ResponsiveContainer>

            <div className="mt-4 text-center text-emerald-800 space-y-1">
              <p>
                <strong>Height:</strong> {profile?.height_cm} cm
              </p>
              <p>
                <strong>Current Weight:</strong> {profile?.weight_kg} kg
              </p>
              <p>
                <strong>BMI:</strong>{" "}
                {bmi !== null ? bmi : "--"}{" "}
                <span className="text-sm text-emerald-600">
                  {bmi !== null ? getBmiCategory(bmi) : ""}
                </span>
              </p>
              {heightM && (
                <p className="text-sm text-emerald-600">
                  Target Normal Weight: {Math.round(minNormalWeight)} -{" "}
                  {Math.round(maxNormalWeight)} kg
                </p>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Recipe Suggestions */}
        <Card className="shadow-stamp rounded-lg bg-white/70 backdrop-blur-lg border border-lime-100">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lime-700">
              <Utensils className="text-lime-600" /> Quick Recipes
            </CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            {profile?.IngredientLists?.map((recipe: any) => (
              <div
                key={recipe.id}
                className="p-3 rounded-xl bg-lime-100 text-emerald-900 shadow-stamp-sm hover:bg-lime-200 transition"
              >
                🥗 {recipe.title}
              </div>
            ))}
            <Button
              className="mt-3 w-full bg-emerald-600 hover:bg-emerald-700 text-white font-semibold rounded-xl shadow-stamp"
              onClick={() => router.push("/recipes")}
            >
              See More Recipes
            </Button>
          </CardContent>
        </Card>
      </motion.div>
    </div>
  );
}
