"use client";

import { useState, useRef, useEffect, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { Header } from "@/components/layout/Header";
import { chatWithAI, ChatMessage } from "@/lib/api";

function ChatContent() {
  const searchParams = useSearchParams();
  const initialQuery = searchParams.get("q");

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const initialized = useRef(false);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Auto-start if query param exists
  useEffect(() => {
    if (initialQuery && !initialized.current) {
      initialized.current = true;
      handleSend(initialQuery);
    }
  }, [initialQuery]);

  const handleSend = async (overrideInput?: string) => {
    const userMsg = (overrideInput || input).trim();
    if (!userMsg || isLoading) return;

    if (!overrideInput) setInput("");
    
    const newMessages: ChatMessage[] = [
      ...messages,
      { role: "user", content: userMsg },
    ];
    setMessages(newMessages);
    setIsLoading(true);

    try {
      // Send the history (excluding the current msg to avoid duplication in context if API expects it differently,
      // but our API schema expects history + message separately).
      const historyToSend = messages.slice(-10); // keep last 10 messages for context
      
      const response = await chatWithAI(userMsg, historyToSend);
      
      setMessages([
        ...newMessages,
        { role: "model", content: response },
      ]);
    } catch (error) {
      console.error("Chat error:", error);
      setMessages([
        ...newMessages,
        { role: "model", content: "❌ Erreur de connexion à l'assistant IA." },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-2rem)]">
      <Header
        title="Assistant IA (Alpha Terminal)"
        subtitle="Posez vos questions sur les derniers signaux OSINT"
      />

      <div className="flex-1 bg-slate-900/50 border border-slate-700/50 rounded-lg mt-4 overflow-hidden flex flex-col relative">
        {/* Messages Area */}
        <div className="flex-1 overflow-y-auto p-4 space-y-6">
          {messages.length === 0 && (
            <div className="text-center text-slate-500 mt-20">
              <div className="text-5xl mb-4">💬</div>
              <h3 className="text-xl font-medium text-slate-300">Bienvenue sur l'Assistant IA</h3>
              <p className="mt-2 text-sm max-w-md mx-auto">
                Je suis connecté à vos flux OSINT en temps réel. Posez-moi des questions sur les dernières alertes géopolitiques, les mouvements crypto, ou demandez-moi une analyse de marché.
              </p>
            </div>
          )}

          {messages.map((msg, i) => (
            <div
              key={i}
              className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-[80%] rounded-2xl px-5 py-3 ${
                  msg.role === "user"
                    ? "bg-indigo-600 text-white rounded-br-sm"
                    : "bg-slate-800 border border-slate-700 text-slate-200 rounded-bl-sm"
                }`}
              >
                <div className="text-xs opacity-50 mb-1 font-medium uppercase tracking-wider">
                  {msg.role === "user" ? "Vous" : "IA Alpha"}
                </div>
                <div className="whitespace-pre-wrap text-sm leading-relaxed">
                  {msg.content}
                </div>
              </div>
            </div>
          ))}
          {isLoading && (
            <div className="flex justify-start">
              <div className="bg-slate-800 border border-slate-700 text-slate-400 rounded-2xl rounded-bl-sm px-5 py-3 text-sm flex items-center gap-2">
                <div className="w-2 h-2 bg-indigo-500 rounded-full animate-bounce" style={{ animationDelay: "0ms" }}></div>
                <div className="w-2 h-2 bg-indigo-500 rounded-full animate-bounce" style={{ animationDelay: "150ms" }}></div>
                <div className="w-2 h-2 bg-indigo-500 rounded-full animate-bounce" style={{ animationDelay: "300ms" }}></div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Area */}
        <div className="p-4 bg-slate-800/80 border-t border-slate-700/50">
          <div className="relative">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Demandez une analyse sur les frappes récentes, les mouvements de whale, etc..."
              className="w-full bg-slate-900 border border-slate-700 rounded-xl pl-4 pr-14 py-3 text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 resize-none overflow-hidden"
              rows={2}
            />
            <button
              onClick={() => handleSend()}
              disabled={!input.trim() || isLoading}
              className="absolute right-2 bottom-2 p-2 bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-700 disabled:text-slate-500 text-white rounded-lg transition-colors flex items-center justify-center"
            >
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5">
                <path d="M3.478 2.404a.75.75 0 00-.926.941l2.432 7.905H13.5a.75.75 0 010 1.5H4.984l-2.432 7.905a.75.75 0 00.926.94 60.519 60.519 0 0018.445-8.986.75.75 0 000-1.218A60.517 60.517 0 003.478 2.404z" />
              </svg>
            </button>
          </div>
          <div className="text-xs text-center mt-2 text-slate-500">
            L'IA utilise les données collectées par l'Alpha Terminal pour fournir ses analyses.
          </div>
        </div>
      </div>
    </div>
  );
}

export default function ChatPage() {
  return (
    <Suspense fallback={<div className="p-8 text-slate-400">Chargement de l'assistant...</div>}>
      <ChatContent />
    </Suspense>
  );
}
