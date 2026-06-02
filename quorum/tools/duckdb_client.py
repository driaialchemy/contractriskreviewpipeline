"""Deterministic DuckDB client for local TPC-H query execution.

No LLM calls. Lazy singleton connection. Never raises query exceptions.
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any

import duckdb

from quorum.schemas.query import QueryResult

TPCH_TABLES = (
    "customer",
    "lineitem",
    "nation",
    "orders",
    "part",
    "partsupp",
    "region",
    "supplier",
)


class DuckDBConnectionError(Exception):
    """Raised when DuckDB connection or local TPC-H setup fails."""


class DuckDBClient:
    """Singleton DuckDB client with lazy connection and optional TPC-H setup."""

    _instance: "DuckDBClient | None" = None
    _connection: Any | None = None

    def __new__(cls) -> "DuckDBClient":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def _get_connection(self) -> Any:
        """Get or create the DuckDB connection."""
        if self._connection is None:
            try:
                self._connection = duckdb.connect(self._database_path())
                self._initialize_tpch_if_needed(self._connection)
            except Exception as exc:
                raise DuckDBConnectionError(
                    f"Failed to initialize DuckDB TPC-H database: {exc}"
                ) from exc

        return self._connection

    def execute_query(self, sql: str, step_number: int) -> QueryResult:
        """Execute SQL query against the local DuckDB TPC-H database."""
        start_time = time.perf_counter()

        try:
            connection = self._get_connection()
            cursor = connection.execute(sql)
            rows = [list(row) for row in cursor.fetchall()]
            columns = [column[0] for column in cursor.description or []]
            execution_time_ms = (time.perf_counter() - start_time) * 1000

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
        except Exception as exc:
            execution_time_ms = (time.perf_counter() - start_time) * 1000
            return QueryResult(
                step_number=step_number,
                sql_executed=sql,
                columns=[],
                rows=[],
                row_count=0,
                execution_time_ms=execution_time_ms,
                success=False,
                error_detail=str(exc),
            )

    def _database_path(self) -> str:
        configured_path = os.environ.get(
            "QUORUM_DUCKDB_PATH", "data/quorum_tpch.duckdb"
        )
        if configured_path == ":memory:":
            return configured_path

        database_path = Path(configured_path).expanduser()
        if not database_path.is_absolute():
            database_path = Path.cwd() / database_path

        database_path.parent.mkdir(parents=True, exist_ok=True)
        return str(database_path)

    def _initialize_tpch_if_needed(self, connection: Any) -> None:
        if not _env_flag("QUORUM_DUCKDB_INIT_TPCH", default=True):
            return
        if self._tpch_tables_exist(connection):
            return

        scale = _tpch_scale()
        connection.execute("INSTALL tpch")
        connection.execute("LOAD tpch")
        connection.execute(f"CALL dbgen(sf = {scale:g})")

    def _tpch_tables_exist(self, connection: Any) -> bool:
        placeholders = ", ".join(f"'{table}'" for table in TPCH_TABLES)
        result = connection.execute(
            f"""
            SELECT COUNT(*)
            FROM information_schema.tables
            WHERE table_schema = 'main'
              AND lower(table_name) IN ({placeholders})
            """
        ).fetchone()
        return bool(result and result[0] == len(TPCH_TABLES))


def get_duckdb_schema_context() -> str:
    """Return local DuckDB TPC-H schema context for planning and SQL generation."""
    scale = _tpch_scale()

    return f"""DuckDB local TPC-H schema, generated with scale factor {scale:g}:

REGION       R_REGIONKEY(PK), R_NAME, R_COMMENT
             {_scaled_count(5, scale)} rows: AFRICA, AMERICA, ASIA, EUROPE, MIDDLE EAST

NATION       N_NATIONKEY(PK), N_NAME, N_REGIONKEY(FK->REGION), N_COMMENT
             {_scaled_count(25, scale)} rows

CUSTOMER     C_CUSTKEY(PK), C_NAME, C_ADDRESS, C_NATIONKEY(FK->NATION),
             C_PHONE, C_ACCTBAL, C_MKTSEGMENT, C_COMMENT
             {_scaled_count(150_000, scale)} rows

SUPPLIER     S_SUPPKEY(PK), S_NAME, S_ADDRESS, S_NATIONKEY(FK->NATION),
             S_PHONE, S_ACCTBAL, S_COMMENT
             {_scaled_count(10_000, scale)} rows

PART         P_PARTKEY(PK), P_NAME, P_MFGR, P_BRAND, P_TYPE,
             P_SIZE, P_CONTAINER, P_RETAILPRICE, P_COMMENT
             {_scaled_count(200_000, scale)} rows

PARTSUPP     PS_PARTKEY(FK->PART), PS_SUPPKEY(FK->SUPPLIER),
             PS_AVAILQTY, PS_SUPPLYCOST, PS_COMMENT
             Composite PK: (PS_PARTKEY, PS_SUPPKEY) - {_scaled_count(800_000, scale)} rows

ORDERS       O_ORDERKEY(PK), O_CUSTKEY(FK->CUSTOMER), O_ORDERSTATUS,
             O_TOTALPRICE, O_ORDERDATE, O_ORDERPRIORITY, O_CLERK,
             O_SHIPPRIORITY, O_COMMENT
             {_scaled_count(1_500_000, scale)} rows
             O_ORDERSTATUS: 'F'=fulfilled, 'O'=open, 'P'=pending
             O_ORDERPRIORITY: '1-URGENT','2-HIGH','3-MEDIUM','4-NOT SPECIFIED','5-LOW'

LINEITEM     L_ORDERKEY(FK->ORDERS), L_PARTKEY(FK->PART), L_SUPPKEY(FK->SUPPLIER),
             L_LINENUMBER, L_QUANTITY, L_EXTENDEDPRICE, L_DISCOUNT, L_TAX,
             L_RETURNFLAG, L_LINESTATUS, L_SHIPDATE, L_COMMITDATE,
             L_RECEIPTDATE, L_SHIPINSTRUCT, L_SHIPMODE, L_COMMENT
             Composite PK: (L_ORDERKEY, L_LINENUMBER) - {_scaled_count(6_000_000, scale)} rows
             Revenue = L_EXTENDEDPRICE * (1 - L_DISCOUNT)
             L_RETURNFLAG: 'R'=returned, 'A'=accepted, 'N'=none

Key Notes:
- DuckDB table names are local TPC-H tables; use unqualified table names such as ORDERS and LINEITEM.
- Revenue calculation: L_EXTENDEDPRICE * (1 - L_DISCOUNT)
- All queries must include LIMIT clause (maximum 100 rows)
"""


def _env_flag(name: str, *, default: bool) -> bool:
    raw_value = os.environ.get(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() not in {"0", "false", "no", "off"}


def _tpch_scale() -> float:
    raw_scale = os.environ.get("QUORUM_DUCKDB_TPCH_SCALE", "0.1")
    scale = float(raw_scale)
    if scale < 0:
        raise ValueError("QUORUM_DUCKDB_TPCH_SCALE must be 0 or greater.")
    return scale


def _scaled_count(base_count: int, scale: float) -> str:
    count = max(1, int(round(base_count * scale)))
    if count >= 1_000_000:
        return f"~{count / 1_000_000:g}M"
    if count >= 1_000:
        return f"~{count / 1_000:g}K"
    return f"~{count}"
