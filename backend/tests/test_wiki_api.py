"""API tests for /api/wiki (contract v5). WikiService is a mock."""

from collections.abc import Iterator
from datetime import UTC, datetime
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.wiki import WikiArticle, WikiVersion
from app.repositories.wiki_repository import (
    WikiArticleNotFoundError,
    WikiSlugTakenError,
    WikiVersionConflictError,
)
from app.services.wiki_service import WikiService, WikiValidationError, get_wiki_service

client = TestClient(app)
NOW = datetime(2026, 11, 18, 10, 0, tzinfo=UTC)


def article(**extra) -> WikiArticle:
    data = dict(
        id=uuid4(), slug="remote-work", title="Remote work", content="# Remote work\n\nUp to **3 days**.",
        summary="Home office rules", status="draft", version=2, created_by="user",
        created_at=NOW, updated_at=NOW,
    )
    return WikiArticle(**{**data, **extra})


@pytest.fixture
def wiki() -> Iterator[MagicMock]:
    fake = MagicMock(spec=WikiService)
    fake.get.return_value = article()
    app.dependency_overrides[get_wiki_service] = lambda: fake
    yield fake
    app.dependency_overrides.clear()


def test_list_articles_with_status_filter(wiki: MagicMock) -> None:
    wiki.list_articles.return_value = [article(status="published")]

    response = client.get("/api/wiki?status=published")

    assert response.status_code == 200
    [summary] = response.json()["articles"]
    assert set(summary) == {"slug", "title", "summary", "status", "version", "created_by", "updated_at"}
    assert "content" not in summary  # the list stays small
    wiki.list_articles.assert_called_once_with("published")


def test_invalid_status_filter_is_422(wiki: MagicMock) -> None:
    assert client.get("/api/wiki?status=secret").status_code == 422


def test_create_returns_201_with_the_article(wiki: MagicMock) -> None:
    wiki.create.return_value = article(version=1)

    response = client.post("/api/wiki", json={"title": "Remote work", "content": "Up to 3 days."})

    assert response.status_code == 201
    assert response.json()["slug"] == "remote-work"
    assert response.json()["content"].startswith("# Remote work")
    wiki.create.assert_called_once_with("Remote work", "Up to 3 days.", None, None)


def test_get_article(wiki: MagicMock) -> None:
    body = client.get("/api/wiki/remote-work").json()

    assert body["version"] == 2 and body["summary"] == "Home office rules"


def test_update_sends_the_expected_version(wiki: MagicMock) -> None:
    wiki.edit.return_value = article(version=3)

    response = client.put(
        "/api/wiki/remote-work",
        json={"title": "Remote work", "content": "Up to 4 days.", "change_note": "Policy update", "expected_version": 2},
    )

    assert response.status_code == 200 and response.json()["version"] == 3
    wiki.edit.assert_called_once_with("remote-work", 2, "Remote work", "Up to 4 days.", None, "Policy update")


def test_update_without_expected_version_is_422(wiki: MagicMock) -> None:
    response = client.put("/api/wiki/remote-work", json={"title": "t", "content": "c"})

    assert response.status_code == 422
    wiki.edit.assert_not_called()


def test_version_conflict_is_409_with_a_helpful_message(wiki: MagicMock) -> None:
    wiki.edit.side_effect = WikiVersionConflictError("remote-work", 2)

    response = client.put("/api/wiki/remote-work", json={"title": "t", "content": "c", "expected_version": 2})

    assert response.status_code == 409
    assert "Someone else changed this article" in response.json()["detail"]


def test_taken_slug_is_409(wiki: MagicMock) -> None:
    wiki.create.side_effect = WikiSlugTakenError("remote-work")

    response = client.post("/api/wiki", json={"title": "Remote work"})

    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]


def test_unknown_article_is_404(wiki: MagicMock) -> None:
    wiki.get.side_effect = WikiArticleNotFoundError("nope")

    response = client.get("/api/wiki/nope")

    assert response.status_code == 404
    assert response.json() == {"detail": "Wiki article not found."}


def test_validation_error_message_is_shown(wiki: MagicMock) -> None:
    wiki.create.side_effect = WikiValidationError("The title must not be empty.")

    response = client.post("/api/wiki", json={"title": "  "})

    assert response.status_code == 422
    assert response.json() == {"detail": "The title must not be empty."}


def test_too_long_title_is_rejected_before_the_service(wiki: MagicMock) -> None:
    assert client.post("/api/wiki", json={"title": "t" * 201}).status_code == 422
    wiki.create.assert_not_called()


def test_versions_newest_first(wiki: MagicMock) -> None:
    wiki.history.return_value = [
        WikiVersion(id=uuid4(), article_id=uuid4(), version=v, title="T", content=f"v{v}",
                    change_note=None, created_by="user", created_at=NOW)
        for v in (2, 1)
    ]

    versions = client.get("/api/wiki/remote-work/versions").json()["versions"]

    assert [v["version"] for v in versions] == [2, 1]


def test_restore(wiki: MagicMock) -> None:
    wiki.restore.return_value = article(version=3)

    response = client.post("/api/wiki/remote-work/restore", json={"version": 1, "expected_version": 2})

    assert response.status_code == 200
    wiki.restore.assert_called_once_with("remote-work", 1, 2)


def test_publish_and_archive(wiki: MagicMock) -> None:
    wiki.publish.return_value = article(status="published")
    wiki.archive.return_value = article(status="archived")

    assert client.post("/api/wiki/remote-work/publish").json()["status"] == "published"
    assert client.post("/api/wiki/remote-work/archive").json()["status"] == "archived"


def test_delete_returns_204(wiki: MagicMock) -> None:
    response = client.delete("/api/wiki/remote-work")

    assert response.status_code == 204
    wiki.delete.assert_called_once_with("remote-work")
