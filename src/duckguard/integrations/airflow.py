"""Apache Airflow integration for DuckGuard.

Provides a DuckGuardOperator for running data quality checks in Airflow DAGs.

Usage:
    from duckguard.integrations.airflow import DuckGuardOperator

    check_orders = DuckGuardOperator(
        task_id="check_orders_quality",
        source="s3://bucket/orders.parquet",
        rules="duckguard.yaml",
        fail_on_warning=False,
    )

Note:
    Requires apache-airflow to be installed:
    pip install duckguard[airflow]
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

# Try to import Airflow - it's an optional dependency
try:
    from airflow.models import BaseOperator
    from airflow.utils.context import Context

    AIRFLOW_AVAILABLE = True
except ImportError:
    # Create stubs when Airflow is not installed
    AIRFLOW_AVAILABLE = False

    class BaseOperator:  # type: ignore[no-redef]
        """Stub BaseOperator when Airflow is not installed."""

        def __init__(self, **kwargs: Any) -> None:
            pass

    Context = dict  # type: ignore[misc,assignment]


class DuckGuardOperator(BaseOperator):
    """Airflow operator for running DuckGuard data quality checks.

    This operator runs DuckGuard validation rules against a data source
    and optionally fails the task if quality checks don't pass.

    Args:
        source: Data source path or connection string (supports Jinja templating)
        rules: Path to duckguard.yaml rules file (supports Jinja templating)
        table: Table name for database connections (supports Jinja templating)
        fail_on_warning: Whether to fail task on warnings (default: False)
        fail_on_error: Whether to fail task on errors (default: True)
        notify_slack: Slack webhook URL for notifications (supports Jinja templating)
        notify_teams: Teams webhook URL for notifications (supports Jinja templating)
        store_history: Whether to store results in history database (default: False)
        history_db: Path to history database (default: ~/.duckguard/history.db)
        **kwargs: Additional BaseOperator arguments (task_id, dag, etc.)

    Returns (via XCom):
        Dict with keys:
        - passed: bool - Whether all checks passed
        - quality_score: float - Overall quality score (0-100)
        - total_checks: int - Total number of checks
        - passed_count: int - Number of passing checks
        - failed_count: int - Number of failing checks
        - warning_count: int - Number of warnings
        - failures: list[dict] - Details of failed checks

    Example:
        from airflow import DAG
        from airflow.utils.dates import days_ago
        from duckguard.integrations.airflow import DuckGuardOperator

        with DAG("data_quality", start_date=days_ago(1)) as dag:
            check_orders = DuckGuardOperator(
                task_id="check_orders",
                source="s3://bucket/orders/{{ ds }}.parquet",
                rules="dags/rules/orders.yaml",
                fail_on_warning=False,
                notify_slack="{{ var.value.slack_webhook }}",
            )

            process_orders = SomeOtherOperator(task_id="process_orders")
            check_orders >> process_orders

    Raises:
        ImportError: If Apache Airflow is not installed
        AirflowException: If checks fail and fail_on_* is True
    """

    # Template fields for Airflow variable substitution
    template_fields: Sequence[str] = (
        "source",
        "rules",
        "table",
        "notify_slack",
        "notify_teams",
    )

    # Operator UI color (DuckGuard green)
    ui_color = "#00D26A"
    ui_fgcolor = "#FFFFFF"

    def __init__(
        self,
        *,
        source: str,
        rules: str | None = None,
        table: str | None = None,
        fail_on_warning: bool = False,
        fail_on_error: bool = True,
        notify_slack: str | None = None,
        notify_teams: str | None = None,
        store_history: bool = False,
        history_db: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize the DuckGuard operator."""
        if not AIRFLOW_AVAILABLE:
            raise ImportError(
                "Apache Airflow is required for DuckGuardOperator. "
                "Install with: pip install duckguard[airflow]"
            )

        super().__init__(**kwargs)

        self.source = source
        self.rules = rules
        self.table = table
        self.fail_on_warning = fail_on_warning
        self.fail_on_error = fail_on_error
        self.notify_slack = notify_slack
        self.notify_teams = notify_teams
        self.store_history = store_history
        self.history_db = history_db

    def execute(self, context: Context) -> dict[str, Any]:
        """Execute the DuckGuard checks.

        Args:
            context: Airflow context dictionary

        Returns:
            Dict with execution results (also pushed to XCom)

        Raises:
            AirflowException: If checks fail and fail_on_* is True
        """
        from airflow.exceptions import AirflowException

        from duckguard import connect
        from duckguard.rules import execute_rules, generate_rules, load_rules

        self.log.info(f"Running DuckGuard checks on: {self.source}")

        # Connect to data source
        dataset = connect(self.source, table=self.table)
        self.log.info(
            f"Connected: {dataset.row_count:,} rows, {dataset.column_count} columns"
        )

        # Load or generate rules
        if self.rules:
            self.log.info(f"Loading rules from: {self.rules}")
            ruleset = load_rules(self.rules)
        else:
            self.log.info("No rules file specified, generating rules from data profile")
            ruleset = generate_rules(dataset, as_yaml=False)

        # Execute validation
        result = execute_rules(ruleset, dataset=dataset)

        # Log results
        self.log.info(f"Quality Score: {result.quality_score:.1f}%")
        self.log.info(
            f"Checks: {result.passed_count}/{result.total_checks} passed"
        )

        if result.failed_count > 0:
            self.log.warning(f"Failures: {result.failed_count}")
            for failure in result.get_failures()[:10]:  # Limit log output
                self.log.warning(f"  - [{failure.column}] {failure.message}")

        if result.warning_count > 0:
            self.log.warning(f"Warnings: {result.warning_count}")

        # Send notifications
        self._send_notifications(result)

        # Store in history
        if self.store_history:
            self._store_history(result, context)

        # Build XCom return value
        xcom_result = {
            "passed": result.passed,
            "quality_score": result.quality_score,
            "total_checks": result.total_checks,
            "passed_count": result.passed_count,
            "failed_count": result.failed_count,
            "warning_count": result.warning_count,
            "source": result.source,
            "failures": [
                {
                    "column": f.column,
                    "check_type": f.check.type.value,
                    "message": f.message,
                    "actual_value": str(f.actual_value),
                    "expected_value": str(f.expected_value),
                }
                for f in result.get_failures()
            ],
        }

        # Determine if we should fail the task
        should_fail = False
        fail_reason = ""

        if self.fail_on_error and result.failed_count > 0:
            should_fail = True
            fail_reason = f"{result.failed_count} check(s) failed"

        if self.fail_on_warning and result.warning_count > 0:
            should_fail = True
            if fail_reason:
                fail_reason += f", {result.warning_count} warning(s)"
            else:
                fail_reason = f"{result.warning_count} warning(s)"

        if should_fail:
            raise AirflowException(
                f"DuckGuard validation failed: {fail_reason}. "
                f"Quality score: {result.quality_score:.1f}%"
            )

        self.log.info("DuckGuard validation passed!")
        return xcom_result

    def _send_notifications(self, result: Any) -> None:
        """Send notifications if configured."""
        if self.notify_slack:
            try:
                from duckguard.notifications import SlackNotifier

                notifier = SlackNotifier(webhook_url=self.notify_slack)
                notifier.send_results(result)
                self.log.info("Sent Slack notification")
            except Exception as e:
                self.log.warning(f"Failed to send Slack notification: {e}")

        if self.notify_teams:
            try:
                from duckguard.notifications import TeamsNotifier

                notifier = TeamsNotifier(webhook_url=self.notify_teams)
                notifier.send_results(result)
                self.log.info("Sent Teams notification")
            except Exception as e:
                self.log.warning(f"Failed to send Teams notification: {e}")

    def _store_history(self, result: Any, context: Context) -> None:
        """Store results in history database."""
        try:
            from duckguard.history import HistoryStorage

            storage = HistoryStorage(db_path=self.history_db)

            # Include Airflow context as metadata
            dag = context.get("dag")
            metadata = {
                "dag_id": dag.dag_id if dag else None,
                "task_id": self.task_id,
                "run_id": context.get("run_id"),
                "execution_date": str(context.get("execution_date")),
                "try_number": context.get("ti").try_number if context.get("ti") else None,
            }

            run_id = storage.store(result, metadata=metadata)
            self.log.info(f"Stored results in history: {run_id}")
        except Exception as e:
            self.log.warning(f"Failed to store history: {e}")


class DuckGuardSensor(BaseOperator):
    """Airflow sensor that waits for data quality to meet threshold.

    This sensor repeatedly checks data quality until it meets
    a minimum quality score threshold.

    Args:
        source: Data source path or connection string
        rules: Path to duckguard.yaml rules file
        min_quality_score: Minimum quality score to pass (0-100)
        poke_interval: Seconds between checks (default: 300)
        timeout: Total seconds before timing out (default: 3600)
        **kwargs: Additional BaseOperator arguments

    Example:
        wait_for_quality = DuckGuardSensor(
            task_id="wait_for_quality",
            source="s3://bucket/data.parquet",
            min_quality_score=95.0,
            poke_interval=300,
            timeout=3600,
        )
    """

    template_fields: Sequence[str] = ("source", "rules")
    ui_color = "#00D26A"
    ui_fgcolor = "#FFFFFF"

    def __init__(
        self,
        *,
        source: str,
        rules: str | None = None,
        min_quality_score: float = 90.0,
        table: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize the DuckGuard sensor."""
        if not AIRFLOW_AVAILABLE:
            raise ImportError(
                "Apache Airflow is required for DuckGuardSensor. "
                "Install with: pip install duckguard[airflow]"
            )

        super().__init__(**kwargs)

        self.source = source
        self.rules = rules
        self.min_quality_score = min_quality_score
        self.table = table

    def execute(self, context: Context) -> bool:
        """Check if data quality meets threshold.

        Returns:
            True if quality score >= min_quality_score
        """
        from duckguard import connect
        from duckguard.rules import execute_rules, generate_rules, load_rules

        self.log.info(f"Checking quality for: {self.source}")
        self.log.info(f"Minimum score required: {self.min_quality_score}")

        dataset = connect(self.source, table=self.table)

        if self.rules:
            ruleset = load_rules(self.rules)
        else:
            ruleset = generate_rules(dataset, as_yaml=False)

        result = execute_rules(ruleset, dataset=dataset)

        self.log.info(f"Current quality score: {result.quality_score:.1f}%")

        if result.quality_score >= self.min_quality_score:
            self.log.info("Quality threshold met!")
            return True
        else:
            self.log.info(
                f"Quality score {result.quality_score:.1f}% "
                f"below threshold {self.min_quality_score}%"
            )
            return False


def duckguard_check(
    task_id: str,
    source: str,
    **kwargs: Any,
) -> DuckGuardOperator:
    """Convenience function for creating a DuckGuard check operator.

    Args:
        task_id: Airflow task ID
        source: Data source path or connection string
        **kwargs: Additional DuckGuardOperator arguments

    Returns:
        DuckGuardOperator instance
    """
    return DuckGuardOperator(task_id=task_id, source=source, **kwargs)
