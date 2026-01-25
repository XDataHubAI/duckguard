"""Console reporter using Rich."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from duckguard.core.result import CheckResult, CheckStatus, ProfileResult, ScanResult


class ConsoleReporter:
    """Reporter that outputs to the console using Rich."""

    def __init__(self):
        self.console = Console()

    def report_profile(self, profile: ProfileResult) -> None:
        """Display a profile result."""
        self.console.print(
            Panel(
                f"[bold]Source:[/bold] {profile.source}\n"
                f"[bold]Rows:[/bold] {profile.row_count:,}\n"
                f"[bold]Columns:[/bold] {profile.column_count}",
                title="Profile Summary",
            )
        )

        # Column table
        table = Table(title="Columns")
        table.add_column("Name", style="cyan")
        table.add_column("Type")
        table.add_column("Nulls %", justify="right")
        table.add_column("Unique %", justify="right")

        for col in profile.columns:
            table.add_row(
                col.name,
                col.dtype,
                f"{col.null_percent:.1f}%",
                f"{col.unique_percent:.1f}%",
            )

        self.console.print(table)

    def report_scan(self, scan: ScanResult) -> None:
        """Display a scan result."""
        status_color = "green" if scan.passed else "red"

        self.console.print(
            Panel(
                f"[bold]Source:[/bold] {scan.source}\n"
                f"[bold]Rows:[/bold] {scan.row_count:,}\n"
                f"[bold]Checks:[/bold] {scan.checks_passed}/{scan.checks_run} passed "
                f"([{status_color}]{scan.pass_rate:.1f}%[/{status_color}])",
                title="Scan Summary",
            )
        )

        if scan.results:
            table = Table(title="Check Results")
            table.add_column("Check", style="cyan")
            table.add_column("Status", justify="center")
            table.add_column("Value")
            table.add_column("Message")

            for result in scan.results:
                status_style = {
                    CheckStatus.PASSED: "[green]PASS[/green]",
                    CheckStatus.FAILED: "[red]FAIL[/red]",
                    CheckStatus.WARNING: "[yellow]WARN[/yellow]",
                    CheckStatus.ERROR: "[red]ERROR[/red]",
                }
                table.add_row(
                    result.name,
                    status_style.get(result.status, str(result.status)),
                    str(result.actual_value),
                    result.message,
                )

            self.console.print(table)

    def report_check(self, result: CheckResult) -> None:
        """Display a single check result."""
        if result.passed:
            self.console.print(f"[green]PASS[/green] {result.name}: {result.message}")
        else:
            self.console.print(f"[red]FAIL[/red] {result.name}: {result.message}")
