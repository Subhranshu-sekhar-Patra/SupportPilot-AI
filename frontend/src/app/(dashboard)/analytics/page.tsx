"use client";

import { useState } from "react";
import {
  Clock,
  ThumbsUp,
  Bot,
  TrendingDown,
  TrendingUp,
  Download,
  Calendar,
  Filter,
  CheckCircle2,
  DollarSign,
  AlertCircle,
  HelpCircle,
} from "lucide-react";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import { MOCK_DASHBOARD_STATS, MOCK_TEAM_MEMBERS } from "@/lib/mock-data";

const RESOLUTION_TIME_BUCKETS = [
  { range: "< 15 min", count: 540, aiPct: 82 },
  { range: "15m - 1h", count: 320, aiPct: 65 },
  { range: "1h - 4h", count: 210, aiPct: 35 },
  { range: "4h - 12h", count: 140, aiPct: 15 },
  { range: "> 12h", count: 74, aiPct: 5 },
];

const AGENT_LEADERBOARD = [
  {
    name: "SupportPilot AI (Autopilot)",
    type: "AI Agent",
    avatar: "🤖",
    ticketsHandled: 952,
    avgFRT: "12 sec",
    avgResolution: "3.5 min",
    csat: 4.89,
    deflectionRate: "74.2%",
  },
  {
    name: "Marcus Vance",
    type: "Human (Senior Escalations)",
    avatar: "MV",
    ticketsHandled: 142,
    avgFRT: "4.8 min",
    avgResolution: "1.4 hrs",
    csat: 4.92,
    deflectionRate: "N/A",
  },
  {
    name: "Elena Rostova",
    type: "Human (Technical Support)",
    avatar: "ER",
    ticketsHandled: 118,
    avgFRT: "6.2 min",
    avgResolution: "1.9 hrs",
    csat: 4.81,
    deflectionRate: "N/A",
  },
  {
    name: "Hannah Abbott",
    type: "Human (Customer Success)",
    avatar: "HA",
    ticketsHandled: 72,
    avgFRT: "5.5 min",
    avgResolution: "1.2 hrs",
    csat: 4.85,
    deflectionRate: "N/A",
  },
];

export default function AnalyticsPage() {
  const [timeRange, setTimeRange] = useState<"7d" | "30d" | "90d">("7d");
  const [exportSuccess, setExportSuccess] = useState(false);

  const handleExport = (format: "CSV" | "PDF") => {
    setExportSuccess(true);
    setTimeout(() => setExportSuccess(false), 3000);
  };

  return (
    <div className="space-y-6 animate-fade-in pb-12">
      {/* Top Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white tracking-tight">
            Analytics & Performance Reports
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Real-time telemetry, deflection efficiency, SLA metrics, and agent resolution throughput.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          {/* Time range selector */}
          <div className="flex items-center bg-gray-100 dark:bg-gray-800 p-1 rounded-xl border border-gray-200 dark:border-gray-700 text-xs font-medium">
            <button
              onClick={() => setTimeRange("7d")}
              className={`px-3 py-1.5 rounded-lg transition-colors ${
                timeRange === "7d"
                  ? "bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-xs font-semibold"
                  : "text-gray-500 hover:text-gray-900 dark:hover:text-white"
              }`}
            >
              Last 7 Days
            </button>
            <button
              onClick={() => setTimeRange("30d")}
              className={`px-3 py-1.5 rounded-lg transition-colors ${
                timeRange === "30d"
                  ? "bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-xs font-semibold"
                  : "text-gray-500 hover:text-gray-900 dark:hover:text-white"
              }`}
            >
              Last 30 Days
            </button>
            <button
              onClick={() => setTimeRange("90d")}
              className={`px-3 py-1.5 rounded-lg transition-colors ${
                timeRange === "90d"
                  ? "bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-xs font-semibold"
                  : "text-gray-500 hover:text-gray-900 dark:hover:text-white"
              }`}
            >
              Quarter
            </button>
          </div>

          <div className="relative">
            <Button
              variant="outline"
              size="sm"
              onClick={() => handleExport("CSV")}
            >
              <Download className="w-4 h-4 mr-1.5" />
              Export Report
            </Button>
            {exportSuccess && (
              <div className="absolute right-0 top-12 z-20 bg-emerald-600 text-white text-xs px-3 py-2 rounded-lg shadow-lg flex items-center gap-2 whitespace-nowrap animate-fade-in">
                <CheckCircle2 className="w-4 h-4" />
                Report exported successfully!
              </div>
            )}
          </div>
        </div>
      </div>

      {/* KPI Stats Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* FRT */}
        <Card className="p-5 relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
              Avg First Response
            </span>
            <div className="w-8 h-8 rounded-lg bg-blue-50 dark:bg-blue-950/60 flex items-center justify-center text-blue-600 dark:text-blue-400">
              <Clock className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-gray-900 dark:text-white">4.2 min</span>
            <span className="inline-flex items-center text-xs font-semibold text-emerald-600 dark:text-emerald-400">
              <TrendingDown className="w-3.5 h-3.5 mr-0.5" />
              -34.8%
            </span>
          </div>
          <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">vs 6.5 min prior period</p>
        </Card>

        {/* MTTR */}
        <Card className="p-5 relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
              Avg Resolution (MTTR)
            </span>
            <div className="w-8 h-8 rounded-lg bg-indigo-50 dark:bg-indigo-950/60 flex items-center justify-center text-indigo-600 dark:text-indigo-400">
              <Clock className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-gray-900 dark:text-white">1.8 hrs</span>
            <span className="inline-flex items-center text-xs font-semibold text-emerald-600 dark:text-emerald-400">
              <TrendingDown className="w-3.5 h-3.5 mr-0.5" />
              -22.1%
            </span>
          </div>
          <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">vs 2.3 hrs prior period</p>
        </Card>

        {/* AI Deflection Rate */}
        <Card className="p-5 relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
              AI Deflection Rate
            </span>
            <div className="w-8 h-8 rounded-lg bg-purple-50 dark:bg-purple-950/60 flex items-center justify-center text-purple-600 dark:text-purple-400">
              <Bot className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-gray-900 dark:text-white">74.2%</span>
            <span className="inline-flex items-center text-xs font-semibold text-emerald-600 dark:text-emerald-400">
              <TrendingUp className="w-3.5 h-3.5 mr-0.5" />
              +5.4%
            </span>
          </div>
          <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">952 tickets resolved autonomously</p>
        </Card>

        {/* CSAT Score */}
        <Card className="p-5 relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
              CSAT Score
            </span>
            <div className="w-8 h-8 rounded-lg bg-emerald-50 dark:bg-emerald-950/60 flex items-center justify-center text-emerald-600 dark:text-emerald-400">
              <ThumbsUp className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-gray-900 dark:text-white">4.86 / 5</span>
            <span className="inline-flex items-center text-xs font-semibold text-emerald-600 dark:text-emerald-400">
              <TrendingUp className="w-3.5 h-3.5 mr-0.5" />
              +0.14
            </span>
          </div>
          <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">Based on 612 verified customer ratings</p>
        </Card>
      </div>

      {/* Value Summary Banner */}
      <div className="p-4 rounded-xl bg-gradient-to-r from-brand-600/10 via-purple-600/10 to-blue-600/10 border border-brand-200/50 dark:border-brand-800/40 flex flex-col md:flex-row items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-brand-600 text-white flex items-center justify-center flex-shrink-0">
            <DollarSign className="w-5 h-5" />
          </div>
          <div>
            <h4 className="text-sm font-semibold text-gray-900 dark:text-white">
              Estimated Support Cost Savings: $14,280 this month
            </h4>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              Calculated at an industry average of $15.00 per human-handled tier-1 escalation vs $0.08 per AI resolution.
            </p>
          </div>
        </div>
        <Badge variant="success" size="md">
          98.2% Positive Feedback Rate
        </Badge>
      </div>

      {/* Main Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Ticket Volume & AI Resolution Breakdown */}
        <Card className="p-5 lg:col-span-2">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="font-semibold text-gray-900 dark:text-white">Ticket Volume & Deflection Trend</h3>
              <p className="text-xs text-gray-500 dark:text-gray-400">Daily incoming volume compared to autonomous AI resolution</p>
            </div>
            <span className="text-xs font-medium text-brand-600 dark:text-brand-400 bg-brand-50 dark:bg-brand-950 px-2.5 py-1 rounded-md">
              74.2% AI Share
            </span>
          </div>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={MOCK_DASHBOARD_STATS.weeklyTicketTrends}>
                <defs>
                  <linearGradient id="colorReceived" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="colorDeflected" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#374151" opacity={0.15} />
                <XAxis dataKey="day" stroke="#9ca3af" fontSize={12} tickLine={false} />
                <YAxis stroke="#9ca3af" fontSize={12} tickLine={false} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#1f2937",
                    borderColor: "#374151",
                    color: "#f3f4f6",
                    borderRadius: "0.5rem",
                  }}
                />
                <Legend />
                <Area
                  type="monotone"
                  dataKey="received"
                  name="Total Influx"
                  stroke="#6366f1"
                  strokeWidth={2}
                  fillOpacity={1}
                  fill="url(#colorReceived)"
                />
                <Area
                  type="monotone"
                  dataKey="aiDeflected"
                  name="AI Deflected"
                  stroke="#10b981"
                  strokeWidth={2}
                  fillOpacity={1}
                  fill="url(#colorDeflected)"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </Card>

        {/* Resolution Time Distribution */}
        <Card className="p-5">
          <div className="mb-4">
            <h3 className="font-semibold text-gray-900 dark:text-white">Resolution Time Distribution</h3>
            <p className="text-xs text-gray-500 dark:text-gray-400">Tickets bucketed by completion duration</p>
          </div>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={RESOLUTION_TIME_BUCKETS} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#374151" opacity={0.15} />
                <XAxis type="number" stroke="#9ca3af" fontSize={11} tickLine={false} />
                <YAxis type="category" dataKey="range" stroke="#9ca3af" fontSize={11} tickLine={false} width={65} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#1f2937",
                    borderColor: "#374151",
                    color: "#f3f4f6",
                    borderRadius: "0.5rem",
                  }}
                />
                <Bar dataKey="count" name="Tickets" fill="#3b82f6" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>

      {/* Category Breakdown & Channel Distribution */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Ticket Categories */}
        <Card className="p-5">
          <div className="mb-4">
            <h3 className="font-semibold text-gray-900 dark:text-white">Issue Category Breakdown</h3>
            <p className="text-xs text-gray-500 dark:text-gray-400">Distribution across incoming request domains</p>
          </div>
          <div className="space-y-4">
            {MOCK_DASHBOARD_STATS.categoryBreakdown.map((cat) => (
              <div key={cat.name} className="space-y-1">
                <div className="flex justify-between text-xs font-medium">
                  <span className="text-gray-700 dark:text-gray-300">{cat.name}</span>
                  <span className="text-gray-500 dark:text-gray-400">
                    {cat.value} tickets ({cat.percentage}%)
                  </span>
                </div>
                <div className="h-2 w-full bg-gray-100 dark:bg-gray-800 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-brand-500 to-indigo-600 rounded-full"
                    style={{ width: `${cat.percentage}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </Card>

        {/* Channel Influx */}
        <Card className="p-5">
          <div className="mb-4">
            <h3 className="font-semibold text-gray-900 dark:text-white">Channel Distribution</h3>
            <p className="text-xs text-gray-500 dark:text-gray-400">Where customers submit their inquiries</p>
          </div>
          <div className="grid grid-cols-2 gap-3">
            {MOCK_DASHBOARD_STATS.channelDistribution.map((ch) => (
              <div
                key={ch.channel}
                className="p-4 rounded-xl border border-gray-100 dark:border-gray-800 bg-gray-50/50 dark:bg-gray-800/40"
              >
                <div className="text-xs text-gray-500 dark:text-gray-400">{ch.channel}</div>
                <div className="text-xl font-bold text-gray-900 dark:text-white mt-1">{ch.count}</div>
                <div className="text-xs text-brand-600 dark:text-brand-400 font-medium mt-0.5">{ch.share} volume</div>
              </div>
            ))}
          </div>
        </Card>
      </div>

      {/* Agent Performance Leaderboard */}
      <Card className="overflow-hidden">
        <div className="p-5 border-b border-gray-100 dark:border-gray-800 flex items-center justify-between">
          <div>
            <h3 className="font-semibold text-gray-900 dark:text-white">Agent Performance & Triage Leaderboard</h3>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
              Comparative efficiency benchmarks across AI autopilot and human support engineers
            </p>
          </div>
          <Badge variant="info" size="sm">
            Live Metrics
          </Badge>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-gray-50/80 dark:bg-gray-800/50 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
              <tr>
                <th className="px-5 py-3">Agent / Assignee</th>
                <th className="px-5 py-3">Type</th>
                <th className="px-5 py-3 text-right">Tickets Handled</th>
                <th className="px-5 py-3 text-right">Avg Response</th>
                <th className="px-5 py-3 text-right">Avg Resolution</th>
                <th className="px-5 py-3 text-right">CSAT Rating</th>
                <th className="px-5 py-3 text-right">Deflection %</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
              {AGENT_LEADERBOARD.map((agent, i) => (
                <tr key={i} className="hover:bg-gray-50/50 dark:hover:bg-gray-800/30 transition-colors">
                  <td className="px-5 py-4">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-lg bg-gray-100 dark:bg-gray-800 flex items-center justify-center font-bold text-xs text-brand-600 dark:text-brand-400">
                        {agent.avatar}
                      </div>
                      <span className="font-medium text-gray-900 dark:text-white">{agent.name}</span>
                    </div>
                  </td>
                  <td className="px-5 py-4">
                    <Badge variant={agent.type.includes("AI") ? "purple" : "neutral"} size="sm">
                      {agent.type}
                    </Badge>
                  </td>
                  <td className="px-5 py-4 text-right font-medium text-gray-900 dark:text-white">
                    {agent.ticketsHandled}
                  </td>
                  <td className="px-5 py-4 text-right text-gray-600 dark:text-gray-300">{agent.avgFRT}</td>
                  <td className="px-5 py-4 text-right text-gray-600 dark:text-gray-300">{agent.avgResolution}</td>
                  <td className="px-5 py-4 text-right">
                    <span className="inline-flex items-center gap-1 font-semibold text-emerald-600 dark:text-emerald-400">
                      ★ {agent.csat}
                    </span>
                  </td>
                  <td className="px-5 py-4 text-right font-semibold text-brand-600 dark:text-brand-400">
                    {agent.deflectionRate}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
