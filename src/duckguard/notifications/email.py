"""Email notification provider for DuckGuard.

Provides SMTP-based email notifications for data quality alerts.
"""

from __future__ import annotations

import json
import os
import smtplib
import ssl
from dataclasses import dataclass, field
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

from duckguard.notifications.notifiers import BaseNotifier, NotificationConfig, NotificationError
from duckguard.rules.executor import ExecutionResult


@dataclass
class EmailConfig:
    """Email configuration.

    Attributes:
        smtp_host: SMTP server hostname
        smtp_port: SMTP server port (default: 587 for TLS)
        smtp_user: SMTP username for authentication
        smtp_password: SMTP password for authentication
        from_address: Email address to send from
        to_addresses: List of recipient email addresses
        use_tls: Whether to use TLS encryption (default: True)
        use_ssl: Whether to use SSL (default: False, use for port 465)
        subject_prefix: Prefix for email subjects
    """

    smtp_host: str
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: str | None = None
    from_address: str | None = None
    to_addresses: list[str] = field(default_factory=list)
    use_tls: bool = True
    use_ssl: bool = False
    subject_prefix: str = "[DuckGuard]"


class EmailNotifier(BaseNotifier):
    """Email notification provider via SMTP.

    Sends HTML-formatted email notifications when data quality checks
    fail or meet other notification conditions.

    Usage:
        from duckguard.notifications import EmailNotifier

        # Direct configuration
        notifier = EmailNotifier(
            smtp_host="smtp.gmail.com",
            smtp_port=587,
            smtp_user="alerts@company.com",
            smtp_password="app_password",
            from_address="alerts@company.com",
            to_addresses=["team@company.com", "oncall@company.com"],
        )

        # Or via environment variable
        # DUCKGUARD_EMAIL_CONFIG='{"smtp_host": "smtp.gmail.com", ...}'
        notifier = EmailNotifier()

        result = execute_rules(rules, dataset)
        notifier.send_results(result)

    Environment Variable Format (DUCKGUARD_EMAIL_CONFIG):
        {
            "smtp_host": "smtp.gmail.com",
            "smtp_port": 587,
            "smtp_user": "user@gmail.com",
            "smtp_password": "app_password",
            "from_address": "alerts@company.com",
            "to_addresses": ["team@company.com"]
        }
    """

    def __init__(
        self,
        smtp_host: str | None = None,
        smtp_port: int = 587,
        smtp_user: str | None = None,
        smtp_password: str | None = None,
        from_address: str | None = None,
        to_addresses: list[str] | None = None,
        use_tls: bool = True,
        use_ssl: bool = False,
        subject_prefix: str = "[DuckGuard]",
        config: NotificationConfig | None = None,
    ):
        """Initialize email notifier.

        Args:
            smtp_host: SMTP server hostname
            smtp_port: SMTP server port
            smtp_user: SMTP username
            smtp_password: SMTP password
            from_address: Sender email address
            to_addresses: List of recipient addresses
            use_tls: Use STARTTLS
            use_ssl: Use SSL (for port 465)
            subject_prefix: Subject line prefix
            config: Notification configuration
        """
        self.config = config or NotificationConfig()

        # Try to load from environment if not provided
        if smtp_host is None:
            env_config = self._load_config_from_env()
            if env_config:
                self.email_config = env_config
            else:
                raise ValueError(
                    "Email configuration required. Set DUCKGUARD_EMAIL_CONFIG environment variable "
                    "or pass smtp_host parameter."
                )
        else:
            self.email_config = EmailConfig(
                smtp_host=smtp_host,
                smtp_port=smtp_port,
                smtp_user=smtp_user,
                smtp_password=smtp_password,
                from_address=from_address or smtp_user,
                to_addresses=to_addresses or [],
                use_tls=use_tls,
                use_ssl=use_ssl,
                subject_prefix=subject_prefix,
            )

        if not self.email_config.to_addresses:
            raise ValueError("At least one recipient address (to_addresses) is required")

        # Populate NotificationConfig with email settings for easy access
        self.config.smtp_host = self.email_config.smtp_host
        self.config.smtp_port = self.email_config.smtp_port
        self.config.from_address = self.email_config.from_address
        self.config.to_addresses = self.email_config.to_addresses
        self.config.use_tls = self.email_config.use_tls
        self.config.use_ssl = self.email_config.use_ssl
        self.config.subject_prefix = self.email_config.subject_prefix

        # Set webhook_url to a placeholder (not used for email)
        self.webhook_url = "email://smtp"

    @property
    def _env_var_name(self) -> str:
        return "DUCKGUARD_EMAIL_CONFIG"

    def _load_config_from_env(self) -> EmailConfig | None:
        """Load configuration from environment variable."""
        env_value = os.environ.get(self._env_var_name)
        if not env_value:
            return None

        try:
            data = json.loads(env_value)
            return EmailConfig(
                smtp_host=data["smtp_host"],
                smtp_port=data.get("smtp_port", 587),
                smtp_user=data.get("smtp_user"),
                smtp_password=data.get("smtp_password"),
                from_address=data.get("from_address", data.get("smtp_user")),
                to_addresses=data.get("to_addresses", []),
                use_tls=data.get("use_tls", True),
                use_ssl=data.get("use_ssl", False),
                subject_prefix=data.get("subject_prefix", "[DuckGuard]"),
            )
        except (json.JSONDecodeError, KeyError) as e:
            raise ValueError(f"Invalid {self._env_var_name} format: {e}") from e

    def _format_message(self, result: ExecutionResult) -> dict[str, Any]:
        """Format the result as email subject and body.

        Returns:
            Dict with 'subject' and 'html_body' keys
        """
        status = "PASSED" if result.passed else "FAILED"
        subject = f"{self.email_config.subject_prefix} Validation {status}: {result.source}"

        html_body = self._generate_html_body(result)

        return {
            "subject": subject,
            "html_body": html_body,
            "text_body": self._generate_text_body(result),
        }

    def _generate_html_body(self, result: ExecutionResult) -> str:
        """Generate HTML email body."""
        status_color = "#28a745" if result.passed else "#dc3545"
        status_text = "PASSED" if result.passed else "FAILED"

        # Get failures and warnings
        failures = result.get_failures()
        warnings = result.get_warnings()

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
        }}
        .header {{
            background: {status_color};
            color: white;
            padding: 20px;
            border-radius: 8px 8px 0 0;
            text-align: center;
        }}
        .header h1 {{
            margin: 0;
            font-size: 24px;
        }}
        .content {{
            background: #f8f9fa;
            padding: 20px;
            border: 1px solid #dee2e6;
            border-top: none;
            border-radius: 0 0 8px 8px;
        }}
        .stats {{
            display: flex;
            justify-content: space-around;
            margin: 20px 0;
            flex-wrap: wrap;
        }}
        .stat {{
            text-align: center;
            padding: 10px 20px;
            background: white;
            border-radius: 8px;
            margin: 5px;
            min-width: 100px;
        }}
        .stat-value {{
            font-size: 24px;
            font-weight: bold;
            color: #333;
        }}
        .stat-label {{
            font-size: 12px;
            color: #666;
            text-transform: uppercase;
        }}
        .section {{
            margin: 20px 0;
        }}
        .section h3 {{
            color: #333;
            border-bottom: 2px solid #dee2e6;
            padding-bottom: 5px;
        }}
        .failure {{
            background: #fff3f3;
            border-left: 4px solid #dc3545;
            padding: 10px 15px;
            margin: 10px 0;
            border-radius: 0 4px 4px 0;
        }}
        .warning {{
            background: #fff8e6;
            border-left: 4px solid #ffc107;
            padding: 10px 15px;
            margin: 10px 0;
            border-radius: 0 4px 4px 0;
        }}
        .column-name {{
            font-weight: bold;
            color: #495057;
        }}
        .footer {{
            text-align: center;
            margin-top: 20px;
            font-size: 12px;
            color: #6c757d;
        }}
        .score-badge {{
            display: inline-block;
            padding: 5px 15px;
            border-radius: 20px;
            font-weight: bold;
            margin-top: 10px;
        }}
        .score-a {{ background: #28a745; color: white; }}
        .score-b {{ background: #5cb85c; color: white; }}
        .score-c {{ background: #ffc107; color: black; }}
        .score-d {{ background: #fd7e14; color: white; }}
        .score-f {{ background: #dc3545; color: white; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>DuckGuard Validation {status_text}</h1>
        <p style="margin: 5px 0; opacity: 0.9;">{result.source}</p>
    </div>

    <div class="content">
        <div class="stats">
            <div class="stat">
                <div class="stat-value">{result.quality_score:.1f}%</div>
                <div class="stat-label">Quality Score</div>
            </div>
            <div class="stat">
                <div class="stat-value">{result.passed_count}/{result.total_checks}</div>
                <div class="stat-label">Checks Passed</div>
            </div>
            <div class="stat">
                <div class="stat-value">{result.failed_count}</div>
                <div class="stat-label">Failures</div>
            </div>
            <div class="stat">
                <div class="stat-value">{result.warning_count}</div>
                <div class="stat-label">Warnings</div>
            </div>
        </div>
"""

        # Add failures section
        if failures:
            html += """
        <div class="section">
            <h3>Failures</h3>
"""
            for f in failures[:self.config.max_failures_shown]:
                col_name = f"[{f.column}]" if f.column else "[table]"
                html += f"""
            <div class="failure">
                <span class="column-name">{col_name}</span> {f.message}
            </div>
"""
            remaining = len(failures) - self.config.max_failures_shown
            if remaining > 0:
                html += f"""
            <p style="color: #6c757d; font-style: italic;">...and {remaining} more failures</p>
"""
            html += "        </div>\n"

        # Add warnings section
        if warnings and self.config.on_warning:
            html += """
        <div class="section">
            <h3>Warnings</h3>
"""
            for w in warnings[:self.config.max_failures_shown]:
                col_name = f"[{w.column}]" if w.column else "[table]"
                html += f"""
            <div class="warning">
                <span class="column-name">{col_name}</span> {w.message}
            </div>
"""
            remaining = len(warnings) - self.config.max_failures_shown
            if remaining > 0:
                html += f"""
            <p style="color: #6c757d; font-style: italic;">...and {remaining} more warnings</p>
"""
            html += "        </div>\n"

        html += f"""
    </div>

    <div class="footer">
        <p>Generated by DuckGuard at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
</body>
</html>
"""
        return html

    def _generate_text_body(self, result: ExecutionResult) -> str:
        """Generate plain text email body."""
        status = "PASSED" if result.passed else "FAILED"
        lines = [
            f"DuckGuard Validation {status}",
            f"Source: {result.source}",
            f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            f"Quality Score: {result.quality_score:.1f}%",
            f"Checks: {result.passed_count}/{result.total_checks} passed",
            f"Failures: {result.failed_count}",
            f"Warnings: {result.warning_count}",
            "",
        ]

        failures = result.get_failures()
        if failures:
            lines.append("FAILURES:")
            for f in failures[:self.config.max_failures_shown]:
                col_name = f"[{f.column}]" if f.column else "[table]"
                lines.append(f"  - {col_name} {f.message}")
            remaining = len(failures) - self.config.max_failures_shown
            if remaining > 0:
                lines.append(f"  ...and {remaining} more")
            lines.append("")

        warnings = result.get_warnings()
        if warnings and self.config.on_warning:
            lines.append("WARNINGS:")
            for w in warnings[:self.config.max_failures_shown]:
                col_name = f"[{w.column}]" if w.column else "[table]"
                lines.append(f"  - {col_name} {w.message}")
            remaining = len(warnings) - self.config.max_failures_shown
            if remaining > 0:
                lines.append(f"  ...and {remaining} more")

        return "\n".join(lines)

    def _send(self, result: ExecutionResult) -> bool:
        """Send the email notification.

        Args:
            result: ExecutionResult to send

        Returns:
            True if sent successfully
        """
        message_data = self._format_message(result)

        # Create message
        msg = MIMEMultipart("alternative")
        msg["Subject"] = message_data["subject"]
        msg["From"] = self.email_config.from_address or self.email_config.smtp_user or ""
        msg["To"] = ", ".join(self.email_config.to_addresses)

        # Attach text and HTML parts
        text_part = MIMEText(message_data["text_body"], "plain")
        html_part = MIMEText(message_data["html_body"], "html")
        msg.attach(text_part)
        msg.attach(html_part)

        try:
            if self.email_config.use_ssl:
                # SSL connection (port 465)
                context = ssl.create_default_context()
                with smtplib.SMTP_SSL(
                    self.email_config.smtp_host,
                    self.email_config.smtp_port,
                    context=context,
                ) as server:
                    if self.email_config.smtp_user and self.email_config.smtp_password:
                        server.login(self.email_config.smtp_user, self.email_config.smtp_password)
                    server.sendmail(
                        msg["From"],
                        self.email_config.to_addresses,
                        msg.as_string(),
                    )
            else:
                # TLS connection (port 587)
                with smtplib.SMTP(
                    self.email_config.smtp_host,
                    self.email_config.smtp_port,
                ) as server:
                    if self.email_config.use_tls:
                        server.starttls()
                    if self.email_config.smtp_user and self.email_config.smtp_password:
                        server.login(self.email_config.smtp_user, self.email_config.smtp_password)
                    server.sendmail(
                        msg["From"],
                        self.email_config.to_addresses,
                        msg.as_string(),
                    )

            return True

        except smtplib.SMTPException as e:
            raise NotificationError(f"Failed to send email: {e}") from e
        except Exception as e:
            raise NotificationError(f"Email error: {e}") from e

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
