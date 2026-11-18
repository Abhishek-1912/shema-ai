-- ============================================================================
-- Shema AI: documents, chunks with embeddings (pgvector), and semantic search
-- Run once in Supabase Dashboard → SQL Editor.
-- ============================================================================

-- 1. Turn on pgvector. Supabase keeps extensions in their own "extensions" schema.
create extension if not exists vector with schema extensions;

-- 2. One row per document (a PDF, a note, a wiki page...).
create table public.documents (
    id           uuid primary key default gen_random_uuid(),
    user_id      uuid references auth.users (id) on delete cascade,  -- owner; used from Module 09
    title        text not null check (length(trim(title)) > 0),
    source_type  text not null default 'text'
                 check (source_type in ('text', 'pdf', 'docx', 'txt', 'md')),
    file_name    text,
    created_at   timestamptz not null default now()
);

-- 3. One row per chunk (a piece of a document) + its embedding.
create table public.document_chunks (
    id           uuid primary key default gen_random_uuid(),
    document_id  uuid not null references public.documents (id) on delete cascade,
    chunk_index  integer not null check (chunk_index >= 0),      -- position inside the document
    content      text not null check (length(trim(content)) > 0),
    page_number  integer,                                        -- filled for PDFs (Module 04)
    -- 768 numbers: must match EMBEDDING_DIMENSIONS in backend/.env (default 768).
    embedding    extensions.vector(768) not null,
    created_at   timestamptz not null default now(),
    unique (document_id, chunk_index)
);

-- 4. Index for fast similarity search. HNSW = a graph that finds the nearest
--    vectors without comparing against every row. vector_cosine_ops = cosine distance.
create index document_chunks_embedding_idx
    on public.document_chunks
    using hnsw (embedding extensions.vector_cosine_ops);

create index document_chunks_document_id_idx
    on public.document_chunks (document_id, chunk_index);

-- 5. Same security rule as conversations: RLS on, no policies = only the backend
--    (secret key) can read or write. Per-user policies come in Module 09.
alter table public.documents enable row level security;
alter table public.document_chunks enable row level security;

-- 6. The search itself, as a database function the backend calls ("RPC").
--    <=> is pgvector's cosine DISTANCE (0 = same direction), so similarity = 1 - distance.
create or replace function public.match_document_chunks(
    query_embedding extensions.vector(768),
    match_count     integer default 5,
    min_similarity  double precision default 0
)
returns table (
    chunk_id        uuid,
    document_id     uuid,
    document_title  text,
    chunk_index     integer,
    page_number     integer,
    content         text,
    similarity      double precision
)
language sql
stable
set search_path = public, extensions
as $$
    select
        c.id,
        c.document_id,
        d.title,
        c.chunk_index,
        c.page_number,
        c.content,
        1 - (c.embedding <=> query_embedding) as similarity
    from document_chunks c
    join documents d on d.id = c.document_id
    where 1 - (c.embedding <=> query_embedding) >= min_similarity
    order by c.embedding <=> query_embedding
    limit least(greatest(match_count, 1), 50);
$$;

-- Only the backend may call it (not the public browser key).
revoke execute on function public.match_document_chunks(extensions.vector, integer, double precision)
    from public, anon, authenticated;
grant execute on function public.match_document_chunks(extensions.vector, integer, double precision)
    to service_role;
