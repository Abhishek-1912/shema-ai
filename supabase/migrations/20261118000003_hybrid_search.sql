-- ============================================================================
-- Shema AI: hybrid search = keyword (full-text) search + vector search
-- Run once in Supabase Dashboard → SQL Editor (project ndcggbkacmptigfdepvc).
-- ============================================================================

-- 1. Keyword index. A "tsvector" is the chunk's text as normalized search words:
--    to_tsvector('english', 'Refunds are paid') → 'paid':3 'refund':1
--    ("are" is dropped as a stop word, "Refunds" is reduced to its stem "refund").
--    GENERATED ... STORED = Postgres keeps it up to date automatically on every insert.
alter table public.document_chunks
    add column if not exists fts tsvector
    generated always as (to_tsvector('english', content)) stored;

create index if not exists document_chunks_fts_idx
    on public.document_chunks using gin (fts);

-- 2. Hybrid search with Reciprocal Rank Fusion (RRF).
--    Two ranked lists (keywords, meaning) are merged: each chunk gets
--    1/(rrf_k + rank) from every list it appears in. Being near the top of EITHER list
--    helps; being near the top of BOTH helps most.
create or replace function public.hybrid_match_document_chunks(
    query_text       text,
    query_embedding  extensions.vector(768),
    match_count      integer default 5,
    min_similarity   double precision default 0,
    keyword_top      integer default 2,   -- the best N keyword hits pass even with low similarity
    rrf_k            integer default 60
)
returns table (
    chunk_id        uuid,
    document_id     uuid,
    document_title  text,
    chunk_index     integer,
    page_number     integer,
    content         text,
    similarity      double precision,
    keyword_rank    integer,              -- null = no keyword match
    score           double precision
)
language sql
stable
set search_path = public, extensions
as $$
    with words as (
        -- Natural questions rarely contain ALL words of a chunk, so match ANY word:
        -- 'tell' & 'kestrel'  →  'tell' | 'kestrel'
        select replace(plainto_tsquery('english', query_text)::text, ' & ', ' | ') as q_text
    ),
    tsq as (
        select case when q_text = '' then null else q_text::tsquery end as q from words
    ),
    full_text as (
        select c.id, row_number() over (order by ts_rank_cd(c.fts, tsq.q) desc) as rank_ix
        from document_chunks c, tsq
        where tsq.q is not null and c.fts @@ tsq.q
        order by rank_ix
        limit 20
    ),
    semantic as (
        select s.id, row_number() over (order by s.distance) as rank_ix
        from (
            select c.id, c.embedding <=> query_embedding as distance
            from document_chunks c
            order by c.embedding <=> query_embedding
            limit 20
        ) s
    )
    select
        c.id,
        c.document_id,
        d.title,
        c.chunk_index,
        c.page_number,
        c.content,
        1 - (c.embedding <=> query_embedding) as similarity,
        full_text.rank_ix::integer as keyword_rank,
        coalesce(1.0 / (rrf_k + full_text.rank_ix), 0.0)
            + coalesce(1.0 / (rrf_k + semantic.rank_ix), 0.0) as score
    from full_text
    full outer join semantic on full_text.id = semantic.id
    join document_chunks c on c.id = coalesce(full_text.id, semantic.id)
    join documents d on d.id = c.document_id
    where 1 - (c.embedding <=> query_embedding) >= min_similarity
       or full_text.rank_ix <= keyword_top
    order by score desc
    limit least(greatest(match_count, 1), 50);
$$;

revoke execute on function public.hybrid_match_document_chunks(text, extensions.vector, integer, double precision, integer, integer)
    from public, anon, authenticated;
grant execute on function public.hybrid_match_document_chunks(text, extensions.vector, integer, double precision, integer, integer)
    to service_role;
