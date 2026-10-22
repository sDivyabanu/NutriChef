"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { BookmarkPlus, BookmarkCheck, ChevronsLeft, ChevronsRight, Clock, Gauge, Leaf, Search, Star } from "lucide-react";
import { Logo } from "@/components/bento/Brand";
import KitchenArt from "@/components/KitchenArt";
import FloatingChat from "@/components/chat/FloatingChat";
import FoodArt from "@/components/bento/FoodArt";
import { api, SearchHit, SearchResponse } from "@/lib/nlp";

const FEATURED_QUERY = "comforting vegetarian dinner with vegetables";
const QUICK_QUERY = "quick vegetarian dinner under 30 minutes";
const VEG_QUERY = "fresh vegetarian lunch";

async function fetchHits(query: string, k: number): Promise<SearchHit[]> {
  try {
    const r = await api<SearchResponse>("/nlp/search", { method: "POST", json: { query, k, apply_profile: false } });
    return r.results;
  } catch {
    return [];
  }
}

function hints(h: SearchHit) {
  return [...h.recipe.ingredients_preview, ...(h.recipe.derived.meal_type_guess || [])];
}

export default function LandingPage() {
  const router = useRouter();
  const [loggedIn, setLoggedIn] = useState<boolean | null>(null);
  const [q, setQ] = useState("");
  const [featured, setFeatured] = useState<SearchHit[] | null>(null);
  const [quick, setQuick] = useState<SearchHit | null>(null);
  const [veg, setVeg] = useState<SearchHit | null>(null);
  const [idx, setIdx] = useState(0);
  const [saved, setSaved] = useState<Record<number, boolean>>({});

  useEffect(() => {
    fetch("/api/me").then((r) => setLoggedIn(r.ok)).catch(() => setLoggedIn(false));
    fetchHits(FEATURED_QUERY, 6).then(setFeatured);
    fetchHits(QUICK_QUERY, 1).then((h) => setQuick(h[0] || null));
    fetchHits(VEG_QUERY, 1).then((h) => setVeg(h[0] || null));
  }, []);

  const step = useCallback((d: number) => setIdx((i) => (featured && featured.length ? (i + d + featured.length) % featured.length : 0)), [featured]);

  const search = (text: string) => {
    if (!text.trim()) return;
    router.push(`/search?q=${encodeURIComponent(text.trim())}`);
  };

  const toggleSave = async (h: SearchHit) => {
    if (!loggedIn) return router.push("/login");
    const id = h.recipe.id;
    const next = !saved[id];
    setSaved((s) => ({ ...s, [id]: next }));
    try {
      await api("/interactions", { method: "POST", json: { recipe_id: id, kind: next ? "favorite" : "unfavorite" } });
      if (next)
        await fetch("/api/favorites", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ recipe: { recipe_name: h.recipe.title, recipe_ref: String(id) } }),
        });
    } catch {
      setSaved((s) => ({ ...s, [id]: !next }));
    }
  };

  const cur = featured?.[idx];

  return (
    <div className="landing">
      <header className="landing-nav">
        <Logo />
        <nav aria-label="Main" className="landing-links">
          <Link href="/search">DISCOVER</Link><Link href="/recipes">RECIPES</Link><Link href="/ingredients">MY INGREDIENTS</Link>
        </nav>
        <Link href={loggedIn ? "/dashboard" : "/login"} className="btn-outline">{loggedIn ? "MY KITCHEN ↗" : "LOG IN ↗"}</Link>
      </header>
      <main>
        <section className="hero">
          <div className="hero-copy">
            <p className="eyebrow"><span className="status-dot" /> SMART COOKING / POWERED BY NLP</p>
            <h1><span>NUTRICHEF</span></h1>
            <h2>YOUR INGREDIENTS <span className="hero-times">×</span><br />ENDLESS POSSIBILITIES.</h2>
            <p className="hero-description">Tell us what’s in your kitchen. Discover recipes that understand your ingredients, cravings and preferences.</p>
            <div className="hero-actions"><Link href="#find-recipe" className="btn-coral">FIND MY RECIPE →</Link><Link href="/recipes" className="text-link">EXPLORE RECIPES ↗</Link></div>
            <p className="hero-note">A LITTLE KITCHEN CREATIVITY. A WHOLE LOT OF POSSIBILITY.</p>
          </div>
          <div className="hero-art"><KitchenArt /></div>
        </section>
        <div className="kitchen-ticker" aria-hidden="true"><span>GOOD FOOD. ZERO GUESSWORK.</span><span>✳</span><span>COOK WITH WHAT YOU HAVE.</span><span>✳</span><span>BIG FLAVOUR. YOUR WAY.</span><span>✳</span></div>
        <section id="find-recipe" className="discovery-section">
          <div className="section-intro"><div><p className="eyebrow">01 / FROM PANTRY TO PLATE</p><h2>What are we<br /><span className="highlight-lavender">cooking today?</span></h2></div><p>No perfect pantry required.<br />Just bring your ingredients and an appetite.</p></div>
          <form role="search" onSubmit={(e) => { e.preventDefault(); search(q); }} className="hero-search">
            <Search size={26} aria-hidden /><label htmlFor="hero-q" className="sr-only">Describe what you want to cook</label>
            <input id="hero-q" value={q} onChange={(e) => setQ(e.target.value)} placeholder="I have tomatoes, rice and onions…" maxLength={500} />
            <button type="submit" className="btn-coral" disabled={!q.trim()}>LET’S COOK →</button>
          </form>
          <div className="ingredient-examples"><span className="eyebrow">TRY A LITTLE INSPIRATION</span>{["Spicy vegetarian dinner under 30 minutes", "South Indian without peanuts", "Paneer and capsicum"].map((ex) => <button key={ex} onClick={() => { setQ(ex); search(ex); }} className="pill">{ex} ↗</button>)}</div>
        </section>
        <section className="featured-section">
          <div className="section-intro"><div><p className="eyebrow">02 / FRESH IDEAS, EVERY DAY</p><h2>Your next <span className="highlight-orange">“yum.”</span></h2></div><Link href="/recipes" className="text-link">ALL RECIPES ↗</Link></div>
          <div className="home-recipes">
            <article className="kitchen-card featured-recipe" aria-roledescription="carousel" aria-label="Featured recipes">
              {cur ? <FoodArt key={cur.recipe.id} title={cur.recipe.title} hints={hints(cur)} size="lg" className="h-56" /> : <div className="recipe-placeholder"><KitchenArt /></div>}
              <div className="p-5 space-y-3"><div className="flex justify-between gap-3"><span className="eyebrow">THE DAILY SPECIAL</span><div className="flex gap-2"><button onClick={() => step(-1)} disabled={!featured?.length} aria-label="Previous featured recipe"><ChevronsLeft size={20} /></button><button onClick={() => step(1)} disabled={!featured?.length} aria-label="Next featured recipe"><ChevronsRight size={20} /></button></div></div>
                {cur ? <><div className="flex justify-between gap-3"><h3 className="text-2xl font-extrabold"><Link href={`/recipes/${cur.recipe.id}`}>{cur.recipe.title}</Link></h3><button onClick={() => toggleSave(cur)} aria-pressed={!!saved[cur.recipe.id]} aria-label={saved[cur.recipe.id] ? "Remove from favourites" : "Save to favourites"}>{saved[cur.recipe.id] ? <BookmarkCheck /> : <BookmarkPlus />}</button></div><p className="text-sm">Made with {cur.recipe.ingredients_preview.slice(0, 5).join(", ")}.</p><div className="flex flex-wrap gap-2">{cur.recipe.derived.estimated_time_min != null && <span className="pill"><Clock size={14} />~{cur.recipe.derived.estimated_time_min} min</span>}{cur.recipe.derived.difficulty && <span className="pill"><Gauge size={14} />{cur.recipe.derived.difficulty}</span>}{cur.recipe.derived.diet?.vegetarian && <span className="pill"><Leaf size={14} />Vegetarian</span>}</div><div className="flex gap-2" aria-label={`Featured ${idx + 1} of ${featured?.length}`}>{featured?.map((f, i) => <button key={f.recipe.id} onClick={() => setIdx(i)} aria-label={`Show featured recipe ${i + 1}`} aria-pressed={i === idx} className={`carousel-dot ${i === idx ? "selected" : ""}`} />)}</div></> : <><h3 className="text-2xl font-extrabold">Something delicious awaits.</h3><p className="text-sm">{featured === null ? "Finding inspiration…" : "Explore your recipe collection to find your next favourite."}</p><Link href="/recipes" className="text-link">EXPLORE RECIPES →</Link></>}
              </div>
            </article>
            <SmallCard label="Quick tonight" hit={quick} tall /><SmallCard label="Fresh & vegetarian" hit={veg} tall />
          </div>
        </section>
        <section className="how-section"><p className="eyebrow">A RECIPE FOR LESS OVERTHINKING</p><h2>Open the fridge.<br />We’ll take it from here.</h2><div className="how-grid">{[["01", "Tell us what you have.", "A handful of ingredients, a craving, or a full dinner dilemma."], ["02", "Find your kind of food.", "Explore recipes matched to your taste, time and dietary preferences."], ["03", "Make something great.", "Save your favourites. Plan your meals. Get cooking."]].map(([n,title,desc]) => <div key={n}><span className="step-number">{n}</span><h3>{title}</h3><p>{desc}</p></div>)}</div><Link href="/ingredients" className="btn-coral">RAID MY FRIDGE →</Link></section>
      </main>
      <footer className="landing-footer"><Logo /><p className="eyebrow">MADE FOR REAL KITCHENS & CURIOUS COOKS.</p><Link href="/about" className="text-link">ABOUT NUTRICHEF ↗</Link></footer>
      <FloatingChat />
    </div>
  );
}

function SmallCard({ label, hit, tall }: { label: string; hit: SearchHit | null; tall?: boolean }) {
  return (
    <Link
      href={hit ? `/recipes/${hit.recipe.id}` : "/recipes"}
      className={`group relative block overflow-hidden kitchen-card ${tall ? "min-h-[260px]" : "min-h-[170px]"} focus-visible:ring-4 focus-visible:ring-coral/50 outline-none`}
    >
      {hit ? <FoodArt title={hit.recipe.title} hints={hints(hit)} size={tall ? "lg" : "md"} className="absolute inset-0" /> : <div className="absolute inset-0 recipe-placeholder"><span className="text-6xl" aria-hidden>✳</span></div>}
      <span className="pill absolute left-4 top-4 bg-cream/95 text-ink shadow-stamp-sm">
        <Star size={16} aria-hidden /> {label}
      </span>
      {hit ? (
        <span className="absolute inset-x-4 bottom-4 rounded-2xl bg-cream/90 px-4 py-2 text-sm font-semibold text-ink line-clamp-1 translate-y-1 opacity-90 transition group-hover:translate-y-0 group-hover:opacity-100">
          {hit.recipe.title}
        </span>
      ) : <span className="absolute inset-x-4 bottom-4 kitchen-outline p-4 font-bold">{label === "Quick tonight" ? "Short on time? Big on flavour." : "A little greener. A lot tastier."}<span className="block mt-2 text-sm underline">Explore recipes →</span></span>}
    </Link>
  );
}
