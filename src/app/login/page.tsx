"use client";

import Link from "next/link";
import { Logo } from "@/components/bento/Brand";
import KitchenArt from "@/components/KitchenArt";
import { motion } from "framer-motion";
import { useRouter } from "next/navigation";
import { useState } from "react";


export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    const res = await fetch("/api/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });

    const data = await res.json();

    if (res.ok) {
      alert("✅ Logged in successfully!");
      const hasOnboarded = localStorage.getItem(`onboarded_${email}`);

      if (!hasOnboarded) {
        localStorage.setItem(`onboarded_${email}`, "true");
        router.push("/onboarding");
      } else {
        router.push("/dashboard");
      }
    } else {
      alert(`❌ ${data.error || "Login failed"}`);
    }
  };

  return (
    <main
      className={`auth-page relative flex min-h-screen items-center justify-center overflow-hidden px-4`}
    >
      <Link href="/" className="auth-home text-link">← BACK TO THE KITCHEN</Link>
      <div className="auth-art"><p className="eyebrow">GOOD FOOD STARTS HERE.</p><KitchenArt /><h1>YOUR NEXT<br />GREAT MEAL<br /><span className="highlight-orange">STARTS WITH YOU.</span></h1></div>
      {/* Animated green blobs */}
      <motion.div
        animate={{ x: [0, 40, 0], y: [0, -40, 0] }}
        transition={{ repeat: Infinity, duration: 10 }}
        className="absolute top-20 left-20 w-72 h-72 bg-[#FF4D35]/20 rounded-full blur-3xl"
      />
      <motion.div
        animate={{ x: [0, -60, 0], y: [0, 60, 0] }}
        transition={{ repeat: Infinity, duration: 12 }}
        className="absolute bottom-20 right-20 w-96 h-96 bg-[#FF4D35]/15 rounded-full blur-3xl"
      />

      {/* Login Card */}
      <motion.div
        initial={{ scale: 0.9, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ duration: 0.6 }}
        className="w-full max-w-md relative bg-blush kitchen-card p-8 border border-[#0A0A0A]"
      >
        <div className="mb-8"><Logo /></div>
        {/* Floating food emojis */}
        <motion.span
          animate={{ y: [0, -10, 0] }}
          transition={{ repeat: Infinity, duration: 3 }}
          className="absolute -top-6 left-8 text-2xl"
        >
          🥑
        </motion.span>
        <motion.span
          animate={{ y: [0, 10, 0] }}
          transition={{ repeat: Infinity, duration: 4 }}
          className="absolute -top-6 right-8 text-2xl"
        >
          🥗
        </motion.span>
        <motion.span
          animate={{ y: [0, -10, 0] }}
          transition={{ repeat: Infinity, duration: 5 }}
          className="absolute bottom-6 right-12 text-2xl"
        >
          🍞
        </motion.span>

        {/* Title */}
        <h2 className="display text-5xl text-center mb-3">
          Welcome Back 👋
        </h2>
        <p className="text-[#45453F] text-center mb-8">
          Log in to continue your <span className="text-[#FF4D35]">NutriChef</span> journey
        </p>

        {/* Form */}
        <form className="flex flex-col gap-5" onSubmit={handleSubmit}>
          <motion.input
            whileFocus={{ scale: 1.02 }}
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            aria-label="Email address" placeholder="Email"
            required
            className="w-full rounded-xl border border-[#0A0A0A] px-4 py-3 bg-white/70 shadow-stamp-sm 
              text-[#0A0A0A] placeholder-[#8fa28c] focus:outline-none focus:ring-2 
              focus:ring-[#FF4D35]/50 transition"
          />
          <motion.input
            whileFocus={{ scale: 1.02 }}
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            aria-label="Password" placeholder="Password"
            required
            className="w-full rounded-xl border border-[#0A0A0A] px-4 py-3 bg-white/70 shadow-stamp-sm 
              text-[#0A0A0A] placeholder-[#8fa28c] focus:outline-none focus:ring-2 
              focus:ring-[#FF4D35]/50 transition"
          />
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.97 }}
            type="submit"
            className="w-full bg-[#FF4D35] text-[#0A0A0A] py-3 rounded-xl font-semibold 
              shadow-stamp hover:bg-[#FFD86B] hover:shadow-lg hover:scale-105 transition-all"
          >
            Log In
          </motion.button>
        </form>

        {/* Footer */}
        <p className="text-sm text-[#45453F] text-center mt-6">
          Don’t have an account?{" "}
          <Link
            href="/signup"
            className="text-[#FF4D35] font-semibold hover:underline"
          >
            Sign up
          </Link>
        </p>
      </motion.div>
    </main>
  );
}
