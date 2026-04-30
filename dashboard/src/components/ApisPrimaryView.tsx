import { useCallback, useEffect, useState } from "react";

type Provider = {
  id: string;
  provider_type: string;
  name: string;
  model: string;
  base_url: string;
  enabled: boolean;
  daily_limit: number;
  has_key: boolean;
};

const PROVIDER_TYPES = [
  "groq",
  "google",
  "cloudflare",
  "openrouter",
  "ollama",
  "cerebras",
  "cohere",
  "mistral",
  "nvidia_nim",
  "github_models",
  "huggingface",
  "sambanova",
  "fireworks",
  "nebius",
  "hyperbolic",
  "scaleway",
  "longcat",
];

export const ApisPrimaryView = () => {
  const [providers, setProviders] = useState<Provider[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [formType, setFormType] = useState("groq");
  const [formName, setFormName] = useState("");
  const [formKey, setFormKey] = useState("");
  const [loading, setLoading] = useState(false);

  const fetchProviders = useCallback(async () => {
    const res = await fetch("/api/providers");
    if (res.ok) {
      const data = await res.json();
      setProviders(data.providers || []);
    }
  }, []);

  useEffect(() => { void fetchProviders(); }, [fetchProviders]);

  const [successMsg, setSuccessMsg] = useState("");

  const handleAdd = async () => {
    setLoading(true);
    await fetch("/api/providers", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        provider_type: formType,
        name: formName,
        api_key: formKey,
      }),
    });
    setShowForm(false);
    setFormName("");
    setFormKey("");
    setLoading(false);
    setSuccessMsg(`${formType} key "${formName}" added successfully`);
    setTimeout(() => setSuccessMsg(""), 4000);
    void fetchProviders();
  };

  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);
  const [confirmInput, setConfirmInput] = useState("");
  const [confirmDisableId, setConfirmDisableId] = useState<string | null>(null);
  const [confirmEnableId, setConfirmEnableId] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [filterType, setFilterType] = useState("");
  const [filterStatus, setFilterStatus] = useState("");
  const [testProviderId, setTestProviderId] = useState<string | null>(null);
  const [testModels, setTestModels] = useState<any[]>([]);
  const [testLimits, setTestLimits] = useState<any>({});
  const [testSelectedModel, setTestSelectedModel] = useState("");
  const [testMessage, setTestMessage] = useState("");
  const [testResponse, setTestResponse] = useState("");
  const [testLoading, setTestLoading] = useState(false);

  const handleDelete = async (id: string) => {
    await fetch(`/api/providers/${id}`, { method: "DELETE" });
    setConfirmDeleteId(null);
    setConfirmInput("");
    void fetchProviders();
  };

  const handleToggle = async (id: string, enabled: boolean) => {
    await fetch(`/api/providers/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ enabled: !enabled }),
    });
    void fetchProviders();
  };

  const openTest = async (id: string) => {
    setTestProviderId(id);
    setTestModels([]);
    setTestLimits({});
    setTestSelectedModel("");
    setTestResponse("");
    const res = await fetch(`/api/providers/${id}/models`);
    if (res.ok) {
      const data = await res.json();
      setTestModels(data.models || []);
      setTestLimits(data.limits || {});
      if (data.models?.length > 0) setTestSelectedModel(data.models[0].id);
    }
  };

  const handleTestChat = async () => {
    if (!testProviderId || !testSelectedModel || !testMessage) return;
    setTestLoading(true);
    setTestResponse("");
    const res = await fetch(`/api/providers/${testProviderId}/test`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ model: testSelectedModel, message: testMessage }),
    });
    if (res.ok) {
      const data = await res.json();
      setTestResponse(data.response || "");
    } else {
      const err = await res.json().catch(() => ({}));
      setTestResponse(`Error: ${err.detail || res.statusText}`);
    }
    setTestLoading(false);
  };

  return (
    <section className="apis-view">
      <header className="apis-header">
        <h2 className="apis-title">API Providers</h2>
        <div className="apis-toolbar">
          <input
            className="apis-search"
            placeholder="Search providers..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <select className="apis-filter" value={filterStatus} onChange={(e) => setFilterStatus(e.target.value)}>
            <option value="">All status</option>
            <option value="enabled">Enabled</option>
            <option value="disabled">Disabled</option>
          </select>
          <select className="apis-filter" value={filterType} onChange={(e) => setFilterType(e.target.value)}>
            <option value="">All types</option>
            {PROVIDER_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
          </select>
        </div>
        <button
          type="button"
          className="apis-add-btn"
          onClick={() => setShowForm((v) => !v)}
        >
          {showForm ? "Cancel" : "+ Add Provider"}
        </button>
      </header>

      {successMsg && <div className="apis-success">{successMsg}</div>}

      {showForm && (
        <div className="apis-overlay" onMouseDown={(e) => { if (e.target === e.currentTarget) setShowForm(false); }}>
          <div className="apis-popup">
            <header className="apis-popup-header">
              <h3>Add Provider</h3>
              <button type="button" className="apis-popup-close" onClick={() => setShowForm(false)}>X</button>
            </header>
            <div className="apis-popup-body">
              <label className="apis-field">
                <span>Provider</span>
                <div className="apis-custom-select">
                  <button type="button" className="apis-custom-select-trigger" onClick={(e) => {
                    const list = (e.currentTarget.nextElementSibling as HTMLElement);
                    list.style.display = list.style.display === "block" ? "none" : "block";
                  }}>
                    {formType} <span className="apis-custom-select-arrow">v</span>
                  </button>
                  <div className="apis-custom-select-options">
                    {PROVIDER_TYPES.map((t) => (
                      <button
                        key={t}
                        type="button"
                        className={`apis-custom-select-option${t === formType ? " apis-custom-select-option--active" : ""}`}
                        onClick={(e) => {
                          setFormType(t);
                          ((e.currentTarget.parentElement) as HTMLElement).style.display = "none";
                        }}
                      >
                        {t}
                      </button>
                    ))}
                  </div>
                </div>
              </label>
              <label className="apis-field">
                <span>Name</span>
                <input placeholder="e.g. my-groq-key" value={formName} onChange={(e) => setFormName(e.target.value)} />
              </label>
              <label className="apis-field">
                <span>API Key</span>
                <input placeholder="Paste your key here" type="password" value={formKey} onChange={(e) => setFormKey(e.target.value)} />
              </label>
            </div>
            <footer className="apis-popup-footer">
              <button type="button" className="apis-popup-cancel" onClick={() => setShowForm(false)}>Cancel</button>
              <button type="button" className="apis-submit-btn" disabled={loading || !formName || !formKey} onClick={() => void handleAdd()}>
                {loading ? "Saving..." : "Save"}
              </button>
            </footer>
          </div>
        </div>
      )}

      <div className="apis-list">
        {providers.filter((p) => {
          if (search && !p.name.toLowerCase().includes(search.toLowerCase()) && !p.provider_type.includes(search.toLowerCase())) return false;
          if (filterStatus === "enabled" && !p.enabled) return false;
          if (filterStatus === "disabled" && p.enabled) return false;
          if (filterType && p.provider_type !== filterType) return false;
          return true;
        }).length === 0 && <p className="apis-empty">No providers configured yet.</p>}
        {providers.filter((p) => {
          if (search && !p.name.toLowerCase().includes(search.toLowerCase()) && !p.provider_type.includes(search.toLowerCase())) return false;
          if (filterStatus === "enabled" && !p.enabled) return false;
          if (filterStatus === "disabled" && p.enabled) return false;
          if (filterType && p.provider_type !== filterType) return false;
          return true;
        }).map((p) => (
          <div key={p.id} className="apis-card" data-enabled={p.enabled}>
            <div className="apis-card-header">
              <span className="apis-card-type">{p.provider_type}</span>
              <span className="apis-card-name">{p.name}</span>
              <span className={`apis-card-status ${p.enabled ? "apis-card-status--on" : "apis-card-status--off"}`}>
                {p.enabled ? "active" : "disabled"}
              </span>
            </div>
            <div className="apis-card-details">
              <span>Limit: {p.daily_limit || "unlimited"}/day</span>
            </div>
            <div className="apis-card-actions">
              <button type="button" onClick={() => {
                if (p.enabled) setConfirmDisableId(p.id);
                else setConfirmEnableId(p.id);
              }}>
                {p.enabled ? "Disable" : "Enable"}
              </button>
              <button type="button" onClick={async () => {
                const res = await fetch(`/api/providers/${p.id}/docs`);
                const data = await res.json();
                if (data.url) window.open(data.url, "_blank");
              }}>
                Docs
              </button>
              <button type="button" onClick={() => void openTest(p.id)}>
                Test
              </button>
              <button type="button" className="apis-card-delete" onClick={() => setConfirmDeleteId(p.id)}>
                Remove
              </button>
            </div>
          </div>
        ))}
      </div>

      {confirmDeleteId && (
        <div className="apis-overlay" onMouseDown={(e) => { if (e.target === e.currentTarget) { setConfirmDeleteId(null); setConfirmInput(""); } }}>
          <div className="apis-popup apis-popup--narrow">
            <header className="apis-popup-header">
              <h3>Confirm Removal</h3>
              <button type="button" className="apis-popup-close" onClick={() => { setConfirmDeleteId(null); setConfirmInput(""); }}>X</button>
            </header>
            <div className="apis-popup-body">
              <p className="apis-confirm-text">Type <strong>confirm</strong> to remove this provider permanently.</p>
              <input
                className="apis-confirm-input"
                placeholder="Type confirm"
                value={confirmInput}
                onChange={(e) => setConfirmInput(e.target.value)}
                autoFocus
              />
            </div>
            <footer className="apis-popup-footer">
              <button type="button" className="apis-popup-cancel" onClick={() => { setConfirmDeleteId(null); setConfirmInput(""); }}>Cancel</button>
              <button
                type="button"
                className="apis-submit-btn apis-submit-btn--danger"
                disabled={confirmInput !== "confirm"}
                onClick={() => void handleDelete(confirmDeleteId)}
              >
                Remove
              </button>
            </footer>
          </div>
        </div>
      )}

      {confirmDisableId && (
        <div className="apis-overlay" onMouseDown={(e) => { if (e.target === e.currentTarget) setConfirmDisableId(null); }}>
          <div className="apis-popup apis-popup--narrow">
            <header className="apis-popup-header">
              <h3>Disable Provider</h3>
              <button type="button" className="apis-popup-close" onClick={() => setConfirmDisableId(null)}>X</button>
            </header>
            <div className="apis-popup-body">
              <p className="apis-confirm-text">Do you want to disable this API? It will no longer be used for requests until re-enabled.</p>
            </div>
            <footer className="apis-popup-footer">
              <button type="button" className="apis-popup-cancel" onClick={() => setConfirmDisableId(null)}>Cancel</button>
              <button
                type="button"
                className="apis-submit-btn apis-submit-btn--danger"
                onClick={() => { void handleToggle(confirmDisableId, true); setConfirmDisableId(null); }}
              >
                Disable
              </button>
            </footer>
          </div>
        </div>
      )}

      {confirmEnableId && (
        <div className="apis-overlay" onMouseDown={(e) => { if (e.target === e.currentTarget) setConfirmEnableId(null); }}>
          <div className="apis-popup apis-popup--narrow">
            <header className="apis-popup-header">
              <h3>Enable Provider</h3>
              <button type="button" className="apis-popup-close" onClick={() => setConfirmEnableId(null)}>X</button>
            </header>
            <div className="apis-popup-body">
              <p className="apis-confirm-text">Do you want to enable this API? It will be available for requests immediately.</p>
            </div>
            <footer className="apis-popup-footer">
              <button type="button" className="apis-popup-cancel" onClick={() => setConfirmEnableId(null)}>Cancel</button>
              <button
                type="button"
                className="apis-submit-btn"
                onClick={() => { void handleToggle(confirmEnableId, false); setConfirmEnableId(null); }}
              >
                Enable
              </button>
            </footer>
          </div>
        </div>
      )}

      {testProviderId && (
        <div className="apis-overlay" onMouseDown={(e) => { if (e.target === e.currentTarget) setTestProviderId(null); }}>
          <div className="apis-popup apis-popup--wide">
            <header className="apis-popup-header">
              <h3>Test Provider</h3>
              <button type="button" className="apis-popup-close" onClick={() => setTestProviderId(null)}>X</button>
            </header>
            <div className="apis-popup-body">
              <div className="apis-test-section">
                <span className="apis-test-label">Available Models ({testModels.length})</span>
                <select className="apis-test-select" value={testSelectedModel} onChange={(e) => setTestSelectedModel(e.target.value)}>
                  {testModels.map((m: any) => <option key={m.id} value={m.id}>{m.name || m.id}</option>)}
                </select>
              </div>
              {testLimits && Object.keys(testLimits).length > 0 && (
                <div className="apis-test-section">
                  <span className="apis-test-label">Limits</span>
                  <div className="apis-test-limits">
                    {testLimits.models ? (
                      Object.entries(testLimits.models as Record<string, any>).map(([model, lim]: [string, any]) => (
                        <div key={model} className="apis-test-limit-row">
                          <span className="apis-test-limit-model">{model}</span>
                          {lim.rpm && <span>{lim.rpm} rpm</span>}
                          {lim.rpd && <span>{lim.rpd} rpd</span>}
                          {lim.tpm && <span>{lim.tpm} tpm</span>}
                        </div>
                      ))
                    ) : (
                      <div className="apis-test-limit-row">
                        {testLimits.rpm && <span>{testLimits.rpm} rpm</span>}
                        {testLimits.rpd && <span>{testLimits.rpd} rpd</span>}
                        {testLimits.notes && <span>{testLimits.notes}</span>}
                      </div>
                    )}
                  </div>
                </div>
              )}
              <div className="apis-test-section">
                <span className="apis-test-label">Chat</span>
                <div className="apis-test-chat">
                  <input
                    className="apis-test-input"
                    placeholder="Type a message to test..."
                    value={testMessage}
                    onChange={(e) => setTestMessage(e.target.value)}
                    onKeyDown={(e) => { if (e.key === "Enter") void handleTestChat(); }}
                  />
                  <button type="button" className="apis-submit-btn" disabled={testLoading || !testMessage} onClick={() => void handleTestChat()}>
                    {testLoading ? "..." : "Send"}
                  </button>
                </div>
                {testResponse && <pre className="apis-test-response">{testResponse}</pre>}
              </div>
            </div>
          </div>
        </div>
      )}
    </section>
  );
};
