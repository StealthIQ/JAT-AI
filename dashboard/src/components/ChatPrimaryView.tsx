import { useCallback, useEffect, useRef, useState } from "react";

type Message = {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: string;
  model?: string;
};

type Conversation = {
  id: string;
  title: string;
  messages: Message[];
  createdAt: string;
  provider?: string;
  model?: string;
};

const MOCK_CONVERSATIONS: Conversation[] = [
  {
    id: "conv-1",
    title: "Code review discussion",
    messages: [
      { id: "m1", role: "user", content: "Review this function for security issues", timestamp: "2026-05-01T09:00:00Z" },
      { id: "m2", role: "assistant", content: "I found 3 potential issues:\n\n1. SQL injection in the query builder\n2. Missing input validation on the `userId` parameter\n3. No rate limiting on the endpoint", timestamp: "2026-05-01T09:00:05Z", model: "LongCat-Flash-Chat" },
    ],
    createdAt: "2026-05-01T09:00:00Z",
    provider: "longcat",
    model: "LongCat-Flash-Chat",
  },
  {
    id: "conv-2",
    title: "Architecture planning",
    messages: [
      { id: "m3", role: "user", content: "Design a microservices architecture for a payment system", timestamp: "2026-04-30T14:00:00Z" },
      { id: "m4", role: "assistant", content: "Here's a recommended architecture:\n\n- **Payment Gateway Service**: Handles payment processing\n- **Order Service**: Manages order lifecycle\n- **Notification Service**: Sends receipts and alerts\n- **Fraud Detection Service**: Real-time transaction scoring", timestamp: "2026-04-30T14:00:08Z", model: "deepseek-ai/deepseek-v4-pro" },
    ],
    createdAt: "2026-04-30T14:00:00Z",
    provider: "nvidia_nim",
    model: "deepseek-ai/deepseek-v4-pro",
  },
];

export const ChatPrimaryView = () => {
  const [conversations, setConversations] = useState<Conversation[]>(MOCK_CONVERSATIONS);
  const [activeConvId, setActiveConvId] = useState<string | null>("conv-1");
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const activeConv = conversations.find((c) => c.id === activeConvId) ?? null;

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [activeConv?.messages.length]);

  const handleSend = useCallback(() => {
    if (!input.trim() || !activeConvId) return;
    const userMsg: Message = {
      id: `m-${Date.now()}`,
      role: "user",
      content: input.trim(),
      timestamp: new Date().toISOString(),
    };
    setConversations((prev) =>
      prev.map((c) => c.id === activeConvId ? { ...c, messages: [...c.messages, userMsg] } : c)
    );
    setInput("");
    setIsTyping(true);

    setTimeout(() => {
      const assistantMsg: Message = {
        id: `m-${Date.now() + 1}`,
        role: "assistant",
        content: "This is a mock response. Wire up the AI provider to get real responses.",
        timestamp: new Date().toISOString(),
        model: activeConv?.model ?? "mock",
      };
      setConversations((prev) =>
        prev.map((c) => c.id === activeConvId ? { ...c, messages: [...c.messages, assistantMsg] } : c)
      );
      setIsTyping(false);
    }, 1200);
  }, [input, activeConvId, activeConv?.model]);

  const handleNewConversation = useCallback(() => {
    const newConv: Conversation = {
      id: `conv-${Date.now()}`,
      title: "New conversation",
      messages: [],
      createdAt: new Date().toISOString(),
    };
    setConversations((prev) => [newConv, ...prev]);
    setActiveConvId(newConv.id);
  }, []);

  return (
    <section className="chat-view" aria-label="Chat primary view">
      <aside className="chat-sidebar">
        <button type="button" className="chat-new-btn" onClick={handleNewConversation}>
          + New Chat
        </button>
        <div className="chat-conv-list">
          {conversations.map((c) => (
            <button
              key={c.id}
              type="button"
              className={`chat-conv-item${activeConvId === c.id ? " is-active" : ""}`}
              onClick={() => setActiveConvId(c.id)}
            >
              <span className="chat-conv-title">{c.title}</span>
              <span className="chat-conv-meta">{c.model ?? "no model"}</span>
            </button>
          ))}
        </div>
      </aside>
      <main className="chat-main">
        {activeConv ? (
          <>
            <header className="chat-header">
              <h3>{activeConv.title}</h3>
              <span className="chat-header-model">{activeConv.model ?? "Select a model"}</span>
            </header>
            <div className="chat-messages">
              {activeConv.messages.map((msg) => (
                <div key={msg.id} className={`chat-msg chat-msg--${msg.role}`}>
                  <span className="chat-msg-role">{msg.role === "user" ? "You" : msg.model ?? "AI"}</span>
                  <div className="chat-msg-content">{msg.content}</div>
                </div>
              ))}
              {isTyping && (
                <div className="chat-msg chat-msg--assistant">
                  <span className="chat-msg-role">AI</span>
                  <div className="chat-msg-content chat-msg-typing">Thinking...</div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
            <div className="chat-input-bar">
              <input
                className="chat-input"
                type="text"
                placeholder="Type a message..."
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter") handleSend(); }}
              />
              <button type="button" className="chat-send-btn" onClick={handleSend} disabled={!input.trim() || isTyping}>
                Send
              </button>
            </div>
          </>
        ) : (
          <div className="chat-empty">Select a conversation or start a new one.</div>
        )}
      </main>
    </section>
  );
};
