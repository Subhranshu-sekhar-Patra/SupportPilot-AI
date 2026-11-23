"use client";

import { useState } from "react";
import {
  Search,
  Filter,
  Plus,
  Bot,
  User,
  Clock,
  Sparkles,
  Send,
  AlertCircle,
  CheckCircle,
  ArrowUpDown,
  Mail,
  MessageSquare,
  Globe,
  Tag,
  ChevronRight,
  ShieldAlert,
} from "lucide-react";
import { toast } from "sonner";
import { MOCK_TICKETS, MockTicket } from "@/lib/mock-data";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";

export default function TicketsPage() {
  const [tickets, setTickets] = useState<MockTicket[]>(MOCK_TICKETS);
  const [selectedTicket, setSelectedTicket] = useState<MockTicket | null>(MOCK_TICKETS[0]);
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [priorityFilter, setPriorityFilter] = useState<string>("all");
  const [replyText, setReplyText] = useState("");
  const [isNewTicketModalOpen, setIsNewTicketModalOpen] = useState(false);

  // New Ticket Form State
  const [newSubject, setNewSubject] = useState("");
  const [newDescription, setNewDescription] = useState("");
  const [newCustomerEmail, setNewCustomerEmail] = useState("");
  const [newPriority, setNewPriority] = useState<MockTicket["priority"]>("medium");
  const [newCategory, setNewCategory] = useState<MockTicket["category"]>("Technical");

  const filteredTickets = tickets.filter((t) => {
    const matchesSearch =
      t.subject.toLowerCase().includes(searchQuery.toLowerCase()) ||
      t.customerName.toLowerCase().includes(searchQuery.toLowerCase()) ||
      t.ticketNumber.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesStatus = statusFilter === "all" || t.status === statusFilter;
    const matchesPriority = priorityFilter === "all" || t.priority === priorityFilter;
    return matchesSearch && matchesStatus && matchesPriority;
  });

  const handleSendReply = () => {
    if (!replyText.trim() || !selectedTicket) return;

    const newMessage = {
      id: `msg_${Date.now()}`,
      sender: "agent" as const,
      senderName: "Alex Turner (You)",
      content: replyText,
      timestamp: new Date().toISOString(),
    };

    const updated = {
      ...selectedTicket,
      status: "in_progress" as const,
      messages: [...selectedTicket.messages, newMessage],
    };

    setSelectedTicket(updated);
    setTickets(tickets.map((t) => (t.id === updated.id ? updated : t)));
    setReplyText("");
    toast.success("Reply dispatched to customer");
  };

  const handleApplyAISuggestion = () => {
    if (!selectedTicket?.aiSuggestedResponse) return;
    setReplyText(selectedTicket.aiSuggestedResponse);
    toast.info("AI suggested response loaded into composer");
  };

  const handleUpdateStatus = (newStatus: MockTicket["status"]) => {
    if (!selectedTicket) return;
    const updated = { ...selectedTicket, status: newStatus };
    setSelectedTicket(updated);
    setTickets(tickets.map((t) => (t.id === updated.id ? updated : t)));
    toast.success(`Ticket marked as ${newStatus.replace("_", " ")}`);
  };

  const handleCreateTicket = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newSubject.trim() || !newDescription.trim() || !newCustomerEmail.trim()) {
      toast.error("Please fill in all required fields");
      return;
    }

    const created: MockTicket = {
      id: `tkt_${Date.now()}`,
      ticketNumber: `SP-${Math.floor(1000 + Math.random() * 9000)}`,
      subject: newSubject,
      description: newDescription,
      customerName: newCustomerEmail.split("@")[0],
      customerEmail: newCustomerEmail,
      status: "open",
      priority: newPriority,
      category: newCategory,
      channel: "portal",
      aiSuggestedResponse: "Hello,\n\nThank you for reaching out. Our support engineering squad is looking into your inquiry and will follow up shortly.",
      aiConfidenceScore: 0.91,
      aiQualityScore: 0.90,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      tags: [newCategory.toLowerCase()],
      messages: [
        {
          id: `m_${Date.now()}`,
          sender: "customer",
          senderName: newCustomerEmail.split("@")[0],
          content: newDescription,
          timestamp: new Date().toISOString(),
        },
      ],
    };

    setTickets([created, ...tickets]);
    setSelectedTicket(created);
    setIsNewTicketModalOpen(false);
    setNewSubject("");
    setNewDescription("");
    setNewCustomerEmail("");
    toast.success("New ticket created successfully!");
  };

  const getPriorityBadge = (p: MockTicket["priority"]) => {
    switch (p) {
      case "urgent":
        return <Badge variant="danger" size="sm">Urgent</Badge>;
      case "high":
        return <Badge variant="warning" size="sm">High</Badge>;
      case "medium":
        return <Badge variant="info" size="sm">Medium</Badge>;
      default:
        return <Badge variant="secondary" size="sm">Low</Badge>;
    }
  };

  const getStatusBadge = (s: MockTicket["status"]) => {
    switch (s) {
      case "escalated":
        return <Badge variant="danger" size="sm">Escalated</Badge>;
      case "resolved":
        return <Badge variant="success" size="sm">Resolved</Badge>;
      case "in_progress":
        return <Badge variant="warning" size="sm">In Progress</Badge>;
      case "pending_review":
        return <Badge variant="purple" size="sm">Review</Badge>;
      default:
        return <Badge variant="default" size="sm">Open</Badge>;
    }
  };

  return (
    <div className="h-[calc(100vh-6rem)] flex flex-col gap-4 animate-fade-in">
      {/* Top Controls Toolbar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center gap-2 flex-1">
          {/* Search */}
          <div className="relative flex-1 max-w-sm">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              placeholder="Search by ID, subject, customer..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-3 py-2 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-xs text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500"
            />
          </div>

          {/* Status Filter */}
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-3 py-2 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-xs text-gray-700 dark:text-gray-300 focus:outline-none"
          >
            <option value="all">All Statuses</option>
            <option value="open">Open</option>
            <option value="in_progress">In Progress</option>
            <option value="escalated">Escalated</option>
            <option value="resolved">Resolved</option>
          </select>

          {/* Priority Filter */}
          <select
            value={priorityFilter}
            onChange={(e) => setPriorityFilter(e.target.value)}
            className="px-3 py-2 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-xs text-gray-700 dark:text-gray-300 focus:outline-none"
          >
            <option value="all">All Priorities</option>
            <option value="urgent">Urgent</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>
        </div>

        <Button variant="primary" size="sm" onClick={() => setIsNewTicketModalOpen(true)}>
          <Plus className="w-4 h-4 mr-1" /> New Ticket
        </Button>
      </div>

      {/* Main Split Layout: Left Ticket List & Right Detail Pane */}
      <div className="flex-1 flex gap-4 min-h-0 overflow-hidden">
        {/* Left List */}
        <div className="w-full lg:w-2/5 flex flex-col bg-white dark:bg-gray-800 rounded-2xl border border-gray-200 dark:border-gray-700 overflow-hidden shadow-xs">
          <div className="p-3 border-b border-gray-100 dark:border-gray-750 flex items-center justify-between text-xs text-gray-500 font-semibold">
            <span>Inbox Queue ({filteredTickets.length})</span>
            <span>Sorted by Recent</span>
          </div>

          <div className="flex-1 overflow-y-auto divide-y divide-gray-100 dark:divide-gray-750">
            {filteredTickets.map((ticket) => {
              const isSelected = selectedTicket?.id === ticket.id;
              return (
                <div
                  key={ticket.id}
                  onClick={() => setSelectedTicket(ticket)}
                  className={`p-4 cursor-pointer transition flex flex-col gap-2 ${
                    isSelected
                      ? "bg-brand-50/70 dark:bg-brand-950/40 border-l-4 border-l-brand-600"
                      : "hover:bg-gray-50/80 dark:hover:bg-gray-750/50"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-[11px] font-bold text-gray-500 dark:text-gray-400">
                      {ticket.ticketNumber}
                    </span>
                    <div className="flex items-center gap-1.5">
                      {getPriorityBadge(ticket.priority)}
                      {getStatusBadge(ticket.status)}
                    </div>
                  </div>

                  <h3 className="text-xs font-bold text-gray-900 dark:text-white line-clamp-1">
                    {ticket.subject}
                  </h3>

                  <p className="text-[11px] text-gray-500 dark:text-gray-400 line-clamp-2">
                    {ticket.description}
                  </p>

                  <div className="flex items-center justify-between pt-1 text-[11px] text-gray-400">
                    <span className="font-medium text-gray-600 dark:text-gray-300 truncate max-w-[140px]">
                      {ticket.customerName}
                    </span>
                    <span className="flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      {new Date(ticket.createdAt).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Right Detail Pane */}
        {selectedTicket ? (
          <div className="hidden lg:flex flex-1 flex-col bg-white dark:bg-gray-800 rounded-2xl border border-gray-200 dark:border-gray-700 overflow-hidden shadow-xs">
            {/* Ticket Header & Status Switcher */}
            <div className="p-5 border-b border-gray-100 dark:border-gray-750 flex items-start justify-between">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <span className="font-mono text-xs font-bold text-brand-600 dark:text-brand-400">
                    {selectedTicket.ticketNumber}
                  </span>
                  {getPriorityBadge(selectedTicket.priority)}
                  {getStatusBadge(selectedTicket.status)}
                  <span className="text-[11px] text-gray-400 font-medium">Category: {selectedTicket.category}</span>
                </div>
                <h2 className="text-base font-bold text-gray-900 dark:text-white">
                  {selectedTicket.subject}
                </h2>
                <p className="text-xs text-gray-400 mt-0.5">
                  Customer: <span className="font-semibold text-gray-700 dark:text-gray-300">{selectedTicket.customerName}</span> ({selectedTicket.customerEmail})
                </p>
              </div>

              {/* Status Action Buttons */}
              <div className="flex items-center gap-1.5">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleUpdateStatus("escalated")}
                >
                  <ShieldAlert className="w-3.5 h-3.5 text-red-500 mr-1" /> Escalate
                </Button>
                <Button
                  variant="primary"
                  size="sm"
                  onClick={() => handleUpdateStatus("resolved")}
                >
                  <CheckCircle className="w-3.5 h-3.5 mr-1" /> Resolve
                </Button>
              </div>
            </div>

            {/* Conversation Thread Messages */}
            <div className="flex-1 p-5 overflow-y-auto space-y-4">
              {selectedTicket.messages.map((m) => (
                <div
                  key={m.id}
                  className={`p-4 rounded-2xl text-xs space-y-1.5 ${
                    m.sender === "customer"
                      ? "bg-gray-50 dark:bg-gray-750/80 border border-gray-100 dark:border-gray-700 mr-8"
                      : m.sender === "ai"
                      ? "bg-purple-50/70 dark:bg-purple-950/40 border border-purple-200/60 dark:border-purple-800/40 ml-4 mr-4"
                      : "bg-blue-50/80 dark:bg-blue-950/40 border border-blue-200/60 dark:border-blue-800/40 ml-8"
                  }`}
                >
                  <div className="flex items-center justify-between font-semibold">
                    <span className="flex items-center gap-1.5">
                      {m.sender === "ai" && <Sparkles className="w-3.5 h-3.5 text-purple-600" />}
                      {m.senderName}
                    </span>
                    <span className="text-[10px] text-gray-400 font-normal">
                      {new Date(m.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                    </span>
                  </div>
                  <p className="text-gray-700 dark:text-gray-200 leading-relaxed whitespace-pre-wrap">
                    {m.content}
                  </p>
                </div>
              ))}

              {/* AI Draft Assist Banner */}
              {selectedTicket.aiSuggestedResponse && (
                <div className="p-4 rounded-2xl bg-gradient-to-r from-brand-50 to-purple-50 dark:from-brand-950/40 dark:to-purple-950/40 border border-brand-200/80 dark:border-brand-800/60">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <Sparkles className="w-4 h-4 text-purple-600 dark:text-purple-400" />
                      <span className="text-xs font-bold text-gray-900 dark:text-white">
                        AI Recommended Draft Resolution
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] font-semibold text-emerald-600 bg-emerald-50 dark:bg-emerald-950 px-2 py-0.5 rounded-full">
                        Confidence: {Math.round((selectedTicket.aiConfidenceScore ?? 0.9) * 100)}%
                      </span>
                      <Button variant="secondary" size="sm" onClick={handleApplyAISuggestion}>
                        Insert into Reply
                      </Button>
                    </div>
                  </div>
                  <p className="text-xs text-gray-600 dark:text-gray-300 leading-relaxed italic bg-white/70 dark:bg-gray-800/70 p-3 rounded-xl">
                    &ldquo;{selectedTicket.aiSuggestedResponse}&rdquo;
                  </p>
                </div>
              )}
            </div>

            {/* Reply Composer */}
            <div className="p-4 border-t border-gray-100 dark:border-gray-750 bg-gray-50/50 dark:bg-gray-850/50">
              <div className="relative">
                <textarea
                  rows={3}
                  placeholder="Type your response to the customer or internal note..."
                  value={replyText}
                  onChange={(e) => setReplyText(e.target.value)}
                  className="w-full p-3 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-xs text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500 resize-none pr-24"
                />
                <div className="absolute right-3 bottom-3 flex items-center gap-2">
                  <Button variant="primary" size="sm" onClick={handleSendReply}>
                    <Send className="w-3.5 h-3.5 mr-1" /> Send
                  </Button>
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div className="hidden lg:flex flex-1 items-center justify-center bg-white dark:bg-gray-800 rounded-2xl border border-gray-200 dark:border-gray-700 text-gray-400 text-xs">
            Select a ticket from the left to view thread and AI recommendations.
          </div>
        )}
      </div>

      {/* New Ticket Modal */}
      <Modal
        isOpen={isNewTicketModalOpen}
        onClose={() => setIsNewTicketModalOpen(false)}
        title="Create New Support Ticket"
        description="Manual ticket creation for omnichannel inbound requests"
        maxWidth="lg"
      >
        <form onSubmit={handleCreateTicket} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1">
              Customer Email Address
            </label>
            <input
              type="email"
              placeholder="customer@company.com"
              value={newCustomerEmail}
              onChange={(e) => setNewCustomerEmail(e.target.value)}
              className="w-full px-3 py-2 rounded-xl border border-gray-300 dark:border-gray-600 text-xs bg-transparent text-gray-900 dark:text-white"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1">
              Subject Line
            </label>
            <input
              type="text"
              placeholder="Brief summary of the issue"
              value={newSubject}
              onChange={(e) => setNewSubject(e.target.value)}
              className="w-full px-3 py-2 rounded-xl border border-gray-300 dark:border-gray-600 text-xs bg-transparent text-gray-900 dark:text-white"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1">
                Priority
              </label>
              <select
                value={newPriority}
                onChange={(e) => setNewPriority(e.target.value as any)}
                className="w-full px-3 py-2 rounded-xl border border-gray-300 dark:border-gray-600 text-xs bg-transparent text-gray-900 dark:text-white"
              >
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
                <option value="urgent">Urgent</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1">
                Category
              </label>
              <select
                value={newCategory}
                onChange={(e) => setNewCategory(e.target.value as any)}
                className="w-full px-3 py-2 rounded-xl border border-gray-300 dark:border-gray-600 text-xs bg-transparent text-gray-900 dark:text-white"
              >
                <option value="Technical">Technical</option>
                <option value="Billing">Billing</option>
                <option value="Account">Account</option>
                <option value="Security">Security</option>
                <option value="Feature Request">Feature Request</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1">
              Detailed Description
            </label>
            <textarea
              rows={4}
              placeholder="Describe the issue, reproduction steps, or question..."
              value={newDescription}
              onChange={(e) => setNewDescription(e.target.value)}
              className="w-full p-3 rounded-xl border border-gray-300 dark:border-gray-600 text-xs bg-transparent text-gray-900 dark:text-white resize-none"
            />
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <Button variant="outline" size="sm" type="button" onClick={() => setIsNewTicketModalOpen(false)}>
              Cancel
            </Button>
            <Button variant="primary" size="sm" type="submit">
              Submit Ticket
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
