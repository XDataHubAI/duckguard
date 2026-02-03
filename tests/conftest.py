"""Pytest configuration and fixtures for DuckGuard tests."""

import gc
import os
import tempfile
from pathlib import Path

import pytest

from duckguard.core.engine import DuckGuardEngine

# ============================================================================
# Engine Reset Fixture
# ============================================================================


@pytest.fixture(autouse=True)
def reset_engine():
    """Reset engine singleton before each test."""
    DuckGuardEngine.reset_instance()
    yield
    DuckGuardEngine.reset_instance()
    gc.collect()


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
    gc.collect()  # Force garbage collection to release file handles
    try:
        os.unlink(temp_path)
    except PermissionError:
        pass  # On Windows, the file may still be locked by DuckDB


# ============================================================================
# Distribution Drift Fixtures
# ============================================================================


@pytest.fixture
def baseline_data_csv():
    """Create baseline data for drift detection."""
    content = """id,amount,score
1,100.0,0.5
2,150.0,0.6
3,120.0,0.55
4,180.0,0.7
5,130.0,0.58
6,140.0,0.62
7,160.0,0.65
8,110.0,0.52
9,170.0,0.68
10,125.0,0.56
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write(content)
        temp_path = f.name

    yield temp_path

    gc.collect()
    try:
        os.unlink(temp_path)
    except PermissionError:
        pass


@pytest.fixture
def drifted_data_csv():
    """Create data with significant drift from baseline."""
    content = """id,amount,score
1,1000.0,0.9
2,1500.0,0.95
3,1200.0,0.88
4,1800.0,0.99
5,1300.0,0.92
6,1400.0,0.94
7,1600.0,0.96
8,1100.0,0.87
9,1700.0,0.98
10,1250.0,0.91
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write(content)
        temp_path = f.name

    yield temp_path

    gc.collect()
    try:
        os.unlink(temp_path)
    except PermissionError:
        pass


@pytest.fixture
def similar_data_csv():
    """Create data similar to baseline (no drift)."""
    content = """id,amount,score
1,105.0,0.51
2,145.0,0.59
3,125.0,0.56
4,175.0,0.69
5,135.0,0.59
6,138.0,0.61
7,158.0,0.64
8,115.0,0.53
9,168.0,0.67
10,122.0,0.55
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write(content)
        temp_path = f.name

    yield temp_path

    gc.collect()
    try:
        os.unlink(temp_path)
    except PermissionError:
        pass


# ============================================================================
# Reconciliation Fixtures
# ============================================================================


@pytest.fixture
def source_orders_csv():
    """Create source orders for reconciliation."""
    content = """order_id,customer_id,amount,status
ORD-001,CUST-001,100.00,shipped
ORD-002,CUST-002,200.00,pending
ORD-003,CUST-001,150.00,shipped
ORD-004,CUST-003,50.00,delivered
ORD-005,CUST-002,300.00,pending
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write(content)
        temp_path = f.name

    yield temp_path

    gc.collect()
    try:
        os.unlink(temp_path)
    except PermissionError:
        pass


@pytest.fixture
def target_orders_matching_csv():
    """Create target orders that match source exactly."""
    content = """order_id,customer_id,amount,status
ORD-001,CUST-001,100.00,shipped
ORD-002,CUST-002,200.00,pending
ORD-003,CUST-001,150.00,shipped
ORD-004,CUST-003,50.00,delivered
ORD-005,CUST-002,300.00,pending
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write(content)
        temp_path = f.name

    yield temp_path

    gc.collect()
    try:
        os.unlink(temp_path)
    except PermissionError:
        pass


@pytest.fixture
def target_orders_mismatched_csv():
    """Create target orders with mismatches."""
    content = """order_id,customer_id,amount,status
ORD-001,CUST-001,100.00,shipped
ORD-002,CUST-002,205.00,pending
ORD-003,CUST-001,150.00,shipped
ORD-006,CUST-003,75.00,delivered
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write(content)
        temp_path = f.name

    yield temp_path

    gc.collect()
    try:
        os.unlink(temp_path)
    except PermissionError:
        pass


# ============================================================================
# Group By Fixtures
# ============================================================================


@pytest.fixture
def grouped_orders_csv():
    """Create orders with multiple groups for group by tests."""
    content = """order_id,customer_id,amount,status,region,date
ORD-001,CUST-001,100.00,shipped,US,2024-01-01
ORD-002,CUST-002,200.00,pending,US,2024-01-01
ORD-003,CUST-001,150.00,shipped,EU,2024-01-02
ORD-004,CUST-003,50.00,delivered,EU,2024-01-02
ORD-005,CUST-002,300.00,pending,US,2024-01-03
ORD-006,CUST-001,75.00,shipped,EU,2024-01-03
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write(content)
        temp_path = f.name

    yield temp_path

    gc.collect()
    try:
        os.unlink(temp_path)
    except PermissionError:
        pass
