"""Tests for connectors."""

import os
import tempfile

import pytest

from duckguard import connect
from duckguard.connectors.factory import _is_database_connection
from duckguard.connectors.files import FileConnector


class TestFileConnector:
    """Tests for file connector."""

    def test_can_handle_csv(self):
        """Test CSV file detection."""
        assert FileConnector.can_handle("data.csv")
        assert FileConnector.can_handle("path/to/data.csv")
        assert FileConnector.can_handle("C:\\path\\data.csv")

    def test_can_handle_parquet(self):
        """Test Parquet file detection."""
        assert FileConnector.can_handle("data.parquet")
        assert FileConnector.can_handle("data.pq")

    def test_can_handle_json(self):
        """Test JSON file detection."""
        assert FileConnector.can_handle("data.json")
        assert FileConnector.can_handle("data.jsonl")
        assert FileConnector.can_handle("data.ndjson")

    def test_can_handle_s3(self):
        """Test S3 path detection."""
        assert FileConnector.can_handle("s3://bucket/data.parquet")
        assert FileConnector.can_handle("s3://bucket/path/data.csv")

    def test_cannot_handle_unknown(self):
        """Test unknown file types."""
        assert not FileConnector.can_handle("data.xyz")
        assert not FileConnector.can_handle("data.txt")


class TestConnect:
    """Tests for connect() function."""

    def test_connect_csv(self, orders_csv):
        """Test connecting to CSV file."""
        dataset = connect(orders_csv)
        assert dataset is not None
        assert dataset.row_count == 30

    def test_connect_nonexistent_file(self):
        """Test connecting to non-existent file raises error."""
        with pytest.raises(FileNotFoundError):
            connect("nonexistent.csv")

    def test_connect_unsupported_format(self):
        """Test connecting to unsupported format raises error."""
        # Create a temp file with unsupported extension
        with tempfile.NamedTemporaryFile(suffix=".xyz", delete=False) as f:
            f.write(b"data")
            temp_path = f.name

        try:
            with pytest.raises(ValueError, match="No connector found"):
                connect(temp_path)
        finally:
            os.unlink(temp_path)


class TestDatabaseConnectionDetection:
    """Tests for database connection string detection."""

    def test_postgres_detection(self):
        """Test PostgreSQL connection string detection."""
        assert _is_database_connection("postgres://localhost/db")
        assert _is_database_connection("postgresql://localhost/db")
        assert _is_database_connection("postgres://user:pass@host:5432/db")

    def test_mysql_detection(self):
        """Test MySQL connection string detection."""
        assert _is_database_connection("mysql://localhost/db")
        assert _is_database_connection("mysql+pymysql://localhost/db")

    def test_snowflake_detection(self):
        """Test Snowflake connection string detection."""
        assert _is_database_connection("snowflake://account/db")

    def test_file_not_database(self):
        """Test that file paths are not detected as databases."""
        assert not _is_database_connection("data.csv")
        assert not _is_database_connection("s3://bucket/data.parquet")
