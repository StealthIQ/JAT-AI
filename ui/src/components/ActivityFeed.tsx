interface Activity {
  id: string;
  session_id: string;
  originator: string;
  description: string;
  activity_type: string;
  created_at: string;
}

const TYPE_COLORS: Record<string, string> = {
  plan_generated: "var(--accent)",
  plan_approved: "var(--success)",
  agent_messaged: "var(--text)",
  progress_updated: "var(--warning)",
  session_completed: "var(--success)",
  session_failed: "var(--danger)",
};

export function ActivityFeed({ activities }: { activities: Activity[] }) {
  return (
    <section>
      <h2 style={{ marginBottom: "1rem", fontSize: "1.1rem" }}>Activity Feed</h2>
      <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
        {activities.length === 0 && (
          <p style={{ color: "var(--text-muted)" }}>No activities yet</p>
        )}
        {activities.map((a) => (
          <div
            key={a.id}
            style={{
              background: "var(--surface)",
              border: "1px solid var(--border)",
              borderRadius: "6px",
              padding: "0.6rem 0.8rem",
              fontSize: "0.85rem",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span style={{ color: TYPE_COLORS[a.activity_type] ?? "var(--text-muted)", fontWeight: 600 }}>
                {a.activity_type || a.originator}
              </span>
              <span style={{ color: "var(--text-muted)", fontSize: "0.75rem" }}>
                {new Date(a.created_at).toLocaleTimeString()}
              </span>
            </div>
            {a.description && (
              <p style={{ color: "var(--text-muted)", marginTop: "0.25rem" }}>
                {a.description.length > 150 ? a.description.slice(0, 150) + "..." : a.description}
              </p>
            )}
          </div>
        ))}
      </div>
    </section>
  );
}
