import { SettingsToggle } from "./ui/SettingsToggle";

type SettingsPrimaryViewProps = {
  isRuntimeStatusStripVisible: boolean;
  isMonitorVisible: boolean;
  onRuntimeStatusStripVisibilityChange: (visible: boolean) => void;
  onMonitorVisibilityChange: (visible: boolean) => void;
};

export const SettingsPrimaryView = ({
  isRuntimeStatusStripVisible,
  isMonitorVisible,
  onRuntimeStatusStripVisibilityChange,
  onMonitorVisibilityChange,
}: SettingsPrimaryViewProps) => (
  <section className="settings-view" aria-label="Settings primary view">
    <section className="settings-panel" aria-label="Workspace surface visibility settings">
      <header className="settings-panel-header">
        <h2>Workspace surface visibility</h2>
        <p>Enable or disable surfaces in the main workspace shell.</p>
      </header>

      <div className="settings-toggle-grid">
        <SettingsToggle
          label="Monitor"
          description="Show monitor tab and feed"
          ariaLabel="Enable Monitor"
          checked={isMonitorVisible}
          onChange={onMonitorVisibilityChange}
        />
        <SettingsToggle
          label="Runtime status strip"
          description="Top console status strip metrics"
          ariaLabel="Show runtime status strip"
          checked={isRuntimeStatusStripVisible}
          onChange={onRuntimeStatusStripVisibilityChange}
        />
      </div>
    </section>
  </section>
);
