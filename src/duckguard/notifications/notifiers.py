"""Notification providers for DuckGuard.

Supports Slack and Microsoft Teams webhooks for alerting on data quality issues.
"""

from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from urllib import request
from urllib.error import URLError

from duckguard.rules.executor import ExecutionResult


@dataclass
class NotificationConfig:
    """Configuration for notifications.

    Attributes:
        on_failure: Send notification on check failures (default: True)
        on_warning: Send notification on warnings (default: False)
        on_success: Send notification on all checks passing (default: False)
        include_passed_checks: Include passed checks in message (default: False)
        include_row_samples: Include sample failing rows (default: True)
        max_failures_shown: Max number of failures to show (default: 10)
        mention_users: List of users to mention on failure
        channel: Override default channel (Slack only)
    """

    on_failure: bool = True
    on_warning: bool = False
    on_success: bool = False
    include_passed_checks: bool = False
    include_row_samples: bool = True
    max_failures_shown: int = 10
    mention_users: list[str] = field(default_factory=list)
    channel: str | None = None
    username: str | None = None  # Slack bot username

    # Email-specific attributes (set by EmailNotifier)
    smtp_host: str | None = None
    smtp_port: int | None = None
    from_address: str | None = None
    to_addresses: list[str] | None = None
    use_tls: bool | None = None
    use_ssl: bool | None = None
    subject_prefix: str | None = None


class BaseNotifier(ABC):
    """Abstract base class for notification providers."""

    def __init__(
        self,
        webhook_url: str | None = None,
        config: NotificationConfig | None = None
    ):
        """Initialize the notifier.

        Args:
            webhook_url: Webhook URL for the notification service
            config: Notification configuration
        """
        self.webhook_url = webhook_url or self._get_webhook_from_env()
        self.config = config or NotificationConfig()

        if not self.webhook_url:
            raise ValueError(
                f"Webhook URL required. Set {self._env_var_name} environment variable "
                f"or pass webhook_url parameter."
            )

    @property
    @abstractmethod
    def _env_var_name(self) -> str:
        """Environment variable name for webhook URL."""
        pass

    def _get_webhook_from_env(self) -> str | None:
        """Get webhook URL from environment variable."""
        return os.environ.get(self._env_var_name)

    @abstractmethod
    def _format_message(self, result: ExecutionResult) -> dict[str, Any]:
        """Format the result as a message for the notification service."""
        pass

    def send_results(self, result: ExecutionResult) -> bool:
        """Send notification based on execution results.

        Args:
            result: ExecutionResult from rule execution

        Returns:
            True if notification was sent, False if skipped
        """
        should_send = False

        if not result.passed and self.config.on_failure:
            should_send = True
        elif result.warning_count > 0 and self.config.on_warning:
            should_send = True
        elif result.passed and self.config.on_success:
            should_send = True

        if not should_send:
            return False

        return self._send(result)

    def send_failure_alert(self, result: ExecutionResult) -> bool:
        """Send an alert for failures (ignores config settings).

        Args:
            result: ExecutionResult from rule execution

        Returns:
            True if sent successfully
        """
        return self._send(result)

    def _send(self, result: ExecutionResult) -> bool:
        """Send the notification.

        Args:
            result: ExecutionResult to send

        Returns:
            True if sent successfully
        """
        message = self._format_message(result)
        data = json.dumps(message).encode("utf-8")

        req = request.Request(
            self.webhook_url,
            data=data,
            headers={"Content-Type": "application/json"},
        )

        try:
            with request.urlopen(req, timeout=10) as response:
                return response.status == 200
        except URLError as e:
            raise NotificationError(f"Failed to send notification: {e}") from e


class SlackNotifier(BaseNotifier):
    """Slack webhook notifier.

    Usage:
        notifier = SlackNotifier(
            webhook_url="https://hooks.slack.com/...",
            channel="#data-quality",
            username="DuckGuard Bot"
        )
        # or set DUCKGUARD_SLACK_WEBHOOK environment variable

        result = execute_rules(rules, "data.csv")
        notifier.send_results(result)
    """

    def __init__(
        self,
        webhook_url: str | None = None,
        channel: str | None = None,
        username: str | None = None,
        config: NotificationConfig | None = None,
    ):
        """Initialize Slack notifier.

        Args:
            webhook_url: Slack webhook URL
            channel: Override default channel (e.g., "#data-quality")
            username: Bot username to display
            config: Notification configuration
        """
        super().__init__(webhook_url=webhook_url, config=config)
        # Only override if explicitly provided (don't overwrite config values with None)
        if channel is not None:
            self.config.channel = channel
        if username is not None:
            self.config.username = username

    @property
    def _env_var_name(self) -> str:
        return "DUCKGUARD_SLACK_WEBHOOK"

    def _format_message(self, result: ExecutionResult) -> dict[str, Any]:
        """Format as Slack message blocks."""
        status_emoji = ":white_check_mark:" if result.passed else ":x:"
        status_text = "PASSED" if result.passed else "FAILED"

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{status_emoji} DuckGuard Validation {status_text}",
                    "emoji": True,
                },
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Source:*\n`{result.source}`"},
                    {"type": "mrkdwn", "text": f"*Time:*\n{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"},
                    {"type": "mrkdwn", "text": f"*Checks:*\n{result.passed_count}/{result.total_checks} passed"},
                    {"type": "mrkdwn", "text": f"*Score:*\n{result.quality_score:.1f}%"},
                ],
            },
        ]

        # Add failures
        failures = result.get_failures()
        if failures:
            failure_text = self._format_failures_slack(failures)
            blocks.append({"type": "divider"})
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": failure_text},
            })

        # Add warnings if configured
        warnings = result.get_warnings()
        if warnings and self.config.on_warning:
            warning_text = self._format_warnings_slack(warnings)
            blocks.append({"type": "divider"})
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": warning_text},
            })

        # Add mentions
        if not result.passed and self.config.mention_users:
            mentions = " ".join(f"<@{u}>" for u in self.config.mention_users)
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": f":bell: {mentions}"},
            })

        message = {"blocks": blocks}

        if self.config.channel:
            message["channel"] = self.config.channel
        if self.config.username:
            message["username"] = self.config.username

        return message

    def _format_failures_slack(self, failures: list) -> str:
        """Format failures for Slack."""
        lines = [":rotating_light: *Failures:*"]

        shown = failures[:self.config.max_failures_shown]
        for f in shown:
            col = f"[{f.column}]" if f.column else "[table]"
            lines.append(f"• {col} {f.message}")

            # Include sample failing rows if available
            if self.config.include_row_samples and f.details.get("failed_rows"):
                sample = f.details["failed_rows"][:3]
                lines.append(f"  _Sample values: {sample}_")

        remaining = len(failures) - len(shown)
        if remaining > 0:
            lines.append(f"_...and {remaining} more failures_")

        return "\n".join(lines)

    def _format_warnings_slack(self, warnings: list) -> str:
        """Format warnings for Slack."""
        lines = [":warning: *Warnings:*"]

        shown = warnings[:self.config.max_failures_shown]
        for w in shown:
            col = f"[{w.column}]" if w.column else "[table]"
            lines.append(f"• {col} {w.message}")

        remaining = len(warnings) - len(shown)
        if remaining > 0:
            lines.append(f"_...and {remaining} more warnings_")

        return "\n".join(lines)


class TeamsNotifier(BaseNotifier):
    """Microsoft Teams webhook notifier.

    Usage:
        notifier = TeamsNotifier(webhook_url="https://outlook.office.com/webhook/...")
        # or set DUCKGUARD_TEAMS_WEBHOOK environment variable

        result = execute_rules(rules, "data.csv")
        notifier.send_results(result)
    """

    @property
    def _env_var_name(self) -> str:
        return "DUCKGUARD_TEAMS_WEBHOOK"

    def _format_message(self, result: ExecutionResult) -> dict[str, Any]:
        """Format as Teams Adaptive Card."""
        status_text = "PASSED" if result.passed else "FAILED"

        facts = [
            {"title": "Source", "value": result.source},
            {"title": "Time", "value": datetime.now().strftime("%Y-%m-%d %H:%M:%S")},
            {"title": "Checks", "value": f"{result.passed_count}/{result.total_checks} passed"},
            {"title": "Score", "value": f"{result.quality_score:.1f}%"},
        ]

        sections = [
            {
                "activityTitle": f"DuckGuard Validation {status_text}",
                "facts": facts,
            }
        ]

        # Add failures
        failures = result.get_failures()
        if failures:
            failure_text = self._format_failures_teams(failures)
            sections.append({
                "title": "Failures",
                "text": failure_text,
            })

        # Add warnings
        warnings = result.get_warnings()
        if warnings and self.config.on_warning:
            warning_text = self._format_warnings_teams(warnings)
            sections.append({
                "title": "Warnings",
                "text": warning_text,
            })

        # Add mentions
        if not result.passed and self.config.mention_users:
            mentions = ", ".join(f"@{u}" for u in self.config.mention_users)
            sections.append({
                "text": f"**Attention:** {mentions}",
            })

        return {
            "@type": "MessageCard",
            "@context": "http://schema.org/extensions",
            "themeColor": "FF0000" if not result.passed else "00FF00",
            "summary": f"DuckGuard Validation {status_text}",
            "sections": sections,
        }

    def _format_failures_teams(self, failures: list) -> str:
        """Format failures for Teams."""
        lines = []

        shown = failures[:self.config.max_failures_shown]
        for f in shown:
            col = f"[{f.column}]" if f.column else "[table]"
            lines.append(f"- {col} {f.message}")

            if self.config.include_row_samples and f.details.get("failed_rows"):
                sample = f.details["failed_rows"][:3]
                lines.append(f"  *Sample values: {sample}*")

        remaining = len(failures) - len(shown)
        if remaining > 0:
            lines.append(f"*...and {remaining} more failures*")

        return "<br>".join(lines)

    def _format_warnings_teams(self, warnings: list) -> str:
        """Format warnings for Teams."""
        lines = []

        shown = warnings[:self.config.max_failures_shown]
        for w in shown:
            col = f"[{w.column}]" if w.column else "[table]"
            lines.append(f"- {col} {w.message}")

        remaining = len(warnings) - len(shown)
        if remaining > 0:
            lines.append(f"*...and {remaining} more warnings*")

        return "<br>".join(lines)


class NotificationError(Exception):
    """Exception raised when notification fails."""

    pass
