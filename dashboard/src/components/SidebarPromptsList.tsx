import { useMemo, useState } from "react";

import type { PromptLibraryEntry } from "../app/types";

type SidebarPromptsListProps = {
  prompts: PromptLibraryEntry[];
  selectedPromptName: string | null;
  isLoadingPrompts: boolean;
  onSelectPrompt: (name: string) => void;
  onRefresh: () => void;
  onNewPrompt: () => void;
  activeTerminalId: string | null;
  onRestoreTerminal: () => void;
  onCloseTerminal: () => void;
};

export const SidebarPromptsList = ({
  prompts,
  selectedPromptName,
  isLoadingPrompts,
  onSelectPrompt,
  onRefresh,
  onNewPrompt,
  activeTerminalId,
  onRestoreTerminal,
  onCloseTerminal,
}: SidebarPromptsListProps) => {
  const [search, setSearch] = useState("");
  const [skillsOpen, setSkillsOpen] = useState(true);
  const [customOpen, setCustomOpen] = useState(true);

  const filtered = useMemo(() => {
    if (!search.trim()) return prompts;
    const q = search.toLowerCase();
    return prompts.filter((p) => p.name.toLowerCase().includes(q));
  }, [prompts, search]);
  const userPrompts = useMemo(() => filtered.filter((p) => p.source === "user"), [filtered]);
  const builtinPrompts = useMemo(() => filtered.filter((p) => p.source === "builtin"), [filtered]);

  return (
    <div className="sidebar-prompts">
      <div className="sidebar-prompts-toolbar">
        <button type="button" className="sidebar-prompts-new-btn" onClick={onNewPrompt}>
          + New Prompt
        </button>
        <button type="button" className="sidebar-prompts-refresh-btn" onClick={onRefresh} disabled={isLoadingPrompts} aria-label="Refresh prompts">
          R
        </button>
      </div>

      <input className="sidebar-prompts-search" type="text" placeholder="Search prompts..." value={search} onChange={(e) => setSearch(e.target.value)} />

      {isLoadingPrompts && prompts.length === 0 ? (
        <p className="sidebar-prompts-empty">Loading...</p>
      ) : filtered.length === 0 ? (
        <p className="sidebar-prompts-empty">{search ? "No matches" : "No prompts yet"}</p>
      ) : (
        <div className="sidebar-prompts-list">
          {builtinPrompts.length > 0 && (
            <div className="sidebar-prompts-group">
              <button type="button" className="sidebar-prompts-group-toggle" onClick={() => setSkillsOpen((o) => !o)}>
                <span className={`sidebar-prompts-arrow${skillsOpen ? " is-open" : ""}`}>▶</span>
                Skills ({builtinPrompts.length})
              </button>
              {skillsOpen && builtinPrompts.map((p) => (
                <button key={p.name} type="button" className="sidebar-prompts-item" data-active={selectedPromptName === p.name ? "true" : undefined} onClick={() => onSelectPrompt(p.name)}>
                  {p.name}
                </button>
              ))}
            </div>
          )}

          {userPrompts.length > 0 && (
            <div className="sidebar-prompts-group">
              <button type="button" className="sidebar-prompts-group-toggle" onClick={() => setCustomOpen((o) => !o)}>
                <span className={`sidebar-prompts-arrow${customOpen ? " is-open" : ""}`}>▶</span>
                Custom Prompts ({userPrompts.length})
              </button>
              {customOpen && userPrompts.map((p) => (
                <button key={p.name} type="button" className="sidebar-prompts-item" data-active={selectedPromptName === p.name ? "true" : undefined} onClick={() => onSelectPrompt(p.name)}>
                  {p.name}
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {activeTerminalId && (
        <div className="sidebar-prompts-minimized-terminal">
          <button type="button" className="sidebar-prompts-minimized-terminal-restore" onClick={onRestoreTerminal}>
            <span className="sidebar-prompts-minimized-terminal-icon">{">_"}</span>
            <span className="sidebar-prompts-minimized-terminal-label">Prompt Engineer</span>
          </button>
          <button type="button" className="sidebar-prompts-minimized-terminal-close" onClick={onCloseTerminal} aria-label="Close terminal">x</button>
        </div>
      )}
    </div>
  );
};
