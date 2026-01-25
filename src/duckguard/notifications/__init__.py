"""
DuckGuard Notifications - Slack and Teams alerting for data quality checks.

Usage:
    from duckguard.notifications import SlackNotifier, TeamsNotifier

    # Slack
    slack = SlackNotifier(webhook_url="https://hooks.slack.com/...")
    slack.send_results(execution_result)

    # Microsoft Teams
    teams = TeamsNotifier(webhook_url="https://outlook.office.com/webhook/...")
    teams.send_results(execution_result)

    # Auto-notify on failures
    from duckguard import execute_rules, load_rules

    rules = load_rules("duckguard.yaml")
    result = execute_rules(rules, "data.csv")

    if not result.passed:
        slack.send_failure_alert(result)
"""

from duckguard.notifications.formatter import (
    format_results_markdown,
    format_results_text,
)
from duckguard.notifications.notifiers import (
    BaseNotifier,
    NotificationConfig,
    SlackNotifier,
    TeamsNotifier,
)

__all__ = [
    "BaseNotifier",
    "NotificationConfig",
    "SlackNotifier",
    "TeamsNotifier",
    "format_results_text",
    "format_results_markdown",
]
