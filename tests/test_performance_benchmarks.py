"""
Performance benchmarks for DuckGuard 3.0 new features.

This test suite validates performance with large datasets:
- 1M+ row datasets
- Complex queries and expressions
- Memory usage validation
- Execution time benchmarks

Target: All operations complete within acceptable time limits
"""

import gc
import os
import tempfile
import time

import numpy as np
import pandas as pd
import pytest

from duckguard import connect

# Skip slow tests by default
pytestmark = pytest.mark.slow


# =============================================================================
# PERFORMANCE TEST DATA GENERATORS
# =============================================================================


def generate_large_dataset(rows: int = 1_000_000) -> str:
    """Generate large dataset for performance testing."""
    np.random.seed(42)

    # Generate in chunks to avoid memory issues
    chunk_size = 100_000
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False)

    # Write header
    temp_file.write("id,value,category,amount,date,status\n")

    for chunk_start in range(0, rows, chunk_size):
        chunk_end = min(chunk_start + chunk_size, rows)
        chunk_rows = chunk_end - chunk_start

        ids = range(chunk_start, chunk_end)
        values = np.random.uniform(0, 1000, size=chunk_rows)
        categories = np.random.choice(['A', 'B', 'C', 'D', 'E'], size=chunk_rows)
        amounts = np.random.uniform(10, 10000, size=chunk_rows)
        dates = pd.date_range('2024-01-01', periods=chunk_rows, freq='s')
        statuses = np.random.choice(['active', 'inactive', 'pending'], size=chunk_rows)

        # Write chunk
        for i in range(chunk_rows):
            temp_file.write(
                f"{ids[i]},{values[i]:.2f},{categories[i]},"
                f"{amounts[i]:.2f},{dates[i].isoformat()},{statuses[i]}\n"
            )

    temp_file.close()
    return temp_file.name


# =============================================================================
# CONDITIONAL CHECKS PERFORMANCE
# =============================================================================


class TestConditionalPerformance:
    """Performance tests for conditional checks."""

    @pytest.fixture(scope='class')
    def large_dataset(self):
        """Generate 1M row dataset once for all tests."""
        filepath = generate_large_dataset(1_000_000)
        yield filepath
        # Clean up with garbage collection to release file handles (Windows)
        gc.collect()
        try:
            os.unlink(filepath)
        except (PermissionError, FileNotFoundError):
            pass  # Ignore cleanup errors on Windows

    def test_not_null_when_1m_rows(self, large_dataset):
        """Test not_null_when performance with 1M rows."""
        data = connect(large_dataset)

        start = time.time()
        result = data.value.not_null_when("category = 'A'")
        elapsed = time.time() - start

        assert isinstance(result.passed, bool)
        assert elapsed < 3.0  # Target: < 3 seconds
        print(f"\nnot_null_when (1M rows): {elapsed:.2f}s")

    def test_between_when_1m_rows(self, large_dataset):
        """Test between_when performance with 1M rows."""
        data = connect(large_dataset)

        start = time.time()
        result = data.amount.between_when(
            min_val=0,
            max_val=5000,
            condition="status = 'active'"
        )
        elapsed = time.time() - start

        assert isinstance(result.passed, bool)
        assert elapsed < 3.0
        print(f"between_when (1M rows): {elapsed:.2f}s")

    def test_multiple_conditional_checks(self, large_dataset):
        """Test multiple conditional checks in sequence."""
        data = connect(large_dataset)

        start = time.time()

        checks = [
            data.value.not_null_when("category = 'A'"),
            data.value.not_null_when("category = 'B'"),
            data.amount.between_when(0, 5000, "status = 'active'"),
            data.amount.between_when(0, 8000, "status = 'inactive'"),
        ]

        elapsed = time.time() - start

        assert all(isinstance(c.passed, bool) for c in checks)
        assert elapsed < 10.0  # 4 checks in < 10 seconds
        print(f"4 conditional checks (1M rows): {elapsed:.2f}s")


# =============================================================================
# MULTI-COLUMN CHECKS PERFORMANCE
# =============================================================================


class TestMultiColumnPerformance:
    """Performance tests for multi-column checks."""

    @pytest.fixture(scope='class')
    def large_dataset_multicolumn(self):
        """Generate dataset with multiple related columns."""
        np.random.seed(42)
        rows = 1_000_000

        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False)

        # Write header
        temp_file.write("id,col_a,col_b,col_c,total\n")

        chunk_size = 100_000
        for chunk_start in range(0, rows, chunk_size):
            chunk_end = min(chunk_start + chunk_size, rows)
            chunk_rows = chunk_end - chunk_start

            ids = range(chunk_start, chunk_end)
            col_a = np.random.uniform(10, 100, size=chunk_rows)
            col_b = np.random.uniform(5, 50, size=chunk_rows)
            col_c = np.random.uniform(1, 10, size=chunk_rows)
            total = col_a + col_b + col_c

            for i in range(chunk_rows):
                temp_file.write(
                    f"{ids[i]},{col_a[i]:.2f},{col_b[i]:.2f},"
                    f"{col_c[i]:.2f},{total[i]:.2f}\n"
                )

        temp_file.close()
        yield temp_file.name
        # Clean up with garbage collection to release file handles (Windows)
        gc.collect()
        try:
            os.unlink(temp_file.name)
        except (PermissionError, FileNotFoundError):
            pass  # Ignore cleanup errors on Windows

    def test_column_pair_satisfy_1m_rows(self, large_dataset_multicolumn):
        """Test column_pair_satisfy performance with 1M rows."""
        data = connect(large_dataset_multicolumn)

        start = time.time()
        result = data.expect_column_pair_satisfy(
            column_a="total",
            column_b="col_a",
            expression="total >= col_a",
            threshold=1.0
        )
        elapsed = time.time() - start

        assert isinstance(result.passed, bool)
        assert elapsed < 5.0  # Target: < 5 seconds
        print(f"\ncolumn_pair_satisfy (1M rows): {elapsed:.2f}s")

    def test_multicolumn_unique_1m_rows(self, large_dataset_multicolumn):
        """Test multicolumn uniqueness with 1M rows."""
        data = connect(large_dataset_multicolumn)

        start = time.time()
        result = data.expect_columns_unique(
            columns=["col_a", "col_b"],
            threshold=0.9  # Allow some duplicates
        )
        elapsed = time.time() - start

        assert isinstance(result.passed, bool)
        assert elapsed < 8.0  # Target: < 8 seconds
        print(f"multicolumn_unique (1M rows): {elapsed:.2f}s")


# =============================================================================
# QUERY-BASED CHECKS PERFORMANCE
# =============================================================================


class TestQueryBasedPerformance:
    """Performance tests for query-based checks."""

    @pytest.fixture(scope='class')
    def large_dataset(self):
        """Generate 1M row dataset."""
        filepath = generate_large_dataset(1_000_000)
        yield filepath
        # Clean up with garbage collection to release file handles (Windows)
        gc.collect()
        try:
            os.unlink(filepath)
        except (PermissionError, FileNotFoundError):
            pass  # Ignore cleanup errors on Windows

    def test_query_no_rows_1m_rows(self, large_dataset):
        """Test query_no_rows performance with 1M rows."""
        data = connect(large_dataset)

        start = time.time()
        result = data.expect_query_to_return_no_rows(
            query="SELECT * FROM table WHERE value < 0"
        )
        elapsed = time.time() - start

        assert isinstance(result.passed, bool)
        assert elapsed < 3.0  # Target: < 3 seconds
        print(f"\nquery_no_rows (1M rows): {elapsed:.2f}s")

    def test_query_aggregate_1m_rows(self, large_dataset):
        """Test aggregate query performance with 1M rows."""
        data = connect(large_dataset)

        start = time.time()
        result = data.expect_query_result_to_be_between(
            query="SELECT AVG(amount) FROM table",
            min_value=0,
            max_value=20000
        )
        elapsed = time.time() - start

        assert isinstance(result.passed, bool)
        assert elapsed < 5.0  # Target: < 5 seconds
        print(f"query_aggregate (1M rows): {elapsed:.2f}s")

    def test_complex_query_1m_rows(self, large_dataset):
        """Test complex query with GROUP BY on 1M rows."""
        data = connect(large_dataset)

        start = time.time()
        result = data.expect_query_to_return_rows(
            query="""
                SELECT category, COUNT(*) as cnt
                FROM table
                GROUP BY category
                HAVING COUNT(*) > 100000
            """
        )
        elapsed = time.time() - start

        assert isinstance(result.passed, bool)
        assert elapsed < 8.0  # Target: < 8 seconds
        print(f"complex_query with GROUP BY (1M rows): {elapsed:.2f}s")


# =============================================================================
# DISTRIBUTIONAL CHECKS PERFORMANCE
# =============================================================================


try:
    import scipy.stats

    class TestDistributionalPerformance:
        """Performance tests for distributional checks."""

        @pytest.fixture(scope='class')
        def normal_data_large(self):
            """Generate large normally distributed dataset."""
            np.random.seed(42)
            values = np.random.normal(100, 15, size=1_000_000)

            df = pd.DataFrame({'values': values})
            temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False)
            df.to_csv(temp_file.name, index=False)
            temp_file.close()

            yield temp_file.name
            # Clean up with garbage collection to release file handles (Windows)
            gc.collect()
            try:
                os.unlink(temp_file.name)
            except (PermissionError, FileNotFoundError):
                pass  # Ignore cleanup errors on Windows

        def test_distribution_normal_1m_rows(self, normal_data_large):
            """Test normality test performance with 1M rows."""
            data = connect(normal_data_large)

            start = time.time()
            result = data.values.expect_distribution_normal()
            elapsed = time.time() - start

            assert isinstance(result.passed, bool)
            assert elapsed < 10.0  # Target: < 10 seconds
            print(f"\ndistribution_normal (1M rows): {elapsed:.2f}s")

        def test_ks_test_1m_rows(self, normal_data_large):
            """Test KS test performance with 1M rows."""
            data = connect(normal_data_large)

            start = time.time()
            result = data.values.expect_ks_test(distribution='norm')
            elapsed = time.time() - start

            assert isinstance(result.passed, bool)
            assert elapsed < 10.0
            print(f"ks_test (1M rows): {elapsed:.2f}s")

except ImportError:
    pass


# =============================================================================
# MEMORY USAGE TESTS
# =============================================================================


class TestMemoryUsage:
    """Tests for memory usage with large datasets."""

    def test_memory_efficient_processing(self):
        """Test that large dataset processing doesn't cause memory issues."""
        import gc

        import psutil

        # Get initial memory
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Generate and process dataset
        filepath = generate_large_dataset(500_000)  # 500K rows
        try:
            data = connect(filepath)

            # Run multiple checks
            _ = [
                data.value.not_null_when("category = 'A'"),
                data.expect_column_pair_satisfy(
                    column_a="amount",
                    column_b="value",
                    expression="amount > value",
                    threshold=0.8
                ),
                data.expect_query_result_to_equal(
                    query="SELECT COUNT(*) FROM table",
                    expected=500_000
                ),
            ]

            # Get peak memory
            peak_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_increase = peak_memory - initial_memory

            # Should not exceed reasonable memory increase
            assert memory_increase < 1000  # < 1GB increase
            print(f"\nMemory increase (500K rows): {memory_increase:.0f} MB")

        finally:
            # Clean up with garbage collection to release file handles (Windows)
            gc.collect()
            try:
                os.unlink(filepath)
            except (PermissionError, FileNotFoundError):
                pass  # Ignore cleanup errors on Windows


# =============================================================================
# SCALABILITY TESTS
# =============================================================================


class TestScalability:
    """Tests for scalability with increasing data sizes."""

    def test_linear_scalability(self):
        """Test that execution time scales linearly with data size."""
        sizes = [10_000, 50_000, 100_000]
        times = []

        for size in sizes:
            filepath = generate_large_dataset(size)
            try:
                data = connect(filepath)

                start = time.time()
                _ = data.value.not_null_when("category = 'A'")
                elapsed = time.time() - start

                times.append(elapsed)
                print(f"\n{size:,} rows: {elapsed:.3f}s")

            finally:
                # Clean up with garbage collection to release file handles (Windows)
                gc.collect()
                try:
                    os.unlink(filepath)
                except (PermissionError, FileNotFoundError):
                    pass  # Ignore cleanup errors on Windows

        # Check that time doesn't grow super-linearly
        # time[100K] should be ~10x time[10K], not 100x
        ratio = times[2] / times[0]
        assert ratio < 15  # Allow some overhead, but not quadratic growth


# =============================================================================
# BENCHMARK SUMMARY
# =============================================================================


class TestBenchmarkSummary:
    """Summary test showing all performance benchmarks."""

    def test_performance_summary(self):
        """Generate performance summary report."""
        print("\n" + "="*70)
        print("DuckGuard 3.0 Performance Benchmark Summary")
        print("="*70)

        # Generate small test dataset
        filepath = generate_large_dataset(100_000)
        try:
            data = connect(filepath)

            benchmarks = []

            # Conditional check
            start = time.time()
            data.value.not_null_when("category = 'A'")
            benchmarks.append(("Conditional Check", time.time() - start))

            # Multi-column check
            start = time.time()
            data.expect_column_pair_satisfy(
                column_a="amount",
                column_b="value",
                expression="amount >= value",
                threshold=1.0
            )
            benchmarks.append(("Multi-Column Check", time.time() - start))

            # Query-based check
            start = time.time()
            data.expect_query_to_return_no_rows(
                query="SELECT * FROM table WHERE value < 0"
            )
            benchmarks.append(("Query-Based Check", time.time() - start))

            # Regular check for comparison
            start = time.time()
            data.id.is_unique()
            benchmarks.append(("Regular Check (baseline)", time.time() - start))

            print("\nResults (100K rows):")
            print("-" * 70)
            for name, elapsed in benchmarks:
                print(f"{name:.<50} {elapsed:.3f}s")

            print("-" * 70)
            print(f"{'Total':.50} {sum(t for _, t in benchmarks):.3f}s")
            print("="*70)

        finally:
            # Clean up with garbage collection to release file handles (Windows)
            gc.collect()
            try:
                os.unlink(filepath)
            except (PermissionError, FileNotFoundError):
                pass  # Ignore cleanup errors on Windows
