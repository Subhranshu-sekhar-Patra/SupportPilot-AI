"use client";

import { useState } from "react";
import Link from "next/link";
import {
  Ticket,
  Clock,
  CheckCircle2,
  AlertTriangle,
  Zap,
  TrendingUp,
  Bot,
  ArrowUpRight,
  ArrowRight,
  ShieldAlert,
  Sparkles,
  Users,
  Activity,
} from "lucide-react";
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from "recharts";
import {
  MOCK_DASHBOARD_STATS,
  MOCK_TICKETS,
  MOCK_AGENT_ACTIVITIES,
} from "@/lib/mock-data";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";

const PIE_COLORS = ["#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6"];

export default function DashboardPage() {
  const [timeRange, setTimeRange] = useState<"7d" | "30d" | "90d">("7d");

  const escalatedTickets = MOCK_TICKETS.filter((t) => t.status === "escalated" || t.priority === "urgent");
  const recentActivities = MOCK_AGENT_ACTIVITIES.slice(0, 4);

  return (
    <div className="space-y-6 animate-fade-in pb-8">
      {/* Top Banner & Date Range Filter */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-gray-900 dark:text-white tracking-tight">
            Executive Operations Overview
          </h1>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
            Real-time multi-agent customer support telemetry and deflection metrics
          </p>
        </div>

        <div className="flex items-center gap-2">
          <div className="inline-flex rounded-xl bg-gray-100 dark:bg-gray-800 p-1 border border-gray-200 dark:border-gray-700 text-xs">
            {(["7d", "30d", "90d"] as const).map((r) => (
              <button
                key={r}
                onClick={() => setTimeRange(r)}
                className={`px-3 py-1 rounded-lg font-medium transition ${
                  timeRange === r
                    ? "bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-2xs font-semibold"
                    : "text-gray-500 hover:text-gray-900 dark:hover:text-white"
                }`}
              >
                {r === "7d" ? "Last 7 Days" : r === "30d" ? "Last 30 Days" : "Quarterly"}
              </button>
            ))}
          </div>

          <Link href="/tickets">
            <Button variant="primary" size="sm">
              View All Tickets
            </Button>
          </Link>
        </div>
      </div>

      {/* KPI Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Tickets */}
        <div className="p-5 rounded-2xl bg-white dark:bg-gray-800 border border-gray-200/80 dark:border-gray-700/80 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-gray-500 dark:text-gray-400">Total Inbound Tickets</span>
            <div className="w-8 h-8 rounded-xl bg-blue-50 dark:bg-blue-950/60 text-blue-600 flex items-center justify-center">
              <Ticket className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-gray-900 dark:text-white">{MOCK_DASHBOARD_STATS.totalTickets}</span>
            <span className="text-xs font-semibold text-emerald-600 flex items-center gap-0.5">
              <ArrowUpRight className="w-3 h-3" /> +8.4%
            </span>
          </div>
          <p className="text-[11px] text-gray-400 mt-1">vs. previous period</p>
        </div>

        {/* AI Deflection Rate */}
        <div className="p-5 rounded-2xl bg-gradient-to-br from-brand-600 to-indigo-700 text-white shadow-md shadow-brand-500/20">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-blue-100">AI Autonomous Deflection</span>
            <div className="w-8 h-8 rounded-xl bg-white/20 text-white flex items-center justify-center backdrop-blur-xs">
              <Sparkles className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl font-extrabold">{MOCK_DASHBOARD_STATS.aiDeflectionRate}%</span>
            <span className="text-xs font-semibold text-emerald-200 flex items-center gap-0.5">
              <ArrowUpRight className="w-3 h-3" /> +14.2%
            </span>
          </div>
          <p className="text-[11px] text-blue-100/80 mt-1">Resolved without human escalation</p>
        </div>

        {/* First Response Time */}
        <div className="p-5 rounded-2xl bg-white dark:bg-gray-800 border border-gray-200/80 dark:border-gray-700/80 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-gray-500 dark:text-gray-400">Avg First Response Time</span>
            <div className="w-8 h-8 rounded-xl bg-amber-50 dark:bg-amber-950/60 text-amber-600 flex items-center justify-center">
              <Clock className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-gray-900 dark:text-white">
              {MOCK_DASHBOARD_STATS.avgFirstResponseTimeMin} <span className="text-sm font-normal text-gray-400">min</span>
            </span>
            <span className="text-xs font-semibold text-emerald-600 flex items-center gap-0.5">
              ↓ 42% faster
            </span>
          </div>
          <p className="text-[11px] text-gray-400 mt-1">SLA Target: &lt; 15 mins</p>
        </div>

        {/* CSAT Score */}
        <div className="p-5 rounded-2xl bg-white dark:bg-gray-800 border border-gray-200/80 dark:border-gray-700/80 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-gray-500 dark:text-gray-400">Customer Satisfaction (CSAT)</span>
            <div className="w-8 h-8 rounded-xl bg-emerald-50 dark:bg-emerald-950/60 text-emerald-600 flex items-center justify-center">
              <CheckCircle2 className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-gray-900 dark:text-white">
              {MOCK_DASHBOARD_STATS.csatScore} <span className="text-sm font-normal text-gray-400">/ 5.0</span>
            </span>
            <span className="text-xs font-semibold text-emerald-600">97.2% positive</span>
          </div>
          <p className="text-[11px] text-gray-400 mt-1">Based on 642 verified survey ratings</p>
        </div>
      </div>

      {/* Main Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Ticket Volume & AI Deflection Area Chart */}
        <div className="lg:col-span-2 p-6 rounded-2xl bg-white dark:bg-gray-800 border border-gray-200/80 dark:border-gray-700/80 shadow-xs">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-sm font-bold text-gray-900 dark:text-white">Ticket Volume vs. AI Autonomy</h2>
              <p className="text-xs text-gray-400 mt-0.5">Daily received, resolved, and deflected volumes</p>
            </div>
            <div className="flex items-center gap-3 text-xs text-gray-500">
              <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-brand-600" /> Received</span>
              <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-emerald-500" /> Resolved</span>
              <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-purple-500" /> AI Deflected</span>
            </div>
          </div>
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={MOCK_DASHBOARD_STATS.weeklyTicketTrends}>
                <defs>
                  <linearGradient id="colorReceived" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.2} />
                    <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="colorDeflected" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <XAxis dataKey="day" stroke="#9ca3af" fontSize={11} tickLine={false} />
                <YAxis stroke="#9ca3af" fontSize={11} tickLine={false} axisLine={false} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#1f2937",
                    borderColor: "#374151",
                    borderRadius: "0.75rem",
                    color: "#fff",
                    fontSize: "12px",
                  }}
                />
                <Area type="monotone" dataKey="received" stroke="#3b82f6" strokeWidth={2} fillOpacity={1} fill="url(#colorReceived)" />
                <Area type="monotone" dataKey="aiDeflected" stroke="#8b5cf6" strokeWidth={2} fillOpacity={1} fill="url(#colorDeflected)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* AI Agents Live Status Box */}
        <div className="p-6 rounded-2xl bg-white dark:bg-gray-800 border border-gray-200/80 dark:border-gray-700/80 shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-bold text-gray-900 dark:text-white flex items-center gap-2">
                <Bot className="w-4 h-4 text-brand-600" /> Multi-Agent Health
              </h2>
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            </div>

            <div className="space-y-3">
              {[
                { name: "Classifier Agent", desc: "Intent & Priority Triage", latency: "340ms", accuracy: "98.4%", active: true },
                { name: "Retriever Agent", desc: "ChromaDB Semantic RAG", latency: "180ms", accuracy: "96.1%", active: true },
                { name: "Generator Agent", desc: "Contextual Resolution", latency: "820ms", accuracy: "94.8%", active: true },
                { name: "Evaluator Agent", desc: "Quality & Safety Gate", latency: "290ms", accuracy: "99.1%", active: true },
              ].map((agent) => (
                <div key={agent.name} className="p-3 rounded-xl bg-gray-50 dark:bg-gray-750/70 border border-gray-100 dark:border-gray-700 flex items-center justify-between">
                  <div>
                    <p className="text-xs font-bold text-gray-900 dark:text-white">{agent.name}</p>
                    <p className="text-[10px] text-gray-400">{agent.desc}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-xs font-semibold text-emerald-600 dark:text-emerald-400">{agent.accuracy}</p>
                    <p className="text-[10px] text-gray-400">{agent.latency}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <Link href="/agents" className="mt-4">
            <Button variant="outline" size="sm" className="w-full">
              Inspect Agent Logs <ArrowRight className="w-3.5 h-3.5 ml-1" />
            </Button>
          </Link>
        </div>
      </div>

      {/* Lower Row: Escalated Tickets Table & Category Distribution */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Urgent Attention / Escalated Tickets */}
        <div className="lg:col-span-2 p-6 rounded-2xl bg-white dark:bg-gray-800 border border-gray-200/80 dark:border-gray-700/80 shadow-xs">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <ShieldAlert className="w-4 h-4 text-red-500" />
              <h2 className="text-sm font-bold text-gray-900 dark:text-white">Requires Urgent Attention</h2>
            </div>
            <span className="text-xs font-semibold text-red-600 bg-red-50 dark:bg-red-950 px-2 py-0.5 rounded-full">
              {escalatedTickets.length} Critical
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-gray-100 dark:border-gray-700 text-gray-400 uppercase">
                  <th className="py-2.5 px-3">Ticket ID</th>
                  <th className="py-2.5 px-3">Subject</th>
                  <th className="py-2.5 px-3">Assignee</th>
                  <th className="py-2.5 px-3">Priority</th>
                  <th className="py-2.5 px-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 dark:divide-gray-750">
                {escalatedTickets.map((t) => (
                  <tr key={t.id} className="hover:bg-gray-50/60 dark:hover:bg-gray-750/50 transition">
                    <td className="py-3 px-3 font-mono font-bold text-brand-600 dark:text-brand-400">
                      {t.ticketNumber}
                    </td>
                    <td className="py-3 px-3 font-medium text-gray-900 dark:text-white max-w-xs truncate">
                      {t.subject}
                    </td>
                    <td className="py-3 px-3 text-gray-600 dark:text-gray-300">
                      {t.assignedTo?.name ?? "Unassigned"}
                    </td>
                    <td className="py-3 px-3">
                      <Badge variant="danger" size="sm">
                        {t.priority}
                      </Badge>
                    </td>
                    <td className="py-3 px-3 text-right">
                      <Link href="/tickets">
                        <Button variant="outline" size="sm">
                          Review
                        </Button>
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Category Breakdown */}
        <div className="p-6 rounded-2xl bg-white dark:bg-gray-800 border border-gray-200/80 dark:border-gray-700/80 shadow-xs">
          <h2 className="text-sm font-bold text-gray-900 dark:text-white mb-1">Inbound by Category</h2>
          <p className="text-xs text-gray-400 mb-4">Breakdown across customer segments</p>

          <div className="space-y-3">
            {MOCK_DASHBOARD_STATS.categoryBreakdown.map((item, idx) => (
              <div key={item.name}>
                <div className="flex justify-between text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                  <span>{item.name}</span>
                  <span>{item.value} ({item.percentage}%)</span>
                </div>
                <div className="w-full bg-gray-100 dark:bg-gray-700 h-2 rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all duration-500"
                    style={{
                      width: `${item.percentage}%`,
                      backgroundColor: PIE_COLORS[idx % PIE_COLORS.length],
                    }}
                  />
                </div>
              </div>
            ))}
          </div>

          <div className="mt-6 pt-4 border-t border-gray-100 dark:border-gray-700 flex justify-between items-center text-xs text-gray-400">
            <span>Primary Inbound: Web Portal (45%)</span>
            <Link href="/analytics" className="text-brand-600 dark:text-brand-400 font-semibold hover:underline">
              Full Report
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
