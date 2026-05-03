import { useCallback, useEffect, useState } from "react";

type SettingsPrimaryViewProps = {
  isRuntimeStatusStripVisible: boolean;
  isMonitorVisible: boolean;
  onRuntimeStatusStripVisibilityChange: (visible: boolean) => void;
  onMonitorVisibilityChange: (visible: boolean) => void;
};

type AppSettings = {
  github_token: string;
  github_fg_token: string;
  supabase_url: string;
  supabase_key: string;
  encryption_key_status: string;
  database_mode: "local" | "supabase" | "hybrid";
};

export const SettingsPrimaryView = (_props: SettingsPrimaryViewProps) => {
  const [settings, setSettings] = useState<AppSettings>({
    github_token: "", github_fg_token: "",
    supabase_url: "", supabase_key: "",
    encryption_key_status: "", database_mode: "local",
  });
  const [original, setOriginal] = useState<AppSettings | null>(null);
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const [showRegenPopup, setShowRegenPopup] = useState(false);
  const [regenInput, setRegenInput] = useState("");
  const [regenerating, setRegenerating] = useState(false);
  const [showDbConfirm, setShowDbConfirm] = useState(false);
  const [pendingDbMode, setPendingDbMode] = useState<"local" | "supabase" | "hybrid" | null>(null);
  const [dbConfirmInput, setDbConfirmInput] = useState("");
  const [keyStatus, setKeyStatus] = useState<Record<string, { status: string; error?: string; user?: string }>>({});
  const [errorPopup, setErrorPopup] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/settings")
      .then((r) => r.json())
      .then((d) => { setSettings(d); setOriginal(d); setLoaded(true); })
      .catch(() => setLoaded(true));
    fetch("/api/settings/status")
      .then((r) => r.json())
      .then((d) => setKeyStatus(d))
      .catch(() => {});
  }, []);

  const hasChanges = original && JSON.stringify(settings) !== JSON.stringify(original);

  const handleSave = useCallback(() => {
    setSaving(true);
    fetch("/api/settings", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(settings),
    })
      .then(() => { setSaved(true); setOriginal(settings); setEditing(false); setTimeout(() => setSaved(false), 3000); })
      .catch(() => {})
      .finally(() => setSaving(false));
  }, [settings]);

  const handleCancel = () => {
    if (original) setSettings(original);
    setEditing(false);
  };

  const handleRegenerate = useCallback(() => {
    setRegenerating(true);
    fetch("/api/settings/regenerate-key", { method: "POST" })
      .then(() => {
        setShowRegenPopup(false);
        setRegenInput("");
        setSettings((s) => ({ ...s, encryption_key_status: "configured" }));
        setSaved(true);
        setTimeout(() => setSaved(false), 3000);
      })
      .catch(() => {})
      .finally(() => setRegenerating(false));
  }, []);

  const updateField = (field: keyof AppSettings, value: string) => {
    setSettings((prev) => ({ ...prev, [field]: value }));
  };

  return (
    <section className="settings-view" aria-label="Settings primary view">
      <section className="settings-panel">
        <header className="settings-panel-header">
          <h2>Database Mode</h2>
          <p>Choose where data is stored.</p>
        </header>
        <div className="settings-db-modes">
          {(["local", "supabase", "hybrid"] as const).map((m) => (
            <button key={m} type="button" className={`settings-db-btn${settings.database_mode === m ? " settings-db-btn--active" : ""}`} onClick={() => {
              if (m !== settings.database_mode) { setPendingDbMode(m); setShowDbConfirm(true); }
            }}>
              {m.toUpperCase()}
            </button>
          ))}
        </div>
        <p className="settings-db-desc">
          {settings.database_mode === "local" && "All data stored in local SQLite (./data/jat.db). No network needed."}
          {settings.database_mode === "supabase" && "All data stored in Supabase. Requires URL and key below."}
          {settings.database_mode === "hybrid" && "Reads from local SQLite, writes to both. Background sync to Supabase."}
        </p>
      </section>

      <section className="settings-panel">
        <header className="settings-panel-header">
          <h2>Connection Keys</h2>
          <p>API keys for external services.</p>
          {!editing && <button type="button" className="settings-edit-btn" onClick={() => setEditing(true)}>Edit</button>}
        </header>
        <div className="settings-fields">
          <SettingsFieldWithStatus label="GitHub Classic Token (ghp_...)" value={settings.github_token} onChange={(v) => updateField("github_token", v)} placeholder="ghp_xxxxxxxxxxxx" type="password" disabled={!editing} loaded={loaded} status={keyStatus.github_token} onErrorClick={(err) => setErrorPopup(err)} />
          <SettingsFieldWithStatus label="GitHub Fine-Grained Token (github_pat_...)" value={settings.github_fg_token} onChange={(v) => updateField("github_fg_token", v)} placeholder="github_pat_xxxxxxxxxxxx" type="password" disabled={!editing} loaded={loaded} status={keyStatus.github_fg_token} onErrorClick={(err) => setErrorPopup(err)} />
          <SettingsFieldWithStatus label="Supabase URL" value={settings.supabase_url} onChange={(v) => updateField("supabase_url", v)} placeholder="https://xxxxx.supabase.co" disabled={!editing} loaded={loaded} status={keyStatus.supabase} onErrorClick={(err) => setErrorPopup(err)} />
          <SettingsField label="Supabase Key (service_role)" value={settings.supabase_key} onChange={(v) => updateField("supabase_key", v)} placeholder="eyJhbGciOi..." type="password" disabled={!editing} loaded={loaded} />
        </div>
      </section>

      <section className="settings-panel">
        <header className="settings-panel-header">
          <h2>Encryption</h2>
          <p>Used to encrypt all stored API keys. Auto-generated on first run.</p>
        </header>
        <div className="settings-encryption-row">
          <span className="settings-encryption-status">
            Status: {settings.encryption_key_status === "configured" ? "Active" : "Not configured (will auto-generate on save)"}
          </span>
          <button type="button" className="settings-regen-btn" onClick={() => setShowRegenPopup(true)}>
            Regenerate Key
          </button>
        </div>
      </section>

      {editing && (
        <div className="settings-save-row">
          <button type="button" className="settings-cancel-btn" onClick={handleCancel}>Cancel</button>
          <button type="button" className="settings-save-btn" onClick={handleSave} disabled={saving || !hasChanges}>
            {saving ? "Saving..." : "Save Settings"}
          </button>
          {saved && <span className="settings-saved-pill">Saved</span>}
        </div>
      )}
      {!editing && saved && <span className="settings-saved-pill">Saved</span>}

      {showRegenPopup && (
        <div className="settings-popup-overlay" onMouseDown={(e) => { if (e.target === e.currentTarget) { setShowRegenPopup(false); setRegenInput(""); } }}>
          <div className="settings-popup">
            <h3 className="settings-popup-title">Regenerate Encryption Key</h3>
            <p className="settings-popup-warning">
              This will generate a new encryption key. All existing encrypted API keys
              (providers, Jules accounts) will become unreadable. You will need to
              re-add all API keys after regeneration.
            </p>
            <p className="settings-popup-confirm-text">Type "yes regenerate key" to confirm:</p>
            <input className="settings-popup-input" type="text" value={regenInput} onChange={(e) => setRegenInput(e.target.value)} placeholder="yes regenerate key" />
            <div className="settings-popup-footer">
              <button type="button" onClick={() => { setShowRegenPopup(false); setRegenInput(""); }}>Cancel</button>
              <button type="button" className="settings-popup-danger" disabled={regenInput !== "yes regenerate key" || regenerating} onClick={handleRegenerate}>
                {regenerating ? "Regenerating..." : "Confirm Regenerate"}
              </button>
            </div>
          </div>
        </div>
      )}

      {showDbConfirm && pendingDbMode && (
        <div className="settings-popup-overlay" onMouseDown={(e) => { if (e.target === e.currentTarget) { setShowDbConfirm(false); setDbConfirmInput(""); setPendingDbMode(null); } }}>
          <div className="settings-popup">
            <h3 className="settings-popup-title">Switch Database Mode</h3>
            <p className="settings-popup-warning">
              Switching to "{pendingDbMode}" mode will update the database configuration
              and require an app restart. Existing data in the current mode will remain
              but won't be accessible until you switch back.
            </p>
            <p className="settings-popup-confirm-text">Type "confirm" to proceed:</p>
            <input className="settings-popup-input" type="text" value={dbConfirmInput} onChange={(e) => setDbConfirmInput(e.target.value)} placeholder="confirm" />
            <div className="settings-popup-footer">
              <button type="button" onClick={() => { setShowDbConfirm(false); setDbConfirmInput(""); setPendingDbMode(null); }}>Cancel</button>
              <button type="button" className="settings-popup-danger" disabled={dbConfirmInput !== "confirm"} onClick={() => {
                setSettings((s) => ({ ...s, database_mode: pendingDbMode }));
                setShowDbConfirm(false); setDbConfirmInput(""); setPendingDbMode(null); setEditing(true);
              }}>Confirm Switch</button>
            </div>
          </div>
        </div>
      )}

      {errorPopup && (
        <div className="settings-popup-overlay" onMouseDown={(e) => { if (e.target === e.currentTarget) setErrorPopup(null); }}>
          <div className="settings-popup">
            <h3 className="settings-popup-title">Connection Error</h3>
            <p className="settings-popup-warning">{errorPopup}</p>
            <div className="settings-popup-footer">
              <button type="button" onClick={() => setErrorPopup(null)}>Close</button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
};

const SettingsField = ({ label, value, onChange, placeholder, type = "text", disabled, loaded }: {
  label: string; value: string; onChange: (v: string) => void; placeholder: string; type?: string; disabled: boolean; loaded: boolean;
}) => (
  <div className="settings-field">
    <label className="settings-field-label">{label}</label>
    <input
      className="settings-field-input"
      type={type}
      value={loaded ? value : ""}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      disabled={disabled || !loaded}
    />
  </div>
);

const SettingsFieldWithStatus = ({ label, value, onChange, placeholder, type = "text", disabled, loaded, status, onErrorClick }: {
  label: string; value: string; onChange: (v: string) => void; placeholder: string; type?: string; disabled: boolean; loaded: boolean;
  status?: { status: string; error?: string; user?: string }; onErrorClick: (err: string) => void;
}) => (
  <div className="settings-field">
    <div className="settings-field-label-row">
      <label className="settings-field-label">{label}</label>
      {status?.status === "active" && <span className="settings-status-badge settings-status-badge--active">Active{status.user ? ` (${status.user})` : ""}</span>}
      {status?.status === "error" && <button type="button" className="settings-status-badge settings-status-badge--error" onClick={() => onErrorClick(status.error ?? "Unknown error")}>Error</button>}
      {status?.status === "not_configured" && <span className="settings-status-badge settings-status-badge--none">Not set</span>}
    </div>
    <input
      className="settings-field-input"
      type={type}
      value={loaded ? value : ""}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      disabled={disabled || !loaded}
    />
  </div>
);
