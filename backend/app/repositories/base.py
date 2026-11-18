"""Shared pieces for every Supabase repository."""

from typing import Any

import httpx
from postgrest.exceptions import APIError


class RepositoryError(Exception):
    """The database could not be reached or rejected the operation."""


def execute_query(query: Any) -> list[dict[str, Any]]:
    """Execute a Supabase query and translate library errors into RepositoryError."""
    try:
        return query.execute().data
    except APIError as error:
        raise RepositoryError(f"Database rejected the request: {error.message}") from error
    except httpx.HTTPError as error:
        raise RepositoryError("Could not reach the database.") from error
