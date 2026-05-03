import { useCallback, useEffect, useRef, useState } from "react";
import { TaskListPanel } from "./TaskListPanel";
import { useLiveTaskStatus } from "../app/hooks/useLiveTaskStatus";
import { SearchableDropdown } from "./chat/SearchableDropdown";
import { useExecutionActions } from "./chat/useExecutionActions";

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

type ProviderGroup = { type: string; keyCount: number; ids: string[] };

export const ChatPrimaryView = () => {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConvId, setActiveConvId] = useState<string | null>(null);
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const [providerTypes, setProviderTypes] = useState<ProviderGroup[]>([]);
  const [selectedProviderType, setSelectedProviderType] = useState("");
  const [models, setModels] = useState<{ id: string; name: string }[]>([]);
  const [selectedModel, setSelectedModel] = useState("");
  const [modelsLoading, setModelsLoading] = useState(false);
  const [repos, setRepos] = useState<string[]>([]);
  const [selectedRepo, setSelectedRepo] = useState("");
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const imageInputRef = useRef<HTMLInputElement>(null);
  const [mode, setMode] = useState<"ask" | "plan" | "build" | "auto">("ask");
  const [isStarted, setIsStarted] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [usage, setUsage] = useState({ tokensUsed: 0, tokensLimit: 0, rpmLimit: 40, requestsToday: 0 });
  const [chatSearch, setChatSearch] = useState("");

  const tasks = useLiveTaskStatus();
  const activeConv = conversations.find((c) => c.id === activeConvId) ?? null;

  const exec = useExecutionActions(
    activeConv, activeConvId, selectedRepo,
    selectedProviderType, selectedModel, setConversations, setMode,
  );

  const fetchConversations = useCallback(() => {
    fetch("/api/conversations").then((r) => r.json()).then((d) => {
      const convs = (d.conversations ?? []).map((c: any) => ({
        id: c.id, title: c.title || "Untitled", messages: [], createdAt: c.created_at, model: c.model,
      }));
      if (convs.length > 0) { setConversations(convs); setActiveConvId(convs[0].id); }
    }).catch(() => {});
  }, []);

  useEffect(() => { fetchConversations(); }, [fetchConversations]);

  useEffect(() => {
    fetch("/api/providers").then((r) => r.json()).then((d) => {
      const enabled = (d.providers ?? []).filter((p: any) => p.enabled);
      const grouped: Record<string, ProviderGroup> = {};
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
      setUsage((u) => ({ ...u, rpmLimit: (lim.rpm ?? 40) * group.keyCount, tokensLimit: (lim.rpd ?? 0) * group.keyCount }));
    }).catch(() => {}).finally(() => setModelsLoading(false));
  }, [selectedProviderType, providerTypes]);

  useEffect(() => {
    fetch("/api/github/repos").then((r) => r.json()).then((d) => {
      const names = (d.repos ?? []).map((r: { name: string }) => r.name);
      setRepos(names);
      if (names.length > 0) setSelectedRepo(names[0]);
    }).catch(() => {});
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [activeConv?.messages.length]);

  const handleSend = useCallback(() => {
    if (!input.trim() || !activeConvId) return;
    const userMsg: Message = { id: `m-${Date.now()}`, role: "user", content: input.trim(), timestamp: new Date().toISOString() };
    setConversations((prev) => prev.map((c) => c.id === activeConvId ? { ...c, messages: [...c.messages, userMsg] } : c));
    const currentInput = input.trim();
    setInput("");
    setIsTyping(true);
    setUsage((u) => ({ ...u, requestsToday: u.requestsToday + 1, tokensUsed: u.tokensUsed + currentInput.length }));

    fetch(`/api/conversations/${activeConvId}/messages`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ role: "user", content: currentInput }),
    }).catch(() => {});

    const conv = conversations.find((c) => c.id === activeConvId);
    const history = [...(conv?.messages ?? []), { role: "user", content: currentInput }]
      .map((m) => ({ role: m.role, content: m.content }));

    fetch("/api/chat/send", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        provider_type: selectedProviderType, model: selectedModel, messages: history,
        image_base64: imagePreview ?? undefined,
        repo: selectedRepo ? `iceyxsm/${selectedRepo}` : undefined, mode,
      }),
    })
      .then((r) => r.json())
      .then((data) => {
        const content = data.response ?? data.detail ?? "No response";
        const assistantMsg: Message = { id: `m-${Date.now() + 1}`, role: "assistant", content, timestamp: new Date().toISOString(), model: selectedModel };
        setConversations((prev) => prev.map((c) => c.id === activeConvId ? { ...c, messages: [...c.messages, assistantMsg] } : c));
        setUsage((u) => ({ ...u, tokensUsed: u.tokensUsed + content.length }));
        // Detect plan JSON in AI response to enable the Approve button
        if (mode === "plan" && (content.includes('"tasks"') || content.includes('"execution_mode"'))) {
          exec.setPlanReady(true);
        }
        fetch(`/api/conversations/${activeConvId}/messages`, {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ role: "assistant", content }),
        }).catch(() => {});
      })
      .catch(() => {
        const errMsg: Message = { id: `m-${Date.now() + 1}`, role: "assistant", content: "Failed to get response. Check backend.", timestamp: new Date().toISOString() };
        setConversations((prev) => prev.map((c) => c.id === activeConvId ? { ...c, messages: [...c.messages, errMsg] } : c));
      })
      .finally(() => { setIsTyping(false); setImagePreview(null); });
  }, [input, activeConvId, selectedModel, selectedProviderType, conversations, imagePreview, mode, exec]);

  const handleStart = useCallback(() => {
    if (!selectedRepo || !selectedProviderType || !selectedModel || !activeConvId) return;
    setIsAnalyzing(true);
    fetch(`/api/repos/iceyxsm/${selectedRepo}/analyze`, { method: "POST" })
      .then((r) => r.json())
      .then((data) => {
        if (!data.xml) throw new Error(data.detail ?? "Analysis failed");
        return fetch("/api/chat/send", {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            provider_type: selectedProviderType, model: selectedModel,
            messages: [{ role: "user", content: "Analyze this repo and give me a structured summary: project name, tech stack, structure, and what it does." }],
            system: `Analyze this codebase and provide a structured summary:\n\n${data.xml.slice(0, 80000)}`,
            repo: `iceyxsm/${selectedRepo}`,
          }),
        });
      })
      .then((r) => r?.json())
      .then((data) => {
        if (data?.response) {
          const msg: Message = { id: `m-${Date.now()}`, role: "assistant", content: data.response, timestamp: new Date().toISOString(), model: selectedModel };
          setConversations((prev) => prev.map((c) => c.id === activeConvId ? { ...c, messages: [...c.messages, msg] } : c));
          setIsStarted(true);
        }
      })
      .catch((e) => {
        const errMsg: Message = { id: `m-${Date.now()}`, role: "assistant", content: `Start failed: ${e.message}`, timestamp: new Date().toISOString() };
        setConversations((prev) => prev.map((c) => c.id === activeConvId ? { ...c, messages: [...c.messages, errMsg] } : c));
      })
      .finally(() => setIsAnalyzing(false));
  }, [selectedRepo, selectedProviderType, selectedModel, activeConvId]);

  const handleNewConversation = useCallback(() => {
    const newConv: Conversation = { id: `conv-${Date.now()}`, title: "New conversation", messages: [], createdAt: new Date().toISOString() };
    setConversations((prev) => [newConv, ...prev]);
    setActiveConvId(newConv.id);
    setIsStarted(false);
    exec.resetExecution();
  }, [exec]);

  const handleImageChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => setImagePreview(reader.result as string);
    reader.readAsDataURL(file);
    e.target.value = "";
  }, []);

  const providerItems = providerTypes.map((g) => ({
    id: g.type,
    label: `${g.type.replace("_", " ").toUpperCase()} (${g.keyCount} key${g.keyCount > 1 ? "s" : ""})`,
  }));
  const modelItems = models.map((m) => ({ id: m.id, label: m.name }));
  const repoItems = repos.map((r) => ({ id: r, label: r }));
  const showTasks = (mode === "plan" || mode === "build" || mode === "auto") && tasks.length > 0;
  const hasExistingMessages = (activeConv?.messages.length ?? 0) > 0;
  const chatEnabled = isStarted || hasExistingMessages;

  const hasProviders = providerTypes.length > 0;

  return (
    <section className="chat-view" aria-label="Chat primary view" style={{ position: "relative" }}>
      {!hasProviders && (
        <div className="apis-setup-overlay">
          <div className="apis-setup-card">
            <h3>AI Provider Key Required</h3>
            <p>Add at least one AI provider API key to start chatting. Free options include Groq, Google AI Studio, and NVIDIA NIM.</p>
            <button type="button" className="apis-setup-btn" onClick={() => { window.dispatchEvent(new CustomEvent("navigate", { detail: 6 })); }}>
              Go to APIs
            </button>
          </div>
        </div>
      )}
      <aside className="chat-sidebar">
        <div className="chat-sidebar-toolbar">
          <button type="button" className="chat-new-btn" onClick={handleNewConversation}>+ New Chat</button>
          <button type="button" className="chat-refresh-btn" onClick={fetchConversations} aria-label="Refresh chats">R</button>
        </div>
        <input className="chat-search" type="text" placeholder="Search chats..." value={chatSearch} onChange={(e) => setChatSearch(e.target.value)} />
        <div className="chat-conv-list">
          {conversations.filter((c) => c.title.toLowerCase().includes(chatSearch.toLowerCase())).map((c) => (
            <button key={c.id} type="button" className={`chat-conv-item${activeConvId === c.id ? " is-active" : ""}`} onClick={() => setActiveConvId(c.id)}>
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
              <SearchableDropdown items={providerItems} selected={selectedProviderType} onSelect={setSelectedProviderType} placeholder="No providers" searchPlaceholder="Search providers..." />
              <SearchableDropdown items={modelItems} selected={selectedModel} onSelect={setSelectedModel} placeholder="Select model" searchPlaceholder="Search models..." disabled={modelsLoading} />
              <div className="chat-header-spacer" />
              <span className="chat-header-label">Repo:</span>
              <SearchableDropdown items={repoItems} selected={selectedRepo} onSelect={setSelectedRepo} placeholder="Select repo" searchPlaceholder="Search repos..." />
              <div className="chat-header-spacer" />
              <div className="chat-mode-selector">
                {(["ask", "plan", "build"] as const).map((m) => (
                  <button key={m} type="button" className={`chat-mode-btn${mode === m ? " is-active" : ""}`} onClick={() => setMode(m)}>{m.toUpperCase()}</button>
                ))}
                <button type="button" className={`chat-mode-btn${mode === "auto" ? " is-active" : ""}`} onClick={exec.handleAutoMode} disabled={!selectedRepo || !selectedModel || exec.isExecuting}>AUTO</button>
              </div>
              {exec.planReady && !exec.isExecuting && (
                <button type="button" className="chat-approve-btn" onClick={exec.handleApprove}>Approve Plan</button>
              )}
              {exec.executionStatus && <span className="chat-exec-status">{exec.executionStatus}</span>}
              {!isStarted && (
                <button type="button" className="chat-start-btn" onClick={handleStart} disabled={!selectedRepo || !selectedModel || isAnalyzing}>
                  {isAnalyzing ? "Analyzing..." : "Start"}
                </button>
              )}
              <div className="chat-usage-stats">
                <div className="chat-usage-bar-group">
                  <span className="chat-usage-label">Tokens</span>
                  <div className="chat-usage-bar"><div className="chat-usage-bar-fill" style={{ width: `${usage.tokensLimit > 0 ? Math.max(0, 100 - (usage.tokensUsed / usage.tokensLimit) * 100) : 100}%` }} /></div>
                  <span className="chat-usage-value">{usage.tokensUsed.toLocaleString()}{usage.tokensLimit > 0 ? `/${usage.tokensLimit.toLocaleString()}` : ""}</span>
                </div>
                <div className="chat-usage-bar-group">
                  <span className="chat-usage-label">RPM</span>
                  <div className="chat-usage-bar"><div className="chat-usage-bar-fill" style={{ width: `${Math.max(0, 100 - (usage.requestsToday / usage.rpmLimit) * 100)}%` }} /></div>
                  <span className="chat-usage-value">{usage.requestsToday}/{usage.rpmLimit}</span>
                </div>
              </div>
            </header>
            <div className="chat-body-row">
              <div className="chat-messages">
                {isAnalyzing && (
                  <div className="chat-setup-overlay">
                    <div className="chat-setup-spinner" />
                    <span className="chat-setup-text">Setting up — analyzing repository...</span>
                  </div>
                )}
                {!chatEnabled && !isAnalyzing && activeConv.messages.length === 0 && (
                  <div className="chat-setup-overlay">
                    <span className="chat-setup-text">Select a repo and click Start to begin</span>
                  </div>
                )}
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
              <TaskListPanel tasks={tasks} visible={showTasks} />
            </div>
            <div className={`chat-input-bar${!chatEnabled ? " chat-input-bar--disabled" : ""}`}>
              <input ref={imageInputRef} type="file" accept="image/*" className="chat-image-input-hidden" onChange={handleImageChange} />
              <button type="button" className="chat-image-btn" onClick={() => imageInputRef.current?.click()} title="Attach image">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
                  <circle cx="8.5" cy="8.5" r="1.5" />
                  <polyline points="21 15 16 10 5 21" />
                </svg>
              </button>
              {imagePreview && (
                <div className="chat-image-preview">
                  <img src={imagePreview} alt="Attached" />
                  <button type="button" className="chat-image-remove" onClick={() => setImagePreview(null)}>x</button>
                </div>
              )}
              <input className="chat-input" type="text" placeholder={chatEnabled ? "Type a message..." : "Click Start to begin"} value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter") handleSend(); }} disabled={!chatEnabled} />
              <button type="button" className="chat-send-btn" onClick={handleSend} disabled={!input.trim() || isTyping || !chatEnabled}>Send</button>
            </div>
          </>
        ) : (
          <div className="chat-empty">Select a conversation or start a new one.</div>
        )}
      </main>
    </section>
  );
};
