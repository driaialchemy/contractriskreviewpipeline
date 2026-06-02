"""Deterministic Snowflake client for TPCH_SF1 query execution.

This module handles Snowflake connection management and query execution.
No LLM calls. Lazy singleton connection. Never raises query exceptions.
"""

import os
import time
from typing import Any

import snowflake.connector

from quorum.schemas.query import QueryResult


class SnowflakeConnectionError(Exception):
    """Raised when Snowflake connection cannot be established."""

    pass


class SnowflakeClient:
    """Singleton Snowflake client with lazy connection initialization."""

    _instance: "SnowflakeClient | None" = None
    _connection: Any | None = None

    def __new__(cls) -> "SnowflakeClient":
        """Ensure only one instance exists (singleton pattern)."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def _get_connection(self) -> Any:
        """Get or create the Snowflake connection (lazy initialization).

        Returns:
            Snowflake connection object

        Raises:
            SnowflakeConnectionError: If connection cannot be established
        """
        if self._connection is None:
            try:
                self._connection = snowflake.connector.connect(
                    account=os.environ["SNOWFLAKE_ACCOUNT"],
                    user=os.environ["SNOWFLAKE_USER"],
                    password=os.environ["SNOWFLAKE_PASSWORD"],
                    warehouse=os.environ.get("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH"),
                    database=os.environ.get(
                        "SNOWFLAKE_DATABASE", "SNOWFLAKE_SAMPLE_DATA"
                    ),
                    schema=os.environ.get("SNOWFLAKE_SCHEMA", "TPCH_SF1"),
                    role=os.environ.get("SNOWFLAKE_ROLE", "ACCOUNTADMIN"),
                )
            except Exception as e:
                raise SnowflakeConnectionError(
                    f"Failed to connect to Snowflake: {str(e)}"
                ) from e

        return self._connection

    def execute_query(self, sql: str, step_number: int) -> QueryResult:
        """Execute SQL query against Snowflake TPCH_SF1.

        Args:
            sql: SQL query string (already validated)
            step_number: Step number from query plan (1-indexed)

        Returns:
            QueryResult with success=True and populated data, or
            QueryResult with success=False and error_detail

        Raises:
            SnowflakeConnectionError: If connection cannot be established

        Note:
            Never raises query execution exceptions. All query errors are
            caught and returned in QueryResult.error_detail with success=False.
            Connection errors are raised to fail fast before graph starts.
        """
        # Record start time
        start_time = time.perf_counter()

        # Get or create connection (may raise SnowflakeConnectionError)
        connection = self._get_connection()

        try:
            cursor = connection.cursor()

            # Execute query
            cursor.execute(sql)

            # Fetch all results
            rows = cursor.fetchall()

            # Extract column names from cursor.description
            columns = (
                [col[0] for col in cursor.description] if cursor.description else []
            )

            # Calculate elapsed time in milliseconds
            execution_time_ms = (time.perf_counter() - start_time) * 1000

            # Close cursor
            cursor.close()

            # Return successful result
            return QueryResult(
                step_number=step_number,
                sql_executed=sql,
                columns=columns,
                rows=rows,
                row_count=len(rows),
                execution_time_ms=execution_time_ms,
                success=True,
                error_detail=None,
            )

        except Exception as e:
            # Calculate elapsed time even for failures
            execution_time_ms = (time.perf_counter() - start_time) * 1000

            # Return failed result with error detail
            return QueryResult(
                step_number=step_number,
                sql_executed=sql,
                columns=[],
                rows=[],
                row_count=0,
                execution_time_ms=execution_time_ms,
                success=False,
                error_detail=str(e),
            )


def get_schema_context() -> str:
    """Return TPCH_SF1 schema context for LLM planning and SQL generation.

    Returns:
        Hardcoded string describing TPCH_SF1 schema including table names,
        column names with types, key relationships, approximate row counts,
        and revenue calculation formula.

    Note:
        This is a pure function with no external dependencies.
        Used to inject schema context into AgentState at graph start.
    """
    return """SNOWFLAKE_SAMPLE_DATA.TPCH_SF1 Schema:

REGION       R_REGIONKEY(PK), R_NAME, R_COMMENT
             5 rows: AFRICA, AMERICA, ASIA, EUROPE, MIDDLE EAST

NATION       N_NATIONKEY(PK), N_NAME, N_REGIONKEY(FK→REGION), N_COMMENT
             25 rows

CUSTOMER     C_CUSTKEY(PK), C_NAME, C_ADDRESS, C_NATIONKEY(FK→NATION),
             C_PHONE, C_ACCTBAL, C_MKTSEGMENT, C_COMMENT
             ~150K rows

SUPPLIER     S_SUPPKEY(PK), S_NAME, S_ADDRESS, S_NATIONKEY(FK→NATION),
             S_PHONE, S_ACCTBAL, S_COMMENT
             ~10K rows

PART         P_PARTKEY(PK), P_NAME, P_MFGR, P_BRAND, P_TYPE,
             P_SIZE, P_CONTAINER, P_RETAILPRICE, P_COMMENT
             ~200K rows

PARTSUPP     PS_PARTKEY(FK→PART), PS_SUPPKEY(FK→SUPPLIER),
             PS_AVAILQTY, PS_SUPPLYCOST, PS_COMMENT
             Composite PK: (PS_PARTKEY, PS_SUPPKEY) — ~800K rows

ORDERS       O_ORDERKEY(PK), O_CUSTKEY(FK→CUSTOMER), O_ORDERSTATUS,
             O_TOTALPRICE, O_ORDERDATE, O_ORDERPRIORITY, O_CLERK,
             O_SHIPPRIORITY, O_COMMENT
             ~1.5M rows
             O_ORDERSTATUS: 'F'=fulfilled, 'O'=open, 'P'=pending
             O_ORDERPRIORITY: '1-URGENT','2-HIGH','3-MEDIUM','4-NOT SPECIFIED','5-LOW'

LINEITEM     L_ORDERKEY(FK→ORDERS), L_PARTKEY(FK→PART), L_SUPPKEY(FK→SUPPLIER),
             L_LINENUMBER, L_QUANTITY, L_EXTENDEDPRICE, L_DISCOUNT, L_TAX,
             L_RETURNFLAG, L_LINESTATUS, L_SHIPDATE, L_COMMITDATE,
             L_RECEIPTDATE, L_SHIPINSTRUCT, L_SHIPMODE, L_COMMENT
             Composite PK: (L_ORDERKEY, L_LINENUMBER) — ~6M rows
             Revenue = L_EXTENDEDPRICE * (1 - L_DISCOUNT)
             L_RETURNFLAG: 'R'=returned, 'A'=accepted, 'N'=none

Key Notes:
- Session is already scoped to TPCH_SF1, so use unqualified table names (e.g., ORDERS not SNOWFLAKE_SAMPLE_DATA.TPCH_SF1.ORDERS)
- Revenue calculation: L_EXTENDEDPRICE * (1 - L_DISCOUNT)
- All queries must include LIMIT clause (maximum 100 rows)
"""
