"""File-based connectors (CSV, Parquet, JSON, Excel)."""

from __future__ import annotations

import os
from pathlib import Path

from duckguard.connectors.base import ConnectionConfig, Connector
from duckguard.core.dataset import Dataset
from duckguard.core.engine import DuckGuardEngine


class FileConnector(Connector):
    """
    Connector for file-based data sources.

    Supports:
    - CSV files (.csv)
    - Parquet files (.parquet, .pq)
    - JSON files (.json, .jsonl, .ndjson)
    - Excel files (.xlsx, .xls) - requires additional setup
    """

    SUPPORTED_EXTENSIONS = {
        ".csv": "csv",
        ".parquet": "parquet",
        ".pq": "parquet",
        ".json": "json",
        ".jsonl": "json",
        ".ndjson": "json",
        ".xlsx": "excel",
        ".xls": "excel",
    }

    def __init__(self, engine: DuckGuardEngine | None = None):
        super().__init__(engine)

    def connect(self, config: ConnectionConfig) -> Dataset:
        """
        Connect to a file and return a Dataset.

        Args:
            config: Connection configuration with file path

        Returns:
            Dataset object
        """
        path = config.source
        ext = Path(path).suffix.lower()

        # Determine file type
        file_type = self.SUPPORTED_EXTENSIONS.get(ext)
        if not file_type:
            raise ValueError(f"Unsupported file type: {ext}")

        # Validate file exists (for local files)
        if not self._is_remote_path(path) and not os.path.exists(path):
            raise FileNotFoundError(f"File not found: {path}")

        # Create dataset name from filename
        name = Path(path).stem

        return Dataset(source=path, engine=self.engine, name=name)

    @classmethod
    def can_handle(cls, source: str) -> bool:
        """Check if this connector can handle the source."""
        # Only handle string paths
        if not isinstance(source, str):
            return False

        # Check for file extensions
        path = Path(source)
        ext = path.suffix.lower()

        if ext in cls.SUPPORTED_EXTENSIONS:
            return True

        # Check for S3/GCS/Azure paths with supported extensions
        if cls._is_remote_path(source):
            # Extract extension from remote path
            for supported_ext in cls.SUPPORTED_EXTENSIONS:
                if source.lower().endswith(supported_ext):
                    return True

        return False

    @staticmethod
    def _is_remote_path(path: str) -> bool:
        """Check if path is a remote storage path."""
        remote_prefixes = ("s3://", "gs://", "gcs://", "az://", "abfs://", "http://", "https://")
        return path.lower().startswith(remote_prefixes)

    @classmethod
    def get_priority(cls) -> int:
        """File connector has default priority."""
        return 10


class S3Connector(FileConnector):
    """Connector for S3 paths."""

    @classmethod
    def can_handle(cls, source: str) -> bool:
        """Check if this is an S3 path."""
        return isinstance(source, str) and source.lower().startswith("s3://")

    @classmethod
    def get_priority(cls) -> int:
        """S3 connector has higher priority."""
        return 20


class GCSConnector(FileConnector):
    """Connector for Google Cloud Storage paths."""

    @classmethod
    def can_handle(cls, source: str) -> bool:
        """Check if this is a GCS path."""
        return isinstance(source, str) and source.lower().startswith(("gs://", "gcs://"))

    @classmethod
    def get_priority(cls) -> int:
        """GCS connector has higher priority."""
        return 20


class AzureConnector(FileConnector):
    """Connector for Azure Blob Storage paths."""

    @classmethod
    def can_handle(cls, source: str) -> bool:
        """Check if this is an Azure path."""
        return isinstance(source, str) and source.lower().startswith(("az://", "abfs://"))

    @classmethod
    def get_priority(cls) -> int:
        """Azure connector has higher priority."""
        return 20
