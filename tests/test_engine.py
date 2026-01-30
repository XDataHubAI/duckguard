"""Tests for the DuckGuard engine."""

from duckguard.core.engine import DuckGuardEngine


class TestDuckGuardEngine:
    """Tests for DuckGuardEngine class."""

    def test_engine_creation(self):
        """Test basic engine creation."""
        engine = DuckGuardEngine()
        assert engine is not None
        assert engine.conn is not None
        engine.close()

    def test_execute_simple_query(self, engine):
        """Test executing a simple query."""
        result = engine.fetch_value("SELECT 1 + 1")
        assert result == 2

    def test_fetch_one(self, engine):
        """Test fetching one row."""
        result = engine.fetch_one("SELECT 1 as a, 2 as b")
        assert result == (1, 2)

    def test_fetch_all(self, engine):
        """Test fetching all rows."""
        result = engine.fetch_all("SELECT * FROM (VALUES (1), (2), (3)) AS t(n)")
        assert len(result) == 3
        assert result[0] == (1,)

    def test_get_columns_from_csv(self, engine, orders_csv):
        """Test getting columns from a CSV file."""
        columns = engine.get_columns(orders_csv)
        assert "order_id" in columns
        assert "customer_id" in columns
        assert "total_amount" in columns

    def test_get_row_count(self, engine, orders_csv):
        """Test getting row count."""
        count = engine.get_row_count(orders_csv)
        assert count == 30

    def test_get_column_stats(self, engine, orders_csv):
        """Test getting column statistics."""
        stats = engine.get_column_stats(orders_csv, "quantity")
        assert stats["total_count"] == 30
        assert stats["null_count"] == 0
        assert stats["min_value"] == -2
        assert stats["max_value"] == 500

    def test_get_numeric_stats(self, engine, orders_csv):
        """Test getting numeric statistics."""
        stats = engine.get_numeric_stats(orders_csv, "quantity")
        assert "mean" in stats
        assert "stddev" in stats
        assert stats["mean"] is not None

    def test_singleton_instance(self):
        """Test singleton pattern."""
        DuckGuardEngine.reset_instance()
        engine1 = DuckGuardEngine.get_instance()
        engine2 = DuckGuardEngine.get_instance()
        assert engine1 is engine2
        DuckGuardEngine.reset_instance()

    def test_context_manager(self):
        """Test using engine as context manager."""
        with DuckGuardEngine() as engine:
            result = engine.fetch_value("SELECT 42")
            assert result == 42
