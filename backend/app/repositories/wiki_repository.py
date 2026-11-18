"""Repository for wiki articles and their version history."""

from functools import lru_cache
from uuid import UUID

from supabase import Client

from app.core.supabase import get_supabase_client
from app.models.wiki import ArticleStatus, Author, WikiArticle, WikiVersion
from app.repositories.base import UNIQUE_VIOLATION, RepositoryError, execute_query

ARTICLES = "wiki_articles"
VERSIONS = "wiki_article_versions"


class WikiArticleNotFoundError(Exception):
    def __init__(self, key: str) -> None:
        super().__init__(f"Wiki article '{key}' not found.")
        self.key = key


class WikiSlugTakenError(Exception):
    def __init__(self, slug: str) -> None:
        super().__init__(f"A wiki article with the slug '{slug}' already exists.")
        self.slug = slug


class WikiVersionConflictError(Exception):
    """Someone saved the article after you opened it (optimistic locking)."""

    def __init__(self, slug: str, expected_version: int) -> None:
        super().__init__(f"'{slug}' was changed by someone else after version {expected_version}.")
        self.slug = slug
        self.expected_version = expected_version


class WikiRepository:
    def __init__(self, client: Client) -> None:
        self._client = client

    _run = staticmethod(execute_query)

    def create(
        self,
        slug: str,
        title: str,
        content: str,
        summary: str | None,
        created_by: Author,
        status: ArticleStatus = "draft",
    ) -> WikiArticle:
        """Article + its version 1, in one database transaction (SQL function)."""
        try:
            rows = self._run(
                self._client.rpc(
                    "create_wiki_article",
                    {
                        "p_slug": slug, "p_title": title, "p_content": content,
                        "p_summary": summary, "p_created_by": created_by, "p_status": status,
                    },
                )
            )
        except RepositoryError as error:
            if error.code == UNIQUE_VIOLATION:
                raise WikiSlugTakenError(slug) from error
            raise
        return WikiArticle.model_validate(rows[0])

    def update(
        self,
        article: WikiArticle,
        expected_version: int,
        title: str,
        content: str,
        summary: str | None,
        change_note: str | None,
        created_by: Author,
    ) -> WikiArticle:
        """Save a new version, but only if nobody saved since `expected_version`."""
        try:
            rows = self._run(
                self._client.rpc(
                    "update_wiki_article",
                    {
                        "p_id": str(article.id), "p_expected_version": expected_version,
                        "p_title": title, "p_content": content, "p_summary": summary,
                        "p_change_note": change_note, "p_created_by": created_by,
                    },
                )
            )
        except RepositoryError as error:
            message = error.db_message or ""
            if "wiki_version_conflict" in message:
                raise WikiVersionConflictError(article.slug, expected_version) from error
            if "wiki_article_not_found" in message:
                raise WikiArticleNotFoundError(article.slug) from error
            raise
        return WikiArticle.model_validate(rows[0])

    def get_by_slug(self, slug: str) -> WikiArticle | None:
        rows = self._run(self._client.table(ARTICLES).select("*").eq("slug", slug).limit(1))
        return WikiArticle.model_validate(rows[0]) if rows else None

    # Not called "list": a method with that name would hide Python's built-in `list`
    # for every type hint written after it in this class (e.g. -> list[WikiVersion]).
    def list_articles(self, status: ArticleStatus | None = None) -> list[WikiArticle]:
        query = self._client.table(ARTICLES).select("*").order("updated_at", desc=True)
        if status is not None:
            query = query.eq("status", status)
        return [WikiArticle.model_validate(row) for row in self._run(query)]

    def set_status(self, article_id: UUID, status: ArticleStatus) -> WikiArticle:
        """Status changes (publish/archive) don't change the content, so no new version."""
        rows = self._run(
            self._client.table(ARTICLES).update({"status": status}).eq("id", str(article_id))
        )
        return WikiArticle.model_validate(rows[0])

    def delete(self, article_id: UUID) -> None:
        self._run(self._client.table(ARTICLES).delete().eq("id", str(article_id)))

    def versions(self, article_id: UUID) -> list[WikiVersion]:
        """Full history, newest first."""
        rows = self._run(
            self._client.table(VERSIONS)
            .select("*")
            .eq("article_id", str(article_id))
            .order("version", desc=True)
        )
        return [WikiVersion.model_validate(row) for row in rows]


@lru_cache
def get_wiki_repository() -> WikiRepository:
    return WikiRepository(get_supabase_client())
