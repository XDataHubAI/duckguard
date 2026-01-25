"""Pytest configuration and fixtures for DuckGuard tests."""

import os
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def sample_data_dir():
    """Get the sample data directory path."""
    return Path(__file__).parent.parent / "examples" / "sample_data"


@pytest.fixture
def orders_csv(sample_data_dir):
    """Get path to orders.csv sample file."""
    return str(sample_data_dir / "orders.csv")


@pytest.fixture
def temp_csv():
    """Create a temporary CSV file for testing."""
    content = """id,name,email,amount,status
1,Alice,alice@example.com,100.50,active
2,Bob,bob@example.com,200.75,active
3,Charlie,charlie@example.com,50.25,inactive
4,Diana,diana@example.com,300.00,active
5,Eve,,150.00,pending
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write(content)
        temp_path = f.name

    yield temp_path

    # Cleanup
    os.unlink(temp_path)


@pytest.fixture
def temp_parquet(temp_csv):
    """Create a temporary Parquet file for testing."""
    try:
        import duckdb

        temp_path = temp_csv.replace(".csv", ".parquet")
        conn = duckdb.connect(":memory:")
        conn.execute(f"COPY (SELECT * FROM read_csv('{temp_csv}')) TO '{temp_path}' (FORMAT PARQUET)")
        conn.close()

        yield temp_path

        os.unlink(temp_path)
    except Exception:
        pytest.skip("Could not create parquet file")


@pytest.fixture
def orders_dataset():
    """Get a connected orders dataset."""
    from duckguard import connect

    sample_dir = Path(__file__).parent.parent / "examples" / "sample_data"
    return connect(str(sample_dir / "orders.csv"))


@pytest.fixture
def engine():
    """Create a DuckGuard engine for testing."""
    from duckguard.core.engine import DuckGuardEngine

    eng = DuckGuardEngine()
    yield eng
    eng.close()


@pytest.fixture
def temp_csv_with_nulls():
    """Create a temporary CSV file with null values for testing."""
    # Note: Using 'user_name' instead of 'name' because 'name' is a reserved
    # attribute in Dataset class that returns the dataset name
    content = """id,user_name,email,amount
1,Alice,alice@example.com,100.50
2,Bob,bob@example.com,200.75
3,Charlie,charlie@example.com,50.25
4,,diana@example.com,300.00
5,Eve,eve@example.com,150.00
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write(content)
        temp_path = f.name

    yield temp_path

    # Cleanup - ignore errors on Windows due to file locking
    import gc
    gc.collect()  # Force garbage collection to release file handles
    try:
        os.unlink(temp_path)
    except PermissionError:
        pass  # On Windows, the file may still be locked by DuckDB
