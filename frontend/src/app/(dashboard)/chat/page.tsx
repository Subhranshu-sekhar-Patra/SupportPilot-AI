"use client";

import { useState, useRef, useEffect } from "react";
import {
  Send,
  Bot,
  User,
  Sparkles,
  BookOpen,
  RotateCcw,
  ThumbsUp,
  ThumbsDown,
  ExternalLink,
  ShieldCheck,
  Check,
  Paperclip,
} from "lucide-react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";

interface ChatMessage {
  id: string;
  sender: "user" | "ai";
  content: string;
  timestamp: string;
  confidence?: number;
  sources?: string[];
  feedback?: "up" | "down";
}

const INITIAL_MESSAGES: ChatMessage[] = [
  {
    id: "m_init",
    sender: "ai",
    content: "Hello! I am SupportPilot AI, your intelligent customer support co-pilot. I can diagnose API errors, explain billing policies, or guide you through SSO configuration based on your organization's knowledge base. What can I help you resolve today?",
    timestamp: "10:00 AM",
    confidence: 0.99,
    sources: ["SupportPilot AI Platform Guide"],
  },
  {
    id: "m_user_1",
    sender: "user",
    content: "Why are our webhooks receiving 401 Unauthorized errors after we rotated keys?",
    timestamp: "10:01 AM",
  },
  {
    id: "m_ai_1",
    sender: "ai",
    content: "When you rotate API credentials, incoming webhooks verify signatures against the endpoint signing secret. Here is the resolution checklist:\n\n1. Ensure you updated the signing secret (`whsec_...`) in SupportPilot under **Settings > Webhooks**.\n2. Confirm your server clock is synchronized with NTP (timestamp drift > 300 seconds triggers automatic 401 rejection).\n3. Any queued webhooks sent during key rotation will be retried automatically with exponential backoff over the next 24 hours.",
    timestamp: "10:01 AM",
    confidence: 0.96,
    sources: ["Webhook Retry Logic & Idempotency Keys", "API Authentication & Token Lifecycle"],
  },
];

const SUGGESTED_PROMPTS = [
  "How do I configure SAML 2.0 with Okta?",
  "What is your SLA guarantee for Enterprise Tier?",
  "Can I generate an invoice refund credit note?",
  "How does the Classifier Agent determine ticket priority?",
];

export default function AILiveChatPage() {
  const [messages, setMessages] = useState<ChatMessage[]>(INITIAL_MESSAGES);
  const [inputPrompt, setInputPrompt] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping]);

  const handleSendMessage = (textToSend?: string) => {
    const text = textToSend || inputPrompt;
    if (!text.trim()) return;

    const userMsg: ChatMessage = {
      id: `u_${Date.now()}`,
      sender: "user",
      content: text,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInputPrompt("");
    setIsTyping(true);

    // Simulate realistic AI generation with retrieval citations
    setTimeout(() => {
      let aiResponseText = "I retrieved our knowledge base articles to address your query. Our system policies confirm that configurations can be adjusted directly from Organization Settings. Please ensure your user role has Admin or Owner permissions.";
      let sources = ["SupportPilot Knowledge Base"];

      if (text.toLowerCase().includes("okta") || text.toLowerCase().includes("saml")) {
        aiResponseText = "To configure Okta SAML 2.0 SSO:\n\n1. Go to **Settings > Authentication > SAML SSO**.\n2. In Okta Admin Console, add a new SAML App and paste your organization's Entity ID and ACS Consumer URL.\n3. Upload your Okta X.509 Certificate and Metadata XML.\n4. Enable 'Enforce SSO for all domain users' once validated.";
        sources = ["Okta & Azure AD SAML Configuration Runbook.docx"];
      } else if (text.toLowerCase().includes("sla")) {
        aiResponseText = "SupportPilot Enterprise tier includes a 99.95% uptime SLA and 15-minute First Response Time for Urgent/P1 tickets. If an SLA breach occurs, a 10% monthly service credit is automatically calculated and applied to your billing ledger.";
        sources = ["Enterprise Service Level Agreement (SLA) Policy"];
      } else if (text.toLowerCase().includes("refund")) {
        aiResponseText = "Refunds can be initiated by Admins under **Billing > Invoices**. Full refunds for duplicate charges within 30 days are processed automatically to the original payment method in 3-5 business days.";
        sources = ["Enterprise Billing & Refund Policy.pdf"];
      }

      const aiMsg: ChatMessage = {
        id: `ai_${Date.now()}`,
        sender: "ai",
        content: aiResponseText,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        confidence: 0.95,
        sources,
      };

      setMessages((prev) => [...prev, aiMsg]);
      setIsTyping(false);
    }, 900);
  };

  const handleFeedback = (id: string, type: "up" | "down") => {
    setMessages((prev) =>
      prev.map((m) => (m.id === id ? { ...m, feedback: type } : m))
    );
    toast.success(type === "up" ? "Thanks for positive feedback!" : "Feedback recorded for model tuning.");
  };

  const handleResetChat = () => {
    setMessages(INITIAL_MESSAGES.slice(0, 1));
    toast.info("Chat conversation session reset");
  };

  return (
    <div className="h-[calc(100vh-6rem)] flex flex-col bg-white dark:bg-gray-800 rounded-2xl border border-gray-200 dark:border-gray-700 overflow-hidden shadow-xs animate-fade-in">
      {/* Header */}
      <div className="p-4 border-b border-gray-100 dark:border-gray-750 flex items-center justify-between bg-white dark:bg-gray-800">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-brand-600 to-purple-600 flex items-center justify-center text-white shadow-sm">
            <Sparkles className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-sm font-bold text-gray-900 dark:text-white">SupportPilot AI Assistant</h2>
              <span className="flex items-center gap-1 text-[11px] font-semibold text-emerald-600 bg-emerald-50 dark:bg-emerald-950 px-2 py-0.5 rounded-full">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" /> Model: Gemini 2.0 Flash
              </span>
            </div>
            <p className="text-xs text-gray-400">Connected to 5 ChromaDB Knowledge Collections · RAG Enabled</p>
          </div>
        </div>

        <Button variant="outline" size="sm" onClick={handleResetChat}>
          <RotateCcw className="w-3.5 h-3.5 mr-1" /> New Session
        </Button>
      </div>

      {/* Messages Thread Container */}
      <div className="flex-1 p-4 sm:p-6 overflow-y-auto space-y-5 bg-gray-50/40 dark:bg-gray-900/40">
        {messages.map((m) => (
          <div
            key={m.id}
            className={`flex gap-3 max-w-3xl ${m.sender === "user" ? "ml-auto flex-row-reverse" : ""}`}
          >
            <div
              className={`w-8 h-8 rounded-xl flex items-center justify-center flex-shrink-0 text-xs font-bold ${
                m.sender === "user"
                  ? "bg-brand-600 text-white"
                  : "bg-gradient-to-tr from-brand-600 to-purple-600 text-white shadow-xs"
              }`}
            >
              {m.sender === "user" ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
            </div>

            <div className={`space-y-1.5 max-w-[85%] ${m.sender === "user" ? "items-end" : ""}`}>
              <div
                className={`p-4 rounded-2xl text-xs leading-relaxed whitespace-pre-wrap ${
                  m.sender === "user"
                    ? "bg-brand-600 text-white rounded-tr-xs"
                    : "bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-200 border border-gray-200/80 dark:border-gray-700/80 rounded-tl-xs shadow-xs"
                }`}
              >
                {m.content}
              </div>

              {/* AI Metadata & Sources */}
              {m.sender === "ai" && (
                <div className="flex flex-wrap items-center gap-3 pt-1 text-[11px] text-gray-400">
                  {m.confidence && (
                    <span className="text-emerald-600 dark:text-emerald-400 font-semibold">
                      Confidence: {Math.round(m.confidence * 100)}%
                    </span>
                  )}
                  {m.sources && m.sources.length > 0 && (
                    <span className="flex items-center gap-1 text-gray-500 dark:text-gray-400">
                      <BookOpen className="w-3 h-3 text-brand-600" />
                      Cited: {m.sources.join(", ")}
                    </span>
                  )}
                  <div className="flex items-center gap-1 ml-auto">
                    <button
                      onClick={() => handleFeedback(m.id, "up")}
                      className={`p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-700 ${
                        m.feedback === "up" ? "text-emerald-600" : "text-gray-400"
                      }`}
                    >
                      <ThumbsUp className="w-3 h-3" />
                    </button>
                    <button
                      onClick={() => handleFeedback(m.id, "down")}
                      className={`p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-700 ${
                        m.feedback === "down" ? "text-red-500" : "text-gray-400"
                      }`}
                    >
                      <ThumbsDown className="w-3 h-3" />
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        ))}

        {isTyping && (
          <div className="flex gap-3 max-w-xl">
            <div className="w-8 h-8 rounded-xl bg-purple-600 text-white flex items-center justify-center flex-shrink-0">
              <Bot className="w-4 h-4" />
            </div>
            <div className="p-3.5 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-2xl rounded-tl-xs flex items-center gap-1.5 shadow-xs">
              <span className="w-2 h-2 rounded-full bg-brand-600 animate-bounce" />
              <span className="w-2 h-2 rounded-full bg-brand-600 animate-bounce [animation-delay:0.2s]" />
              <span className="w-2 h-2 rounded-full bg-brand-600 animate-bounce [animation-delay:0.4s]" />
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Suggested Canned Questions */}
      <div className="px-4 py-2 bg-gray-50 dark:bg-gray-850/60 border-t border-gray-100 dark:border-gray-750 flex items-center gap-2 overflow-x-auto text-xs no-scrollbar">
        <span className="text-[11px] font-semibold text-gray-400 uppercase flex-shrink-0">Try asking:</span>
        {SUGGESTED_PROMPTS.map((prompt) => (
          <button
            key={prompt}
            onClick={() => handleSendMessage(prompt)}
            className="px-2.5 py-1 rounded-lg bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-300 hover:border-brand-500 flex-shrink-0 transition truncate max-w-xs"
          >
            {prompt}
          </button>
        ))}
      </div>

      {/* Chat Input Bar */}
      <div className="p-3 sm:p-4 bg-white dark:bg-gray-800 border-t border-gray-100 dark:border-gray-750">
        <div className="flex items-center gap-2">
          <input
            type="text"
            placeholder="Ask a question or enter customer query..."
            value={inputPrompt}
            onChange={(e) => setInputPrompt(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSendMessage()}
            className="flex-1 px-4 py-2.5 rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50/60 dark:bg-gray-750/60 text-xs sm:text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500"
          />
          <Button variant="primary" size="md" onClick={() => handleSendMessage()}>
            <Send className="w-4 h-4 mr-1" /> Send
          </Button>
        </div>
      </div>
    </div>
  );
}
