"""Tests for local DuckDB TPC-H client behavior."""

from unittest.mock import MagicMock, patch

import pytest

from quorum.tools.duckdb_client import (
    DuckDBClient,
    DuckDBConnectionError,
    get_duckdb_schema_context,
)


class TestDuckDBClient:
    """Tests for DuckDBClient with mocked DuckDB connections."""

    def setup_method(self):
        DuckDBClient._instance = None
        DuckDBClient._connection = None

    def test_lazy_connection_initialization(self):
        client = DuckDBClient()

        assert client._connection is None

    @patch("quorum.tools.duckdb_client.duckdb.connect")
    def test_successful_query_execution(self, mock_connect):
        query_cursor = MagicMock()
        query_cursor.fetchall.return_value = [
            (1, "Customer A", 1000.00),
            (2, "Customer B", 2000.00),
        ]
        query_cursor.description = [
            ("C_CUSTKEY", None),
            ("C_NAME", None),
            ("REVENUE", None),
        ]

        mock_connection = MagicMock()
        mock_connection.execute.return_value = query_cursor
        mock_connect.return_value = mock_connection

        with patch.dict(
            "os.environ",
            {
                "QUORUM_DUCKDB_PATH": ":memory:",
                "QUORUM_DUCKDB_INIT_TPCH": "false",
            },
        ):
            result = DuckDBClient().execute_query(
                sql="SELECT C_CUSTKEY, C_NAME FROM CUSTOMER LIMIT 2",
                step_number=1,
            )

        mock_connect.assert_called_once_with(":memory:")
        mock_connection.execute.assert_called_once_with(
            "SELECT C_CUSTKEY, C_NAME FROM CUSTOMER LIMIT 2"
        )
        assert result.success is True
        assert result.columns == ["C_CUSTKEY", "C_NAME", "REVENUE"]
        assert result.rows == [
            [1, "Customer A", 1000.00],
            [2, "Customer B", 2000.00],
        ]
        assert result.row_count == 2
        assert result.error_detail is None

    @patch("quorum.tools.duckdb_client.duckdb.connect")
    def test_auto_initializes_tpch_when_tables_are_missing(self, mock_connect):
        info_cursor = MagicMock()
        info_cursor.fetchone.return_value = (0,)

        query_cursor = MagicMock()
        query_cursor.fetchall.return_value = []
        query_cursor.description = []

        mock_connection = MagicMock()
        mock_connection.execute.side_effect = [
            info_cursor,
            MagicMock(),
            MagicMock(),
            MagicMock(),
            query_cursor,
        ]
        mock_connect.return_value = mock_connection

        with patch.dict(
            "os.environ",
            {
                "QUORUM_DUCKDB_PATH": ":memory:",
                "QUORUM_DUCKDB_TPCH_SCALE": "0.1",
                "QUORUM_DUCKDB_INIT_TPCH": "true",
            },
        ):
            result = DuckDBClient().execute_query("SELECT * FROM ORDERS LIMIT 1", 1)

        assert result.success is True
        executed_sql = [call.args[0] for call in mock_connection.execute.call_args_list]
        assert "INSTALL tpch" in executed_sql
        assert "LOAD tpch" in executed_sql
        assert "CALL dbgen(sf = 0.1)" in executed_sql

    @patch("quorum.tools.duckdb_client.duckdb.connect")
    def test_skips_tpch_initialization_when_tables_exist(self, mock_connect):
        info_cursor = MagicMock()
        info_cursor.fetchone.return_value = (8,)

        query_cursor = MagicMock()
        query_cursor.fetchall.return_value = []
        query_cursor.description = []

        mock_connection = MagicMock()
        mock_connection.execute.side_effect = [info_cursor, query_cursor]
        mock_connect.return_value = mock_connection

        with patch.dict(
            "os.environ",
            {
                "QUORUM_DUCKDB_PATH": ":memory:",
                "QUORUM_DUCKDB_INIT_TPCH": "true",
            },
        ):
            result = DuckDBClient().execute_query("SELECT * FROM ORDERS LIMIT 1", 1)

        assert result.success is True
        executed_sql = [call.args[0] for call in mock_connection.execute.call_args_list]
        assert "INSTALL tpch" not in executed_sql
        assert "LOAD tpch" not in executed_sql

    @patch("quorum.tools.duckdb_client.duckdb.connect")
    def test_query_execution_failure_returns_failed_query_result(self, mock_connect):
        mock_connection = MagicMock()
        mock_connection.execute.side_effect = RuntimeError("syntax error")
        mock_connect.return_value = mock_connection

        with patch.dict(
            "os.environ",
            {
                "QUORUM_DUCKDB_PATH": ":memory:",
                "QUORUM_DUCKDB_INIT_TPCH": "false",
            },
        ):
            result = DuckDBClient().execute_query("SELECT * FROM MISSING", 3)

        assert result.success is False
        assert result.step_number == 3
        assert result.sql_executed == "SELECT * FROM MISSING"
        assert result.columns == []
        assert result.rows == []
        assert result.row_count == 0
        assert "syntax error" in result.error_detail

    @patch("quorum.tools.duckdb_client.duckdb.connect")
    def test_connection_failure_is_returned_as_failed_query_result(self, mock_connect):
        mock_connect.side_effect = DuckDBConnectionError("cannot open database")

        with patch.dict(
            "os.environ",
            {
                "QUORUM_DUCKDB_PATH": ":memory:",
                "QUORUM_DUCKDB_INIT_TPCH": "false",
            },
        ):
            result = DuckDBClient().execute_query("SELECT 1", 1)

        assert result.success is False
        assert "cannot open database" in result.error_detail

    def test_invalid_scale_raises_connection_error_during_initialization(self):
        with patch.dict(
            "os.environ",
            {
                "QUORUM_DUCKDB_PATH": ":memory:",
                "QUORUM_DUCKDB_TPCH_SCALE": "-1",
                "QUORUM_DUCKDB_INIT_TPCH": "true",
            },
        ):
            result = DuckDBClient().execute_query("SELECT 1", 1)

        assert result.success is False
        assert "QUORUM_DUCKDB_TPCH_SCALE" in result.error_detail


class TestDuckDBSchemaContext:
    """Tests for local DuckDB schema context."""

    def test_returns_tpch_schema_string(self):
        schema = get_duckdb_schema_context()

        assert "DuckDB local TPC-H schema" in schema
        assert "REGION" in schema
        assert "NATION" in schema
        assert "CUSTOMER" in schema
        assert "SUPPLIER" in schema
        assert "PART" in schema
        assert "PARTSUPP" in schema
        assert "ORDERS" in schema
        assert "LINEITEM" in schema

    def test_includes_revenue_formula_and_usage_notes(self):
        schema = get_duckdb_schema_context()

        assert "L_EXTENDEDPRICE * (1 - L_DISCOUNT)" in schema
        assert "unqualified table names" in schema
        assert "LIMIT" in schema

    def test_negative_scale_is_invalid_for_schema_context(self):
        with patch.dict("os.environ", {"QUORUM_DUCKDB_TPCH_SCALE": "-1"}):
            with pytest.raises(ValueError, match="QUORUM_DUCKDB_TPCH_SCALE"):
                get_duckdb_schema_context()
