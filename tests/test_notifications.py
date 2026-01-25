"""Tests for the notifications module."""

from unittest.mock import Mock, patch

import pytest

from duckguard.notifications import (
    NotificationConfig,
    SlackNotifier,
    TeamsNotifier,
    format_results_markdown,
    format_results_text,
)
from duckguard.rules.executor import CheckResult, ExecutionResult
from duckguard.rules.schema import Check, CheckType, RuleSet, Severity, TableRules


@pytest.fixture
def sample_execution_result():
    """Create a sample execution result for testing."""
    ruleset = RuleSet(
        name="test_rules",
        table=TableRules(),
        columns={},
    )

    result = ExecutionResult(
        ruleset=ruleset,
        source="test.csv",
    )

    # Add some passed checks
    result.results.append(CheckResult(
        check=Check(type=CheckType.NOT_NULL),
        column="order_id",
        passed=True,
        actual_value=0,
        expected_value=0,
        message="Column 'order_id' has no null values",
    ))

    # Add a failed check
    result.results.append(CheckResult(
        check=Check(type=CheckType.BETWEEN),
        column="quantity",
        passed=False,
        actual_value=5,
        expected_value="[1, 10]",
        message="Column 'quantity' has 5 values outside [1, 10]",
        severity=Severity.ERROR,
        details={"failed_rows": [1, 2, 3, 4, 5]},
    ))

    # Add a warning
    result.results.append(CheckResult(
        check=Check(type=CheckType.NULL_PERCENT),
        column="email",
        passed=False,
        actual_value=15.0,
        expected_value="<= 10%",
        message="Column 'email' null_percent is 15%",
        severity=Severity.WARNING,
    ))

    return result


class TestNotificationConfig:
    """Tests for NotificationConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = NotificationConfig()
        assert config.on_failure is True
        assert config.on_warning is False
        assert config.on_success is False
        assert config.include_passed_checks is False
        assert config.max_failures_shown == 10

    def test_custom_config(self):
        """Test custom configuration."""
        config = NotificationConfig(
            on_failure=True,
            on_warning=True,
            on_success=True,
            mention_users=["U123", "U456"],
            channel="#data-quality",
        )
        assert config.on_warning is True
        assert config.on_success is True
        assert config.mention_users == ["U123", "U456"]
        assert config.channel == "#data-quality"


class TestSlackNotifier:
    """Tests for SlackNotifier."""

    def test_requires_webhook(self):
        """Test that webhook URL is required."""
        with pytest.raises(ValueError, match="Webhook URL required"):
            SlackNotifier()

    def test_accepts_webhook(self):
        """Test initialization with webhook URL."""
        notifier = SlackNotifier(webhook_url="https://hooks.slack.com/test")
        assert notifier.webhook_url == "https://hooks.slack.com/test"

    def test_env_var_name(self):
        """Test environment variable name."""
        notifier = SlackNotifier(webhook_url="https://test")
        assert notifier._env_var_name == "DUCKGUARD_SLACK_WEBHOOK"

    def test_format_message(self, sample_execution_result):
        """Test Slack message formatting."""
        notifier = SlackNotifier(webhook_url="https://test")
        message = notifier._format_message(sample_execution_result)

        assert "blocks" in message
        blocks = message["blocks"]

        # Should have header block
        header = blocks[0]
        assert header["type"] == "header"
        assert "FAILED" in header["text"]["text"]

    def test_format_message_with_mentions(self, sample_execution_result):
        """Test Slack message with user mentions."""
        config = NotificationConfig(mention_users=["U123", "U456"])
        notifier = SlackNotifier(webhook_url="https://test", config=config)
        message = notifier._format_message(sample_execution_result)

        # Should include mentions block
        message_text = str(message)
        assert "<@U123>" in message_text
        assert "<@U456>" in message_text

    @patch("duckguard.notifications.notifiers.request.urlopen")
    def test_send_results_on_failure(self, mock_urlopen, sample_execution_result):
        """Test sending notification on failure."""
        mock_response = Mock()
        mock_response.status = 200
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response

        notifier = SlackNotifier(webhook_url="https://test")
        result = notifier.send_results(sample_execution_result)

        assert result is True
        mock_urlopen.assert_called_once()


class TestTeamsNotifier:
    """Tests for TeamsNotifier."""

    def test_requires_webhook(self):
        """Test that webhook URL is required."""
        with pytest.raises(ValueError, match="Webhook URL required"):
            TeamsNotifier()

    def test_env_var_name(self):
        """Test environment variable name."""
        notifier = TeamsNotifier(webhook_url="https://test")
        assert notifier._env_var_name == "DUCKGUARD_TEAMS_WEBHOOK"

    def test_format_message(self, sample_execution_result):
        """Test Teams message formatting."""
        notifier = TeamsNotifier(webhook_url="https://test")
        message = notifier._format_message(sample_execution_result)

        assert message["@type"] == "MessageCard"
        assert "sections" in message
        assert "FAILED" in message["summary"]


class TestFormatters:
    """Tests for message formatters."""

    def test_format_results_text(self, sample_execution_result):
        """Test plain text formatting."""
        text = format_results_text(sample_execution_result)

        assert "DuckGuard Validation FAILED" in text
        assert "test.csv" in text
        assert "FAILURES:" in text
        assert "quantity" in text

    def test_format_results_text_include_passed(self, sample_execution_result):
        """Test text formatting with passed checks."""
        text = format_results_text(sample_execution_result, include_passed=True)

        assert "PASSED:" in text
        assert "order_id" in text

    def test_format_results_markdown(self, sample_execution_result):
        """Test Markdown formatting."""
        md = format_results_markdown(sample_execution_result)

        assert "# " in md  # Has headers
        assert "| Metric | Value |" in md  # Has table
        assert "## :rotating_light: Failures" in md
        assert "**`quantity`**" in md

    def test_format_results_markdown_include_passed(self, sample_execution_result):
        """Test Markdown formatting with passed checks."""
        md = format_results_markdown(sample_execution_result, include_passed=True)

        assert "## :white_check_mark: Passed" in md


class TestNotificationEdgeCases:
    """Edge case tests for notifications."""

    @pytest.fixture
    def passed_execution_result(self):
        """Create a passing execution result."""
        ruleset = RuleSet(
            name="test_rules",
            table=TableRules(),
            columns={},
        )

        result = ExecutionResult(
            ruleset=ruleset,
            source="test.csv",
        )

        result.results.append(CheckResult(
            check=Check(type=CheckType.NOT_NULL),
            column="order_id",
            passed=True,
            actual_value=0,
            expected_value=0,
            message="Column 'order_id' has no null values",
        ))

        return result

    def test_skip_notification_on_success_default(self, passed_execution_result):
        """Test that notifications are skipped for success by default."""
        notifier = SlackNotifier(webhook_url="https://test")
        result = notifier.send_results(passed_execution_result)

        # Default config doesn't send on success
        assert result is False

    def test_send_notification_on_success_when_configured(self, passed_execution_result):
        """Test sending notification on success when configured."""
        config = NotificationConfig(on_success=True)
        notifier = SlackNotifier(webhook_url="https://test", config=config)

        with patch("duckguard.notifications.notifiers.request.urlopen") as mock:
            mock_response = Mock()
            mock_response.status = 200
            mock_response.__enter__ = Mock(return_value=mock_response)
            mock_response.__exit__ = Mock(return_value=False)
            mock.return_value = mock_response

            result = notifier.send_results(passed_execution_result)
            assert result is True

    def test_format_passed_result_text(self, passed_execution_result):
        """Test formatting passed result as text."""
        text = format_results_text(passed_execution_result)

        assert "PASSED" in text
        assert "FAILURES:" not in text

    def test_format_passed_result_markdown(self, passed_execution_result):
        """Test formatting passed result as markdown."""
        md = format_results_markdown(passed_execution_result)

        assert ":white_check_mark:" in md
        assert ":rotating_light: Failures" not in md

    def test_teams_format_passed_result(self, passed_execution_result):
        """Test Teams formatting for passed result."""
        notifier = TeamsNotifier(webhook_url="https://test")
        message = notifier._format_message(passed_execution_result)

        assert "PASSED" in message["summary"]
        assert message["themeColor"] == "00FF00"  # Green for success

    @patch("duckguard.notifications.notifiers.request.urlopen")
    def test_teams_send_results(self, mock_urlopen, sample_execution_result):
        """Test Teams send_results."""
        mock_response = Mock()
        mock_response.status = 200
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response

        notifier = TeamsNotifier(webhook_url="https://test")
        result = notifier.send_results(sample_execution_result)

        assert result is True
        mock_urlopen.assert_called_once()

    def test_slack_with_channel_override(self, sample_execution_result):
        """Test Slack message with channel override."""
        config = NotificationConfig(channel="#custom-channel")
        notifier = SlackNotifier(webhook_url="https://test", config=config)
        message = notifier._format_message(sample_execution_result)

        assert message.get("channel") == "#custom-channel"
