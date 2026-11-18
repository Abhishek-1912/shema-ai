"""Unit tests for the wiki: slugs, service rules, and repository error mapping."""

from datetime import UTC, datetime
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from postgrest.exceptions import APIError

from app.models.wiki import WikiArticle, WikiVersion
from app.repositories.wiki_repository import (
    WikiArticleNotFoundError,
    WikiRepository,
    WikiSlugTakenError,
    WikiVersionConflictError,
)
from app.services.wiki_service import WikiService, WikiValidationError, slugify

NOW = datetime(2026, 11, 18, tzinfo=UTC)


def article(**extra) -> WikiArticle:
    data = dict(
        id=uuid4(), slug="remote-work", title="Remote work", content="Up to 3 days.",
        status="draft", version=1, created_by="user", created_at=NOW, updated_at=NOW,
    )
    return WikiArticle(**{**data, **extra})


def version(n: int, content: str) -> WikiVersion:
    return WikiVersion(
        id=uuid4(), article_id=uuid4(), version=n, title=f"Title v{n}", content=content,
        change_note=None, created_by="user", created_at=NOW,
    )


# --- slugify -------------------------------------------------------------------------

@pytest.mark.parametrize(
    ("text", "slug"),
    [
        ("Remote Work Policy", "remote-work-policy"),
        ("  Leave & Holidays (2026)!  ", "leave-holidays-2026"),
        ("Café résumé", "cafe-resume"),
        ("HR-12 form", "hr-12-form"),
        ("!!!", ""),
    ],
)
def test_slugify(text: str, slug: str) -> None:
    assert slugify(text) == slug


def test_slugify_limits_length() -> None:
    assert len(slugify("word " * 50)) <= 80


# --- WikiService ----------------------------------------------------------------------

@pytest.fixture
def repo() -> MagicMock:
    fake = MagicMock(spec=WikiRepository)
    fake.get_by_slug.return_value = article()
    return fake


def test_create_makes_a_slug_and_cleans_input(repo: MagicMock) -> None:
    WikiService(repo).create("  Remote Work Policy ", " Up to 3 days. ", summary="  ")

    repo.create.assert_called_once_with("remote-work-policy", "Remote Work Policy", "Up to 3 days.", None, "user")


def test_create_with_explicit_slug(repo: MagicMock) -> None:
    WikiService(repo).create("Remote work", "x", slug="Home Office", created_by="ai")

    assert repo.create.call_args.args[0] == "home-office"
    assert repo.create.call_args.args[-1] == "ai"


@pytest.mark.parametrize(
    ("title", "content", "message"),
    [("   ", "x", "must not be empty"), ("!!!", "x", "letters or numbers"), ("t" * 201, "x", "title is longer"),
     ("ok", "x" * 50_001, "content is longer")],
)
def test_create_rejects_bad_input(repo: MagicMock, title: str, content: str, message: str) -> None:
    with pytest.raises(WikiValidationError, match=message):
        WikiService(repo).create(title, content)
    repo.create.assert_not_called()


def test_edit_passes_the_expected_version(repo: MagicMock) -> None:
    current = repo.get_by_slug.return_value

    WikiService(repo).edit("remote-work", 1, "Remote work", "Up to 4 days.", change_note=" Policy changed ")

    repo.update.assert_called_once_with(current, 1, "Remote work", "Up to 4 days.", None, "Policy changed", "user")


def test_unknown_article_is_not_found(repo: MagicMock) -> None:
    repo.get_by_slug.return_value = None

    with pytest.raises(WikiArticleNotFoundError):
        WikiService(repo).edit("missing", 1, "t", "c")


def test_restore_adds_the_old_content_as_a_new_version(repo: MagicMock) -> None:
    current = repo.get_by_slug.return_value
    repo.versions.return_value = [version(3, "v3 text"), version(2, "v2 text"), version(1, "v1 text")]

    WikiService(repo).restore("remote-work", version=1, expected_version=3)

    repo.update.assert_called_once_with(current, 3, "Title v1", "v1 text", None, "Restored version 1", "user")


def test_restore_unknown_version_is_rejected(repo: MagicMock) -> None:
    repo.versions.return_value = [version(1, "v1")]

    with pytest.raises(WikiValidationError, match="Version 7"):
        WikiService(repo).restore("remote-work", version=7, expected_version=1)


def test_publish_changes_only_the_status(repo: MagicMock) -> None:
    current = repo.get_by_slug.return_value

    WikiService(repo).publish("remote-work")

    repo.set_status.assert_called_once_with(current.id, "published")
    repo.update.assert_not_called()  # no new content version for a status change


# --- WikiRepository error mapping --------------------------------------------------------

def failing_client(code: str, message: str) -> MagicMock:
    client = MagicMock()
    client.rpc.return_value.execute.side_effect = APIError(
        {"message": message, "code": code, "hint": None, "details": None}
    )
    return client


def test_duplicate_slug_becomes_slug_taken() -> None:
    client = failing_client("23505", 'duplicate key value violates unique constraint "wiki_articles_slug_key"')

    with pytest.raises(WikiSlugTakenError):
        WikiRepository(client).create("remote-work", "Remote work", "x", None, "user")


def test_version_conflict_is_recognised() -> None:
    client = failing_client("P0001", "wiki_version_conflict")

    with pytest.raises(WikiVersionConflictError):
        WikiRepository(client).update(article(), 1, "t", "c", None, None, "user")


def test_missing_article_during_update_is_recognised() -> None:
    client = failing_client("P0001", "wiki_article_not_found")

    with pytest.raises(WikiArticleNotFoundError):
        WikiRepository(client).update(article(), 1, "t", "c", None, None, "user")


def test_create_sends_all_fields_to_the_sql_function() -> None:
    row = article().model_dump(mode="json")
    client = MagicMock()
    client.rpc.return_value.execute.return_value = MagicMock(data=[row])

    created = WikiRepository(client).create("remote-work", "Remote work", "Up to 3 days.", None, "user")

    client.rpc.assert_called_once_with(
        "create_wiki_article",
        {"p_slug": "remote-work", "p_title": "Remote work", "p_content": "Up to 3 days.",
         "p_summary": None, "p_created_by": "user", "p_status": "draft"},
    )
    assert created.slug == "remote-work"
