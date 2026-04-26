import { useEffect, useState } from "react";
import { supabase } from "./supabase";
import { TaskList } from "./components/TaskList";
import { ActivityFeed } from "./components/ActivityFeed";

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

interface Activity {
  id: string;
  session_id: string;
  originator: string;
  description: string;
  activity_type: string;
  created_at: string;
}

export function App() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [activities, setActivities] = useState<Activity[]>([]);

  useEffect(() => {
    loadTasks();
    loadActivities();

    const taskChannel = supabase
      .channel("task-changes")
      .on("postgres_changes", { event: "*", schema: "public", table: "agent_tasks" }, (payload) => {
        if (payload.eventType === "INSERT") {
          setTasks((prev) => [payload.new as Task, ...prev]);
        } else if (payload.eventType === "UPDATE") {
          setTasks((prev) => prev.map((t) => (t.id === (payload.new as Task).id ? (payload.new as Task) : t)));
        }
      })
      .subscribe();

    const activityChannel = supabase
      .channel("activity-changes")
      .on("postgres_changes", { event: "INSERT", schema: "public", table: "session_activities" }, (payload) => {
        setActivities((prev) => [payload.new as Activity, ...prev].slice(0, 100));
      })
      .subscribe();

    return () => {
      supabase.removeChannel(taskChannel);
      supabase.removeChannel(activityChannel);
    };
  }, []);

  async function loadTasks() {
    const { data } = await supabase
      .from("agent_tasks")
      .select("*")
      .order("created_at", { ascending: false })
      .limit(50);
    if (data) setTasks(data);
  }

  async function loadActivities() {
    const { data } = await supabase
      .from("session_activities")
      .select("*")
      .order("created_at", { ascending: false })
      .limit(100);
    if (data) setActivities(data);
  }

  return (
    <>
      <header>
        <h1>JAT-AI Dashboard</h1>
        <span style={{ color: "var(--text-muted)" }}>
          {tasks.filter((t) => t.status === "running").length} running
        </span>
      </header>
      <div className="container">
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.5rem", marginTop: "1.5rem" }}>
          <TaskList tasks={tasks} />
          <ActivityFeed activities={activities} />
        </div>
      </div>
    </>
  );
}
