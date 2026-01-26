"""Tests for ML-based anomaly detection methods."""

import tempfile
from pathlib import Path

import pytest

from duckguard.anomaly.baselines import (
    BaselineStorage,
    ColumnBaseline,
)
from duckguard.anomaly.ml_methods import (
    BaselineMethod,
    KSTestMethod,
    SeasonalMethod,
)


class TestBaselineMethod:
    """Tests for BaselineMethod class."""

    def test_init_default(self):
        """Test default initialization."""
        method = BaselineMethod()
        assert method.name == "baseline"
        assert method.sensitivity == 2.0
        assert method.min_samples == 5

    def test_init_custom(self):
        """Test custom initialization."""
        method = BaselineMethod(sensitivity=3.0, min_samples=10)
        assert method.sensitivity == 3.0
        assert method.min_samples == 10

    def test_fit(self):
        """Test fitting to data."""
        method = BaselineMethod()
        values = [100, 102, 98, 105, 97, 103, 101, 99]
        method.fit(values)

        assert method._fitted is True
        assert abs(method._mean - 100.625) < 0.01
        assert method._min == 97
        assert method._max == 105
        assert method._sample_count == 8

    def test_fit_with_nulls(self):
        """Test fitting with null values."""
        method = BaselineMethod()
        values = [100, None, 102, float('nan'), 98, 105]
        method.fit(values)

        assert method._fitted is True
        assert method._sample_count == 4

    def test_score_normal_value(self):
        """Test scoring a normal value."""
        method = BaselineMethod(sensitivity=2.0)
        method.fit([100, 102, 98, 105, 97, 103, 101, 99])

        score = method.score(101)
        assert score.is_anomaly is False
        assert score.value == 101

    def test_score_anomalous_value(self):
        """Test scoring an anomalous value."""
        method = BaselineMethod(sensitivity=2.0)
        method.fit([100, 102, 98, 105, 97, 103, 101, 99])

        # Value far from mean should be anomalous
        score = method.score(200)
        assert score.is_anomaly is True
        assert score.score > 2.0

    def test_score_null_value(self):
        """Test scoring null values."""
        method = BaselineMethod()
        method.fit([100, 102, 98, 105])

        score = method.score(None)
        assert score.is_anomaly is False
        assert score.details.get("reason") == "null_or_nan"

    def test_score_insufficient_samples(self):
        """Test scoring with insufficient samples."""
        method = BaselineMethod(min_samples=10)
        method.fit([100, 102, 98])  # Only 3 samples

        score = method.score(200)
        assert score.is_anomaly is False
        assert score.details.get("reason") == "insufficient_samples"

    def test_compare_to_baseline_mean(self):
        """Test comparing to baseline mean."""
        method = BaselineMethod()
        method.fit([100, 102, 98, 105, 97, 103])

        new_values = [110, 112, 108, 115]  # Higher mean
        comparison = method.compare_to_baseline(new_values, metric="mean")

        assert comparison.metric == "mean"
        assert comparison.baseline_value < comparison.current_value

    def test_detect(self):
        """Test detecting anomalies in a list."""
        method = BaselineMethod(sensitivity=2.0)
        method.fit([100, 102, 98, 105, 97, 103, 101, 99])

        values = [100, 101, 200, 102, 50]  # 200 and 50 are anomalies
        scores = method.detect(values)

        assert len(scores) == 5
        anomalies = [s for s in scores if s.is_anomaly]
        assert len(anomalies) >= 1  # At least one anomaly


class TestKSTestMethod:
    """Tests for KSTestMethod class."""

    def test_init_default(self):
        """Test default initialization."""
        method = KSTestMethod()
        assert method.name == "ks_test"
        assert method.p_value_threshold == 0.05

    def test_init_custom(self):
        """Test custom initialization."""
        method = KSTestMethod(p_value_threshold=0.01)
        assert method.p_value_threshold == 0.01

    def test_fit(self):
        """Test fitting to baseline data."""
        method = KSTestMethod()
        values = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        method.fit(values)

        assert method._fitted is True
        assert len(method._baseline_values) == 10
        assert len(method._baseline_ecdf) == 10

    def test_compare_distributions_same(self):
        """Test comparing same distributions."""
        method = KSTestMethod()
        baseline = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        method.fit(baseline)

        # Same distribution should not drift
        comparison = method.compare_distributions(baseline)
        assert comparison.method == "ks_test"
        assert comparison.is_drifted is False
        assert comparison.p_value > 0.05

    def test_compare_distributions_different(self):
        """Test comparing different distributions."""
        method = KSTestMethod()
        baseline = [1, 2, 3, 4, 5]
        method.fit(baseline)

        # Very different distribution should drift
        current = [100, 200, 300, 400, 500]
        comparison = method.compare_distributions(current)
        assert comparison.is_drifted is True
        assert comparison.statistic > 0.5

    def test_score_single_value(self):
        """Test scoring single values."""
        method = KSTestMethod()
        method.fit([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])

        # Value in range
        score = method.score(5)
        assert score.is_anomaly is False

        # Extreme value
        score = method.score(100)
        assert score.is_anomaly is True


class TestSeasonalMethod:
    """Tests for SeasonalMethod class."""

    def test_init_default(self):
        """Test default initialization."""
        method = SeasonalMethod()
        assert method.period == "daily"
        assert method.sensitivity == 2.0
        assert method._num_buckets == 7  # Days of week

    def test_init_hourly(self):
        """Test hourly period."""
        method = SeasonalMethod(period="hourly")
        assert method._num_buckets == 24

    def test_init_monthly(self):
        """Test monthly period."""
        method = SeasonalMethod(period="monthly")
        assert method._num_buckets == 12

    def test_init_invalid_period(self):
        """Test invalid period raises error."""
        with pytest.raises(ValueError):
            SeasonalMethod(period="invalid")

    def test_fit(self):
        """Test fitting without timestamps."""
        method = SeasonalMethod()
        values = [100, 102, 98, 105, 97, 103]
        method.fit(values)

        assert method._fitted is True
        assert method._global_mean > 0

    def test_fit_with_timestamps(self):
        """Test fitting with timestamps."""
        from datetime import datetime

        method = SeasonalMethod(period="daily")

        # Create data for different days of week
        data = [
            (datetime(2024, 1, 15, 10, 0), 100),  # Monday
            (datetime(2024, 1, 16, 10, 0), 110),  # Tuesday
            (datetime(2024, 1, 17, 10, 0), 105),  # Wednesday
            (datetime(2024, 1, 22, 10, 0), 102),  # Next Monday
            (datetime(2024, 1, 23, 10, 0), 108),  # Next Tuesday
        ]

        method.fit_with_timestamps(data)

        assert method._fitted is True
        assert len(method._bucket_means) > 0

    def test_score_without_timestamp(self):
        """Test scoring without timestamp."""
        method = SeasonalMethod()
        method.fit([100, 102, 98, 105, 97, 103])

        score = method.score(101)
        assert score.is_anomaly is False
        assert "No timestamp provided" in score.details.get("note", "")

    def test_score_with_timestamp(self):
        """Test scoring with timestamp."""
        from datetime import datetime

        method = SeasonalMethod(period="daily")
        data = [
            (datetime(2024, 1, 15, 10, 0), 100),
            (datetime(2024, 1, 22, 10, 0), 102),
            (datetime(2024, 1, 29, 10, 0), 98),
        ]
        method.fit_with_timestamps(data)

        score = method.score_with_timestamp(datetime(2024, 2, 5, 10, 0), 105)
        assert score.details.get("period") == "daily"


class TestBaselineStorage:
    """Tests for BaselineStorage class."""

    def test_store_and_get(self):
        """Test storing and retrieving baselines."""
        from duckguard.history import HistoryStorage

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_history.db"
            history_storage = HistoryStorage(db_path=db_path)
            try:
                storage = BaselineStorage(storage=history_storage)

                # Store a baseline
                storage.store("test.csv", "amount", "mean", 150.5, sample_size=1000)

                # Retrieve it
                baseline = storage.get("test.csv", "amount", "mean")

                assert baseline is not None
                assert baseline.source == "test.csv"
                assert baseline.column_name == "amount"
                assert baseline.metric == "mean"
                assert baseline.value == 150.5
                assert baseline.sample_size == 1000
            finally:
                history_storage.close()

    def test_get_nonexistent(self):
        """Test getting nonexistent baseline."""
        from duckguard.history import HistoryStorage

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_history.db"
            history_storage = HistoryStorage(db_path=db_path)
            try:
                storage = BaselineStorage(storage=history_storage)

                baseline = storage.get("nonexistent.csv", "col", "mean")
                assert baseline is None
            finally:
                history_storage.close()

    def test_update_replace(self):
        """Test updating baseline with replace method."""
        from duckguard.history import HistoryStorage

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_history.db"
            history_storage = HistoryStorage(db_path=db_path)
            try:
                storage = BaselineStorage(storage=history_storage)

                storage.store("test.csv", "amount", "mean", 100.0)
                storage.update("test.csv", "amount", "mean", 200.0, method="replace")

                baseline = storage.get("test.csv", "amount", "mean")
                assert baseline.value == 200.0
            finally:
                history_storage.close()

    def test_update_rolling(self):
        """Test updating baseline with rolling average."""
        from duckguard.history import HistoryStorage

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_history.db"
            history_storage = HistoryStorage(db_path=db_path)
            try:
                storage = BaselineStorage(storage=history_storage)

                storage.store("test.csv", "amount", "mean", 100.0, sample_size=100)
                storage.update("test.csv", "amount", "mean", 200.0, sample_size=100, method="rolling")

                baseline = storage.get("test.csv", "amount", "mean")
                # Should be weighted average: 0.7 * 100 + 0.3 * 200 = 130
                assert 125 < baseline.value < 135
            finally:
                history_storage.close()

    def test_get_all(self):
        """Test getting all baselines for a source."""
        from duckguard.history import HistoryStorage

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_history.db"
            history_storage = HistoryStorage(db_path=db_path)
            try:
                storage = BaselineStorage(storage=history_storage)

                storage.store("test.csv", "amount", "mean", 100.0)
                storage.store("test.csv", "amount", "stddev", 10.0)
                storage.store("test.csv", "quantity", "mean", 50.0)

                baselines = storage.get_all("test.csv")
                assert len(baselines) == 3
            finally:
                history_storage.close()

    def test_delete(self):
        """Test deleting baselines."""
        from duckguard.history import HistoryStorage

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_history.db"
            history_storage = HistoryStorage(db_path=db_path)
            try:
                storage = BaselineStorage(storage=history_storage)

                storage.store("test.csv", "amount", "mean", 100.0)
                storage.store("test.csv", "amount", "stddev", 10.0)

                count = storage.delete("test.csv")
                assert count == 2

                baselines = storage.get_all("test.csv")
                assert len(baselines) == 0
            finally:
                history_storage.close()


class TestColumnBaseline:
    """Tests for ColumnBaseline dataclass."""

    def test_to_dict(self):
        """Test to_dict conversion."""
        baseline = ColumnBaseline(
            column_name="amount",
            mean=150.5,
            stddev=25.0,
            min=10.0,
            max=500.0,
            null_percent=2.5,
            sample_size=1000,
        )

        data = baseline.to_dict()
        assert data["column_name"] == "amount"
        assert data["mean"] == 150.5
        assert data["stddev"] == 25.0

    def test_from_dict(self):
        """Test from_dict creation."""
        data = {
            "column_name": "amount",
            "mean": 150.5,
            "stddev": 25.0,
        }

        baseline = ColumnBaseline.from_dict(data)
        assert baseline.column_name == "amount"
        assert baseline.mean == 150.5
        assert baseline.stddev == 25.0
        assert baseline.min is None
