"use client";

import Link from "next/link";
import { useState, useEffect, useRef } from "react";
import { Menu, X } from "lucide-react";
import { useRouter } from "next/navigation";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [user, setUser] = useState<{ name: string } | null>(null);
  const [showMenu, setShowMenu] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const router = useRouter();

  // Fetch logged-in user info
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

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setShowMenu(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleLogout = async () => {
    await fetch("/api/logout");
    setUser(null);
    router.push("/login");
  };

  const handleProfileClick = () => setShowMenu(prev => !prev);

  const getInitial = (user: { name?: string; full_name?: string; email?: string } | null) => {
    if (user?.name) return user.name.charAt(0).toUpperCase();
    if (user?.full_name) return user.full_name.charAt(0).toUpperCase();
    if (user?.email) return user.email.charAt(0).toUpperCase();
    return "?";
  };

  return (
    <main className="flex min-h-screen bg-gradient-to-br from-green-50 via-white to-emerald-100">
      {/* Sidebar */}
      <aside
        className={`fixed top-0 left-0 h-screen w-64 bg-white/70 backdrop-blur-lg border-r border-emerald-100 shadow-md p-6 flex flex-col justify-between
          transform transition-transform duration-300 z-50
          ${sidebarOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0"}`}
      >
        <div>
          <h2 className="text-2xl font-extrabold text-emerald-700 mb-8 tracking-tight">
            🥗 NutriChef
          </h2>
          <nav className="flex flex-col gap-5 text-slate-700 font-medium">
            {[
              ["📊 Dashboard", "/dashboard"],
              ["🥦 Ingredients", "/ingredients"],
              ["🍲 Recipes", "/recipes"],
              ["🗄️ Pantry", "/pantry"],
              ["⭐ Favorites", "/favorites"],
              ["📈 Track", "/track"],
              ["⚙️ Settings", "/settings"],
            ].map(([label, href]) => (
              <Link
                key={href}
                href={href}
                className="transition hover:text-emerald-600 hover:translate-x-1"
              >
                {label}
              </Link>
            ))}
          </nav>
        </div>
        <div className="text-xs text-slate-500 mt-6">© 2025 NutriChef</div>
      </aside>

      {/* Overlay for mobile */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/30 backdrop-blur-[2px] md:hidden z-40"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Main Section */}
      <section className="flex-1 flex flex-col">
        {/* Top Bar */}
        <header className="flex justify-between items-center px-6 py-4 border-b border-emerald-100 bg-white/70 backdrop-blur-md shadow-sm sticky top-0 z-40">
          {/* Menu button + logo */}
          <div className="flex items-center gap-3">
            <button
              className="p-2 rounded-lg hover:bg-emerald-100 text-emerald-700 transition"
              onClick={() => setSidebarOpen(!sidebarOpen)}
            >
              {sidebarOpen ? <X size={24} /> : <Menu size={24} />}
            </button>
            <h1 className="text-2xl font-extrabold text-emerald-700 drop-shadow-sm">
              NutriChef
            </h1>
          </div>

          {/* Profile Avatar */}
          <div className="relative" ref={menuRef}>
            <button
              onClick={handleProfileClick}
              className="w-10 h-10 flex items-center justify-center rounded-full bg-emerald-500 text-white font-bold hover:bg-emerald-600 shadow-md transition"
              title="Profile"
            >
              {getInitial(user)}
            </button>

            {showMenu && (
              <div className="absolute right-0 mt-2 w-48 bg-white/90 backdrop-blur-md shadow-xl rounded-xl border border-emerald-100 py-3 z-50">
                <div className="text-center">
                  <p className="text-slate-700 font-semibold">{user?.name}</p>
                </div>
                <hr className="my-2 border-slate-200" />
                <button
                  onClick={() => router.push("/profile")}
                  className="block w-full text-left px-4 py-2 text-sm text-slate-600 hover:bg-emerald-50 transition"
                >
                  Edit Profile
                </button>
                <button
                  onClick={handleLogout}
                  className="block w-full text-left px-4 py-2 text-sm text-red-600 hover:bg-red-50 transition"
                >
                  Logout
                </button>
              </div>
            )}
          </div>
        </header>

        {/* Page content */}
        <div className="flex-1 p-8">{children}</div>
      </section>
    </main>
  );
}
