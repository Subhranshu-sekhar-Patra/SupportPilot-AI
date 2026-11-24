"use client";

import { useEffect, useState, useRef } from "react";
import { useSearchParams } from "next/navigation";
import { Send, Bot, User, Sparkles, CheckCircle2, AlertCircle } from "lucide-react";

interface Message {
  id: string;
  sender: "bot" | "user" | "system";
  content: string;
  timestamp: string;
  citations?: Array<{ title: string; chunk_index: number }>;
}

interface WidgetConfig {
  organization_name: string;
  organization_slug: string;
  primary_color: string;
  greeting: string;
  enabled: boolean;
}

export default function EmbeddableChatWidgetPage() {
  const searchParams = useSearchParams();
  const orgSlug = searchParams.get("org") || "demo-org";

  const [config, setConfig] = useState<WidgetConfig | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputText, setInputText] = useState("");
  const [loading, setLoading] = useState(false);
  const [sessionId] = useState(() => "sess_" + Math.random().toString(36).substring(2, 10));
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  useEffect(() => {
    fetch(`${apiUrl}/api/v1/widget/${orgSlug}/config`)
      .then((res) => {
        if (!res.ok) throw new Error("Widget not found");
        return res.json();
      })
      .then((cfg: WidgetConfig) => {
        setConfig(cfg);
        setMessages([
          {
            id: "greeting",
            sender: "bot",
            content: cfg.greeting,
            timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
          },
        ]);
      })
      .catch(() => {
        setConfig({
          organization_name: "Customer Support",
          organization_slug: orgSlug,
          primary_color: "#4F46E5",
          greeting: "Hi there! How can we help you today?",
          enabled: true,
        });
      });
  }, [apiUrl, orgSlug]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputText.trim() || loading) return;

    const userText = inputText.trim();
    setInputText("");

    const newMsg: Message = {
      id: `usr_${Date.now()}`,
      sender: "user",
      content: userText,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };
    setMessages((prev) => [...prev, newMsg]);
    setLoading(true);

    try {
      const res = await fetch(`${apiUrl}/api/v1/widget/${orgSlug}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: userText,
          session_id: sessionId,
          customer_name: "Visitor",
        }),
      });

      if (!res.ok) throw new Error("Chat request failed");
      const data = await res.json();

      const botMsg: Message = {
        id: `bot_${Date.now()}`,
        sender: "bot",
        content: data.reply,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        citations: data.citations,
      };
      setMessages((prev) => [...prev, botMsg]);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          id: `err_${Date.now()}`,
          sender: "system",
          content: "Unable to reach support server. Please try again later.",
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const primaryColor = config?.primary_color || "#4F46E5";

  return (
    <div className="flex flex-col h-screen w-full bg-white dark:bg-gray-900 font-sans overflow-hidden text-sm">
      {/* Widget Header */}
      <div
        className="px-4 py-3.5 flex items-center justify-between text-white shadow-md z-10"
        style={{ backgroundColor: primaryColor }}
      >
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-full bg-white/20 flex items-center justify-center font-bold text-sm">
            <Bot className="w-4 h-4 text-white" />
          </div>
          <div>
            <h1 className="font-semibold text-sm leading-tight">
              {config?.organization_name || "SupportPilot AI"}
            </h1>
            <p className="text-[11px] text-white/80 flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-300 animate-pulse" />
              Automated Assistant
            </p>
          </div>
        </div>
        <span className="text-[10px] bg-black/20 px-2 py-0.5 rounded-full text-white/90 font-medium">
          Powered by SupportPilot
        </span>
      </div>

      {/* Message Feed */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3 bg-gray-50/70 dark:bg-gray-950">
        {messages.map((m) => (
          <div
            key={m.id}
            className={`flex gap-2 max-w-[85%] ${
              m.sender === "user" ? "ml-auto flex-row-reverse" : "mr-auto"
            }`}
          >
            {m.sender !== "system" && (
              <div
                className={`w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0 text-xs ${
                  m.sender === "user"
                    ? "bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300"
                    : "text-white"
                }`}
                style={m.sender === "bot" ? { backgroundColor: primaryColor } : {}}
              >
                {m.sender === "user" ? <User className="w-3.5 h-3.5" /> : <Sparkles className="w-3.5 h-3.5" />}
              </div>
            )}

            <div>
              <div
                className={`p-3 rounded-2xl text-xs leading-relaxed ${
                  m.sender === "user"
                    ? "text-white rounded-br-2xs"
                    : m.sender === "system"
                    ? "bg-red-50 dark:bg-red-950/40 text-red-600 dark:text-red-400 border border-red-200 dark:border-red-900"
                    : "bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-200 border border-gray-100 dark:border-gray-700 shadow-2xs rounded-bl-2xs"
                }`}
                style={m.sender === "user" ? { backgroundColor: primaryColor } : {}}
              >
                <p className="whitespace-pre-wrap">{m.content}</p>

                {/* Citations badge */}
                {m.citations && m.citations.length > 0 && (
                  <div className="mt-2 pt-2 border-t border-gray-100 dark:border-gray-700 flex flex-wrap gap-1">
                    {m.citations.map((c, i) => (
                      <span
                        key={i}
                        className="inline-flex items-center gap-1 text-[10px] bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 px-1.5 py-0.5 rounded"
                      >
                        <CheckCircle2 className="w-2.5 h-2.5 text-emerald-500" />
                        {c.title}
                      </span>
                    ))}
                  </div>
                )}
              </div>
              <span className="text-[9px] text-gray-400 mt-1 block px-1">{m.timestamp}</span>
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex gap-2 mr-auto items-center text-xs text-gray-400">
            <div
              className="w-6 h-6 rounded-full flex items-center justify-center text-white"
              style={{ backgroundColor: primaryColor }}
            >
              <Bot className="w-3 h-3 animate-spin" />
            </div>
            <div className="bg-white dark:bg-gray-800 border border-gray-100 dark:border-gray-700 px-3 py-2 rounded-2xl shadow-2xs">
              <span className="animate-pulse">Searching knowledge base & drafting answer...</span>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Composer */}
      <form onSubmit={handleSendMessage} className="p-3 bg-white dark:bg-gray-900 border-t border-gray-100 dark:border-gray-800 flex gap-2 items-center">
        <input
          type="text"
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          placeholder="Ask a question..."
          className="flex-1 bg-gray-100 dark:bg-gray-800 text-xs px-3.5 py-2.5 rounded-xl border border-transparent focus:border-brand-500 focus:outline-hidden dark:text-white"
        />
        <button
          type="submit"
          disabled={!inputText.trim() || loading}
          className="w-9 h-9 rounded-xl flex items-center justify-center text-white transition disabled:opacity-40"
          style={{ backgroundColor: primaryColor }}
        >
          <Send className="w-4 h-4" />
        </button>
      </form>
    </div>
  );
}
