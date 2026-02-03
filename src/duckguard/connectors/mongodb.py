"""MongoDB connector."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from duckguard.connectors.base import ConnectionConfig, Connector
from duckguard.core.dataset import Dataset
from duckguard.core.engine import DuckGuardEngine


class MongoDBConnector(Connector):
    """
    Connector for MongoDB.

    Uses pymongo for connectivity. Converts MongoDB collections to
    a tabular format for validation using DuckDB.

    Examples:
        # Using connection string
        data = connect(
            "mongodb://user:pass@host:27017/database",
            table="orders"  # collection name
        )

        # Using MongoDB Atlas
        data = connect(
            "mongodb+srv://user:pass@cluster.mongodb.net/database",
            table="orders"
        )

        # Using options
        data = connect(
            "mongodb://host:27017",
            table="orders",
            database="mydb",
            sample_size=10000  # Sample for large collections
        )
    """

    def __init__(self, engine: DuckGuardEngine | None = None):
        super().__init__(engine)
        self._client = None
        self._db = None

    def connect(self, config: ConnectionConfig) -> Dataset:
        """
        Connect to MongoDB and return a Dataset.

        Args:
            config: Connection configuration

        Returns:
            Dataset object
        """
        try:
            from pymongo import MongoClient
        except ImportError:
            raise ImportError(
                "MongoDB support requires pymongo. "
                "Install with: pip install duckguard[mongodb]"
            )

        if not config.table:
            raise ValueError(
                "Collection name is required for MongoDB connections (use table parameter)"
            )

        # Parse connection parameters
        conn_params = self._parse_connection_string(config.source, config)

        # Connect to MongoDB
        self._client = MongoClient(conn_params["connection_string"])

        database_name = config.database or conn_params.get("database")
        if not database_name:
            raise ValueError("Database name is required for MongoDB connections")

        self._db = self._client[database_name]
        collection_name = config.table

        # Get sample size from options
        sample_size = (config.options or {}).get("sample_size", 100000)

        return MongoDBDataset(
            source=collection_name,
            engine=self.engine,
            name=collection_name,
            database=self._db,
            collection_name=collection_name,
            sample_size=sample_size,
        )

    def _parse_connection_string(self, conn_string: str, config: ConnectionConfig) -> dict:
        """Parse MongoDB connection string."""
        params: dict[str, Any] = {}

        # Keep the full connection string for pymongo
        params["connection_string"] = conn_string

        # Parse to extract database name if present
        if conn_string.lower().startswith(("mongodb://", "mongodb+srv://")):
            parsed = urlparse(conn_string)
            if parsed.path and parsed.path != "/":
                params["database"] = parsed.path.lstrip("/").split("?")[0]

        # Override with config options
        if config.database:
            params["database"] = config.database

        return params

    @classmethod
    def can_handle(cls, source: str) -> bool:
        """Check if this is a MongoDB connection string."""
        source_lower = source.lower()
        return source_lower.startswith(("mongodb://", "mongodb+srv://"))

    @classmethod
    def get_priority(cls) -> int:
        """MongoDB connector has high priority."""
        return 55


class MongoDBDataset(Dataset):
    """
    Dataset that queries MongoDB.

    Loads data from MongoDB collection into DuckDB for validation.
    """

    def __init__(
        self,
        source: str,
        engine: DuckGuardEngine,
        name: str,
        database: Any,
        collection_name: str,
        sample_size: int = 100000,
    ):
        super().__init__(source=source, engine=engine, name=name)
        self._database = database
        self._collection_name = collection_name
        self._sample_size = sample_size
        self._collection = database[collection_name]
        self._loaded = False
        self._view_name = f"_duckguard_mongo_{collection_name}"

    def _ensure_loaded(self) -> None:
        """Load MongoDB data into DuckDB if not already loaded."""
        if self._loaded:
            return

        try:
            import pandas as pd
        except ImportError:
            raise ImportError(
                "MongoDB connector requires pandas for data loading. "
                "Install with: pip install pandas"
            )

        # Get documents from MongoDB
        cursor = self._collection.find().limit(self._sample_size)
        documents = list(cursor)

        if not documents:
            # Create empty dataframe with no columns
            df = pd.DataFrame()
        else:
            # Flatten nested documents and convert to DataFrame
            df = pd.json_normalize(documents)

            # Convert ObjectId to string
            if "_id" in df.columns:
                df["_id"] = df["_id"].astype(str)

        # Register with DuckDB
        self._engine.conn.register(self._view_name, df)
        self._source = self._view_name
        self._loaded = True

    @property
    def row_count(self) -> int:
        """Get row count."""
        if self._row_count_cache is None:
            # Use MongoDB count for accuracy
            self._row_count_cache = self._collection.count_documents({})
        return self._row_count_cache

    @property
    def columns(self) -> list[str]:
        """Get column names (field names from documents)."""
        if self._columns_cache is None:
            self._ensure_loaded()
            self._columns_cache = self._engine.get_columns(self._view_name)
        return self._columns_cache

    @property
    def sample_row_count(self) -> int:
        """Get the number of rows in the sample (may be less than total)."""
        self._ensure_loaded()
        return self._engine.get_row_count(self._view_name)


class MongoDBColumn:
    """Column for MongoDB datasets with document-aware validation."""

    def __init__(self, name: str, dataset: MongoDBDataset):
        self._name = name
        self._dataset = dataset

    @property
    def null_percent(self) -> float:
        """Get null/missing percentage."""
        self._dataset._ensure_loaded()
        stats = self._dataset._engine.get_column_stats(
            self._dataset._view_name, self._name
        )
        return stats.get("null_percent", 0.0)

    @property
    def field_exists_percent(self) -> float:
        """
        Get percentage of documents that have this field.

        This is MongoDB-specific - checks for field existence.
        """
        total = self._dataset._collection.count_documents({})
        if total == 0:
            return 100.0

        with_field = self._dataset._collection.count_documents(
            {self._name: {"$exists": True}}
        )
        return (with_field / total) * 100
