import { useCallback, useEffect, useState } from "react";

type UsageStats = {
  total: { input_tokens: number; output_tokens: number; requests: number };
  today: { input_tokens: number; output_tokens: number; requests: number };
  by_provider: Record<string, { input_tokens: number; output_tokens: number; requests: number }>;
  by_model: Record<string, { input_tokens: number; output_tokens: number; requests: number }>;
  daily: { date: string; input_tokens: number; output_tokens: number; requests: number }[];
  recent: { provider: string; model: string; input: number; output: number; at: string }[];
};

const StatCard = ({ label, value, sub }: { label: string; value: string; sub?: string }) => (
  <div className="usage-stat-card">
    <span className="usage-stat-label">{label}</span>
    <span className="usage-stat-value">{value}</span>
    {sub && <span className="usage-stat-sub">{sub}</span>}
  </div>
);

const DailyBar = ({ day }: { day: { date: string; input_tokens: number; output_tokens: number; requests: number } }) => {
  const total = day.input_tokens + day.output_tokens;
  const maxHeight = 80;
  const height = Math.min(maxHeight, Math.max(4, total / 500));
  const inputPct = total > 0 ? (day.input_tokens / total) * 100 : 50;
  return (
    <div className="usage-daily-bar-col">
      <div className="usage-daily-bar" style={{ height: `${height}px` }}>
        <div className="usage-daily-bar-input" style={{ height: `${inputPct}%` }} />
        <div className="usage-daily-bar-output" style={{ height: `${100 - inputPct}%` }} />
      </div>
      <span className="usage-daily-bar-label">{day.date.slice(5)}</span>
    </div>
  );
};

export const UsagePrimaryView = () => {
  const [stats, setStats] = useState<UsageStats | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchStats = useCallback(() => {
    setLoading(true);
    fetch("/api/usage/stats")
      .then((r) => r.json())
      .then((d) => {
        const empty = { input_tokens: 0, output_tokens: 0, requests: 0 };
        setStats({
          total: d.total ?? empty,
          today: d.today ?? empty,
          by_provider: d.by_provider ?? {},
          by_model: d.by_model ?? {},
          daily: d.daily ?? [],
          recent: d.recent ?? [],
        });
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { fetchStats(); }, [fetchStats]);

  if (loading && !stats) {
    return <section className="usage-view"><div className="usage-loading">Loading usage data...</div></section>;
  }

  if (!stats) {
    return <section className="usage-view"><div className="usage-loading">No usage data available yet. Start chatting to track tokens.</div></section>;
  }

  return (
    <section className="usage-view" aria-label="Usage analytics">
      <header className="usage-header">
        <h2>Token Usage Analytics</h2>
        <button type="button" className="usage-refresh-btn" onClick={fetchStats}>Refresh</button>
      </header>

      <div className="usage-stats-grid">
        <StatCard label="Total Tokens" value={(stats.total.input_tokens + stats.total.output_tokens).toLocaleString()} sub={`${stats.total.requests} requests`} />
        <StatCard label="Input Tokens" value={stats.total.input_tokens.toLocaleString()} sub="prompts + context" />
        <StatCard label="Output Tokens" value={stats.total.output_tokens.toLocaleString()} sub="AI responses" />
        <StatCard label="Today" value={(stats.today.input_tokens + stats.today.output_tokens).toLocaleString()} sub={`${stats.today.requests} requests today`} />
      </div>

      <div className="usage-sections-row">
        <div className="usage-section">
          <h3>Last 7 Days</h3>
          <div className="usage-daily-chart">
            {stats.daily.map((day) => <DailyBar key={day.date} day={day} />)}
          </div>
          <div className="usage-daily-legend">
            <span className="usage-legend-input">Input</span>
            <span className="usage-legend-output">Output</span>
          </div>
        </div>

        <div className="usage-section">
          <h3>By Provider</h3>
          <div className="usage-breakdown-list">
            {Object.entries(stats.by_provider).map(([name, data]) => (
              <div key={name} className="usage-breakdown-row">
                <span className="usage-breakdown-name">{name.replace("_", " ").toUpperCase()}</span>
                <span className="usage-breakdown-tokens">{(data.input_tokens + data.output_tokens).toLocaleString()} tok</span>
                <span className="usage-breakdown-reqs">{data.requests} req</span>
              </div>
            ))}
            {Object.keys(stats.by_provider).length === 0 && <p className="usage-empty">No data yet</p>}
          </div>
        </div>

        <div className="usage-section">
          <h3>By Model</h3>
          <div className="usage-breakdown-list">
            {Object.entries(stats.by_model).map(([name, data]) => (
              <div key={name} className="usage-breakdown-row">
                <span className="usage-breakdown-name">{name}</span>
                <span className="usage-breakdown-tokens">{(data.input_tokens + data.output_tokens).toLocaleString()} tok</span>
                <span className="usage-breakdown-reqs">{data.requests} req</span>
              </div>
            ))}
            {Object.keys(stats.by_model).length === 0 && <p className="usage-empty">No data yet</p>}
          </div>
        </div>
      </div>

      <div className="usage-section usage-recent">
        <h3>Recent Requests</h3>
        <table className="usage-table">
          <thead>
            <tr><th>Provider</th><th>Model</th><th>Input</th><th>Output</th><th>Time</th></tr>
          </thead>
          <tbody>
            {stats.recent.map((r, i) => (
              <tr key={i}>
                <td>{r.provider}</td>
                <td>{r.model}</td>
                <td>{r.input?.toLocaleString()}</td>
                <td>{r.output?.toLocaleString()}</td>
                <td>{r.at ? new Date(r.at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : "-"}</td>
              </tr>
            ))}
            {stats.recent.length === 0 && <tr><td colSpan={5} className="usage-empty">No requests yet</td></tr>}
          </tbody>
        </table>
      </div>
    </section>
  );
};
