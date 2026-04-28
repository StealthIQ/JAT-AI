-- JAT-AI Full Schema
-- Run this once to set up all tables

create extension if not exists "uuid-ossp";
create extension if not exists "pgcrypto";

-- Jules account management

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

-- Workflows and tasks

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

-- Context passing and merge queue

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

-- AI provider management (encrypted keys)

create table ai_providers (
    id uuid primary key default uuid_generate_v4(),
    provider_type text not null
        check (provider_type in ('groq', 'google', 'cloudflare', 'openrouter', 'ollama')),
    name text not null unique,
    api_key_encrypted bytea,
    model text not null default '',
    base_url text not null default '',
    enabled boolean not null default true,
    daily_limit int not null default 0,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

-- Conversations

create table conversations (
    id uuid primary key default uuid_generate_v4(),
    title text not null default 'New Conversation',
    provider_id uuid references ai_providers(id) on delete set null,
    model text not null default '',
    mode text not null default 'plan'
        check (mode in ('plan', 'direct')),
    repo_owner text not null default '',
    repo_name text not null default '',
    template text not null default '',
    status text not null default 'active'
        check (status in ('active', 'archived', 'completed')),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table conversation_messages (
    id uuid primary key default uuid_generate_v4(),
    conversation_id uuid not null references conversations(id) on delete cascade,
    role text not null check (role in ('user', 'assistant', 'system')),
    content text not null,
    image_urls text[] not null default '{}',
    metadata jsonb not null default '{}',
    created_at timestamptz not null default now()
);

-- Indexes

create index idx_agent_tasks_workflow on agent_tasks(workflow_id);
create index idx_agent_tasks_status on agent_tasks(status);
create index idx_context_messages_to on context_messages(to_task_id);
create index idx_merge_queue_task on merge_queue(task_id);
create index idx_session_activities_task on session_activities(task_id);
create index idx_session_activities_session on session_activities(session_id);
create index idx_conv_messages_conv on conversation_messages(conversation_id);
create index idx_conversations_status on conversations(status);
create index idx_ai_providers_type on ai_providers(provider_type);
