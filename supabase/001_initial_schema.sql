create extension if not exists "uuid-ossp";

create table accounts (
    id uuid primary key default uuid_generate_v4(),
    name text not null,
    api_key_hash text not null,
    plan text not null default 'free' check (plan in ('free', 'pro', 'ultra')),
    max_concurrent int not null default 3,
    max_daily_tasks int not null default 15,
    enabled boolean not null default true,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table account_sources (
    id uuid primary key default uuid_generate_v4(),
    account_id uuid not null references accounts(id) on delete cascade,
    source_name text not null,
    repo_owner text not null,
    repo_name text not null,
    created_at timestamptz not null default now(),
    unique (account_id, source_name)
);

create table workflows (
    id uuid primary key default uuid_generate_v4(),
    name text not null,
    description text not null default '',
    status text not null default 'created'
        check (status in ('created', 'running', 'completed', 'failed', 'cancelled')),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table agent_tasks (
    id uuid primary key default uuid_generate_v4(),
    workflow_id uuid references workflows(id) on delete cascade,
    parent_task_id uuid references agent_tasks(id) on delete set null,
    account_id uuid references accounts(id) on delete set null,
    session_id text,
    prompt text not null,
    repo_owner text not null default '',
    repo_name text not null default '',
    branch text not null default 'main',
    status text not null default 'pending'
        check (status in ('pending', 'waiting', 'running', 'completed', 'failed', 'cancelled')),
    depends_on uuid[] not null default '{}',
    pr_url text not null default '',
    context jsonb not null default '{}',
    error text not null default '',
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);
