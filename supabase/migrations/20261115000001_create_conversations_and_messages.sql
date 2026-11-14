-- ============================================================================
-- Shema AI: conversations and messages
-- Run once in Supabase Dashboard → SQL Editor.
-- ============================================================================

-- One row per chat (what the sidebar will list).
create table public.conversations (
    id          uuid primary key default gen_random_uuid(),
    -- Owner of the chat. Nullable until we add login in Module 09.
    user_id     uuid references auth.users (id) on delete cascade,
    title       text not null default 'New conversation',
    created_at  timestamptz not null default now(),
    updated_at  timestamptz not null default now()
);

-- One row per message inside a chat.
create table public.messages (
    id               uuid primary key default gen_random_uuid(),
    conversation_id  uuid not null references public.conversations (id) on delete cascade,
    role             text not null check (role in ('user', 'assistant')),
    content          text not null check (length(trim(content)) > 0),
    -- Filled only for assistant messages: which model answered and what it cost.
    model            text,
    input_tokens     integer,
    output_tokens    integer,
    thinking_tokens  integer,
    total_tokens     integer,
    created_at       timestamptz not null default now()
);

-- Fast lookups: "all messages of chat X in order" and "most recent chats first".
create index messages_conversation_id_created_at_idx
    on public.messages (conversation_id, created_at);
create index conversations_updated_at_idx
    on public.conversations (updated_at desc);

-- Row Level Security ON with no policies = nobody can read/write through the
-- public (publishable/anon) key. Only our backend, using the secret key, can.
-- We add per-user policies when we build login in Module 09.
alter table public.conversations enable row level security;
alter table public.messages enable row level security;
