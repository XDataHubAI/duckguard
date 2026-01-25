"""Reporting module for DuckGuard."""

from duckguard.reporting.console import ConsoleReporter
from duckguard.reporting.json_report import JSONReporter

__all__ = ["ConsoleReporter", "JSONReporter"]
