"""DuckDB-based execution engine for DuckGuard."""

from __future__ import annotations

from typing import Any

import duckdb


class DuckGuardEngine:
    """
    Central DuckDB execution engine for DuckGuard.

    This engine handles all database operations, providing a fast,
    memory-efficient way to validate data from various sources.
    """

    _instance: DuckGuardEngine | None = None

    def __init__(self, memory_limit: str | None = None):
        """
        Initialize the DuckGuard engine.

        Args:
            memory_limit: Optional memory limit for DuckDB (e.g., "4GB")
        """
        self.conn = duckdb.connect(":memory:")

        # Configure DuckDB for optimal performance
        # Wrap in try-except for compatibility with different DuckDB versions
        try:
            self.conn.execute("SET enable_progress_bar = false")
        except duckdb.InvalidInputException:
            # Setting not supported in this DuckDB version - ignore
            pass

        if memory_limit:
            try:
                self.conn.execute(f"SET memory_limit = '{memory_limit}'")
            except duckdb.InvalidInputException:
                pass

        # Track registered sources
        self._sources: dict[str, str] = {}

    @classmethod
    def get_instance(cls) -> DuckGuardEngine:
        """Get or create the singleton engine instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton instance (useful for testing)."""
        if cls._instance is not None:
            cls._instance.close()
            cls._instance = None

    def execute(self, sql: str, params: list[Any] | None = None) -> duckdb.DuckDBPyRelation:
        """
        Execute a SQL query and return the result.

        Args:
            sql: The SQL query to execute
            params: Optional parameters for the query

        Returns:
            DuckDB relation with query results
        """
        if params:
            return self.conn.execute(sql, params)
        return self.conn.execute(sql)

    def fetch_one(self, sql: str, params: list[Any] | None = None) -> tuple[Any, ...] | None:
        """Execute a query and fetch one row."""
        result = self.execute(sql, params)
        return result.fetchone()

    def fetch_all(self, sql: str, params: list[Any] | None = None) -> list[tuple[Any, ...]]:
        """Execute a query and fetch all rows."""
        result = self.execute(sql, params)
        return result.fetchall()

    def fetch_value(self, sql: str, params: list[Any] | None = None) -> Any:
        """Execute a query and fetch a single value."""
        row = self.fetch_one(sql, params)
        return row[0] if row else None

    def register_file(self, name: str, path: str) -> None:
        """
        Register a file as a named source.

        Args:
            name: Name to reference the source
            path: Path to the file (CSV, Parquet, JSON)
        """
        # DuckDB auto-detects file type from extension
        self._sources[name] = path

    def register_dataframe(self, name: str, df: Any) -> None:
        """
        Register a DataFrame (pandas, polars, or pyarrow) as a named source.

        Args:
            name: Name to reference the source
            df: DataFrame to register
        """
        self.conn.register(name, df)
        self._sources[name] = f"registered:{name}"

    def get_source_reference(self, name: str) -> str:
        """
        Get the SQL reference for a registered source.

        Args:
            name: Name of the registered source

        Returns:
            SQL-safe reference to the source
        """
        if name in self._sources:
            source = self._sources[name]
            if source.startswith("registered:"):
                return name
            # Return quoted path for file sources
            return f"'{source}'"
        # Assume it's a direct path or table name
        return f"'{name}'" if "." in name or "/" in name or "\\" in name else name

    def table_exists(self, name: str) -> bool:
        """Check if a table or source exists."""
        try:
            self.execute(f"SELECT 1 FROM {self.get_source_reference(name)} LIMIT 1")
            return True
        except duckdb.Error:
            return False

    def get_columns(self, source: str) -> list[str]:
        """
        Get column names for a source.

        Args:
            source: Source reference (file path or registered name)

        Returns:
            List of column names
        """
        ref = self.get_source_reference(source)
        result = self.execute(f"DESCRIBE SELECT * FROM {ref}")
        return [row[0] for row in result.fetchall()]

    def get_row_count(self, source: str) -> int:
        """
        Get row count for a source.

        Args:
            source: Source reference

        Returns:
            Number of rows
        """
        ref = self.get_source_reference(source)
        return self.fetch_value(f"SELECT COUNT(*) FROM {ref}") or 0

    def get_column_stats(self, source: str, column: str) -> dict[str, Any]:
        """
        Get basic statistics for a column.

        Args:
            source: Source reference
            column: Column name

        Returns:
            Dictionary with column statistics
        """
        ref = self.get_source_reference(source)
        col = f'"{column}"'

        sql = f"""
        SELECT
            COUNT(*) as total_count,
            COUNT({col}) as non_null_count,
            COUNT(*) - COUNT({col}) as null_count,
            COUNT(DISTINCT {col}) as unique_count,
            MIN({col}) as min_value,
            MAX({col}) as max_value
        FROM {ref}
        """

        row = self.fetch_one(sql)
        if not row:
            return {}

        total = row[0] or 0
        non_null = row[1] or 0
        null_count = row[2] or 0
        unique_count = row[3] or 0

        return {
            "total_count": total,
            "non_null_count": non_null,
            "null_count": null_count,
            "null_percent": (null_count / total * 100) if total > 0 else 0.0,
            "unique_count": unique_count,
            "unique_percent": (unique_count / total * 100) if total > 0 else 0.0,
            "min_value": row[4],
            "max_value": row[5],
        }

    def get_all_column_stats(self, source: str, columns: list[str]) -> dict[str, dict[str, Any]]:
        """
        Get basic statistics for ALL columns in a single query.

        This is dramatically faster than calling get_column_stats per column
        because it does one table scan instead of N.

        Args:
            source: Source reference
            columns: List of column names

        Returns:
            Dictionary mapping column name -> stats dict
        """
        if not columns:
            return {}

        ref = self.get_source_reference(source)

        # Build a single query that computes stats for all columns
        select_parts = ["COUNT(*) AS _total_count"]
        for col_name in columns:
            col = f'"{col_name}"'
            safe = col_name.replace('"', '').replace("'", "")
            select_parts.extend([
                f'COUNT({col}) AS "{safe}__non_null"',
                f'COUNT(DISTINCT {col}) AS "{safe}__unique"',
                f'MIN({col}) AS "{safe}__min"',
                f'MAX({col}) AS "{safe}__max"',
            ])

        sql = f"SELECT {', '.join(select_parts)} FROM {ref}"
        row = self.fetch_one(sql)
        if not row:
            return {}

        total = row[0] or 0
        result = {}
        idx = 1
        for col_name in columns:
            non_null = row[idx] or 0
            null_count = total - non_null
            unique_count = row[idx + 1] or 0
            min_val = row[idx + 2]
            max_val = row[idx + 3]

            result[col_name] = {
                "total_count": total,
                "non_null_count": non_null,
                "null_count": null_count,
                "null_percent": (null_count / total * 100) if total > 0 else 0.0,
                "unique_count": unique_count,
                "unique_percent": (unique_count / total * 100) if total > 0 else 0.0,
                "min_value": min_val,
                "max_value": max_val,
            }
            idx += 4

        return result

    def get_all_numeric_stats(self, source: str, columns: list[str]) -> dict[str, dict[str, Any]]:
        """
        Get numeric statistics for multiple columns in a single query.

        Args:
            source: Source reference
            columns: List of numeric column names

        Returns:
            Dictionary mapping column name -> numeric stats dict
        """
        if not columns:
            return {}

        ref = self.get_source_reference(source)

        select_parts = []
        valid_cols = []
        for col_name in columns:
            col = f'"{col_name}"'
            safe = col_name.replace('"', '').replace("'", "")
            select_parts.extend([
                f'AVG({col}::DOUBLE) AS "{safe}__mean"',
                f'STDDEV({col}::DOUBLE) AS "{safe}__stddev"',
                f'MEDIAN({col}::DOUBLE) AS "{safe}__median"',
                f'PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY {col}::DOUBLE) AS "{safe}__p25"',
                f'PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY {col}::DOUBLE) AS "{safe}__p75"',
            ])
            valid_cols.append(col_name)

        if not select_parts:
            return {}

        # Build WHERE clause to exclude rows where all columns are NULL
        sql = f"SELECT {', '.join(select_parts)} FROM {ref}"

        try:
            row = self.fetch_one(sql)
            if not row:
                return {}
        except duckdb.Error:
            return {}

        result = {}
        idx = 0
        for col_name in valid_cols:
            result[col_name] = {
                "mean": row[idx],
                "stddev": row[idx + 1],
                "median": row[idx + 2],
                "p25": row[idx + 3],
                "p75": row[idx + 4],
            }
            idx += 5

        return result

    def get_sample_distinct_values(
        self, source: str, columns: list[str], sample_size: int = 1000, limit_per_col: int = 100
    ) -> dict[str, list[Any]]:
        """
        Get distinct non-null values for multiple columns using a single SAMPLE query.

        Much faster than running SELECT DISTINCT per column.

        Args:
            source: Source reference
            columns: Column names
            sample_size: Number of rows to sample
            limit_per_col: Max distinct values per column

        Returns:
            Dictionary mapping column name -> list of distinct values
        """
        ref = self.get_source_reference(source)

        try:
            sql = f"SELECT * FROM {ref} USING SAMPLE {sample_size} ROWS"
            rows = self.fetch_all(sql)
        except duckdb.Error:
            # SAMPLE not supported for this source, fall back
            return {}

        if not rows:
            return {}

        # Get column names to map positions
        all_cols = self.get_columns(source)
        col_indices = {col: i for i, col in enumerate(all_cols)}

        result = {}
        for col_name in columns:
            idx = col_indices.get(col_name)
            if idx is None:
                result[col_name] = []
                continue

            seen = set()
            values = []
            for row in rows:
                val = row[idx]
                if val is not None and val not in seen:
                    seen.add(val)
                    values.append(val)
                    if len(values) >= limit_per_col:
                        break
            result[col_name] = values

        return result

    def get_numeric_stats(self, source: str, column: str) -> dict[str, Any]:
        """
        Get numeric statistics for a column.

        Args:
            source: Source reference
            column: Column name

        Returns:
            Dictionary with numeric statistics
        """
        ref = self.get_source_reference(source)
        col = f'"{column}"'

        sql = f"""
        SELECT
            AVG({col}::DOUBLE) as mean_value,
            STDDEV({col}::DOUBLE) as stddev_value,
            MEDIAN({col}::DOUBLE) as median_value,
            PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY {col}::DOUBLE) as p25,
            PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY {col}::DOUBLE) as p75
        FROM {ref}
        WHERE {col} IS NOT NULL
        """

        try:
            row = self.fetch_one(sql)
            if not row:
                return {}

            return {
                "mean": row[0],
                "stddev": row[1],
                "median": row[2],
                "p25": row[3],
                "p75": row[4],
            }
        except duckdb.Error:
            # Column might not be numeric
            return {}

    def close(self) -> None:
        """Close the database connection."""
        if self.conn:
            self.conn.close()

    def __enter__(self) -> DuckGuardEngine:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()
