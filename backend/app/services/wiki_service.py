"""Wiki business rules: slugs, validation, editing with versions, restore, publish.

A wiki article has ONE current version (in wiki_articles) and a full history
(in wiki_article_versions). Every edit adds a version; nothing is ever overwritten
in the history, so any older version can be restored.
"""

import re
import unicodedata
from functools import lru_cache

from app.models.wiki import ArticleStatus, Author, WikiArticle, WikiVersion
from app.repositories.wiki_repository import (
    WikiArticleNotFoundError,
    WikiRepository,
    get_wiki_repository,
)

MAX_TITLE_CHARS = 200
MAX_CONTENT_CHARS = 50_000
MAX_SLUG_CHARS = 80


def slugify(text: str) -> str:
    """'Remote Work Policy (2026)!' → 'remote-work-policy-2026'. ASCII only, URL-safe."""
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_text.lower()).strip("-")
    return slug[:MAX_SLUG_CHARS].rstrip("-")


class WikiValidationError(ValueError):
    """Invalid input; the message is safe to show to the user."""


class WikiService:
    def __init__(self, repository: WikiRepository) -> None:
        self._repo = repository

    # --- Reading -------------------------------------------------------------------

    def get(self, slug: str) -> WikiArticle:
        article = self._repo.get_by_slug(slug)
        if article is None:
            raise WikiArticleNotFoundError(slug)
        return article

    def list_articles(self, status: ArticleStatus | None = None) -> list[WikiArticle]:
        return self._repo.list_articles(status)

    def history(self, slug: str) -> list[WikiVersion]:
        return self._repo.versions(self.get(slug).id)

    # --- Writing -------------------------------------------------------------------

    def create(
        self,
        title: str,
        content: str,
        summary: str | None = None,
        slug: str | None = None,
        created_by: Author = "user",
    ) -> WikiArticle:
        title, content = self._clean(title, content)
        slug = slugify(slug or title)
        if not slug:
            raise WikiValidationError("The title must contain letters or numbers (needed for the URL).")
        return self._repo.create(slug, title, content, self._summary(summary), created_by)

    def edit(
        self,
        slug: str,
        expected_version: int,
        title: str,
        content: str,
        summary: str | None = None,
        change_note: str | None = None,
        created_by: Author = "user",
    ) -> WikiArticle:
        """Save a new version. Raises WikiVersionConflictError if someone saved in between."""
        title, content = self._clean(title, content)
        article = self.get(slug)
        return self._repo.update(
            article, expected_version, title, content, self._summary(summary),
            (change_note or "").strip() or None, created_by,
        )

    def restore(self, slug: str, version: int, expected_version: int) -> WikiArticle:
        """Go back to an older version — by adding it as a NEW version (history is kept)."""
        article = self.get(slug)
        old = next((v for v in self._repo.versions(article.id) if v.version == version), None)
        if old is None:
            raise WikiValidationError(f"Version {version} does not exist.")
        return self._repo.update(
            article, expected_version, old.title, old.content, article.summary,
            f"Restored version {version}", "user",
        )

    def publish(self, slug: str) -> WikiArticle:
        return self._repo.set_status(self.get(slug).id, "published")

    def archive(self, slug: str) -> WikiArticle:
        return self._repo.set_status(self.get(slug).id, "archived")

    def delete(self, slug: str) -> None:
        self._repo.delete(self.get(slug).id)

    # --- Helpers -------------------------------------------------------------------

    @staticmethod
    def _clean(title: str, content: str) -> tuple[str, str]:
        title, content = title.strip(), content.strip()
        if not title:
            raise WikiValidationError("The title must not be empty.")
        if len(title) > MAX_TITLE_CHARS:
            raise WikiValidationError(f"The title is longer than {MAX_TITLE_CHARS} characters.")
        if len(content) > MAX_CONTENT_CHARS:
            raise WikiValidationError(f"The content is longer than {MAX_CONTENT_CHARS} characters.")
        return title, content

    @staticmethod
    def _summary(summary: str | None) -> str | None:
        return (summary or "").strip() or None


@lru_cache
def get_wiki_service() -> WikiService:
    return WikiService(get_wiki_repository())
