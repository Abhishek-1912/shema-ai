-- ============================================================================
-- Shema AI: Module 07 Task 3 — agent planning
-- Run once in Supabase Dashboard → SQL Editor (project ndcggbkacmptigfdepvc),
-- AFTER 20261118000008_agent_sessions.sql.
--
-- The steps the agent planned before acting, e.g. ["Search the documents for ...", ...].
-- Empty list = the planner decided no plan was needed (simple question).
-- ============================================================================

alter table public.agent_runs add column plan jsonb not null default '[]'::jsonb;
