"use client";

import Link from "next/link";
import { Logo } from "@/components/bento/Brand";
import KitchenArt from "@/components/KitchenArt";
import { motion } from "framer-motion";
import { useRouter } from "next/navigation";
import { useState } from "react";


export default function SignupPage() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [success, setSuccess] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name || !email || !password) {
      alert("⚠️ Please fill in all fields!");
      return;
    }

    setLoading(true);

    const res = await fetch("/api/signup", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, email, password }),
    });

    if (res.ok) {
      setSuccess(true);
      setTimeout(() => router.push("/login"), 2000);
    } else {
      const data = await res.json();
      alert(`❌ ${data.error || "Signup failed"}`);
    }

    setLoading(false);
  };

  return (
    <main
      className={`auth-page relative flex min-h-screen items-center justify-center overflow-hidden px-4`}
    >
      <Link href="/" className="auth-home text-link">← BACK TO THE KITCHEN</Link>
      <div className="auth-art"><p className="eyebrow">GOOD FOOD STARTS HERE.</p><KitchenArt /><h1>YOUR NEXT<br />GREAT MEAL<br /><span className="highlight-orange">STARTS WITH YOU.</span></h1></div>
      {/* Animated background blobs */}
      <motion.div
        animate={{ x: [0, 40, 0], y: [0, -40, 0] }}
        transition={{ repeat: Infinity, duration: 10 }}
        className="absolute top-24 left-20 w-72 h-72 bg-[#FF4D35]/20 rounded-full blur-3xl"
      />
      <motion.div
        animate={{ x: [0, -60, 0], y: [0, 60, 0] }}
        transition={{ repeat: Infinity, duration: 12 }}
        className="absolute bottom-20 right-24 w-96 h-96 bg-[#FF4D35]/15 rounded-full blur-3xl"
      />

      {/* Signup Card */}
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
          🥦
        </motion.span>
        <motion.span
          animate={{ y: [0, 12, 0] }}
          transition={{ repeat: Infinity, duration: 4 }}
          className="absolute -top-6 right-8 text-2xl"
        >
          🍞
        </motion.span>
        <motion.span
          animate={{ y: [0, -12, 0] }}
          transition={{ repeat: Infinity, duration: 5 }}
          className="absolute bottom-6 right-12 text-2xl"
        >
          🍓
        </motion.span>

        {/* Title */}
        <h2 className="display text-5xl text-center mb-3">
          Create Account 🧑‍🍳
        </h2>
        <p className="text-[#45453F] text-center mb-8">
          Join <span className="text-[#FF4D35] font-semibold">NutriChef</span> and start your healthy journey today
        </p>

        {/* Success Message */}
        {success && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="mb-4 text-center text-[#FF4D35] font-semibold"
          >
            ✅ Account created successfully! Redirecting to login...
          </motion.div>
        )}

        {/* Form */}
        <form className="flex flex-col gap-5" onSubmit={handleSubmit}>
          <motion.input
            whileFocus={{ scale: 1.02 }}
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            aria-label="Full name" placeholder="Full Name"
            required
            className="w-full rounded-xl border border-[#0A0A0A] px-4 py-3 bg-white/70 shadow-stamp-sm text-[#0A0A0A] placeholder-[#8fa28c] focus:outline-none focus:ring-2 focus:ring-[#FF4D35]/50 transition"
            disabled={loading}
          />
          <motion.input
            whileFocus={{ scale: 1.02 }}
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            aria-label="Email address" placeholder="Email"
            required
            className="w-full rounded-xl border border-[#0A0A0A] px-4 py-3 bg-white/70 shadow-stamp-sm text-[#0A0A0A] placeholder-[#8fa28c] focus:outline-none focus:ring-2 focus:ring-[#FF4D35]/50 transition"
            disabled={loading}
          />
          <motion.input
            whileFocus={{ scale: 1.02 }}
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            aria-label="Password" placeholder="Password"
            required
            className="w-full rounded-xl border border-[#0A0A0A] px-4 py-3 bg-white/70 shadow-stamp-sm text-[#0A0A0A] placeholder-[#8fa28c] focus:outline-none focus:ring-2 focus:ring-[#FF4D35]/50 transition"
            disabled={loading}
          />

          <motion.button
            whileHover={{ scale: loading ? 1 : 1.05 }}
            whileTap={{ scale: loading ? 1 : 0.95 }}
            type="submit"
            disabled={loading}
            className={`w-full py-3 rounded-xl font-semibold shadow-stamp transition-all ${
              loading
                ? "bg-[#A5D6A7] text-white cursor-not-allowed"
                : "bg-[#FF4D35] text-[#0A0A0A] hover:bg-[#FFD86B] hover:shadow-lg hover:scale-105"
            }`}
          >
            {loading ? "Creating Account..." : "Sign Up"}
          </motion.button>
        </form>

        {/* Footer */}
        <p className="text-sm text-[#45453F] text-center mt-6">
          Already have an account?{" "}
          <Link href="/login" className="text-[#FF4D35] font-semibold hover:underline">
            Log in
          </Link>
        </p>
      </motion.div>
    </main>
  );
}
