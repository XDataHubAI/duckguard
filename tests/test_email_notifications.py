"""Tests for email notifications."""

import json
import os
from unittest.mock import MagicMock, patch

import pytest

from duckguard.notifications.email import (
    EmailConfig,
    EmailNotifier,
)


class MockExecutionResult:
    """Mock ExecutionResult for testing."""

    def __init__(
        self,
        passed: bool = True,
        quality_score: float = 95.0,
        total_checks: int = 10,
        passed_count: int = 9,
        failed_count: int = 1,
        warning_count: int = 0,
        source: str = "test.csv",
    ):
        self.passed = passed
        self.quality_score = quality_score
        self.total_checks = total_checks
        self.passed_count = passed_count
        self.failed_count = failed_count
        self.warning_count = warning_count
        self.source = source

    def get_failures(self):
        """Return mock failures."""
        if self.failed_count > 0:
            return [MockCheckResult("email", "Invalid format", "warning")]
        return []

    def get_warnings(self):
        """Return mock warnings."""
        if self.warning_count > 0:
            return [MockCheckResult("phone", "Non-standard format", "warning")]
        return []


class MockCheckResult:
    """Mock check result."""

    def __init__(self, column: str, message: str, severity: str):
        self.column = column
        self.message = message
        self.severity = severity
        self.details = {}


class TestEmailConfig:
    """Tests for EmailConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = EmailConfig(smtp_host="smtp.test.com")

        assert config.smtp_host == "smtp.test.com"
        assert config.smtp_port == 587
        assert config.use_tls is True
        assert config.use_ssl is False
        assert config.subject_prefix == "[DuckGuard]"
        assert config.to_addresses == []

    def test_full_config(self):
        """Test full configuration."""
        config = EmailConfig(
            smtp_host="smtp.gmail.com",
            smtp_port=465,
            smtp_user="user@gmail.com",
            smtp_password="secret",
            from_address="alerts@company.com",
            to_addresses=["team@company.com"],
            use_tls=False,
            use_ssl=True,
            subject_prefix="[ALERT]",
        )

        assert config.smtp_host == "smtp.gmail.com"
        assert config.smtp_port == 465
        assert config.use_ssl is True
        assert config.subject_prefix == "[ALERT]"


class TestEmailNotifier:
    """Tests for EmailNotifier class."""

    def test_init_with_params(self):
        """Test initialization with direct parameters."""
        notifier = EmailNotifier(
            smtp_host="smtp.test.com",
            smtp_port=587,
            smtp_user="user@test.com",
            smtp_password="secret",
            to_addresses=["team@test.com"],
        )

        assert notifier.email_config.smtp_host == "smtp.test.com"
        assert notifier.email_config.to_addresses == ["team@test.com"]

    def test_init_missing_host(self):
        """Test initialization fails without host."""
        with pytest.raises(ValueError, match="Email configuration required"):
            EmailNotifier()

    def test_init_missing_recipients(self):
        """Test initialization fails without recipients."""
        with pytest.raises(ValueError, match="At least one recipient"):
            EmailNotifier(smtp_host="smtp.test.com")

    def test_init_from_env(self):
        """Test initialization from environment variable."""
        env_config = {
            "smtp_host": "smtp.test.com",
            "smtp_port": 587,
            "smtp_user": "user@test.com",
            "smtp_password": "secret",
            "to_addresses": ["team@test.com"],
        }

        with patch.dict(os.environ, {"DUCKGUARD_EMAIL_CONFIG": json.dumps(env_config)}):
            notifier = EmailNotifier()
            assert notifier.email_config.smtp_host == "smtp.test.com"

    def test_env_var_name(self):
        """Test environment variable name."""
        notifier = EmailNotifier(
            smtp_host="smtp.test.com",
            to_addresses=["team@test.com"],
        )
        assert notifier._env_var_name == "DUCKGUARD_EMAIL_CONFIG"

    def test_format_message_passed(self):
        """Test message formatting for passed result."""
        notifier = EmailNotifier(
            smtp_host="smtp.test.com",
            to_addresses=["team@test.com"],
        )

        result = MockExecutionResult(passed=True, failed_count=0)
        message = notifier._format_message(result)

        assert "PASSED" in message["subject"]
        assert "test.csv" in message["subject"]
        assert "html_body" in message
        assert "text_body" in message

    def test_format_message_failed(self):
        """Test message formatting for failed result."""
        notifier = EmailNotifier(
            smtp_host="smtp.test.com",
            to_addresses=["team@test.com"],
        )

        result = MockExecutionResult(passed=False, quality_score=60.0)
        message = notifier._format_message(result)

        assert "FAILED" in message["subject"]

    def test_generate_html_body(self):
        """Test HTML body generation."""
        notifier = EmailNotifier(
            smtp_host="smtp.test.com",
            to_addresses=["team@test.com"],
        )

        result = MockExecutionResult(passed=True)
        html = notifier._generate_html_body(result)

        assert "<!DOCTYPE html>" in html
        assert "DuckGuard" in html
        assert "95.0%" in html  # Quality score
        assert "test.csv" in html

    def test_generate_html_body_with_failures(self):
        """Test HTML body with failures."""
        notifier = EmailNotifier(
            smtp_host="smtp.test.com",
            to_addresses=["team@test.com"],
        )

        result = MockExecutionResult(passed=False, failed_count=2)
        html = notifier._generate_html_body(result)

        assert "Failures" in html
        assert "email" in html  # Column from mock failure

    def test_generate_text_body(self):
        """Test plain text body generation."""
        notifier = EmailNotifier(
            smtp_host="smtp.test.com",
            to_addresses=["team@test.com"],
        )

        result = MockExecutionResult()
        text = notifier._generate_text_body(result)

        assert "DuckGuard Validation" in text
        assert "Quality Score: 95.0%" in text
        assert "test.csv" in text

    @patch('smtplib.SMTP')
    def test_send_success(self, mock_smtp):
        """Test successful email sending."""
        # Setup mock
        mock_instance = MagicMock()
        mock_smtp.return_value.__enter__ = MagicMock(return_value=mock_instance)
        mock_smtp.return_value.__exit__ = MagicMock(return_value=False)

        notifier = EmailNotifier(
            smtp_host="smtp.test.com",
            smtp_user="user@test.com",
            smtp_password="secret",
            to_addresses=["team@test.com"],
        )

        result = MockExecutionResult()
        success = notifier._send(result)

        assert success is True
        mock_instance.sendmail.assert_called_once()

    @patch('smtplib.SMTP')
    def test_send_with_tls(self, mock_smtp):
        """Test email sending with TLS."""
        mock_instance = MagicMock()
        mock_smtp.return_value.__enter__ = MagicMock(return_value=mock_instance)
        mock_smtp.return_value.__exit__ = MagicMock(return_value=False)

        notifier = EmailNotifier(
            smtp_host="smtp.test.com",
            smtp_user="user@test.com",
            smtp_password="secret",
            to_addresses=["team@test.com"],
            use_tls=True,
        )

        result = MockExecutionResult()
        notifier._send(result)

        mock_instance.starttls.assert_called_once()

    @patch('smtplib.SMTP_SSL')
    def test_send_with_ssl(self, mock_smtp_ssl):
        """Test email sending with SSL."""
        mock_instance = MagicMock()
        mock_smtp_ssl.return_value.__enter__ = MagicMock(return_value=mock_instance)
        mock_smtp_ssl.return_value.__exit__ = MagicMock(return_value=False)

        notifier = EmailNotifier(
            smtp_host="smtp.test.com",
            smtp_port=465,
            smtp_user="user@test.com",
            smtp_password="secret",
            to_addresses=["team@test.com"],
            use_ssl=True,
            use_tls=False,
        )

        result = MockExecutionResult()
        notifier._send(result)

        mock_smtp_ssl.assert_called()

    def test_send_results_on_failure(self):
        """Test send_results sends on failure by default."""
        with patch.object(EmailNotifier, '_send', return_value=True) as mock_send:
            notifier = EmailNotifier(
                smtp_host="smtp.test.com",
                to_addresses=["team@test.com"],
            )

            result = MockExecutionResult(passed=False)
            sent = notifier.send_results(result)

            assert sent is True
            mock_send.assert_called_once()

    def test_send_results_skips_success(self):
        """Test send_results skips successful results by default."""
        with patch.object(EmailNotifier, '_send', return_value=True) as mock_send:
            notifier = EmailNotifier(
                smtp_host="smtp.test.com",
                to_addresses=["team@test.com"],
            )

            result = MockExecutionResult(passed=True, failed_count=0)
            sent = notifier.send_results(result)

            assert sent is False
            mock_send.assert_not_called()

    def test_send_failure_alert(self):
        """Test send_failure_alert always sends."""
        with patch.object(EmailNotifier, '_send', return_value=True) as mock_send:
            notifier = EmailNotifier(
                smtp_host="smtp.test.com",
                to_addresses=["team@test.com"],
            )

            result = MockExecutionResult(passed=True)  # Even if passed
            sent = notifier.send_failure_alert(result)

            assert sent is True
            mock_send.assert_called_once()

    def test_multiple_recipients(self):
        """Test email to multiple recipients."""
        notifier = EmailNotifier(
            smtp_host="smtp.test.com",
            to_addresses=["user1@test.com", "user2@test.com", "user3@test.com"],
        )

        assert len(notifier.email_config.to_addresses) == 3

    def test_custom_subject_prefix(self):
        """Test custom subject prefix."""
        notifier = EmailNotifier(
            smtp_host="smtp.test.com",
            to_addresses=["team@test.com"],
            subject_prefix="[URGENT]",
        )

        result = MockExecutionResult(passed=False)
        message = notifier._format_message(result)

        assert "[URGENT]" in message["subject"]
