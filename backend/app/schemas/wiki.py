"""Request/response shapes for /api/wiki (docs/api-contract.md v5)."""

from datetime import datetime

from pydantic import BaseModel, Field

from app.models.wiki import ArticleStatus, Author, WikiArticle, WikiVersion
from app.services.wiki_service import MAX_CONTENT_CHARS, MAX_TITLE_CHARS


class ArticleSummary(BaseModel):
    slug: str
    title: str
    summary: str | None
    status: ArticleStatus
    version: int
    created_by: Author
    updated_at: datetime

    @classmethod
    def from_model(cls, article: WikiArticle) -> "ArticleSummary":
        return cls(**article.model_dump(include=set(cls.model_fields)))


class ArticleDetail(ArticleSummary):
    content: str
    created_at: datetime

    @classmethod
    def from_model(cls, article: WikiArticle) -> "ArticleDetail":
        return cls(**article.model_dump(include=set(cls.model_fields)))


class ArticleListResponse(BaseModel):
    articles: list[ArticleSummary]


class ArticleVersionOut(BaseModel):
    version: int
    title: str
    content: str
    change_note: str | None
    created_by: Author
    created_at: datetime

    @classmethod
    def from_model(cls, version: WikiVersion) -> "ArticleVersionOut":
        return cls(**version.model_dump(include=set(cls.model_fields)))


class VersionListResponse(BaseModel):
    versions: list[ArticleVersionOut]


# Limits are checked here (fast 422) AND in WikiService (the rule's real home).
class CreateArticleRequest(BaseModel):
    title: str = Field(max_length=MAX_TITLE_CHARS)
    content: str = Field(default="", max_length=MAX_CONTENT_CHARS)
    summary: str | None = Field(default=None, max_length=500)
    slug: str | None = Field(default=None, max_length=80)


class UpdateArticleRequest(BaseModel):
    title: str = Field(max_length=MAX_TITLE_CHARS)
    content: str = Field(max_length=MAX_CONTENT_CHARS)
    summary: str | None = Field(default=None, max_length=500)
    change_note: str | None = Field(default=None, max_length=300)
    expected_version: int = Field(ge=1)


class RestoreRequest(BaseModel):
    version: int = Field(ge=1)
    expected_version: int = Field(ge=1)
