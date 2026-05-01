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
  providerId?: string;
  model?: string;
};

type ProviderInfo = { id: string; name: string; provider_type: string; enabled: boolean };

const MOCK_CONVERSATIONS: Conversation[] = [
  {
    id: "conv-1",
    title: "Code review discussion",
    messages: [
      { id: "m1", role: "user", content: "Review this function for security issues", timestamp: "2026-05-01T09:00:00Z" },
      { id: "m2", role: "assistant", content: "I found 3 potential issues:\n\n1. SQL injection in the query builder\n2. Missing input validation on the `userId` parameter\n3. No rate limiting on the endpoint", timestamp: "2026-05-01T09:00:05Z", model: "LongCat-Flash-Chat" },
    ],
    createdAt: "2026-05-01T09:00:00Z",
    providerId: "longcat-1",
    model: "LongCat-Flash-Chat",
  },
];

export const ChatPrimaryView = () => {
  const [conversations, setConversations] = useState<Conversation[]>(MOCK_CONVERSATIONS);
  const [activeConvId, setActiveConvId] = useState<string | null>("conv-1");
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const [providers, setProviders] = useState<ProviderInfo[]>([]);
  const [selectedProviderId, setSelectedProviderId] = useState("");
  const [models, setModels] = useState<{ id: string; name: string }[]>([]);
  const [selectedModel, setSelectedModel] = useState("");
  const [modelsLoading, setModelsLoading] = useState(false);
  const [usage, setUsage] = useState({ tokensUsed: 0, tokensLimit: 0, rpm: 0, rpmLimit: 40, requestsToday: 0, resetIn: "24h" });

  const activeConv = conversations.find((c) => c.id === activeConvId) ?? null;

  useEffect(() => {
    fetch("/api/providers").then((r) => r.json()).then((d) => {
      const enabled = (d.providers ?? []).filter((p: ProviderInfo) => p.enabled);
      setProviders(enabled);
      if (enabled.length > 0 && !selectedProviderId) setSelectedProviderId(enabled[0].id);
    }).catch(() => {});
  }, []);

  useEffect(() => {
    if (!selectedProviderId) return;
    setModelsLoading(true);
    setModels([]);
    fetch(`/api/providers/${selectedProviderId}/models`).then((r) => r.json()).then((d) => {
      setModels(d.models ?? []);
      if (d.models?.length > 0) setSelectedModel(d.models[0].id);
      const lim = d.limits ?? {};
      setUsage((u) => ({ ...u, rpmLimit: lim.rpm ?? 40, tokensLimit: lim.rpd ?? 0 }));
    }).catch(() => {}).finally(() => setModelsLoading(false));
  }, [selectedProviderId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [activeConv?.messages.length]);

  const handleSend = useCallback(() => {
    if (!input.trim() || !activeConvId) return;
    const userMsg: Message = { id: `m-${Date.now()}`, role: "user", content: input.trim(), timestamp: new Date().toISOString() };
    setConversations((prev) => prev.map((c) => c.id === activeConvId ? { ...c, messages: [...c.messages, userMsg] } : c));
    setInput("");
    setIsTyping(true);
    setUsage((u) => ({ ...u, requestsToday: u.requestsToday + 1, tokensUsed: u.tokensUsed + input.length }));

    setTimeout(() => {
      const assistantMsg: Message = { id: `m-${Date.now() + 1}`, role: "assistant", content: "Mock response. Wire provider to get real answers.", timestamp: new Date().toISOString(), model: selectedModel };
      setConversations((prev) => prev.map((c) => c.id === activeConvId ? { ...c, messages: [...c.messages, assistantMsg] } : c));
      setIsTyping(false);
      setUsage((u) => ({ ...u, tokensUsed: u.tokensUsed + 50 }));
    }, 1200);
  }, [input, activeConvId, selectedModel]);

  const handleNewConversation = useCallback(() => {
    const newConv: Conversation = { id: `conv-${Date.now()}`, title: "New conversation", messages: [], createdAt: new Date().toISOString() };
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
              <select className="chat-provider-select" value={selectedProviderId} onChange={(e) => setSelectedProviderId(e.target.value)}>
                {providers.map((p) => <option key={p.id} value={p.id}>{p.provider_type} — {p.name}</option>)}
              </select>
              <select className="chat-model-select" value={selectedModel} onChange={(e) => setSelectedModel(e.target.value)} disabled={modelsLoading}>
                {modelsLoading ? <option>Loading...</option> : models.map((m) => <option key={m.id} value={m.id}>{m.name}</option>)}
              </select>
              <div className="chat-usage-stats">
                <span className="chat-usage-item">Tokens: {usage.tokensUsed.toLocaleString()}{usage.tokensLimit > 0 ? `/${usage.tokensLimit.toLocaleString()}` : ""}</span>
                <span className="chat-usage-item">RPM: {usage.requestsToday}/{usage.rpmLimit}</span>
                <span className="chat-usage-item">Reset: {usage.resetIn}</span>
              </div>
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
