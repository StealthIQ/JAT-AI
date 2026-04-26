interface Task {
  id: string;
  prompt: string;
  status: string;
  session_id: string;
  pr_url: string;
  repo_owner: string;
  repo_name: string;
  created_at: string;
}

const STATUS_COLORS: Record<string, string> = {
  pending: "var(--text-muted)",
  waiting: "var(--warning)",
  running: "var(--accent)",
  completed: "var(--success)",
  failed: "var(--danger)",
  cancelled: "var(--text-muted)",
};

export function TaskList({ tasks }: { tasks: Task[] }) {
  return (
    <section>
      <h2 style={{ marginBottom: "1rem", fontSize: "1.1rem" }}>Tasks</h2>
      <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
        {tasks.length === 0 && (
          <p style={{ color: "var(--text-muted)" }}>No tasks yet</p>
        )}
        {tasks.map((task) => (
          <div
            key={task.id}
            style={{
              background: "var(--surface)",
              border: "1px solid var(--border)",
              borderRadius: "6px",
              padding: "0.75rem 1rem",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span
                style={{
                  color: STATUS_COLORS[task.status] ?? "var(--text)",
                  fontWeight: 600,
                  fontSize: "0.85rem",
                  textTransform: "uppercase",
                }}
              >
                {task.status}
              </span>
              {task.repo_owner && (
                <span style={{ color: "var(--text-muted)", fontSize: "0.8rem" }}>
                  {task.repo_owner}/{task.repo_name}
                </span>
              )}
            </div>
            <p style={{ marginTop: "0.4rem", fontSize: "0.9rem" }}>
              {task.prompt.length > 120 ? task.prompt.slice(0, 120) + "..." : task.prompt}
            </p>
            {task.pr_url && (
              <a
                href={task.pr_url}
                target="_blank"
                rel="noopener noreferrer"
                style={{ fontSize: "0.8rem", marginTop: "0.3rem", display: "inline-block" }}
              >
                View PR
              </a>
            )}
          </div>
        ))}
      </div>
    </section>
  );
}
