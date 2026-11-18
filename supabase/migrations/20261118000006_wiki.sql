-- ============================================================================
-- Shema AI: LLM Wiki — articles, version history, links (knowledge graph), sources
-- Run once in Supabase Dashboard → SQL Editor (project ndcggbkacmptigfdepvc).
-- All Module 06 tables are created here, so this module needs only this migration.
-- ============================================================================

-- 1. Articles: the CURRENT version of each wiki page (Markdown).
create table public.wiki_articles (
    id           uuid primary key default gen_random_uuid(),
    -- "remote-work-policy": the readable id used in URLs and in [[links]]
    slug         text not null unique check (slug ~ '^[a-z0-9]+(-[a-z0-9]+)*$'),
    title        text not null check (length(trim(title)) > 0),
    content      text not null default '',            -- Markdown
    summary      text,
    status       text not null default 'draft' check (status in ('draft', 'published', 'archived')),
    version      integer not null default 1,          -- goes up by 1 on every edit
    created_by   text not null default 'user' check (created_by in ('user', 'ai')),
    user_id      uuid references auth.users (id) on delete set null,     -- owner (Module 09)
    document_id  uuid references public.documents (id) on delete set null, -- searchable copy (Task 5)
    created_at   timestamptz not null default now(),
    updated_at   timestamptz not null default now()
);

-- 2. Versions: a full copy of the article after every change (never edited, only added).
create table public.wiki_article_versions (
    id           uuid primary key default gen_random_uuid(),
    article_id   uuid not null references public.wiki_articles (id) on delete cascade,
    version      integer not null,
    title        text not null,
    content      text not null,
    change_note  text,                                 -- "Fixed the leave days", "Created"...
    created_by   text not null check (created_by in ('user', 'ai')),
    created_at   timestamptz not null default now(),
    unique (article_id, version)
);

-- 3. Links between articles = the edges of a small knowledge graph.
create table public.wiki_links (
    from_article_id  uuid not null references public.wiki_articles (id) on delete cascade,
    to_article_id    uuid not null references public.wiki_articles (id) on delete cascade,
    relation         text not null default 'related'
                     check (relation in ('related', 'part_of', 'depends_on', 'see_also')),
    created_at       timestamptz not null default now(),
    primary key (from_article_id, to_article_id, relation),
    check (from_article_id <> to_article_id)
);
create index wiki_links_to_idx on public.wiki_links (to_article_id);  -- fast "what links HERE?"

-- 4. Sources: where an article's facts came from. A COPY of title/excerpt is kept, so the
--    provenance survives even if the original document is deleted later.
create table public.wiki_article_sources (
    id              uuid primary key default gen_random_uuid(),
    article_id      uuid not null references public.wiki_articles (id) on delete cascade,
    document_id     uuid references public.documents (id) on delete set null,
    document_title  text not null,
    page_number     integer,
    excerpt         text not null,
    created_at      timestamptz not null default now()
);
create index wiki_article_sources_article_idx on public.wiki_article_sources (article_id);

-- Secure by default (same as every other table): only the backend's secret key can access.
alter table public.wiki_articles enable row level security;
alter table public.wiki_article_versions enable row level security;
alter table public.wiki_links enable row level security;
alter table public.wiki_article_sources enable row level security;

-- 5. Create an article AND its version 1 in ONE transaction (both or neither).
create or replace function public.create_wiki_article(
    p_slug        text,
    p_title       text,
    p_content     text,
    p_summary     text,
    p_created_by  text,
    p_status      text default 'draft'
)
returns setof public.wiki_articles
language plpgsql
set search_path = public
as $$
declare
    article public.wiki_articles;
begin
    insert into wiki_articles (slug, title, content, summary, created_by, status)
    values (p_slug, p_title, p_content, p_summary, p_created_by, p_status)
    returning * into article;

    insert into wiki_article_versions (article_id, version, title, content, change_note, created_by)
    values (article.id, 1, article.title, article.content, 'Created', p_created_by);

    return next article;
end;
$$;

-- 6. Edit an article safely ("optimistic locking"):
--    the caller says which version it edited. If someone else saved in between,
--    the version no longer matches → 'wiki_version_conflict' instead of silently
--    overwriting their work. Update + new version row happen in ONE transaction.
create or replace function public.update_wiki_article(
    p_id                uuid,
    p_expected_version  integer,
    p_title             text,
    p_content           text,
    p_summary           text,
    p_change_note       text,
    p_created_by        text
)
returns setof public.wiki_articles
language plpgsql
set search_path = public
as $$
declare
    article public.wiki_articles;
begin
    update wiki_articles
       set title = p_title,
           content = p_content,
           summary = p_summary,
           version = version + 1,
           updated_at = now()
     where id = p_id
       and version = p_expected_version
    returning * into article;

    if not found then
        if exists (select 1 from wiki_articles where id = p_id) then
            raise exception 'wiki_version_conflict';
        end if;
        raise exception 'wiki_article_not_found';
    end if;

    insert into wiki_article_versions (article_id, version, title, content, change_note, created_by)
    values (article.id, article.version, article.title, article.content, p_change_note, p_created_by);

    return next article;
end;
$$;

-- Only the backend may call them.
revoke execute on function public.create_wiki_article(text, text, text, text, text, text) from public, anon, authenticated;
revoke execute on function public.update_wiki_article(uuid, integer, text, text, text, text, text) from public, anon, authenticated;
grant execute on function public.create_wiki_article(text, text, text, text, text, text) to service_role;
grant execute on function public.update_wiki_article(uuid, integer, text, text, text, text, text) to service_role;
