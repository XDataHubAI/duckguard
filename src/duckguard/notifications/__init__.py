"""
DuckGuard Notifications - Slack, Teams, and Email alerting for data quality checks.

Usage:
    from duckguard.notifications import SlackNotifier, TeamsNotifier, EmailNotifier

    # Slack
    slack = SlackNotifier(webhook_url="https://hooks.slack.com/...")
    slack.send_results(execution_result)

    # Microsoft Teams
    teams = TeamsNotifier(webhook_url="https://outlook.office.com/webhook/...")
    teams.send_results(execution_result)

    # Email
    email = EmailNotifier(
        smtp_host="smtp.gmail.com",
        smtp_user="alerts@company.com",
        smtp_password="app_password",
        to_addresses=["team@company.com"],
    )
    email.send_results(execution_result)

    # Auto-notify on failures
    from duckguard import execute_rules, load_rules

    rules = load_rules("duckguard.yaml")
    result = execute_rules(rules, "data.csv")

    if not result.passed:
        slack.send_failure_alert(result)
        email.send_failure_alert(result)
"""

from duckguard.notifications.email import (
    EmailConfig,
    EmailNotifier,
)
from duckguard.notifications.formatter import (
    format_results_markdown,
    format_results_text,
)
from duckguard.notifications.notifiers import (
    BaseNotifier,
    NotificationConfig,
    NotificationError,
    SlackNotifier,
    TeamsNotifier,
)

__all__ = [
    "BaseNotifier",
    "NotificationConfig",
    "NotificationError",
    "SlackNotifier",
    "TeamsNotifier",
    "EmailNotifier",
    "EmailConfig",
    "format_results_text",
    "format_results_markdown",
]
