"""Integration test: the wiki's versioning and optimistic locking in the REAL database.

Needs migration 20261118000006_wiki.sql. Run with: pytest -m integration -v
"""

from uuid import uuid4

import pytest

from app.repositories.wiki_repository import WikiSlugTakenError, WikiVersionConflictError
from app.services.wiki_service import get_wiki_service

pytestmark = pytest.mark.integration


def test_article_lifecycle_with_versions_and_conflicts() -> None:
    wiki = get_wiki_service()
    slug = f"integration-test-{uuid4().hex[:8]}"
    article = wiki.create("Integration test article", "Version one text.", slug=slug)

    try:
        assert (article.slug, article.version, article.status) == (slug, 1, "draft")

        # Same slug twice is refused by the database's UNIQUE rule.
        with pytest.raises(WikiSlugTakenError):
            wiki.create("Another", "x", slug=slug)

        # Two people opened version 1. The first save wins and creates version 2 ...
        first = wiki.edit(slug, 1, "Integration test article", "Version two text.", change_note="Second")
        assert first.version == 2

        # ... the second save still says "I edited version 1" → conflict, nothing overwritten.
        with pytest.raises(WikiVersionConflictError):
            wiki.edit(slug, 1, "Integration test article", "Someone else's text.")
        assert wiki.get(slug).content == "Version two text."

        # History keeps every version, newest first.
        history = wiki.history(slug)
        assert [(v.version, v.change_note) for v in history] == [(2, "Second"), (1, "Created")]

        # Restoring version 1 ADDS version 3 with the old text (history is never rewritten).
        restored = wiki.restore(slug, version=1, expected_version=2)
        assert (restored.version, restored.content) == (3, "Version one text.")
        assert [v.version for v in wiki.history(slug)] == [3, 2, 1]

        # Publishing changes the status only — no new version.
        published = wiki.publish(slug)
        assert (published.status, published.version) == ("published", 3)
    finally:
        wiki.delete(slug)
