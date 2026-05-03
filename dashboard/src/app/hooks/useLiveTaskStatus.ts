import { useEffect, useState } from "react";
import { supabase } from "../../lib/supabase";

export type LiveTask = {
  id: string;
  status: string;
  repo_owner: string;
  repo_name: string;
  prompt: string;
  session_id: string | null;
  updated_at: string;
};

export function useLiveTaskStatus() {
  const [tasks, setTasks] = useState<LiveTask[]>([]);

  useEffect(() => {
    supabase
      .from("agent_tasks")
      .select("id, status, repo_owner, repo_name, prompt, session_id, updated_at")
      .order("updated_at", { ascending: false })
      .limit(50)
      .then(({ data }) => {
        if (data) setTasks(data as LiveTask[]);
      });

    const channel = supabase
      .channel("agent_tasks_changes")
      .on("postgres_changes", { event: "*", schema: "public", table: "agent_tasks" }, (payload) => {
        const row = payload.new as LiveTask;
        setTasks((prev) => {
          const idx = prev.findIndex((t) => t.id === row.id);
          if (idx >= 0) {
            const updated = [...prev];
            updated[idx] = row;
            return updated;
          }
          return [row, ...prev].slice(0, 50);
        });
      })
      .subscribe();

    return () => { supabase.removeChannel(channel); };
  }, []);

  return tasks;
}
