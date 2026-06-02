"""Tests for Snowflake client with lazy connection and error handling."""

from unittest.mock import MagicMock, patch

import pytest

from quorum.tools.snowflake_client import (
    SnowflakeClient,
    SnowflakeConnectionError,
    get_schema_context,
)


class TestSnowflakeClient:
    """Tests for SnowflakeClient with mocked Snowflake connector."""

    def setup_method(self):
        """Reset singleton before each test."""
        SnowflakeClient._instance = None
        SnowflakeClient._connection = None

    def test_lazy_connection_initialization(self):
        """Should not connect to Snowflake at instantiation time."""
        client = SnowflakeClient()
        # Connection should be None until first query
        assert client._connection is None

    @patch("quorum.tools.snowflake_client.snowflake.connector.connect")
    def test_successful_query_execution(self, mock_connect):
        """Should execute query and return populated QueryResult."""
        # Mock Snowflake connection and cursor
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            [1, "Customer A", 1000.00],
            [2, "Customer B", 2000.00],
        ]
        mock_cursor.description = [
            ("C_CUSTKEY", None),
            ("C_NAME", None),
            ("REVENUE", None),
        ]

        mock_connection = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_connection

        # Set required environment variables
        with patch.dict(
            "os.environ",
            {
                "SNOWFLAKE_ACCOUNT": "test-account",
                "SNOWFLAKE_USER": "test-user",
                "SNOWFLAKE_PASSWORD": "test-password",
            },
        ):
            client = SnowflakeClient()
            result = client.execute_query(
                sql="SELECT C_CUSTKEY, C_NAME, SUM(REVENUE) FROM CUSTOMER LIMIT 2",
                step_number=1,
            )

        # Verify connection was created
        mock_connect.assert_called_once()

        # Verify cursor was used
        mock_cursor.execute.assert_called_once()
        mock_cursor.fetchall.assert_called_once()
        mock_cursor.close.assert_called_once()

        # Verify result
        assert result.success is True
        assert result.step_number == 1
        assert result.row_count == 2
        assert result.columns == ["C_CUSTKEY", "C_NAME", "REVENUE"]
        assert len(result.rows) == 2
        assert result.rows[0] == [1, "Customer A", 1000.00]
        assert result.execution_time_ms > 0
        assert result.error_detail is None

    @patch("quorum.tools.snowflake_client.snowflake.connector.connect")
    def test_connection_reuse(self, mock_connect):
        """Should reuse connection across multiple queries (singleton)."""
        # Mock connection
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_cursor.description = []

        mock_connection = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_connection

        with patch.dict(
            "os.environ",
            {
                "SNOWFLAKE_ACCOUNT": "test-account",
                "SNOWFLAKE_USER": "test-user",
                "SNOWFLAKE_PASSWORD": "test-password",
            },
        ):
            client = SnowflakeClient()

            # Execute first query
            client.execute_query("SELECT * FROM ORDERS LIMIT 1", step_number=1)

            # Execute second query
            client.execute_query("SELECT * FROM CUSTOMER LIMIT 1", step_number=2)

        # Connection should only be created once
        mock_connect.assert_called_once()

    @patch("quorum.tools.snowflake_client.snowflake.connector.connect")
    def test_query_execution_failure(self, mock_connect):
        """Should catch exceptions and return QueryResult with success=False."""
        # Mock cursor that raises exception
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = Exception("SQL syntax error: invalid query")

        mock_connection = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_connection

        with patch.dict(
            "os.environ",
            {
                "SNOWFLAKE_ACCOUNT": "test-account",
                "SNOWFLAKE_USER": "test-user",
                "SNOWFLAKE_PASSWORD": "test-password",
            },
        ):
            client = SnowflakeClient()
            result = client.execute_query(
                sql="SELECT * FROM INVALID_TABLE", step_number=1
            )

        # Verify failure was caught and returned
        assert result.success is False
        assert result.row_count == 0
        assert result.columns == []
        assert result.rows == []
        assert "SQL syntax error" in result.error_detail
        assert result.execution_time_ms >= 0

    @patch("quorum.tools.snowflake_client.snowflake.connector.connect")
    def test_connection_failure_raises_error(self, mock_connect):
        """Should raise SnowflakeConnectionError if connection fails."""
        # Mock connection failure
        mock_connect.side_effect = Exception("Invalid credentials")

        with patch.dict(
            "os.environ",
            {
                "SNOWFLAKE_ACCOUNT": "test-account",
                "SNOWFLAKE_USER": "test-user",
                "SNOWFLAKE_PASSWORD": "wrong-password",
            },
        ):
            client = SnowflakeClient()

        # Connection error should occur when executing query (lazy initialization)
        with pytest.raises(
            SnowflakeConnectionError, match="Failed to connect to Snowflake"
        ):
            client.execute_query("SELECT 1", step_number=1)

    @patch("quorum.tools.snowflake_client.snowflake.connector.connect")
    def test_uses_environment_variables(self, mock_connect):
        """Should use environment variables for connection config."""
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_cursor.description = []

        mock_connection = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_connection

        with patch.dict(
            "os.environ",
            {
                "SNOWFLAKE_ACCOUNT": "my-account",
                "SNOWFLAKE_USER": "my-user",
                "SNOWFLAKE_PASSWORD": "my-password",
                "SNOWFLAKE_WAREHOUSE": "MY_WAREHOUSE",
                "SNOWFLAKE_DATABASE": "MY_DATABASE",
                "SNOWFLAKE_SCHEMA": "MY_SCHEMA",
                "SNOWFLAKE_ROLE": "MY_ROLE",
            },
        ):
            client = SnowflakeClient()
            client.execute_query("SELECT 1", step_number=1)

        # Verify connection was called with correct parameters
        mock_connect.assert_called_once_with(
            account="my-account",
            user="my-user",
            password="my-password",
            warehouse="MY_WAREHOUSE",
            database="MY_DATABASE",
            schema="MY_SCHEMA",
            role="MY_ROLE",
        )

    @patch("quorum.tools.snowflake_client.snowflake.connector.connect")
    def test_uses_default_config_when_optional_vars_missing(self, mock_connect):
        """Should use default values when optional env vars are missing."""
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_cursor.description = []

        mock_connection = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_connection

        # Only required vars
        with patch.dict(
            "os.environ",
            {
                "SNOWFLAKE_ACCOUNT": "test-account",
                "SNOWFLAKE_USER": "test-user",
                "SNOWFLAKE_PASSWORD": "test-password",
            },
            clear=True,
        ):
            client = SnowflakeClient()
            client.execute_query("SELECT 1", step_number=1)

        # Verify defaults were used
        mock_connect.assert_called_once_with(
            account="test-account",
            user="test-user",
            password="test-password",
            warehouse="COMPUTE_WH",
            database="SNOWFLAKE_SAMPLE_DATA",
            schema="TPCH_SF1",
            role="ACCOUNTADMIN",
        )

    @patch("quorum.tools.snowflake_client.snowflake.connector.connect")
    def test_singleton_pattern(self, mock_connect):
        """Should return same instance across multiple instantiations."""
        with patch.dict(
            "os.environ",
            {
                "SNOWFLAKE_ACCOUNT": "test-account",
                "SNOWFLAKE_USER": "test-user",
                "SNOWFLAKE_PASSWORD": "test-password",
            },
        ):
            client1 = SnowflakeClient()
            client2 = SnowflakeClient()

        # Both should be the same instance
        assert client1 is client2


class TestGetSchemaContext:
    """Tests for get_schema_context function."""

    def test_returns_tpch_schema_string(self):
        """Should return hardcoded TPCH_SF1 schema description."""
        schema = get_schema_context()

        # Verify schema is a string
        assert isinstance(schema, str)

        # Verify key TPCH tables are documented
        assert "REGION" in schema
        assert "NATION" in schema
        assert "CUSTOMER" in schema
        assert "SUPPLIER" in schema
        assert "PART" in schema
        assert "PARTSUPP" in schema
        assert "ORDERS" in schema
        assert "LINEITEM" in schema

    def test_includes_revenue_formula(self):
        """Should include revenue calculation formula."""
        schema = get_schema_context()
        assert "L_EXTENDEDPRICE * (1 - L_DISCOUNT)" in schema

    def test_includes_row_counts(self):
        """Should include approximate row counts for tables."""
        schema = get_schema_context()
        assert "~150K rows" in schema  # CUSTOMER
        assert "~1.5M rows" in schema  # ORDERS
        assert "~6M rows" in schema  # LINEITEM

    def test_includes_column_names(self):
        """Should include key column names."""
        schema = get_schema_context()
        # Check some representative columns
        assert "C_CUSTKEY" in schema
        assert "O_ORDERKEY" in schema
        assert "L_EXTENDEDPRICE" in schema
        assert "R_REGIONKEY" in schema

    def test_includes_usage_notes(self):
        """Should include notes about unqualified table names and LIMIT."""
        schema = get_schema_context()
        assert "unqualified table names" in schema
        assert "LIMIT" in schema
