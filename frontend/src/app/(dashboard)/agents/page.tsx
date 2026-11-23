"use client";

import { useState } from "react";
import {
  Activity,
  Bot,
  Zap,
  CheckCircle,
  AlertTriangle,
  Clock,
  Sparkles,
  Search,
  Filter,
  Pause,
  Play,
  RotateCcw,
  Sliders,
  Database,
  ShieldCheck,
  Cpu,
} from "lucide-react";
import { toast } from "sonner";
import { MOCK_AGENT_ACTIVITIES, AgentActivity } from "@/lib/mock-data";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";

export default function AIAgentActivityPage() {
  const [activities, setActivities] = useState<AgentActivity[]>(MOCK_AGENT_ACTIVITIES);
  const [selectedAgentFilter, setSelectedAgentFilter] = useState<string>("all");
  const [agentStatuses, setAgentStatuses] = useState({
    classifier: true,
    retriever: true,
    generator: true,
    evaluator: true,
  });

  const toggleAgent = (key: keyof typeof agentStatuses, name: string) => {
    const next = !agentStatuses[key];
    setAgentStatuses((prev) => ({ ...prev, [key]: next }));
    toast.info(`${name} is now ${next ? "ACTIVE" : "PAUSED"}`);
  };

  const filteredActivities = activities.filter((act) => {
    if (selectedAgentFilter === "all") return true;
    return act.agentName.toLowerCase().includes(selectedAgentFilter.toLowerCase());
  });

  return (
    <div className="space-y-6 animate-fade-in pb-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-gray-900 dark:text-white tracking-tight flex items-center gap-2">
            <Cpu className="w-6 h-6 text-brand-600" /> Multi-Agent Orchestration & Telemetry
          </h1>
          <p className="text-xs text-gray-400 mt-0.5">
            Real-time execution traces, token consumption metrics, and safety evaluation logs
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              setActivities([...MOCK_AGENT_ACTIVITIES]);
              toast.success("Telemetry log refreshed");
            }}
          >
            <RotateCcw className="w-3.5 h-3.5 mr-1" /> Refresh Stream
          </Button>
        </div>
      </div>

      {/* 4 Agent Cluster Status Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          {
            key: "classifier" as const,
            name: "Classifier Agent",
            role: "Intent & Priority Routing",
            model: "Gemini 2.0 Flash",
            latency: "342ms",
            tokens: "418 avg",
            accuracy: "98.4%",
            color: "text-blue-500",
            bg: "bg-blue-50 dark:bg-blue-950/60",
          },
          {
            key: "retriever" as const,
            name: "Retriever Agent",
            role: "ChromaDB Semantic Search",
            model: "text-embedding-004",
            latency: "184ms",
            tokens: "120 avg",
            accuracy: "96.1%",
            color: "text-purple-500",
            bg: "bg-purple-50 dark:bg-purple-950/60",
          },
          {
            key: "generator" as const,
            name: "Generator Agent",
            role: "Contextual Draft Synthesis",
            model: "Gemini 2.0 Flash",
            latency: "820ms",
            tokens: "940 avg",
            accuracy: "94.8%",
            color: "text-amber-500",
            bg: "bg-amber-50 dark:bg-amber-950/60",
          },
          {
            key: "evaluator" as const,
            name: "Evaluator Agent",
            role: "Safety & Quality Guardrail",
            model: "Gemini 2.0 Flash",
            latency: "290ms",
            tokens: "380 avg",
            accuracy: "99.1%",
            color: "text-emerald-500",
            bg: "bg-emerald-50 dark:bg-emerald-950/60",
          },
        ].map((agent) => {
          const isActive = agentStatuses[agent.key];
          return (
            <div
              key={agent.key}
              className="p-5 rounded-2xl bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 shadow-xs flex flex-col justify-between"
            >
              <div>
                <div className="flex items-center justify-between mb-3">
                  <div className={`w-9 h-9 rounded-xl ${agent.bg} ${agent.color} flex items-center justify-center font-bold`}>
                    <Bot className="w-5 h-5" />
                  </div>
                  <button
                    onClick={() => toggleAgent(agent.key, agent.name)}
                    className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase transition flex items-center gap-1 ${
                      isActive
                        ? "bg-emerald-50 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-400"
                        : "bg-gray-100 text-gray-500 dark:bg-gray-700"
                    }`}
                  >
                    {isActive ? <Play className="w-2.5 h-2.5 fill-current" /> : <Pause className="w-2.5 h-2.5" />}
                    {isActive ? "Active" : "Paused"}
                  </button>
                </div>

                <h3 className="text-sm font-bold text-gray-900 dark:text-white">{agent.name}</h3>
                <p className="text-[11px] text-gray-400 mt-0.5">{agent.role}</p>
                <p className="text-[10px] text-brand-600 dark:text-brand-400 font-mono mt-1">{agent.model}</p>
              </div>

              <div className="grid grid-cols-3 gap-2 pt-4 mt-4 border-t border-gray-100 dark:border-gray-750 text-center">
                <div>
                  <span className="text-[10px] text-gray-400">Latency</span>
                  <p className="text-xs font-bold text-gray-800 dark:text-gray-200">{agent.latency}</p>
                </div>
                <div>
                  <span className="text-[10px] text-gray-400">Tokens</span>
                  <p className="text-xs font-bold text-gray-800 dark:text-gray-200">{agent.tokens}</p>
                </div>
                <div>
                  <span className="text-[10px] text-gray-400">Accuracy</span>
                  <p className="text-xs font-bold text-emerald-600">{agent.accuracy}</p>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Live Agent Activity Stream Table */}
      <div className="p-6 rounded-2xl bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 shadow-xs">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
          <div>
            <h2 className="text-sm font-bold text-gray-900 dark:text-white flex items-center gap-2">
              <Activity className="w-4 h-4 text-brand-600" /> Live Pipeline Execution Log
            </h2>
            <p className="text-xs text-gray-400 mt-0.5">Streaming pipeline step executions for inbound tickets</p>
          </div>

          <div className="flex items-center gap-2">
            <select
              value={selectedAgentFilter}
              onChange={(e) => setSelectedAgentFilter(e.target.value)}
              className="px-3 py-1.5 rounded-xl border border-gray-200 dark:border-gray-700 text-xs bg-transparent text-gray-700 dark:text-gray-300"
            >
              <option value="all">All Agent Roles</option>
              <option value="classifier">Classifier Agent</option>
              <option value="retriever">Retriever Agent</option>
              <option value="generator">Generator Agent</option>
              <option value="evaluator">Evaluator Agent</option>
            </select>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-gray-100 dark:border-gray-700 text-gray-400 uppercase text-[11px]">
                <th className="py-2.5 px-3">Agent</th>
                <th className="py-2.5 px-3">Ticket Target</th>
                <th className="py-2.5 px-3">Execution Detail</th>
                <th className="py-2.5 px-3">Latency</th>
                <th className="py-2.5 px-3">Confidence</th>
                <th className="py-2.5 px-3 text-right">Time</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-gray-750">
              {filteredActivities.map((act) => (
                <tr key={act.id} className="hover:bg-gray-50/60 dark:hover:bg-gray-750/50 transition">
                  <td className="py-3 px-3">
                    <span className="font-bold text-gray-900 dark:text-white flex items-center gap-1.5">
                      <Sparkles className="w-3 h-3 text-brand-600" />
                      {act.agentName}
                    </span>
                    <span className="text-[10px] text-gray-400">{act.action}</span>
                  </td>
                  <td className="py-3 px-3">
                    <span className="font-mono font-bold text-brand-600 dark:text-brand-400">{act.ticketId}</span>
                    <p className="text-[11px] text-gray-500 dark:text-gray-400 truncate max-w-xs">{act.ticketSubject}</p>
                  </td>
                  <td className="py-3 px-3 text-gray-600 dark:text-gray-300 max-w-md">
                    {act.details}
                  </td>
                  <td className="py-3 px-3 font-mono text-[11px] text-gray-500">
                    {act.latencyMs}ms ({act.tokensUsed} tok)
                  </td>
                  <td className="py-3 px-3">
                    <span className="text-[11px] font-semibold text-emerald-600 dark:text-emerald-400">
                      {(act.confidence * 100).toFixed(1)}%
                    </span>
                  </td>
                  <td className="py-3 px-3 text-right text-gray-400 whitespace-nowrap">
                    {act.timestamp}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
