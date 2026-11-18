-- ============================================================================
-- Shema AI: Module 07 Task 1 — saved agent runs and tool-call logs
-- Run once in Supabase Dashboard → SQL Editor (project ndcggbkacmptigfdepvc).
--
-- Every agent run is stored: question, answer, status, usage, and every tool call.
-- A run that waits for human approval keeps its saved state here (survives a backend
-- restart and works with several backend processes).
-- ============================================================================

-- 1. One row per agent run.
create table public.agent_runs (
    id             uuid primary key default gen_random_uuid(),   -- random = unguessable run_id
    question       text not null check (length(trim(question)) > 0),
    --  running → done | needs_approval | failed;  needs_approval → resuming → done | needs_approval | failed
    status         text not null default 'running'
                   check (status in ('running', 'needs_approval', 'resuming', 'done', 'failed')),
    answer         text not null default '',
    state          jsonb,                 -- saved agent state while waiting for approval, else null
    expires_at     timestamptz,           -- approval deadline (only while needs_approval)
    steps          integer not null default 0,
    stopped_early  boolean not null default false,
    model          text,
    usage          jsonb,                 -- {input_tokens, output_tokens, thinking_tokens, total_tokens}
    error          text,                  -- why it failed (server-side detail, never sent to users)
    user_id        uuid references auth.users (id) on delete set null,   -- owner (Module 09)
    created_at     timestamptz not null default now(),
    updated_at     timestamptz not null default now()
);
create index agent_runs_created_idx on public.agent_runs (created_at desc);

-- 2. Every tool call of a run, in the order the AI asked for them (append-only log).
create table public.agent_tool_calls (
    id           uuid primary key default gen_random_uuid(),
    run_id       uuid not null references public.agent_runs (id) on delete cascade,
    position     integer not null check (position >= 0),
    name         text not null,
    arguments    jsonb not null default '{}'::jsonb,
    result       text not null,
    is_error     boolean not null default false,
    duration_ms  double precision not null default 0,
    approval     text not null check (approval in ('auto', 'approved', 'rejected')),
    created_at   timestamptz not null default now(),
    unique (run_id, position)
);

-- 3. Secure by default (same as every other table): no policies yet, the backend uses
--    the secret key. Per-user policies come with login (Module 09).
alter table public.agent_runs enable row level security;
alter table public.agent_tool_calls enable row level security;

-- 4. Claim a paused run for resuming — ATOMICALLY, so a decision is processed only once,
--    even if two requests (or two backend processes) arrive at the same moment.
--    Returns the row, or nothing if the run is unknown, expired or already claimed.
create or replace function public.claim_agent_run(p_id uuid)
returns setof public.agent_runs
language sql
as $$
    update public.agent_runs
       set status = 'resuming', updated_at = now()
     where id = p_id
       and status = 'needs_approval'
       and expires_at > now()
    returning *;
$$;
