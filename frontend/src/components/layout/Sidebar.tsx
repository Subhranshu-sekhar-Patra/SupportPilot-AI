"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Bot,
  LayoutDashboard,
  Ticket,
  MessageSquare,
  BookOpen,
  Inbox,
  Activity,
  BarChart3,
  Settings,
  User as UserIcon,
  LogOut,
  ChevronRight,
  X,
  Sparkles,
} from "lucide-react";
import { useAuthStore } from "@/store/auth";
import { useUIStore } from "@/store/ui";
import { clsx } from "clsx";

export const NAV_ITEMS = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/tickets", label: "Support Tickets", icon: Ticket, badge: "6" },
  { href: "/chat", label: "AI Live Chat", icon: MessageSquare, badge: "AI" },
  { href: "/inbox", label: "Human Inbox", icon: Inbox, badge: "12" },
  { href: "/knowledge-base", label: "Knowledge Base", icon: BookOpen },
  { href: "/agents", label: "AI Agent Activity", icon: Activity },
  { href: "/analytics", label: "Analytics & Reports", icon: BarChart3 },
  { href: "/settings", label: "Org Settings", icon: Settings },
  { href: "/profile", label: "User Profile", icon: UserIcon },
];

export default function Sidebar() {
  const pathname = usePathname();
  const { user, clearAuth } = useAuthStore();
  const { isMobileSidebarOpen, closeMobileSidebar } = useUIStore();

  const sidebarContent = (
    <div className="flex flex-col h-full bg-white dark:bg-gray-900 border-r border-gray-200 dark:border-gray-800">
      {/* Brand Header */}
      <div className="flex items-center justify-between px-6 py-5 border-b border-gray-100 dark:border-gray-800">
        <Link href="/" className="flex items-center gap-3 group" onClick={closeMobileSidebar}>
          <div className="w-10 h-10 bg-gradient-to-tr from-brand-600 to-blue-500 rounded-xl flex items-center justify-center shadow-md shadow-brand-500/20 group-hover:scale-105 transition-transform">
            <Bot className="w-5 h-5 text-white" />
          </div>
          <div>
            <div className="flex items-center gap-1.5">
              <span className="font-bold text-gray-900 dark:text-white text-base tracking-tight">SupportPilot</span>
              <span className="text-xs font-semibold px-1.5 py-0.5 rounded bg-brand-50 text-brand-600 dark:bg-brand-950 dark:text-brand-400">AI</span>
            </div>
            <p className="text-[11px] text-gray-400 dark:text-gray-500 font-medium truncate max-w-[140px]">
              {user?.organization?.name ?? "Enterprise SaaS"}
            </p>
          </div>
        </Link>
        {/* Mobile close button */}
        <button
          onClick={closeMobileSidebar}
          className="lg:hidden p-1.5 rounded-lg text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* Main Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        <div className="px-3 pb-2 text-[10px] font-bold uppercase tracking-wider text-gray-400 dark:text-gray-500">
          Core Platform
        </div>
        {NAV_ITEMS.map(({ href, label, icon: Icon, badge }) => {
          const isActive = pathname === href || (href !== "/" && pathname.startsWith(href));
          return (
            <Link
              key={href}
              href={href}
              onClick={closeMobileSidebar}
              className={clsx(
                "flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-sm font-medium transition-all group relative",
                isActive
                  ? "bg-brand-50 dark:bg-brand-950/60 text-brand-700 dark:text-brand-300 font-semibold shadow-xs"
                  : "text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800/60 hover:text-gray-900 dark:hover:text-white"
              )}
            >
              <Icon
                className={clsx(
                  "w-4 h-4 flex-shrink-0 transition-colors",
                  isActive ? "text-brand-600 dark:text-brand-400" : "text-gray-400 group-hover:text-gray-600 dark:group-hover:text-gray-300"
                )}
              />
              <span className="flex-1 truncate">{label}</span>
              {badge && (
                <span
                  className={clsx(
                    "text-[10px] font-semibold px-2 py-0.5 rounded-full flex-shrink-0",
                    badge === "AI"
                      ? "bg-gradient-to-r from-blue-500/20 to-purple-500/20 text-purple-600 dark:text-purple-400 border border-purple-500/30 flex items-center gap-0.5"
                      : isActive
                      ? "bg-brand-200/60 text-brand-800 dark:bg-brand-900/60 dark:text-brand-200"
                      : "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400"
                  )}
                >
                  {badge === "AI" && <Sparkles className="w-2.5 h-2.5" />}
                  {badge}
                </span>
              )}
              {isActive && (
                <span className="absolute left-0 top-2 bottom-2 w-1 bg-brand-600 rounded-r-full" />
              )}
            </Link>
          );
        })}
      </nav>

      {/* User Footer Profile & Sign out */}
      <div className="p-3 border-t border-gray-100 dark:border-gray-800 bg-gray-50/50 dark:bg-gray-900/50">
        <div className="flex items-center gap-3 px-2 py-2 rounded-xl hover:bg-white dark:hover:bg-gray-800 transition shadow-2xs">
          <Link href="/profile" onClick={closeMobileSidebar} className="flex items-center gap-2.5 flex-1 min-w-0">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-brand-600 to-indigo-600 text-white flex items-center justify-center font-bold text-xs flex-shrink-0 shadow-sm">
              {user?.full_name?.charAt(0) ?? "A"}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-xs font-semibold text-gray-900 dark:text-white truncate">
                {user?.full_name ?? "Alex Turner"}
              </p>
              <p className="text-[10px] text-gray-400 dark:text-gray-500 truncate capitalize">
                {user?.role ?? "Admin"} · Online
              </p>
            </div>
          </Link>
          <button
            onClick={clearAuth}
            title="Sign out"
            className="p-1.5 rounded-lg text-gray-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-950/30 transition flex-shrink-0"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );

  return (
    <>
      {/* Desktop fixed sidebar */}
      <aside className="hidden lg:block w-64 flex-shrink-0 h-screen sticky top-0 z-30">
        {sidebarContent}
      </aside>

      {/* Mobile drawer with backdrop */}
      {isMobileSidebarOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <div
            className="fixed inset-0 bg-black/60 backdrop-blur-xs transition-opacity"
            onClick={closeMobileSidebar}
          />
          <div className="fixed inset-y-0 left-0 w-72 max-w-[85vw] shadow-2xl z-50 animate-slide-in">
            {sidebarContent}
          </div>
        </div>
      )}
    </>
  );
}
