"""Tests for database backend selection."""

from unittest.mock import patch

import pytest

import quorum.tools.database as database_module


class FakeDuckDBClient:
    pass


class FakeSnowflakeClient:
    pass


def setup_function():
    database_module.reset_query_client_cache()


def teardown_function():
    database_module.reset_query_client_cache()


def test_default_backend_is_duckdb(monkeypatch):
    fake_client = FakeDuckDBClient()
    monkeypatch.setattr(database_module, "DuckDBClient", lambda: fake_client)

    with patch.dict("os.environ", {}, clear=True):
        assert database_module.get_database_backend() == "duckdb"
        assert database_module.get_query_client() is fake_client


def test_snowflake_backend_can_be_selected(monkeypatch):
    fake_client = FakeSnowflakeClient()
    monkeypatch.setattr(database_module, "SnowflakeClient", lambda: fake_client)

    with patch.dict("os.environ", {"QUORUM_DATABASE_BACKEND": "snowflake"}):
        assert database_module.get_query_client() is fake_client


def test_backend_selection_is_case_insensitive(monkeypatch):
    fake_client = FakeDuckDBClient()
    monkeypatch.setattr(database_module, "DuckDBClient", lambda: fake_client)

    with patch.dict("os.environ", {"QUORUM_DATABASE_BACKEND": " DuckDB "}):
        assert database_module.get_database_backend() == "duckdb"
        assert database_module.get_query_client() is fake_client


def test_invalid_backend_is_rejected():
    with patch.dict("os.environ", {"QUORUM_DATABASE_BACKEND": "postgres"}):
        with pytest.raises(ValueError, match="duckdb.*snowflake"):
            database_module.get_query_client()


def test_schema_context_dispatches_to_duckdb(monkeypatch):
    monkeypatch.setattr(database_module, "get_duckdb_schema_context", lambda: "duckdb")

    with patch.dict("os.environ", {"QUORUM_DATABASE_BACKEND": "duckdb"}):
        assert database_module.get_schema_context() == "duckdb"


def test_schema_context_dispatches_to_snowflake(monkeypatch):
    monkeypatch.setattr(
        database_module, "get_snowflake_schema_context", lambda: "snowflake"
    )

    with patch.dict("os.environ", {"QUORUM_DATABASE_BACKEND": "snowflake"}):
        assert database_module.get_schema_context() == "snowflake"
