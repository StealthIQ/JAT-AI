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

  const [providerTypes, setProviderTypes] = useState<{ type: string; keyCount: number; ids: string[] }[]>([]);
  const [selectedProviderType, setSelectedProviderType] = useState("");
  const [models, setModels] = useState<{ id: string; name: string }[]>([]);
  const [selectedModel, setSelectedModel] = useState("");
  const [modelsLoading, setModelsLoading] = useState(false);
  const [usage, setUsage] = useState({ tokensUsed: 0, tokensLimit: 0, rpm: 0, rpmLimit: 40, requestsToday: 0, resetIn: "24h" });

  const activeConv = conversations.find((c) => c.id === activeConvId) ?? null;

  useEffect(() => {
    fetch("/api/providers").then((r) => r.json()).then((d) => {
      const enabled = (d.providers ?? []).filter((p: ProviderInfo) => p.enabled);
      const grouped: Record<string, { type: string; keyCount: number; ids: string[] }> = {};
      for (const p of enabled) {
        if (!grouped[p.provider_type]) grouped[p.provider_type] = { type: p.provider_type, keyCount: 0, ids: [] };
        grouped[p.provider_type].keyCount++;
        grouped[p.provider_type].ids.push(p.id);
      }
      const types = Object.values(grouped);
      setProviderTypes(types);
      if (types.length > 0 && !selectedProviderType) setSelectedProviderType(types[0].type);
    }).catch(() => {});
  }, []);

  useEffect(() => {
    if (!selectedProviderType) return;
    const group = providerTypes.find((g) => g.type === selectedProviderType);
    if (!group || group.ids.length === 0) return;
    setModelsLoading(true);
    setModels([]);
    fetch(`/api/providers/${group.ids[0]}/models`).then((r) => r.json()).then((d) => {
      setModels(d.models ?? []);
      if (d.models?.length > 0) setSelectedModel(d.models[0].id);
      const lim = d.limits ?? {};
      const keyCount = group.keyCount;
      setUsage((u) => ({ ...u, rpmLimit: (lim.rpm ?? 40) * keyCount, tokensLimit: (lim.rpd ?? 0) * keyCount }));
    }).catch(() => {}).finally(() => setModelsLoading(false));
  }, [selectedProviderType, providerTypes]);

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
              <select className="chat-provider-select" value={selectedProviderType} onChange={(e) => { setSelectedProviderType(e.target.value); }}>
                {providerTypes.length === 0 && <option value="">No providers</option>}
                {providerTypes.map((g) => <option key={g.type} value={g.type}>{g.type.replace("_", " ").toUpperCase()} ({g.keyCount} key{g.keyCount > 1 ? "s" : ""})</option>)}
              </select>
              <select className="chat-model-select" value={selectedModel} onChange={(e) => {
                setSelectedModel(e.target.value);
                setConversations((prev) => prev.map((c) => c.id === activeConvId ? { ...c, model: e.target.value, providerId: selectedProviderType } : c));
              }} disabled={modelsLoading}>
                {modelsLoading ? <option>Loading...</option> : models.map((m) => <option key={m.id} value={m.id}>{m.name}</option>)}
              </select>
              <div className="chat-usage-stats">
                <div className="chat-usage-bar-group">
                  <span className="chat-usage-label">Tokens</span>
                  <div className="chat-usage-bar">
                    <div className="chat-usage-bar-fill" style={{ width: `${usage.tokensLimit > 0 ? Math.max(0, 100 - (usage.tokensUsed / usage.tokensLimit) * 100) : 100}%` }} />
                  </div>
                  <span className="chat-usage-value">{usage.tokensUsed.toLocaleString()}{usage.tokensLimit > 0 ? `/${usage.tokensLimit.toLocaleString()}` : ""}</span>
                </div>
                <div className="chat-usage-bar-group">
                  <span className="chat-usage-label">RPM</span>
                  <div className="chat-usage-bar">
                    <div className="chat-usage-bar-fill" style={{ width: `${Math.max(0, 100 - (usage.requestsToday / usage.rpmLimit) * 100)}%` }} />
                  </div>
                  <span className="chat-usage-value">{usage.requestsToday}/{usage.rpmLimit}</span>
                </div>
                <span className="chat-usage-reset">Reset: {usage.resetIn}</span>
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
