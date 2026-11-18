-- ============================================================================
-- Shema AI: Module 07 Task 2 — agent memory (sessions)
-- Run once in Supabase Dashboard → SQL Editor (project ndcggbkacmptigfdepvc),
-- AFTER 20261118000007_agent_runs.sql.
--
-- Runs with the same session_id belong to one agent conversation: a new question
-- sees the earlier questions and answers of its session ("short-term memory").
-- ============================================================================

alter table public.agent_runs add column session_id uuid;

-- Fast "last N finished runs of this session".
create index agent_runs_session_idx on public.agent_runs (session_id, created_at desc);
