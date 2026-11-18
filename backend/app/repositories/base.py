"""Shared pieces for every Supabase repository."""

from typing import Any

import httpx
from postgrest.exceptions import APIError

UNIQUE_VIOLATION = "23505"  # Postgres error code: a unique constraint was violated


class RepositoryError(Exception):
    """The database could not be reached or rejected the operation.

    `code` is the Postgres error code when the database rejected it (e.g. "23505"),
    and `db_message` the database's own message, so repositories can tell cases apart.
    """

    def __init__(self, message: str, code: str | None = None, db_message: str | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.db_message = db_message


def execute_query(query: Any) -> list[dict[str, Any]]:
    """Execute a Supabase query and translate library errors into RepositoryError."""
    try:
        return query.execute().data
    except APIError as error:
        raise RepositoryError(
            f"Database rejected the request: {error.message}",
            code=error.code,
            db_message=error.message,
        ) from error
    except httpx.HTTPError as error:
        raise RepositoryError("Could not reach the database.") from error
