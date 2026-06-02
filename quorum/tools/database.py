"""Database backend selection for deterministic query execution."""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Protocol

from quorum.schemas.query import QueryResult
from quorum.tools.duckdb_client import DuckDBClient, get_duckdb_schema_context
from quorum.tools.snowflake_client import (
    SnowflakeClient,
    get_schema_context as get_snowflake_schema_context,
)


class QueryClient(Protocol):
    """Execution client interface shared by local and cloud backends."""

    def execute_query(self, sql: str, step_number: int) -> QueryResult:
        """Execute validated SQL for a plan step."""


def get_database_backend() -> str:
    """Return the configured query backend name."""
    return os.environ.get("QUORUM_DATABASE_BACKEND", "duckdb").strip().lower()


@lru_cache(maxsize=1)
def get_query_client() -> QueryClient:
    """Return the singleton query client for the configured backend."""
    backend = get_database_backend()
    if backend == "duckdb":
        return DuckDBClient()
    if backend == "snowflake":
        return SnowflakeClient()
    raise ValueError(
        "Unsupported QUORUM_DATABASE_BACKEND. Use 'duckdb' or 'snowflake'."
    )


def get_schema_context() -> str:
    """Return schema context for the configured backend."""
    backend = get_database_backend()
    if backend == "duckdb":
        return get_duckdb_schema_context()
    if backend == "snowflake":
        return get_snowflake_schema_context()
    raise ValueError(
        "Unsupported QUORUM_DATABASE_BACKEND. Use 'duckdb' or 'snowflake'."
    )


def reset_query_client_cache() -> None:
    """Clear the backend client cache for tests or runtime reconfiguration."""
    get_query_client.cache_clear()
