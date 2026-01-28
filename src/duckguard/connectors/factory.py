"""Factory function for creating connections."""

from __future__ import annotations

from typing import Any

from duckguard.connectors.base import ConnectionConfig, Connector
from duckguard.connectors.files import AzureConnector, FileConnector, GCSConnector, S3Connector
from duckguard.core.dataset import Dataset
from duckguard.core.engine import DuckGuardEngine

# Registry of available connectors
_CONNECTORS: list[type[Connector]] = [
    S3Connector,
    GCSConnector,
    AzureConnector,
    FileConnector,
]


def register_connector(connector_class: type[Connector]) -> None:
    """
    Register a custom connector.

    Args:
        connector_class: Connector class to register
    """
    _CONNECTORS.append(connector_class)
    # Sort by priority (highest first)
    _CONNECTORS.sort(key=lambda c: c.get_priority(), reverse=True)


def connect(
    source: Any,
    *,
    table: str | None = None,
    schema: str | None = None,
    database: str | None = None,
    engine: DuckGuardEngine | None = None,
    **options: Any,
) -> Dataset:
    """
    Connect to a data source and return a Dataset.

    This is the main entry point for connecting to data sources.
    It automatically detects the source type and uses the appropriate connector.

    Args:
        source: Path to file, connection string, URL, or DataFrame (pandas/polars/pyarrow)
        table: Table name (for database connections)
        schema: Schema name (for database connections)
        database: Database name (for database connections)
        engine: Optional DuckGuardEngine instance
        **options: Additional options passed to the connector

    Returns:
        Dataset object ready for validation

    Examples:
        # Connect to a CSV file
        orders = connect("data/orders.csv")

        # Connect to a DataFrame
        orders = connect(df)

        # Connect to a Parquet file on S3
        orders = connect("s3://bucket/orders.parquet")

        # Connect to PostgreSQL
        orders = connect("postgres://localhost/mydb", table="orders")

        # Connect to Snowflake
        orders = connect("snowflake://account/db", table="orders", schema="public")

    Raises:
        ValueError: If no connector can handle the source
    """
    # Handle DataFrame sources (pandas, polars, pyarrow)
    if not isinstance(source, str):
        # Check if it's a DataFrame-like object
        if hasattr(source, '__dataframe__') or hasattr(source, 'to_pandas') or \
           (hasattr(source, 'shape') and hasattr(source, 'columns')):
            # Register DataFrame with engine
            if engine is None:
                engine = DuckGuardEngine.get_instance()

            # Generate a unique name for the DataFrame
            import hashlib
            import time
            df_name = f"df_{hashlib.md5(str(time.time()).encode()).hexdigest()[:8]}"

            engine.register_dataframe(df_name, source)
            return Dataset(source=df_name, engine=engine, name="dataframe")

    config = ConnectionConfig(
        source=source,
        table=table,
        schema=schema,
        database=database,
        options=options,
    )

    # Find a connector that can handle this source
    for connector_class in _CONNECTORS:
        if connector_class.can_handle(source):
            connector = connector_class(engine=engine)
            return connector.connect(config)

    # Check for database connection strings
    if _is_database_connection(source):
        return _handle_database_connection(source, config, engine)

    raise ValueError(
        f"No connector found for source: {source}\n"
        f"Supported formats: CSV, Parquet, JSON, Excel\n"
        f"Supported protocols: s3://, gs://, az://, postgres://, mysql://"
    )


def _is_database_connection(source: str) -> bool:
    """Check if source is a database connection string."""
    # Only handle string sources
    if not isinstance(source, str):
        return False

    db_prefixes = (
        "postgres://",
        "postgresql://",
        "mysql://",
        "mysql+pymysql://",
        "sqlite://",
        "snowflake://",
        "bigquery://",
        "redshift://",
        "mssql://",
        "sqlserver://",
        "databricks://",
        "oracle://",
        "mongodb://",
        "mongodb+srv://",
        "kafka://",
    )
    source_lower = source.lower()

    # Check prefixes
    if source_lower.startswith(db_prefixes):
        return True

    # Check for SQLite file extensions
    if source_lower.endswith((".db", ".sqlite", ".sqlite3")):
        return True

    # Check for Redshift hostname
    if "redshift.amazonaws.com" in source_lower:
        return True

    # Check for Databricks hostname
    if ".databricks.com" in source_lower:
        return True

    return False


def _handle_database_connection(
    source: str,
    config: ConnectionConfig,
    engine: DuckGuardEngine | None,
) -> Dataset:
    """Handle database connection strings."""
    # Validate source is a string
    if not isinstance(source, str):
        raise ValueError(f"Expected string source, got {type(source).__name__}")

    source_lower = source.lower()

    # PostgreSQL
    if source_lower.startswith(("postgres://", "postgresql://")):
        try:
            from duckguard.connectors.postgres import PostgresConnector

            connector = PostgresConnector(engine=engine)
            return connector.connect(config)
        except ImportError:
            raise ImportError(
                "PostgreSQL support requires psycopg2. "
                "Install with: pip install duckguard[postgres]"
            )

    # MySQL
    if source_lower.startswith(("mysql://", "mysql+pymysql://")):
        try:
            from duckguard.connectors.mysql import MySQLConnector

            connector = MySQLConnector(engine=engine)
            return connector.connect(config)
        except ImportError:
            raise ImportError(
                "MySQL support requires pymysql. "
                "Install with: pip install duckguard[mysql]"
            )

    # SQLite
    if source_lower.startswith("sqlite://") or source_lower.endswith(
        (".db", ".sqlite", ".sqlite3")
    ):
        from duckguard.connectors.sqlite import SQLiteConnector

        connector = SQLiteConnector(engine=engine)
        return connector.connect(config)

    # Snowflake
    if source_lower.startswith("snowflake://"):
        try:
            from duckguard.connectors.snowflake import SnowflakeConnector

            connector = SnowflakeConnector(engine=engine)
            return connector.connect(config)
        except ImportError:
            raise ImportError(
                "Snowflake support requires snowflake-connector-python. "
                "Install with: pip install duckguard[snowflake]"
            )

    # BigQuery
    if source_lower.startswith("bigquery://"):
        try:
            from duckguard.connectors.bigquery import BigQueryConnector

            connector = BigQueryConnector(engine=engine)
            return connector.connect(config)
        except ImportError:
            raise ImportError(
                "BigQuery support requires google-cloud-bigquery. "
                "Install with: pip install duckguard[bigquery]"
            )

    # Redshift
    if source_lower.startswith("redshift://") or "redshift.amazonaws.com" in source_lower:
        from duckguard.connectors.redshift import RedshiftConnector

        connector = RedshiftConnector(engine=engine)
        return connector.connect(config)

    # SQL Server
    if source_lower.startswith(("mssql://", "sqlserver://", "mssql+pyodbc://")):
        try:
            from duckguard.connectors.sqlserver import SQLServerConnector

            connector = SQLServerConnector(engine=engine)
            return connector.connect(config)
        except ImportError:
            raise ImportError(
                "SQL Server support requires pyodbc or pymssql. "
                "Install with: pip install duckguard[sqlserver]"
            )

    # Databricks
    if source_lower.startswith("databricks://") or ".databricks.com" in source_lower:
        try:
            from duckguard.connectors.databricks import DatabricksConnector

            connector = DatabricksConnector(engine=engine)
            return connector.connect(config)
        except ImportError:
            raise ImportError(
                "Databricks support requires databricks-sql-connector. "
                "Install with: pip install duckguard[databricks]"
            )

    # Oracle
    if source_lower.startswith("oracle://"):
        try:
            from duckguard.connectors.oracle import OracleConnector

            connector = OracleConnector(engine=engine)
            return connector.connect(config)
        except ImportError:
            raise ImportError(
                "Oracle support requires oracledb. "
                "Install with: pip install duckguard[oracle]"
            )

    # MongoDB
    if source_lower.startswith(("mongodb://", "mongodb+srv://")):
        try:
            from duckguard.connectors.mongodb import MongoDBConnector

            connector = MongoDBConnector(engine=engine)
            return connector.connect(config)
        except ImportError:
            raise ImportError(
                "MongoDB support requires pymongo. "
                "Install with: pip install duckguard[mongodb]"
            )

    # Kafka
    if source_lower.startswith("kafka://"):
        try:
            from duckguard.connectors.kafka import KafkaConnector

            connector = KafkaConnector(engine=engine)
            return connector.connect(config)
        except ImportError:
            raise ImportError(
                "Kafka support requires kafka-python. "
                "Install with: pip install duckguard[kafka]"
            )

    # For other databases, raise helpful error
    raise ValueError(
        f"Database connector not yet implemented for: {source}\n"
        f"Currently supported: postgres://, mysql://, sqlite://, snowflake://, "
        f"bigquery://, redshift://, mssql://, databricks://, oracle://, "
        f"mongodb://, kafka://"
    )


# Alias for backwards compatibility
load = connect
