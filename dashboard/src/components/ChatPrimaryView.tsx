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
  const [modelDropdownOpen, setModelDropdownOpen] = useState(false);
  const [modelSearch, setModelSearch] = useState("");
  const modelDropdownRef = useRef<HTMLDivElement>(null);
  const [providerDropdownOpen, setProviderDropdownOpen] = useState(false);
  const [providerSearch, setProviderSearch] = useState("");
  const providerDropdownRef = useRef<HTMLDivElement>(null);
  const [repos, setRepos] = useState<string[]>([]);
  const [selectedRepo, setSelectedRepo] = useState("");
  const [repoDropdownOpen, setRepoDropdownOpen] = useState(false);
  const [repoSearch, setRepoSearch] = useState("");
  const repoDropdownRef = useRef<HTMLDivElement>(null);
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [imageError, setImageError] = useState("");
  const imageInputRef = useRef<HTMLInputElement>(null);
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
    if (!modelDropdownOpen) return;
    const handleClickOutside = (e: MouseEvent) => {
      if (modelDropdownRef.current && !modelDropdownRef.current.contains(e.target as Node)) {
        setModelDropdownOpen(false);
        setModelSearch("");
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [modelDropdownOpen]);

  useEffect(() => {
    if (!providerDropdownOpen) return;
    const handleClickOutside = (e: MouseEvent) => {
      if (providerDropdownRef.current && !providerDropdownRef.current.contains(e.target as Node)) {
        setProviderDropdownOpen(false);
        setProviderSearch("");
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [providerDropdownOpen]);

  useEffect(() => {
    fetch("/api/github/repos").then((r) => r.json()).then((d) => {
      const names = (d.repos ?? []).map((r: { name: string }) => r.name);
      setRepos(names);
      if (names.length > 0) setSelectedRepo(names[0]);
    }).catch(() => {});
  }, []);

  useEffect(() => {
    if (!repoDropdownOpen) return;
    const handleClickOutside = (e: MouseEvent) => {
      if (repoDropdownRef.current && !repoDropdownRef.current.contains(e.target as Node)) {
        setRepoDropdownOpen(false);
        setRepoSearch("");
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [repoDropdownOpen]);

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

  const VISION_PATTERNS = /vision|gpt-4o|gemini|claude-3|llava|pixtral|qwen-vl|internvl/i;

  const handleImageSelect = useCallback(() => {
    const supportsVision = VISION_PATTERNS.test(selectedModel);
    if (!supportsVision) {
      setImageError("This model does not support image inputs. Select a vision-capable model.");
      setTimeout(() => setImageError(""), 4000);
      return;
    }
    imageInputRef.current?.click();
  }, [selectedModel]);

  const handleImageChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setImageFile(file);
    const reader = new FileReader();
    reader.onload = () => setImagePreview(reader.result as string);
    reader.readAsDataURL(file);
    e.target.value = "";
  }, []);

  const handleRemoveImage = useCallback(() => {
    setImageFile(null);
    setImagePreview(null);
  }, []);

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
              <span className="chat-header-label">Model:</span>
              <div className="chat-model-dropdown" ref={providerDropdownRef}>
                <button
                  type="button"
                  className="chat-model-dropdown-trigger"
                  onClick={() => setProviderDropdownOpen((o) => !o)}
                >
                  {providerTypes.length === 0 ? "No providers" : `${selectedProviderType.replace("_", " ").toUpperCase()} (${providerTypes.find((g) => g.type === selectedProviderType)?.keyCount ?? 0} key${(providerTypes.find((g) => g.type === selectedProviderType)?.keyCount ?? 0) > 1 ? "s" : ""})`}
                  <span className="chat-model-dropdown-arrow">▾</span>
                </button>
                {providerDropdownOpen && (
                  <div className="chat-model-dropdown-panel">
                    <input
                      className="chat-model-dropdown-search"
                      type="text"
                      placeholder="Search providers..."
                      value={providerSearch}
                      onChange={(e) => setProviderSearch(e.target.value)}
                      autoFocus
                    />
                    <div className="chat-model-dropdown-list">
                      {providerTypes
                        .filter((g) => g.type.toLowerCase().includes(providerSearch.toLowerCase()))
                        .map((g) => (
                          <button
                            key={g.type}
                            type="button"
                            className={`chat-model-dropdown-item${g.type === selectedProviderType ? " is-active" : ""}`}
                            onClick={() => {
                              setSelectedProviderType(g.type);
                              setProviderDropdownOpen(false);
                              setProviderSearch("");
                            }}
                          >
                            {g.type.replace("_", " ").toUpperCase()} ({g.keyCount} key{g.keyCount > 1 ? "s" : ""})
                          </button>
                        ))}
                    </div>
                  </div>
                )}
              </div>
              <div className="chat-model-dropdown" ref={modelDropdownRef}>
                <button
                  type="button"
                  className="chat-model-dropdown-trigger"
                  onClick={() => { if (!modelsLoading) setModelDropdownOpen((o) => !o); }}
                  disabled={modelsLoading}
                >
                  {modelsLoading ? "Loading..." : (models.find((m) => m.id === selectedModel)?.name ?? "Select model")}
                  <span className="chat-model-dropdown-arrow">▾</span>
                </button>
                {modelDropdownOpen && (
                  <div className="chat-model-dropdown-panel">
                    <input
                      className="chat-model-dropdown-search"
                      type="text"
                      placeholder="Search models..."
                      value={modelSearch}
                      onChange={(e) => setModelSearch(e.target.value)}
                      autoFocus
                    />
                    <div className="chat-model-dropdown-list">
                      {models
                        .filter((m) => m.name.toLowerCase().includes(modelSearch.toLowerCase()))
                        .map((m) => (
                          <button
                            key={m.id}
                            type="button"
                            className={`chat-model-dropdown-item${m.id === selectedModel ? " is-active" : ""}`}
                            onClick={() => {
                              setSelectedModel(m.id);
                              setConversations((prev) => prev.map((c) => c.id === activeConvId ? { ...c, model: m.id, providerId: selectedProviderType } : c));
                              setModelDropdownOpen(false);
                              setModelSearch("");
                            }}
                          >
                            {m.name}
                          </button>
                        ))}
                    </div>
                  </div>
                )}
              </div>
              <div className="chat-header-spacer" />
              <span className="chat-header-label">Repo:</span>
              <div className="chat-model-dropdown" ref={repoDropdownRef}>
                <button
                  type="button"
                  className="chat-model-dropdown-trigger"
                  onClick={() => setRepoDropdownOpen((o) => !o)}
                >
                  {selectedRepo || "Select repo"}
                  <span className="chat-model-dropdown-arrow">▾</span>
                </button>
                {repoDropdownOpen && (
                  <div className="chat-model-dropdown-panel">
                    <input
                      className="chat-model-dropdown-search"
                      type="text"
                      placeholder="Search repos..."
                      value={repoSearch}
                      onChange={(e) => setRepoSearch(e.target.value)}
                      autoFocus
                    />
                    <div className="chat-model-dropdown-list">
                      {repos
                        .filter((r) => r.toLowerCase().includes(repoSearch.toLowerCase()))
                        .map((r) => (
                          <button
                            key={r}
                            type="button"
                            className={`chat-model-dropdown-item${r === selectedRepo ? " is-active" : ""}`}
                            onClick={() => {
                              setSelectedRepo(r);
                              setRepoDropdownOpen(false);
                              setRepoSearch("");
                            }}
                          >
                            {r}
                          </button>
                        ))}
                    </div>
                  </div>
                )}
              </div>
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
                ref={imageInputRef}
                type="file"
                accept="image/*"
                className="chat-image-input-hidden"
                onChange={handleImageChange}
              />
              <button type="button" className="chat-image-btn" onClick={handleImageSelect} title="Attach image">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
                  <circle cx="8.5" cy="8.5" r="1.5" />
                  <polyline points="21 15 16 10 5 21" />
                </svg>
              </button>
              {imagePreview && (
                <div className="chat-image-preview">
                  <img src={imagePreview} alt="Attached" />
                  <button type="button" className="chat-image-remove" onClick={handleRemoveImage}>x</button>
                </div>
              )}
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
            {imageError && (
              <div className="chat-image-error">{imageError}</div>
            )}
          </>
        ) : (
          <div className="chat-empty">Select a conversation or start a new one.</div>
        )}
      </main>
    </section>
  );
};
