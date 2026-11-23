"use client";

import { usePathname } from "next/navigation";
import { useTheme } from "next-themes";
import { useState, useEffect } from "react";
import Link from "next/link";
import {
  Menu,
  Sun,
  Moon,
  Bell,
  Search,
  Sparkles,
  ShieldCheck,
  Check,
} from "lucide-react";
import { useAuthStore } from "@/store/auth";
import { useUIStore } from "@/store/ui";
import { NAV_ITEMS } from "./Sidebar";

export default function Topbar() {
  const pathname = usePathname();
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);
  const [showNotifications, setShowNotifications] = useState(false);
  const user = useAuthStore((s) => s.user);
  const toggleMobileSidebar = useUIStore((s) => s.toggleMobileSidebar);

  useEffect(() => {
    setMounted(true);
  }, []);

  const activeNavItem = NAV_ITEMS.find(
    (item) => item.href === pathname || (item.href !== "/" && pathname.startsWith(item.href))
  );

  return (
    <header className="h-16 flex-shrink-0 bg-white/80 dark:bg-gray-900/80 backdrop-blur-md border-b border-gray-200/80 dark:border-gray-800 sticky top-0 z-20 flex items-center px-4 sm:px-6 gap-3">
      {/* Mobile hamburger button */}
      <button
        onClick={toggleMobileSidebar}
        className="lg:hidden p-2 rounded-xl text-gray-500 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800 transition"
        aria-label="Toggle navigation menu"
      >
        <Menu className="w-5 h-5" />
      </button>

      {/* Page Title & Breadcrumb */}
      <div className="flex items-center gap-2 flex-1 min-w-0">
        <h1 className="text-base sm:text-lg font-bold text-gray-900 dark:text-white truncate">
          {activeNavItem?.label ?? "SupportPilot"}
        </h1>
        <span className="hidden sm:inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-50 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800/40">
          <ShieldCheck className="w-3 h-3" /> System Operational
        </span>
      </div>

      {/* Search Bar */}
      <div className="hidden md:flex items-center gap-2 bg-gray-100/80 dark:bg-gray-800/80 rounded-xl px-3 py-1.5 w-60 lg:w-72 border border-transparent focus-within:border-brand-500/50 transition">
        <Search className="w-4 h-4 text-gray-400 flex-shrink-0" />
        <input
          type="text"
          placeholder="Search tickets, docs, agents..."
          className="bg-transparent text-xs text-gray-800 dark:text-gray-200 placeholder-gray-400 focus:outline-none w-full"
        />
        <kbd className="hidden lg:inline-block text-[10px] text-gray-400 bg-white dark:bg-gray-700 px-1.5 py-0.5 rounded shadow-2xs">
          ⌘K
        </kbd>
      </div>

      {/* Right Action Icons */}
      <div className="flex items-center gap-1.5 sm:gap-2">
        {/* Dark / Light Mode Toggle */}
        {mounted && (
          <button
            onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
            className="p-2 rounded-xl text-gray-500 hover:text-gray-900 dark:text-gray-400 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-800 transition"
            title={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
          >
            {theme === "dark" ? <Sun className="w-4 h-4 text-amber-400" /> : <Moon className="w-4 h-4 text-gray-600" />}
          </button>
        )}

        {/* Notifications Popover Toggle */}
        <div className="relative">
          <button
            onClick={() => setShowNotifications(!showNotifications)}
            className="relative p-2 rounded-xl text-gray-500 hover:text-gray-900 dark:text-gray-400 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-800 transition"
            title="Notifications"
          >
            <Bell className="w-4 h-4" />
            <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-brand-600 rounded-full ring-2 ring-white dark:ring-gray-900" />
          </button>

          {showNotifications && (
            <div className="absolute right-0 mt-2 w-80 bg-white dark:bg-gray-800 rounded-2xl shadow-xl border border-gray-200 dark:border-gray-700 p-4 z-50 animate-fade-in">
              <div className="flex items-center justify-between pb-3 border-b border-gray-100 dark:border-gray-750">
                <span className="text-xs font-bold text-gray-900 dark:text-white">Recent System Events</span>
                <span className="text-[10px] text-brand-600 dark:text-brand-400 font-semibold cursor-pointer">Mark all read</span>
              </div>
              <div className="space-y-3 pt-3 text-xs">
                <div className="flex gap-2.5">
                  <div className="w-6 h-6 rounded-full bg-red-100 dark:bg-red-900/40 text-red-600 flex items-center justify-center flex-shrink-0">
                    !
                  </div>
                  <div>
                    <p className="font-semibold text-gray-800 dark:text-gray-200">Ticket SP-4892 Escalated</p>
                    <p className="text-gray-400 text-[11px]">Stripe webhook signature mismatch requires attention.</p>
                    <span className="text-[10px] text-gray-400">4 mins ago</span>
                  </div>
                </div>
                <div className="flex gap-2.5">
                  <div className="w-6 h-6 rounded-full bg-emerald-100 dark:bg-emerald-900/40 text-emerald-600 flex items-center justify-center flex-shrink-0">
                    <Check className="w-3.5 h-3.5" />
                  </div>
                  <div>
                    <p className="font-semibold text-gray-800 dark:text-gray-200">Knowledge Ingestion Succeeded</p>
                    <p className="text-gray-400 text-[11px]">'API Authentication & Token Lifecycle' indexed in ChromaDB.</p>
                    <span className="text-[10px] text-gray-400">18 mins ago</span>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Profile Link */}
        <Link
          href="/profile"
          className="flex items-center gap-2 p-1.5 pl-2 pr-3 rounded-xl border border-gray-200 dark:border-gray-750 hover:bg-gray-50 dark:hover:bg-gray-800 transition"
        >
          <div className="w-6 h-6 rounded-lg bg-brand-600 text-white font-bold text-xs flex items-center justify-center">
            {user?.full_name?.charAt(0) ?? "A"}
          </div>
          <span className="text-xs font-semibold text-gray-800 dark:text-gray-200 hidden sm:inline">
            {user?.full_name?.split(" ")[0] ?? "Alex"}
          </span>
        </Link>
      </div>
    </header>
  );
}
