"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Poppins } from "next/font/google";

const poppins = Poppins({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
});

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
      className={`${poppins.className} relative flex min-h-screen items-center justify-center overflow-hidden bg-gradient-to-b from-[#f8fbf7] via-white to-[#eef6eb] px-4`}
    >
      {/* Animated green blobs */}
      <motion.div
        animate={{ x: [0, 40, 0], y: [0, -40, 0] }}
        transition={{ repeat: Infinity, duration: 10 }}
        className="absolute top-20 left-20 w-72 h-72 bg-[#6AB04A]/20 rounded-full blur-3xl"
      />
      <motion.div
        animate={{ x: [0, -60, 0], y: [0, 60, 0] }}
        transition={{ repeat: Infinity, duration: 12 }}
        className="absolute bottom-20 right-20 w-96 h-96 bg-[#6AB04A]/15 rounded-full blur-3xl"
      />

      {/* Login Card */}
      <motion.div
        initial={{ scale: 0.9, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ duration: 0.6 }}
        className="w-full max-w-md relative bg-white/80 backdrop-blur-2xl rounded-3xl shadow-lg p-8 border border-[#eaf3e5]"
      >
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
        <h2 className="text-4xl font-extrabold text-[#1E1E1E] text-center mb-3">
          Welcome Back 👋
        </h2>
        <p className="text-[#555] text-center mb-8">
          Log in to continue your <span className="text-[#6AB04A]">NutriChef</span> journey
        </p>

        {/* Form */}
        <form className="flex flex-col gap-5" onSubmit={handleSubmit}>
          <motion.input
            whileFocus={{ scale: 1.02 }}
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="Email"
            required
            className="w-full rounded-xl border border-[#c8e1bc] px-4 py-3 bg-white/70 shadow-sm 
              text-[#1E1E1E] placeholder-[#8fa28c] focus:outline-none focus:ring-2 
              focus:ring-[#6AB04A]/50 transition"
          />
          <motion.input
            whileFocus={{ scale: 1.02 }}
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Password"
            required
            className="w-full rounded-xl border border-[#c8e1bc] px-4 py-3 bg-white/70 shadow-sm 
              text-[#1E1E1E] placeholder-[#8fa28c] focus:outline-none focus:ring-2 
              focus:ring-[#6AB04A]/50 transition"
          />
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.97 }}
            type="submit"
            className="w-full bg-[#6AB04A] text-white py-3 rounded-xl font-semibold 
              shadow-md hover:bg-[#5a9b3d] hover:shadow-lg hover:scale-105 transition-all"
          >
            Log In
          </motion.button>
        </form>

        {/* Footer */}
        <p className="text-sm text-[#555] text-center mt-6">
          Don’t have an account?{" "}
          <Link
            href="/signup"
            className="text-[#6AB04A] font-semibold hover:underline"
          >
            Sign up
          </Link>
        </p>
      </motion.div>
    </main>
  );
}
