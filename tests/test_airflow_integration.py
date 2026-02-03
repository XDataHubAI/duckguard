"""Tests for the Airflow integration module."""

from __future__ import annotations

import pytest

# Check if Airflow is available
try:
    import airflow  # noqa: F401

    AIRFLOW_AVAILABLE = True
except ImportError:
    AIRFLOW_AVAILABLE = False


class TestDuckGuardOperatorWithoutAirflow:
    """Tests for DuckGuardOperator when Airflow is not installed."""

    def test_import_raises_error_without_airflow(self):
        """Test that importing the operator without Airflow raises ImportError."""
        if AIRFLOW_AVAILABLE:
            pytest.skip("Airflow is installed")

        # The module should import without error
        from duckguard.integrations.airflow import DuckGuardOperator

        # But instantiation should raise ImportError
        with pytest.raises(ImportError) as exc_info:
            DuckGuardOperator(task_id="test", source="test.csv")

        assert "Apache Airflow" in str(exc_info.value)


@pytest.mark.skipif(not AIRFLOW_AVAILABLE, reason="Airflow not installed")
class TestDuckGuardOperatorWithAirflow:
    """Tests for DuckGuardOperator when Airflow is installed."""

    def test_operator_initialization(self):
        """Test basic operator initialization."""
        from duckguard.integrations.airflow import DuckGuardOperator

        op = DuckGuardOperator(
            task_id="test_task",
            source="test.csv",
        )

        assert op.task_id == "test_task"
        assert op.source == "test.csv"
        assert op.fail_on_error is True
        assert op.fail_on_warning is False

    def test_operator_with_all_params(self):
        """Test operator with all parameters."""
        from duckguard.integrations.airflow import DuckGuardOperator

        op = DuckGuardOperator(
            task_id="test_task",
            source="s3://bucket/data.parquet",
            rules="rules.yaml",
            table="orders",
            fail_on_warning=True,
            fail_on_error=True,
            notify_slack="https://hooks.slack.com/xxx",
            notify_teams="https://teams.webhook.url",
            store_history=True,
            history_db="/tmp/history.db",
        )

        assert op.source == "s3://bucket/data.parquet"
        assert op.rules == "rules.yaml"
        assert op.table == "orders"
        assert op.fail_on_warning is True
        assert op.notify_slack == "https://hooks.slack.com/xxx"
        assert op.store_history is True

    def test_template_fields(self):
        """Test that template fields are correctly defined."""
        from duckguard.integrations.airflow import DuckGuardOperator

        expected_fields = ("source", "rules", "table", "notify_slack", "notify_teams")
        assert DuckGuardOperator.template_fields == expected_fields

    def test_ui_color(self):
        """Test UI color is set."""
        from duckguard.integrations.airflow import DuckGuardOperator

        assert DuckGuardOperator.ui_color == "#00D26A"


class TestDuckGuardCheckFunction:
    """Tests for the duckguard_check convenience function."""

    def test_creates_operator(self):
        """Test that duckguard_check creates an operator."""
        if not AIRFLOW_AVAILABLE:
            pytest.skip("Airflow not installed")

        from duckguard.integrations.airflow import duckguard_check

        op = duckguard_check(
            task_id="check_data",
            source="data.csv",
            rules="rules.yaml",
        )

        assert op.task_id == "check_data"
        assert op.source == "data.csv"
        assert op.rules == "rules.yaml"


class TestDuckGuardSensor:
    """Tests for DuckGuardSensor."""

    @pytest.mark.skipif(not AIRFLOW_AVAILABLE, reason="Airflow not installed")
    def test_sensor_initialization(self):
        """Test sensor initialization."""
        from duckguard.integrations.airflow import DuckGuardSensor

        sensor = DuckGuardSensor(
            task_id="wait_for_quality",
            source="data.csv",
            min_quality_score=95.0,
        )

        assert sensor.task_id == "wait_for_quality"
        assert sensor.source == "data.csv"
        assert sensor.min_quality_score == 95.0

    def test_sensor_import_without_airflow(self):
        """Test that sensor import fails gracefully without Airflow."""
        if AIRFLOW_AVAILABLE:
            pytest.skip("Airflow is installed")

        from duckguard.integrations.airflow import DuckGuardSensor

        with pytest.raises(ImportError):
            DuckGuardSensor(task_id="test", source="test.csv")


class TestIntegrationsModule:
    """Tests for the integrations module __init__.py."""

    def test_airflow_import(self):
        """Test that airflow module can be imported from integrations."""
        from duckguard.integrations import airflow

        # airflow may be None if not installed
        if AIRFLOW_AVAILABLE:
            assert airflow is not None
        # If Airflow is not installed, airflow should be None

    def test_dbt_import(self):
        """Test that dbt module can be imported from integrations."""
        from duckguard.integrations import dbt
        assert dbt is not None
