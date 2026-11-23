"use client";

import { useState } from "react";
import {
  Inbox,
  User,
  Clock,
  Send,
  Lock,
  Tag,
  Paperclip,
  CheckCircle,
  AlertTriangle,
  Mail,
  MessageSquare,
  Globe,
  Sparkles,
  Search,
  Filter,
} from "lucide-react";
import { toast } from "sonner";
import { MOCK_TICKETS, MockTicket, MOCK_TEAM_MEMBERS } from "@/lib/mock-data";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";

export default function HumanSupportInboxPage() {
  const [activeTab, setActiveTab] = useState<"unassigned" | "mine" | "escalated" | "all">("all");
  const [selectedTicket, setSelectedTicket] = useState<MockTicket>(MOCK_TICKETS[0]);
  const [replyMode, setReplyMode] = useState<"public" | "internal">("public");
  const [replyText, setReplyText] = useState("");

  const filteredTickets = MOCK_TICKETS.filter((t) => {
    if (activeTab === "unassigned") return !t.assignedTo;
    if (activeTab === "mine") return t.assignedTo?.name.includes("Marcus") || t.assignedTo?.name.includes("Alex");
    if (activeTab === "escalated") return t.status === "escalated";
    return true;
  });

  const handleSendResponse = () => {
    if (!replyText.trim()) return;

    const newMsg = {
      id: `inbox_msg_${Date.now()}`,
      sender: (replyMode === "internal" ? "system" : "agent") as any,
      senderName: replyMode === "internal" ? "Internal Note (Alex Turner)" : "Alex Turner",
      content: replyText,
      timestamp: new Date().toISOString(),
      isInternal: replyMode === "internal",
    };

    const updated = {
      ...selectedTicket,
      messages: [...selectedTicket.messages, newMsg],
    };

    setSelectedTicket(updated);
    setReplyText("");
    toast.success(replyMode === "internal" ? "Internal note added to audit trail" : "Public reply dispatched to customer");
  };

  return (
    <div className="h-[calc(100vh-6rem)] flex flex-col gap-4 animate-fade-in">
      {/* Top Header & Channel Switcher */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold text-gray-900 dark:text-white tracking-tight flex items-center gap-2">
            <Inbox className="w-5 h-5 text-brand-600" /> Human Support Workspace
          </h1>
          <p className="text-xs text-gray-400">Collaborative multi-channel queue for complex and escalated inquiries</p>
        </div>

        {/* Tab Filters */}
        <div className="inline-flex rounded-xl bg-gray-100 dark:bg-gray-800 p-1 border border-gray-200 dark:border-gray-700 text-xs">
          {[
            { id: "all", label: "All Tickets (18)" },
            { id: "mine", label: "Assigned to Me (7)" },
            { id: "unassigned", label: "Unassigned (4)" },
            { id: "escalated", label: "Escalated (6)" },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`px-3 py-1.5 rounded-lg font-medium transition ${
                activeTab === tab.id
                  ? "bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-2xs font-semibold"
                  : "text-gray-500 hover:text-gray-900 dark:hover:text-white"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* 3-Column Split View: Queue List | Conversation Thread | Customer CRM Sidebar */}
      <div className="flex-1 flex gap-4 min-h-0 overflow-hidden">
        {/* Column 1: Ticket Queue List */}
        <div className="w-full sm:w-80 lg:w-96 flex flex-col bg-white dark:bg-gray-800 rounded-2xl border border-gray-200 dark:border-gray-700 overflow-hidden shadow-xs flex-shrink-0">
          <div className="p-3 border-b border-gray-100 dark:border-gray-750 flex items-center gap-2">
            <Search className="w-3.5 h-3.5 text-gray-400" />
            <input
              type="text"
              placeholder="Filter queue..."
              className="w-full bg-transparent text-xs text-gray-900 dark:text-white focus:outline-none"
            />
          </div>

          <div className="flex-1 overflow-y-auto divide-y divide-gray-100 dark:divide-gray-750">
            {filteredTickets.map((t) => (
              <div
                key={t.id}
                onClick={() => setSelectedTicket(t)}
                className={`p-3.5 cursor-pointer transition flex flex-col gap-1.5 ${
                  selectedTicket.id === t.id
                    ? "bg-brand-50/80 dark:bg-brand-950/40 border-l-4 border-l-brand-600"
                    : "hover:bg-gray-50/70 dark:hover:bg-gray-750/50"
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="font-mono text-[11px] font-bold text-gray-400">{t.ticketNumber}</span>
                  <span className="text-[10px] text-gray-400 flex items-center gap-1">
                    <Clock className="w-3 h-3" /> 12m ago
                  </span>
                </div>
                <h3 className="text-xs font-bold text-gray-900 dark:text-white line-clamp-1">{t.subject}</h3>
                <p className="text-[11px] text-gray-500 dark:text-gray-400 line-clamp-1">{t.description}</p>
                <div className="flex items-center justify-between pt-1">
                  <span className="text-[11px] font-semibold text-gray-700 dark:text-gray-300 truncate max-w-[120px]">
                    {t.customerName}
                  </span>
                  <Badge variant={t.priority === "urgent" ? "danger" : "default"} size="sm">
                    {t.priority}
                  </Badge>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Column 2: Conversation View */}
        <div className="flex-1 flex flex-col bg-white dark:bg-gray-800 rounded-2xl border border-gray-200 dark:border-gray-700 overflow-hidden shadow-xs">
          {/* Conversation Header */}
          <div className="p-4 border-b border-gray-100 dark:border-gray-750 flex items-center justify-between">
            <div>
              <div className="flex items-center gap-2">
                <span className="font-mono text-xs font-bold text-brand-600">{selectedTicket.ticketNumber}</span>
                <Badge variant={selectedTicket.status === "escalated" ? "danger" : "warning"} size="sm">
                  {selectedTicket.status}
                </Badge>
                <span className="text-xs text-gray-400">via {selectedTicket.channel.toUpperCase()}</span>
              </div>
              <h2 className="text-sm font-bold text-gray-900 dark:text-white mt-1">{selectedTicket.subject}</h2>
            </div>
            <div className="flex items-center gap-2">
              <Button variant="outline" size="sm">
                <CheckCircle className="w-3.5 h-3.5 mr-1" /> Close Ticket
              </Button>
            </div>
          </div>

          {/* Messages Thread */}
          <div className="flex-1 p-5 overflow-y-auto space-y-4">
            {selectedTicket.messages.map((m) => (
              <div
                key={m.id}
                className={`p-4 rounded-2xl text-xs space-y-1 ${
                  m.isInternal
                    ? "bg-amber-50/70 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-800/40"
                    : m.sender === "customer"
                    ? "bg-gray-50 dark:bg-gray-750/70 border border-gray-100 dark:border-gray-700"
                    : "bg-blue-50/70 dark:bg-blue-950/40 border border-blue-200 dark:border-blue-800/40"
                }`}
              >
                <div className="flex items-center justify-between font-semibold">
                  <span className="flex items-center gap-1.5">
                    {m.isInternal && <Lock className="w-3.5 h-3.5 text-amber-600" />}
                    {m.senderName}
                  </span>
                  <span className="text-[10px] text-gray-400 font-normal">
                    {new Date(m.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                  </span>
                </div>
                <p className="text-gray-700 dark:text-gray-200 leading-relaxed whitespace-pre-wrap">{m.content}</p>
              </div>
            ))}
          </div>

          {/* Composer with Public vs Internal Mode Tabs */}
          <div className="p-4 border-t border-gray-100 dark:border-gray-750 bg-gray-50/40 dark:bg-gray-850/40">
            <div className="flex items-center gap-2 mb-2">
              <button
                onClick={() => setReplyMode("public")}
                className={`px-3 py-1 rounded-lg text-xs font-semibold transition ${
                  replyMode === "public"
                    ? "bg-brand-600 text-white shadow-2xs"
                    : "text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
                }`}
              >
                Public Reply
              </button>
              <button
                onClick={() => setReplyMode("internal")}
                className={`px-3 py-1 rounded-lg text-xs font-semibold transition flex items-center gap-1 ${
                  replyMode === "internal"
                    ? "bg-amber-500 text-white shadow-2xs"
                    : "text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
                }`}
              >
                <Lock className="w-3 h-3" /> Internal Note
              </button>
            </div>

            <textarea
              rows={3}
              placeholder={replyMode === "internal" ? "Write an internal note only visible to team members..." : "Reply to customer..."}
              value={replyText}
              onChange={(e) => setReplyText(e.target.value)}
              className={`w-full p-3 rounded-xl border text-xs focus:outline-none focus:ring-2 resize-none ${
                replyMode === "internal"
                  ? "border-amber-300 dark:border-amber-700 bg-amber-50/20 dark:bg-amber-950/20 focus:ring-amber-500"
                  : "border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 focus:ring-brand-500"
              }`}
            />

            <div className="flex justify-end gap-2 mt-2">
              <Button variant={replyMode === "internal" ? "secondary" : "primary"} size="sm" onClick={handleSendResponse}>
                <Send className="w-3.5 h-3.5 mr-1" />
                {replyMode === "internal" ? "Save Internal Note" : "Send Reply"}
              </Button>
            </div>
          </div>
        </div>

        {/* Column 3: Customer Context Sidebar */}
        <div className="hidden xl:flex w-72 flex-col bg-white dark:bg-gray-800 rounded-2xl border border-gray-200 dark:border-gray-700 p-5 overflow-y-auto space-y-5 flex-shrink-0">
          <div>
            <h3 className="text-xs font-bold uppercase tracking-wider text-gray-400 mb-3">Customer Details</h3>
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-brand-600 to-indigo-600 text-white font-bold text-sm flex items-center justify-center">
                {selectedTicket.customerName.charAt(0)}
              </div>
              <div className="min-w-0">
                <p className="text-xs font-bold text-gray-900 dark:text-white truncate">{selectedTicket.customerName}</p>
                <p className="text-[11px] text-gray-400 truncate">{selectedTicket.customerEmail}</p>
              </div>
            </div>
          </div>

          <div className="space-y-3 pt-3 border-t border-gray-100 dark:border-gray-750 text-xs">
            <div>
              <span className="text-[11px] text-gray-400">Account Tier</span>
              <p className="font-semibold text-gray-800 dark:text-gray-200">Enterprise Plan ($48,000/yr)</p>
            </div>
            <div>
              <span className="text-[11px] text-gray-400">SLA Response Window</span>
              <p className="font-semibold text-emerald-600">Within Target (1.2h remaining)</p>
            </div>
            <div>
              <span className="text-[11px] text-gray-400">Assigned Agent</span>
              <select className="mt-1 w-full px-2.5 py-1.5 rounded-lg border border-gray-200 dark:border-gray-700 text-xs bg-transparent">
                {MOCK_TEAM_MEMBERS.map((m) => (
                  <option key={m.id} value={m.name}>
                    {m.name} ({m.role})
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="pt-3 border-t border-gray-100 dark:border-gray-750">
            <h3 className="text-xs font-bold uppercase tracking-wider text-gray-400 mb-2">Applied Tags</h3>
            <div className="flex flex-wrap gap-1.5">
              {selectedTicket.tags.map((tag) => (
                <span key={tag} className="text-[10px] px-2 py-0.5 rounded bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300">
                  #{tag}
                </span>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
