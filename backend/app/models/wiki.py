"""Wiki data as stored in the database."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

ArticleStatus = Literal["draft", "published", "archived"]
Author = Literal["user", "ai"]
Relation = Literal["related", "part_of", "depends_on", "see_also"]


class WikiArticle(BaseModel):
    id: UUID
    slug: str
    title: str
    content: str
    summary: str | None = None
    status: ArticleStatus
    version: int
    created_by: Author
    document_id: UUID | None = None
    created_at: datetime
    updated_at: datetime


class WikiVersion(BaseModel):
    id: UUID
    article_id: UUID
    version: int
    title: str
    content: str
    change_note: str | None = None
    created_by: Author
    created_at: datetime
