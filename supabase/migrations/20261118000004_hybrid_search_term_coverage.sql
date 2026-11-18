-- ============================================================================
-- Shema AI: hybrid search fix — keyword matches need "term coverage"
-- Run once in Supabase Dashboard → SQL Editor (project ndcggbkacmptigfdepvc).
--
-- Problem found on 2026-11-18: matching ANY query word let filler words create
-- keyword matches. "How do I get my money back?" matched a leave chunk only through
-- the word "get", and RRF ranked it above the correct refund chunk.
-- Fix: a chunk counts as a keyword match only if it contains at least HALF of the
-- question's meaningful words ("KESTREL" → 1/1 ok, "get money back" → 1/3 not ok).
-- Same signature as before, so the backend code does not change.
-- ============================================================================

create or replace function public.hybrid_match_document_chunks(
    query_text       text,
    query_embedding  extensions.vector(768),
    match_count      integer default 5,
    min_similarity   double precision default 0,
    keyword_top      integer default 2,
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
    keyword_rank    integer,
    score           double precision
)
language sql
stable
set search_path = public, extensions
as $$
    with query_terms as (
        -- The question's meaningful words, normalized like the chunks' fts column
        -- ("How do I get my money back?" → get, money, back).
        select distinct unnest(tsvector_to_array(to_tsvector('english', query_text))) as term
    ),
    term_total as (
        select count(*) as n from query_terms
    ),
    keyword_hits as (
        -- For every chunk: how many of the question's words does it contain?
        select c.id, count(*) as matched
        from document_chunks c
        join query_terms t on c.fts @@ quote_literal(t.term)::tsquery
        group by c.id
    ),
    full_text as (
        select h.id, row_number() over (order by h.matched desc, h.id) as rank_ix
        from keyword_hits h, term_total
        where term_total.n > 0
          and h.matched::double precision / term_total.n >= 0.5   -- term coverage ≥ 50 %
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
