"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

const navItems = [
  { href: "/", label: "Alpha Terminal", icon: "📡" },
  { href: "/chat", label: "Assistant IA", icon: "💬" },
  { href: "/alerts", label: "Alertes", icon: "🚨" },
  { href: "/feed", label: "Flux brut", icon: "📰" },
  { href: "/graph", label: "Analyse Graphe", icon: "🕸️" },
  { href: "/markets", label: "Marchés", icon: "📊" },
  { href: "/settings", label: "Configuration", icon: "⚙️" },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-56 bg-gray-950 border-r border-gray-800 flex flex-col h-screen fixed left-0 top-0">
      {/* Logo */}
      <div className="px-4 py-5 border-b border-gray-800">
        <h1 className="text-lg font-bold text-white">Scanner OSINT</h1>
        <p className="text-xs text-gray-500 mt-0.5">Intelligence Polymarket</p>
      </div>

      {/* Nav */}
      <nav className="flex-1 py-4 px-2 space-y-1">
        {navItems.map((item) => {
          const isActive =
            pathname === item.href ||
            (item.href !== "/" && pathname.startsWith(item.href));
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors",
                isActive
                  ? "bg-indigo-500/10 text-indigo-400 border border-indigo-500/30"
                  : "text-gray-400 hover:text-gray-200 hover:bg-gray-800/50"
              )}
            >
              <span className="text-base">{item.icon}</span>
              <span>{item.label}</span>
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="px-4 py-3 border-t border-gray-800 text-xs text-gray-600">
        v1.0.0 — Basé sur règles
      </div>
    </aside>
  );
}
