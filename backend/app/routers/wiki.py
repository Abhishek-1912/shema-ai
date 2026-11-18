"""HTTP layer for the wiki. No rules here: they live in WikiService."""

from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from app.models.wiki import ArticleStatus
from app.schemas.wiki import (
    ArticleDetail,
    ArticleListResponse,
    ArticleSummary,
    ArticleVersionOut,
    CreateArticleRequest,
    RestoreRequest,
    UpdateArticleRequest,
    VersionListResponse,
)
from app.services.wiki_service import WikiService, get_wiki_service

router = APIRouter(prefix="/api/wiki", tags=["wiki"])

Wiki = Annotated[WikiService, Depends(get_wiki_service)]


@router.get("", response_model=ArticleListResponse)
def list_articles(wiki: Wiki, status: ArticleStatus | None = None) -> ArticleListResponse:
    return ArticleListResponse(articles=[ArticleSummary.from_model(a) for a in wiki.list_articles(status)])


@router.post("", response_model=ArticleDetail, status_code=status.HTTP_201_CREATED)
def create_article(request: CreateArticleRequest, wiki: Wiki) -> ArticleDetail:
    article = wiki.create(request.title, request.content, request.summary, request.slug)
    return ArticleDetail.from_model(article)


@router.get("/{slug}", response_model=ArticleDetail)
def get_article(slug: str, wiki: Wiki) -> ArticleDetail:
    return ArticleDetail.from_model(wiki.get(slug))


@router.put("/{slug}", response_model=ArticleDetail)
def update_article(slug: str, request: UpdateArticleRequest, wiki: Wiki) -> ArticleDetail:
    article = wiki.edit(
        slug, request.expected_version, request.title, request.content,
        request.summary, request.change_note,
    )
    return ArticleDetail.from_model(article)


@router.delete("/{slug}", status_code=status.HTTP_204_NO_CONTENT)
def delete_article(slug: str, wiki: Wiki) -> Response:
    wiki.delete(slug)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{slug}/versions", response_model=VersionListResponse)
def list_versions(slug: str, wiki: Wiki) -> VersionListResponse:
    return VersionListResponse(versions=[ArticleVersionOut.from_model(v) for v in wiki.history(slug)])


@router.post("/{slug}/restore", response_model=ArticleDetail)
def restore_version(slug: str, request: RestoreRequest, wiki: Wiki) -> ArticleDetail:
    return ArticleDetail.from_model(wiki.restore(slug, request.version, request.expected_version))


@router.post("/{slug}/publish", response_model=ArticleDetail)
def publish(slug: str, wiki: Wiki) -> ArticleDetail:
    return ArticleDetail.from_model(wiki.publish(slug))


@router.post("/{slug}/archive", response_model=ArticleDetail)
def archive(slug: str, wiki: Wiki) -> ArticleDetail:
    return ArticleDetail.from_model(wiki.archive(slug))
