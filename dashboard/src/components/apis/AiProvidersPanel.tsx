import { useCallback, useEffect, useState, type React } from "react";

type Provider = {
  id: string;
  provider_type: string;
  name: string;
  enabled: boolean;
  daily_limit: number;
};

const PROVIDER_TYPES = [
  "groq", "google", "cloudflare", "openrouter", "ollama", "cerebras",
  "cohere", "mistral", "nvidia_nim", "github_models", "huggingface",
  "sambanova", "fireworks", "nebius", "hyperbolic", "scaleway", "longcat",
];

export const AiProvidersPanel = ({ onAddRef }: { onAddRef: React.MutableRefObject<() => void> }) => {
  const [providers, setProviders] = useState<Provider[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [formType, setFormType] = useState("groq");
  const [formName, setFormName] = useState("");
  const [formKey, setFormKey] = useState("");
  const [loading, setLoading] = useState(false);
  const [successMsg, setSuccessMsg] = useState("");
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);
  const [confirmInput, setConfirmInput] = useState("");

  const fetchProviders = useCallback(async () => {
    const res = await fetch("/api/providers");
    if (res.ok) {
      const data = await res.json();
      setProviders(data.providers || []);
    }
  }, []);

  useEffect(() => { void fetchProviders(); }, [fetchProviders]);

  const getNextName = (type: string) => {
    const prefix = type.toUpperCase().replace("_", "-");
    const existing = providers.map((p) => p.name);
    let n = 1;
    while (existing.includes(`${prefix}_${n}`)) n++;
    return `${prefix}_${n}`;
  };

  onAddRef.current = () => { setFormName(getNextName(formType)); setShowForm(true); };

  const handleAdd = async () => {
    if (!formName.trim() || !formKey.trim()) return;
    setLoading(true);
    await fetch("/api/providers", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ provider_type: formType, name: formName, api_key: formKey }),
    });
    setShowForm(false);
    setFormName("");
    setFormKey("");
    setLoading(false);
    setSuccessMsg(`${formType} key "${formName}" added`);
    setTimeout(() => setSuccessMsg(""), 4000);
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

  const handleDelete = async (id: string) => {
    await fetch(`/api/providers/${id}`, { method: "DELETE" });
    setConfirmDeleteId(null);
    setConfirmInput("");
    void fetchProviders();
  };

  return (
    <>
      {successMsg && <div className="apis-success">{successMsg}</div>}
      <div className="apis-list">
        {providers.length === 0 && <p className="apis-empty">No AI provider keys configured.</p>}
        {providers.map((p) => (
          <div key={p.id} className={`apis-card${p.enabled ? "" : " apis-card--disabled"}`}>
            <div className="apis-card-header">
              <span className="apis-card-name">{p.name}</span>
              <span className="apis-card-type">{p.provider_type}</span>
            </div>
            <div className="apis-card-body">
              <span>Limit: {p.daily_limit}/day</span>
            </div>
            <div className="apis-card-actions">
              <button type="button" className="apis-toggle-btn" onClick={() => void handleToggle(p.id, p.enabled)}>
                {p.enabled ? "Disable" : "Enable"}
              </button>
              <button type="button" className="apis-delete-btn" onClick={() => setConfirmDeleteId(p.id)}>Remove</button>
            </div>
          </div>
        ))}
      </div>

      {showForm && (
        <div className="apis-overlay" onMouseDown={(e) => { if (e.target === e.currentTarget) setShowForm(false); }}>
          <div className="apis-popup">
            <header className="apis-popup-header"><h3>Add AI Provider</h3></header>
            <div className="apis-popup-body">
              <div className="apis-field">
                <label>Provider Type</label>
                <select value={formType} onChange={(e) => { setFormType(e.target.value); setFormName(getNextName(e.target.value)); }}>
                  {PROVIDER_TYPES.map((t) => <option key={t} value={t}>{t.toUpperCase()}</option>)}
                </select>
              </div>
              <div className="apis-field">
                <label>Name</label>
                <input type="text" value={formName} onChange={(e) => setFormName(e.target.value)} />
              </div>
              <div className="apis-field">
                <label>API Key</label>
                <input type="password" value={formKey} onChange={(e) => setFormKey(e.target.value)} placeholder="Enter key..." />
              </div>
            </div>
            <footer className="apis-popup-footer">
              <button type="button" onClick={() => setShowForm(false)}>Cancel</button>
              <button type="button" className="apis-submit-btn" disabled={loading || !formName || !formKey} onClick={() => void handleAdd()}>
                {loading ? "Saving..." : "Save"}
              </button>
            </footer>
          </div>
        </div>
      )}

      {confirmDeleteId && (
        <div className="apis-overlay" onMouseDown={(e) => { if (e.target === e.currentTarget) { setConfirmDeleteId(null); setConfirmInput(""); } }}>
          <div className="apis-popup apis-popup--narrow">
            <h3>Remove Provider</h3>
            <p className="apis-confirm-text">Type "confirm" to remove this key permanently.</p>
            <input className="apis-confirm-input" type="text" value={confirmInput} onChange={(e) => setConfirmInput(e.target.value)} placeholder="confirm" />
            <footer className="apis-popup-footer">
              <button type="button" onClick={() => { setConfirmDeleteId(null); setConfirmInput(""); }}>Cancel</button>
              <button type="button" className="apis-submit-btn apis-submit-btn--danger" disabled={confirmInput !== "confirm"} onClick={() => void handleDelete(confirmDeleteId)}>Remove</button>
            </footer>
          </div>
        </div>
      )}
    </>
  );
};
