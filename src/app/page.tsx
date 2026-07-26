"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { Poppins } from "next/font/google";

// ✅ Load Poppins font from Google
const poppins = Poppins({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700", "800"],
});

export default function LandingPage() {
  return (
    <main
      className={`${poppins.className} min-h-screen bg-gradient-to-b from-[#f8fbf7] via-white to-[#eef6eb] text-[#1E1E1E] selection:bg-[#6AB04A]/20 selection:text-[#1E1E1E]`}
    >
      {/* Navbar */}
      <nav className="flex justify-between items-center px-10 py-6 sticky top-0 z-50 bg-white/70 backdrop-blur-lg shadow-sm">
        <motion.h1
          initial={{ x: -40, opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          transition={{ duration: 0.6 }}
          className="text-3xl font-extrabold tracking-wide text-[#6AB04A]"
        >
          Nutri<span className="text-[#2F2F2F]">Chef</span>
        </motion.h1>

        <motion.div
          initial={{ x: 40, opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          transition={{ duration: 0.6 }}
          className="flex gap-4"
        >
          <Link
            href="/login"
            className="px-5 py-2.5 rounded-xl bg-[#6AB04A] text-white font-semibold shadow-md hover:shadow-lg hover:scale-105 hover:bg-[#5a9b3d] transition-all"
          >
            Log In
          </Link>
          <Link
            href="/signup"
            className="px-5 py-2.5 rounded-xl border-2 border-[#6AB04A] text-[#6AB04A] font-semibold hover:bg-[#f2f9f0] hover:scale-105 shadow-sm transition-all"
          >
            Sign Up
          </Link>
        </motion.div>
      </nav>

      {/* Hero Section */}
      <section className="flex flex-col md:flex-row items-center justify-between px-10 md:px-20 py-24 gap-20">
        {/* Left Text */}
        <motion.div
          initial={{ y: 40, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ duration: 0.8 }}
          className="flex-1 text-left"
        >
          <h2 className="text-5xl md:text-6xl font-extrabold text-[#1E1E1E] mb-6 leading-tight">
            Turn Ingredients <br /> into{" "}
            <span className="text-[#6AB04A]">Delicious Recipes</span>
          </h2>
          <p className="text-lg text-[#555] max-w-lg mb-8 leading-relaxed">
            NutriChef suggests meals based on your diet, helps you track
            hydration and wellness, and makes cooking effortless — smart, simple
            and tasty.
          </p>
          <div className="flex gap-4">
            <Link
              href="/signup"
              className="px-6 py-3 rounded-xl bg-[#6AB04A] text-white font-semibold shadow-md hover:bg-[#5a9b3d] hover:shadow-lg hover:scale-105 transition-all"
            >
              Get Started
            </Link>
            <Link
              href="/about"
              className="px-6 py-3 rounded-xl border-2 border-[#6AB04A] text-[#6AB04A] font-semibold hover:bg-[#f2f9f0] hover:scale-105 shadow-sm transition-all"
            >
              Learn More
            </Link>
          </div>
        </motion.div>

        {/* Right Illustration */}
        <motion.div
          initial={{ scale: 0.8, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ duration: 0.9 }}
          className="flex-1 flex items-center justify-center"
        >
          <div className="w-80 h-80 md:w-96 md:h-96 bg-gradient-to-br from-[#eaf7e2] to-[#d8f2d0] rounded-3xl flex items-center justify-center shadow-xl hover:-rotate-2 hover:scale-105 transition-transform">
            <span className="text-7xl">🍲</span>
          </div>
        </motion.div>
      </section>

      {/* About Section */}
      <section className="px-10 md:px-20 py-20 bg-white">
        <motion.h3
          initial={{ y: 30, opacity: 0 }}
          whileInView={{ y: 0, opacity: 1 }}
          transition={{ duration: 0.6 }}
          viewport={{ once: true }}
          className="text-3xl md:text-4xl font-bold text-center mb-8"
        >
          About <span className="text-[#6AB04A]">NutriChef</span>
        </motion.h3>
        <motion.p
          initial={{ y: 20, opacity: 0 }}
          whileInView={{ y: 0, opacity: 1 }}
          transition={{ duration: 0.8 }}
          viewport={{ once: true }}
          className="max-w-3xl mx-auto text-center text-[#555] text-lg leading-relaxed"
        >
          NutriChef is your smart kitchen assistant. It helps you make the most
          of your pantry, discover healthy recipes tailored to your lifestyle,
          and track your wellness journey with ease. Cook smarter, eat better,
          and live healthier — all in one place.
        </motion.p>
      </section>

      {/* Footer */}
      <footer className="py-8 text-center text-sm text-[#777] bg-[#f8fbf7] border-t border-[#e3efe0]">
        NutriChef — Made with ❤️ by Divya.
      </footer>
    </main>
  );
}
