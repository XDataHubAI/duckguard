"""Connectors for various data sources."""

from duckguard.connectors.base import ConnectionConfig, Connector
from duckguard.connectors.factory import connect, register_connector
from duckguard.connectors.files import AzureConnector, FileConnector, GCSConnector, S3Connector

# Database connectors (imported lazily to avoid import errors)
__all__ = [
    # Base classes
    "Connector",
    "ConnectionConfig",
    # File connectors
    "FileConnector",
    "S3Connector",
    "GCSConnector",
    "AzureConnector",
    # Factory functions
    "connect",
    "register_connector",
]


def __getattr__(name: str):
    """Lazy import database connectors to avoid import errors."""
    if name == "PostgresConnector":
        from duckguard.connectors.postgres import PostgresConnector
        return PostgresConnector
    if name == "MySQLConnector":
        from duckguard.connectors.mysql import MySQLConnector
        return MySQLConnector
    if name == "SQLiteConnector":
        from duckguard.connectors.sqlite import SQLiteConnector
        return SQLiteConnector
    if name == "SnowflakeConnector":
        from duckguard.connectors.snowflake import SnowflakeConnector
        return SnowflakeConnector
    if name == "BigQueryConnector":
        from duckguard.connectors.bigquery import BigQueryConnector
        return BigQueryConnector
    if name == "RedshiftConnector":
        from duckguard.connectors.redshift import RedshiftConnector
        return RedshiftConnector
    if name == "SQLServerConnector":
        from duckguard.connectors.sqlserver import SQLServerConnector
        return SQLServerConnector
    if name == "DatabricksConnector":
        from duckguard.connectors.databricks import DatabricksConnector
        return DatabricksConnector
    if name == "OracleConnector":
        from duckguard.connectors.oracle import OracleConnector
        return OracleConnector
    if name == "MongoDBConnector":
        from duckguard.connectors.mongodb import MongoDBConnector
        return MongoDBConnector
    if name == "KafkaConnector":
        from duckguard.connectors.kafka import KafkaConnector
        return KafkaConnector
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
