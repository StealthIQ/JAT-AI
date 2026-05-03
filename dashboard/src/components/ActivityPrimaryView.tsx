import { useEffect, useState, type ComponentProps } from "react";

import { GitHubPrimaryView } from "./GitHubPrimaryView";
import { UsageBarChart } from "./UsageHeatmap";

type ActivityPrimaryViewProps = {
  usageChartProps: ComponentProps<typeof UsageBarChart>;
  githubPrimaryViewProps: ComponentProps<typeof GitHubPrimaryView>;
};

export const ActivityPrimaryView = ({
  usageChartProps,
  githubPrimaryViewProps,
}: ActivityPrimaryViewProps) => {
  const [hasGithubKey, setHasGithubKey] = useState(true);

  useEffect(() => {
    fetch("/api/settings").then((r) => r.json()).then((d) => {
      setHasGithubKey(Boolean(d.github_token));
    }).catch(() => {});
  }, []);

  return (
    <section className="activity-view" aria-label="Activity primary view" style={{ position: "relative" }}>
      {!hasGithubKey && (
        <div className="apis-setup-overlay">
          <div className="apis-setup-card">
            <h3>GitHub API Key Required</h3>
            <p>Configure your GitHub token in Settings to view activity data, commits, and repository stats.</p>
            <button type="button" className="apis-setup-btn" onClick={() => { window.dispatchEvent(new CustomEvent("navigate", { detail: 7 })); }}>
              Go to Settings
            </button>
          </div>
        </div>
      )}
      <UsageBarChart {...usageChartProps} />
      <GitHubPrimaryView {...githubPrimaryViewProps} />
    </section>
  );
};
