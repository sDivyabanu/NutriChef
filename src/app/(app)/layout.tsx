"use client";

import Link from "next/link";
import { useState, useEffect, useRef } from "react";
import { Menu, X } from "lucide-react";
import { usePathname, useRouter } from "next/navigation";
import FloatingChat from "@/components/chat/FloatingChat";
import { Logo } from "@/components/bento/Brand";

// Assistant lives in the floating chat; Generate stays reachable at /generate but is not linked here.
const NAV: [string, string][] = [
  ["Home", "/dashboard"],
  ["Search", "/search"],
  ["Ingredients", "/ingredients"],
  ["Recipes", "/recipes"],
  ["Meal plan", "/meal-plan"],
  ["Pantry", "/pantry"],
  ["Favourites", "/favorites"],
  ["Preferences", "/preferences"],
  ["Track", "/track"],
];

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const [menuOpen, setMenuOpen] = useState(false);
  const [user, setUser] = useState<{ name?: string; full_name?: string } | null>(null);
  const [showMenu, setShowMenu] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    async function fetchUser() {
      try {
        const res = await fetch("/api/me");
        if (res.ok) {
          const data = await res.json();
          setUser(data.user);
        } else {
          router.push("/login");
        }
      } catch {
        router.push("/login");
      }
    }
    fetchUser();
  }, [router]);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) setShowMenu(false);
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  useEffect(() => setMenuOpen(false), [pathname]);

  const handleLogout = async () => {
    await fetch("/api/logout");
    setUser(null);
    router.push("/login");
  };

  const name = user?.full_name || user?.name || "";
  const initial = name ? name.charAt(0).toUpperCase() : "?";
  const active = (href: string) => pathname === href || pathname?.startsWith(href + "/");

  return (
    <div className="kitchen-shell min-h-screen">
      <a href="#main-content" className="skip-link">Skip to content</a>
      <header className="sticky top-0 z-40 bg-cream/90 backdrop-blur-sm">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 pt-4 pb-3 flex items-stretch gap-3">
          <nav className="kitchen-outline flex-1 min-w-0 flex items-center gap-4 px-4 sm:px-5 py-2.5" aria-label="Main">
            <Logo href="/dashboard" />
            <ul className="hidden xl:flex items-center gap-0.5 min-w-0 ml-auto">
              {NAV.map(([label, href]) => (
                <li key={href}>
                  <Link
                    href={href}
                    aria-current={active(href) ? "page" : undefined}
                    className={`block whitespace-nowrap rounded-full px-3 py-1.5 text-[14px] font-medium transition-colors ${
                      active(href) ? "bg-coral text-ink" : "text-ink/75 hover:bg-blush hover:text-ink"
                    }`}
                  >
                    {label}
                  </Link>
                </li>
              ))}
            </ul>
            <button
              className="xl:hidden ml-auto p-2 rounded-full text-ink hover:bg-blush"
              onClick={() => setMenuOpen((o) => !o)}
              aria-label={menuOpen ? "Close menu" : "Open menu"}
              aria-expanded={menuOpen}
              aria-controls="mobile-nav"
            >
              {menuOpen ? <X size={22} /> : <Menu size={22} />}
            </button>
          </nav>

          <div className="relative" ref={menuRef}>
            <button
              onClick={() => setShowMenu((p) => !p)}
              className="account-button h-full min-h-[52px] rounded-lg bg-coral px-4 sm:px-6 font-bold text-ink hover:bg-salmon transition flex items-center gap-2"
              aria-haspopup="menu"
              aria-expanded={showMenu}
              aria-label="Account menu"
            >
              <span className="h-8 w-8 rounded-full bg-cream/70 flex items-center justify-center text-sm">{initial}</span>
              <span className="hidden sm:inline max-w-[9rem] truncate">{name || "Account"}</span>
            </button>
            {showMenu && (
              <div role="menu" className="absolute right-0 mt-2 w-52 rounded-lg border border-coral/40 bg-cream shadow-xl py-2 z-50 fade-up">
                <button role="menuitem" onClick={() => router.push("/profile")} className="block w-full text-left px-4 py-2 text-sm text-ink hover:bg-blush">
                  Edit profile
                </button>
                <button role="menuitem" onClick={() => router.push("/settings")} className="block w-full text-left px-4 py-2 text-sm text-ink hover:bg-blush">
                  Settings
                </button>
                <button role="menuitem" onClick={handleLogout} className="block w-full text-left px-4 py-2 text-sm text-rose-700 hover:bg-rose-50">
                  Log out
                </button>
              </div>
            )}
          </div>
        </div>

        {menuOpen && (
          <div id="mobile-nav" className="xl:hidden mx-4 sm:mx-6 mb-3 kitchen-outline p-2 fade-up">
            <ul className="grid grid-cols-2 sm:grid-cols-3 gap-1">
              {NAV.map(([label, href]) => (
                <li key={href}>
                  <Link
                    href={href}
                    aria-current={active(href) ? "page" : undefined}
                    className={`block rounded-2xl px-4 py-2.5 text-sm font-medium ${active(href) ? "bg-coral text-ink" : "text-ink hover:bg-blush"}`}
                  >
                    {label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        )}
      </header>

      <main id="main-content" className="mx-auto max-w-7xl px-4 sm:px-6 pb-28 min-w-0">
        <div key={pathname} className="fade-up">
          {children}
        </div>
      </main>

      {/* Floating recipe assistant (single instance; persists across page navigation) */}
      <FloatingChat />
    </div>
  );
}
