create table context_messages (
    id uuid primary key default uuid_generate_v4(),
    from_task_id uuid references agent_tasks(id) on delete cascade,
    to_task_id uuid references agent_tasks(id) on delete cascade,
    task_id uuid references agent_tasks(id) on delete cascade,
    message jsonb not null default '{}',
    context jsonb not null default '{}',
    created_at timestamptz not null default now()
);

create table merge_queue (
    id uuid primary key default uuid_generate_v4(),
    task_id uuid not null references agent_tasks(id) on delete cascade,
    repo_owner text not null,
    repo_name text not null,
    pr_number int not null,
    pr_url text not null default '',
    head_ref text not null default '',
    merge_strategy text not null default 'squash'
        check (merge_strategy in ('squash', 'merge', 'rebase')),
    ci_status text not null default 'pending'
        check (ci_status in ('pending', 'running', 'passed', 'failed')),
    merged boolean not null default false,
    merge_sha text not null default '',
    error text not null default '',
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table session_activities (
    id uuid primary key default uuid_generate_v4(),
    task_id uuid not null references agent_tasks(id) on delete cascade,
    session_id text not null,
    activity_id text not null,
    originator text not null default '',
    description text not null default '',
    activity_type text not null default '',
    artifacts jsonb not null default '[]',
    raw_data jsonb not null default '{}',
    created_at timestamptz not null default now(),
    unique (session_id, activity_id)
);

create index idx_agent_tasks_workflow on agent_tasks(workflow_id);
create index idx_agent_tasks_status on agent_tasks(status);
create index idx_context_messages_to on context_messages(to_task_id);
create index idx_merge_queue_task on merge_queue(task_id);
create index idx_session_activities_task on session_activities(task_id);
create index idx_session_activities_session on session_activities(session_id);
