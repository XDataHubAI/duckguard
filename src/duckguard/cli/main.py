"""DuckGuard CLI - Command line interface for data quality validation.

A modern, beautiful CLI for data quality that just works.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.syntax import Syntax
from rich.table import Table

from duckguard import __version__

app = typer.Typer(
    name="duckguard",
    help="DuckGuard - Data quality that just works. Fast, simple, Pythonic.",
    add_completion=False,
    rich_markup_mode="rich",
)
console = Console()


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        console.print(
            Panel(
                f"[bold blue]DuckGuard[/bold blue] v{__version__}\n"
                "[dim]The fast, simple data quality tool[/dim]",
                border_style="blue",
            )
        )
        raise typer.Exit()


@app.callback()
def main(
    version: bool | None = typer.Option(
        None,
        "--version",
        "-v",
        callback=version_callback,
        is_eager=True,
        help="Show version and exit.",
    ),
) -> None:
    """DuckGuard - Data quality made clear."""
    pass


@app.command()
def check(
    source: str = typer.Argument(..., help="Path to file or connection string"),
    config: str | None = typer.Option(
        None, "--config", "-c", help="Path to duckguard.yaml rules file"
    ),
    table: str | None = typer.Option(None, "--table", "-t", help="Table name (for databases)"),
    not_null: list[str] | None = typer.Option(
        None, "--not-null", "-n", help="Columns that must not be null"
    ),
    unique: list[str] | None = typer.Option(
        None, "--unique", "-u", help="Columns that must be unique"
    ),
    output: str | None = typer.Option(None, "--output", "-o", help="Output file (json)"),
    verbose: bool = typer.Option(False, "--verbose", "-V", help="Verbose output"),
) -> None:
    """
    Run data quality checks on a data source.

    [bold]Examples:[/bold]
        duckguard check data.csv
        duckguard check data.csv --not-null id --unique email
        duckguard check data.csv --config duckguard.yaml
        duckguard check postgres://localhost/db --table orders
    """
    from duckguard.connectors import connect
    from duckguard.core.scoring import score
    from duckguard.rules import execute_rules, load_rules

    console.print(f"\n[bold blue]DuckGuard[/bold blue] Checking: [cyan]{source}[/cyan]\n")

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True,
        ) as progress:
            progress.add_task("Connecting to data source...", total=None)
            dataset = connect(source, table=table)

        # Display basic info
        info_table = Table(show_header=False, box=None, padding=(0, 2))
        info_table.add_column("", style="dim")
        info_table.add_column("")
        info_table.add_row("Rows", f"[green]{dataset.row_count:,}[/green]")
        info_table.add_row("Columns", f"[green]{dataset.column_count}[/green]")
        console.print(info_table)
        console.print()

        # Execute checks
        if config:
            # Use YAML rules
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
                transient=True,
            ) as progress:
                progress.add_task("Running checks...", total=None)
                ruleset = load_rules(config)
                result = execute_rules(ruleset, dataset=dataset)

            _display_execution_result(result, verbose)

        else:
            # Quick checks from CLI arguments
            results = []

            # Row count check
            results.append(
                ("Row count > 0", dataset.row_count > 0, f"{dataset.row_count:,} rows", None)
            )

            # Not null checks
            if not_null:
                for col_name in not_null:
                    if col_name in dataset.columns:
                        col = dataset[col_name]
                        passed = col.null_count == 0
                        results.append(
                            (
                                f"{col_name} not null",
                                passed,
                                f"{col.null_count:,} nulls ({col.null_percent:.1f}%)",
                                col_name,
                            )
                        )
                    else:
                        results.append(
                            (f"{col_name} not null", False, "Column not found", col_name)
                        )

            # Unique checks
            if unique:
                for col_name in unique:
                    if col_name in dataset.columns:
                        col = dataset[col_name]
                        passed = col.unique_percent == 100
                        dup_count = col.total_count - col.unique_count
                        results.append(
                            (
                                f"{col_name} unique",
                                passed,
                                f"{col.unique_percent:.1f}% unique ({dup_count:,} duplicates)",
                                col_name,
                            )
                        )
                    else:
                        results.append((f"{col_name} unique", False, "Column not found", col_name))

            _display_quick_results(results)

        # Calculate quality score
        quality = score(dataset)
        _display_quality_score(quality)

        # Output to file
        if output:
            _save_results(output, dataset, results if not config else None)
            console.print(f"\n[dim]Results saved to {output}[/dim]")

        # Exit with error if any checks failed
        if config and not result.passed:
            raise typer.Exit(1)
        elif not config and not all(r[1] for r in results):
            raise typer.Exit(1)

    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)


@app.command()
def discover(
    source: str = typer.Argument(..., help="Path to file or connection string"),
    table: str | None = typer.Option(None, "--table", "-t", help="Table name"),
    output: str | None = typer.Option(
        None, "--output", "-o", help="Output file for rules (duckguard.yaml)"
    ),
    format: str = typer.Option("yaml", "--format", "-f", help="Output format: yaml, python"),
) -> None:
    """
    Discover data and auto-generate validation rules.

    Analyzes your data and suggests appropriate validation rules.

    [bold]Examples:[/bold]
        duckguard discover data.csv
        duckguard discover data.csv --output duckguard.yaml
        duckguard discover postgres://localhost/db --table users
    """
    from duckguard.connectors import connect
    from duckguard.rules import generate_rules
    from duckguard.rules.generator import ruleset_to_yaml
    from duckguard.semantic import SemanticAnalyzer

    console.print(f"\n[bold blue]DuckGuard[/bold blue] Discovering: [cyan]{source}[/cyan]\n")

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True,
        ) as progress:
            _task = progress.add_task("Analyzing data...", total=None)  # noqa: F841
            dataset = connect(source, table=table)

            # Semantic analysis
            analyzer = SemanticAnalyzer()
            analysis = analyzer.analyze(dataset)

            # Generate rules (as RuleSet object, not YAML string)
            ruleset = generate_rules(dataset, as_yaml=False)

        # Display discovery results
        _display_discovery_results(analysis, ruleset)

        # Output
        if output:
            yaml_content = ruleset_to_yaml(ruleset)
            Path(output).write_text(yaml_content, encoding="utf-8")
            console.print(f"\n[green]SAVED[/green] Rules saved to [cyan]{output}[/cyan]")
            console.print(f"[dim]Run: duckguard check {source} --config {output}[/dim]")
        else:
            # Display YAML
            yaml_content = ruleset_to_yaml(ruleset)
            console.print(
                Panel(
                    Syntax(yaml_content, "yaml", theme="monokai"),
                    title="Generated Rules (duckguard.yaml)",
                    border_style="green",
                )
            )

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command(name="profile")
def profile_command(
    source: str = typer.Argument(..., help="Path to file or connection string"),
    table: str | None = typer.Option(None, "--table", "-t", help="Table name (for databases)"),
    deep: bool = typer.Option(
        False, "--deep", "-d", help="Enable deep profiling (distribution, outliers)"
    ),
    output: str | None = typer.Option(None, "--output", "-o", help="Output file (json)"),
    output_format: str = typer.Option("table", "--format", "-f", help="Output format: table, json"),
) -> None:
    """
    Profile a data source and suggest validation rules.

    Analyzes data patterns, statistics, and quality to generate
    a comprehensive profile with rule suggestions.

    [bold]Examples:[/bold]
        duckguard profile data.csv
        duckguard profile data.csv --deep
        duckguard profile data.csv --format json
        duckguard profile postgres://localhost/db --table orders
    """
    import json as json_module

    from duckguard.connectors import connect
    from duckguard.profiler import AutoProfiler

    if output_format != "json":
        console.print(f"\n[bold blue]DuckGuard[/bold blue] Profiling: [cyan]{source}[/cyan]\n")

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True,
        ) as progress:
            _task = progress.add_task("Profiling data...", total=None)  # noqa: F841
            dataset = connect(source, table=table)
            profiler = AutoProfiler(deep=deep)
            result = profiler.profile(dataset)

        if output_format == "json":
            data = _profile_to_dict(result)
            json_str = json_module.dumps(data, indent=2, default=str)
            if output:
                Path(output).write_text(json_str, encoding="utf-8")
                console.print(f"[green]SAVED[/green] Profile saved to [cyan]{output}[/cyan]")
            else:
                print(json_str)
        else:
            _display_profile_result(result)

            if output:
                data = _profile_to_dict(result)
                Path(output).write_text(
                    json_module.dumps(data, indent=2, default=str), encoding="utf-8"
                )
                console.print(f"\n[green]SAVED[/green] Profile saved to [cyan]{output}[/cyan]")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


def _display_profile_result(result: Any) -> None:
    """Display profiling results in a rich table."""
    _grade_colors = {"A": "green", "B": "blue", "C": "yellow", "D": "orange1", "F": "red"}

    summary_parts = [
        f"Rows: [cyan]{result.row_count:,}[/cyan]",
        f"Columns: [cyan]{result.column_count}[/cyan]",
        f"Rules Suggested: [cyan]{len(result.suggested_rules)}[/cyan]",
    ]
    if result.overall_quality_score is not None:
        color = _grade_colors.get(result.overall_quality_grade, "white")
        summary_parts.append(
            f"Quality: [{color}]{result.overall_quality_score:.0f}/100 "
            f"({result.overall_quality_grade})[/{color}]"
        )

    console.print(Panel("\n".join(summary_parts), title="Profile Summary", border_style="blue"))
    console.print()

    col_table = Table(title="Column Profiles")
    col_table.add_column("Column", style="cyan")
    col_table.add_column("Type", style="magenta")
    col_table.add_column("Nulls", justify="right")
    col_table.add_column("Unique", justify="right")
    col_table.add_column("Min", justify="right")
    col_table.add_column("Max", justify="right")
    col_table.add_column("Grade", justify="center")
    col_table.add_column("Rules", justify="right")

    for col in result.columns:
        grade_str = ""
        if col.quality_grade:
            color = _grade_colors.get(col.quality_grade, "white")
            grade_str = f"[{color}]{col.quality_grade}[/{color}]"

        col_table.add_row(
            col.name,
            col.dtype,
            f"{col.null_percent:.1f}%",
            f"{col.unique_percent:.1f}%",
            str(col.min_value) if col.min_value is not None else "-",
            str(col.max_value) if col.max_value is not None else "-",
            grade_str or "-",
            str(len(col.suggested_rules)),
        )

    console.print(col_table)

    if result.suggested_rules:
        console.print()
        console.print(f"[bold]Suggested Rules ({len(result.suggested_rules)}):[/bold]")
        for rule in result.suggested_rules[:20]:
            console.print(f"  {rule}")
        if len(result.suggested_rules) > 20:
            console.print(f"  [dim]... and {len(result.suggested_rules) - 20} more[/dim]")


def _profile_to_dict(result: Any) -> dict[str, Any]:
    """Convert ProfileResult to a JSON-serializable dict."""

    return {
        "source": result.source,
        "row_count": result.row_count,
        "column_count": result.column_count,
        "overall_quality_score": result.overall_quality_score,
        "overall_quality_grade": result.overall_quality_grade,
        "columns": [
            {
                "name": col.name,
                "dtype": col.dtype,
                "null_count": col.null_count,
                "null_percent": col.null_percent,
                "unique_count": col.unique_count,
                "unique_percent": col.unique_percent,
                "min_value": col.min_value,
                "max_value": col.max_value,
                "mean_value": col.mean_value,
                "stddev_value": col.stddev_value,
                "median_value": col.median_value,
                "p25_value": col.p25_value,
                "p75_value": col.p75_value,
                "quality_score": col.quality_score,
                "quality_grade": col.quality_grade,
                "distribution_type": col.distribution_type,
                "skewness": col.skewness,
                "kurtosis": col.kurtosis,
                "is_normal": col.is_normal,
                "outlier_count": col.outlier_count,
                "outlier_percentage": col.outlier_percentage,
                "suggested_rules": col.suggested_rules,
            }
            for col in result.columns
        ],
        "suggested_rules": result.suggested_rules,
    }


@app.command()
def contract(
    action: str = typer.Argument(..., help="Action: generate, validate, diff"),
    source: str = typer.Argument(None, help="Data source or contract file"),
    contract_file: str | None = typer.Option(None, "--contract", "-c", help="Contract file path"),
    output: str | None = typer.Option(None, "--output", "-o", help="Output file"),
    strict: bool = typer.Option(False, "--strict", help="Strict validation mode"),
) -> None:
    """
    Manage data contracts.

    [bold]Actions:[/bold]
        generate  - Generate a contract from data
        validate  - Validate data against a contract
        diff      - Compare two contract versions

    [bold]Examples:[/bold]
        duckguard contract generate data.csv --output orders.contract.yaml
        duckguard contract validate data.csv --contract orders.contract.yaml
        duckguard contract diff old.contract.yaml new.contract.yaml
    """
    from duckguard.contracts import (
        diff_contracts,
        generate_contract,
        load_contract,
        validate_contract,
    )
    from duckguard.contracts.loader import contract_to_yaml

    try:
        if action == "generate":
            if not source:
                console.print("[red]Error:[/red] Source required for generate")
                raise typer.Exit(1)

            console.print(
                f"\n[bold blue]DuckGuard[/bold blue] Generating contract for: [cyan]{source}[/cyan]\n"
            )

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
                transient=True,
            ) as progress:
                progress.add_task("Analyzing data...", total=None)
                contract_obj = generate_contract(source)

            _display_contract(contract_obj)

            if output:
                yaml_content = contract_to_yaml(contract_obj)
                Path(output).write_text(yaml_content, encoding="utf-8")
                console.print(f"\n[green]SAVED[/green] Contract saved to [cyan]{output}[/cyan]")

        elif action == "validate":
            if not source or not contract_file:
                console.print("[red]Error:[/red] Both source and --contract required for validate")
                raise typer.Exit(1)

            console.print("\n[bold blue]DuckGuard[/bold blue] Validating against contract\n")

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
                transient=True,
            ) as progress:
                progress.add_task("Validating...", total=None)
                contract_obj = load_contract(contract_file)
                result = validate_contract(contract_obj, source, strict_mode=strict)

            _display_contract_validation(result)

            if not result.passed:
                raise typer.Exit(1)

        elif action == "diff":
            if not source or not contract_file:
                console.print("[red]Error:[/red] Two contract files required for diff")
                raise typer.Exit(1)

            old_contract = load_contract(source)
            new_contract = load_contract(contract_file)

            diff_result = diff_contracts(old_contract, new_contract)
            _display_contract_diff(diff_result)

        else:
            console.print(f"[red]Error:[/red] Unknown action: {action}")
            raise typer.Exit(1)

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def anomaly(
    source: str = typer.Argument(..., help="Path to file or connection string"),
    table: str | None = typer.Option(None, "--table", "-t", help="Table name"),
    method: str = typer.Option(
        "zscore", "--method", "-m", help="Method: zscore, iqr, percent_change, baseline, ks_test"
    ),
    threshold: float | None = typer.Option(None, "--threshold", help="Detection threshold"),
    columns: list[str] | None = typer.Option(
        None, "--column", "-c", help="Specific columns to check"
    ),
    learn_baseline: bool = typer.Option(
        False, "--learn-baseline", "-L", help="Learn and store baseline from current data"
    ),
) -> None:
    """
    Detect anomalies in data.

    [bold]Methods:[/bold]
        zscore         - Z-score based detection (default)
        iqr            - Interquartile range detection
        percent_change - Percent change from baseline
        baseline       - Compare to learned baseline (ML)
        ks_test        - Distribution drift detection (ML)

    [bold]Examples:[/bold]
        duckguard anomaly data.csv
        duckguard anomaly data.csv --method iqr --threshold 2.0
        duckguard anomaly data.csv --column amount --column quantity
        duckguard anomaly data.csv --learn-baseline     # Store baseline
        duckguard anomaly data.csv --method baseline    # Compare to baseline
        duckguard anomaly data.csv --method ks_test     # Detect drift
    """
    from duckguard.anomaly import detect_anomalies
    from duckguard.connectors import connect

    console.print(
        f"\n[bold blue]DuckGuard[/bold blue] Detecting anomalies in: [cyan]{source}[/cyan]\n"
    )

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True,
        ) as progress:
            if learn_baseline:
                progress.add_task("Learning baseline...", total=None)
            else:
                progress.add_task("Analyzing data...", total=None)

            dataset = connect(source, table=table)

            # Handle baseline learning
            if learn_baseline:
                from duckguard.anomaly import BaselineMethod
                from duckguard.history import HistoryStorage

                storage = HistoryStorage()
                baseline_method = BaselineMethod(storage=storage)

                # Get numeric columns to learn baselines for
                target_columns = columns if columns else dataset.columns
                learned = 0

                for col_name in target_columns:
                    col = dataset[col_name]
                    if col.mean is not None:  # Numeric column
                        values = col.values
                        baseline_method.fit(values)
                        baseline_method.save_baseline(source, col_name)
                        learned += 1

                console.print(f"[green]LEARNED[/green] Baselines stored for {learned} columns")
                console.print(
                    "[dim]Use --method baseline to compare against stored baselines[/dim]"
                )
                return

            # Regular anomaly detection
            report = detect_anomalies(
                dataset,
                method=method,
                threshold=threshold,
                columns=columns,
            )

        _display_anomaly_report(report)

        if report.has_anomalies:
            raise typer.Exit(1)

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def info(
    source: str = typer.Argument(..., help="Path to file or connection string"),
    table: str | None = typer.Option(None, "--table", "-t", help="Table name"),
) -> None:
    """
    Display information about a data source.

    [bold]Examples:[/bold]
        duckguard info data.csv
        duckguard info postgres://localhost/db --table users
    """
    from duckguard.connectors import connect
    from duckguard.semantic import SemanticAnalyzer

    try:
        dataset = connect(source, table=table)
        analyzer = SemanticAnalyzer()

        console.print(Panel(f"[bold]{dataset.name}[/bold]", border_style="blue"))

        # Basic info
        info_table = Table(show_header=False, box=None)
        info_table.add_column("Property", style="cyan")
        info_table.add_column("Value", style="green")

        info_table.add_row("Source", source)
        info_table.add_row("Rows", f"{dataset.row_count:,}")
        info_table.add_row("Columns", str(dataset.column_count))

        console.print(info_table)
        console.print()

        # Column details
        col_table = Table(title="Columns")
        col_table.add_column("Name", style="cyan")
        col_table.add_column("Type", style="magenta")
        col_table.add_column("Nulls", justify="right")
        col_table.add_column("Unique", justify="right")
        col_table.add_column("Semantic", style="yellow")

        for col_name in dataset.columns[:20]:
            col = dataset[col_name]
            col_analysis = analyzer.analyze_column(dataset, col_name)

            sem_type = col_analysis.semantic_type.value
            if sem_type == "unknown":
                sem_type = "-"
            if col_analysis.is_pii:
                sem_type = f"[PII] {sem_type}"

            col_table.add_row(
                col_name,
                "numeric" if col.mean is not None else "string",
                f"{col.null_percent:.1f}%",
                f"{col.unique_percent:.1f}%",
                sem_type,
            )

        if dataset.column_count > 20:
            col_table.add_row(f"... and {dataset.column_count - 20} more", "", "", "", "")

        console.print(col_table)

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


# Helper display functions


def _display_execution_result(result, verbose: bool = False) -> None:
    """Display rule execution results."""
    table = Table(title="Validation Results")
    table.add_column("Check", style="cyan")
    table.add_column("Status", justify="center")
    table.add_column("Details")

    for check_result in result.results:
        if check_result.passed:
            status = "[green]PASS[/green]"
        elif check_result.severity.value == "warning":
            status = "[yellow]WARN[/yellow]"
        else:
            status = "[red]FAIL[/red]"

        col_str = f"[{check_result.column}] " if check_result.column else ""
        table.add_row(
            f"{col_str}{check_result.check.type.value}",
            status,
            check_result.message[:60],
        )

    console.print(table)

    # Summary
    console.print()
    if result.passed:
        console.print(f"[green]All {result.total_checks} checks passed[/green]")
    else:
        console.print(
            f"[red]{result.failed_count} failed[/red], "
            f"[yellow]{result.warning_count} warnings[/yellow], "
            f"[green]{result.passed_count} passed[/green]"
        )


def _display_quick_results(results: list) -> None:
    """Display quick check results."""
    table = Table()
    table.add_column("Check", style="cyan")
    table.add_column("Status", justify="center")
    table.add_column("Details")

    for check_name, passed, details, _ in results:
        status = "[green]PASS[/green]" if passed else "[red]FAIL[/red]"
        table.add_row(check_name, status, details)

    console.print(table)


def _display_quality_score(quality) -> None:
    """Display quality score."""
    grade_colors = {"A": "green", "B": "blue", "C": "yellow", "D": "orange1", "F": "red"}
    color = grade_colors.get(quality.grade, "white")

    console.print()
    console.print(
        Panel(
            f"[bold]Quality Score: [{color}]{quality.overall:.0f}/100[/{color}] "
            f"(Grade: [{color}]{quality.grade}[/{color}])[/bold]",
            border_style=color,
        )
    )


def _display_discovery_results(analysis, ruleset) -> None:
    """Display discovery results."""
    # Summary
    console.print(f"[bold]Discovered {analysis.column_count} columns[/bold]\n")

    # PII warning
    if analysis.pii_columns:
        console.print(
            Panel(
                "[yellow]WARNING: PII Detected[/yellow]\n"
                + "\n".join(f"  - {col}" for col in analysis.pii_columns),
                border_style="yellow",
            )
        )
        console.print()

    # Column analysis table
    table = Table(title="Column Analysis")
    table.add_column("Column", style="cyan")
    table.add_column("Semantic Type", style="magenta")
    table.add_column("Suggested Rules")

    for col in analysis.columns[:15]:
        sem = col.semantic_type.value
        if col.is_pii:
            sem = f"[PII] {sem}"

        rules = ", ".join(col.suggested_validations[:3])
        if len(col.suggested_validations) > 3:
            rules += f" (+{len(col.suggested_validations) - 3})"

        table.add_row(col.name, sem, rules or "-")

    if len(analysis.columns) > 15:
        table.add_row(f"... and {len(analysis.columns) - 15} more", "", "")

    console.print(table)
    console.print()
    console.print(f"[dim]Generated {ruleset.total_checks} validation rules[/dim]")


def _display_contract(contract) -> None:
    """Display contract details."""
    console.print(f"[bold]Contract: {contract.name}[/bold] v{contract.version}\n")

    # Schema
    table = Table(title="Schema")
    table.add_column("Field", style="cyan")
    table.add_column("Type", style="magenta")
    table.add_column("Required")
    table.add_column("Unique")
    table.add_column("PII")

    for field_obj in contract.schema[:15]:
        type_str = field_obj.type.value if hasattr(field_obj.type, "value") else str(field_obj.type)
        table.add_row(
            field_obj.name,
            type_str,
            "Y" if field_obj.required else "",
            "Y" if field_obj.unique else "",
            "[PII]" if field_obj.pii else "",
        )

    console.print(table)

    # Quality SLA
    if contract.quality:
        console.print("\n[bold]Quality SLA:[/bold]")
        if contract.quality.completeness:
            console.print(f"  - Completeness: {contract.quality.completeness}%")
        if contract.quality.row_count_min:
            console.print(f"  - Min rows: {contract.quality.row_count_min:,}")


def _display_contract_validation(result) -> None:
    """Display contract validation results."""
    status = "[green]PASSED[/green]" if result.passed else "[red]FAILED[/red]"
    console.print(f"Contract: [bold]{result.contract.name}[/bold] v{result.contract.version}")
    console.print(f"Status: {status}\n")

    if result.violations:
        table = Table(title="Violations")
        table.add_column("Type", style="magenta")
        table.add_column("Field", style="cyan")
        table.add_column("Message")
        table.add_column("Severity")

        for v in result.violations[:20]:
            sev_style = {"error": "red", "warning": "yellow", "info": "dim"}.get(
                v.severity.value, "white"
            )
            table.add_row(
                v.type.value,
                v.field or "-",
                v.message[:50],
                f"[{sev_style}]{v.severity.value}[/{sev_style}]",
            )

        console.print(table)
    else:
        console.print("[green]No violations found[/green]")


def _display_contract_diff(diff) -> None:
    """Display contract diff."""
    console.print("[bold]Comparing contracts[/bold]")
    console.print(f"  Old: v{diff.old_contract.version}")
    console.print(f"  New: v{diff.new_contract.version}\n")

    if not diff.has_changes:
        console.print("[green]No changes detected[/green]")
        return

    console.print(f"[bold]{len(diff.changes)} changes detected[/bold]\n")

    if diff.breaking_changes:
        console.print("[red bold]Breaking Changes:[/red bold]")
        for change in diff.breaking_changes:
            console.print(f"  [red]X[/red] {change.message}")
        console.print()

    if diff.minor_changes:
        console.print("[yellow bold]Minor Changes:[/yellow bold]")
        for change in diff.minor_changes:
            console.print(f"  [yellow]![/yellow] {change.message}")
        console.print()

    if diff.non_breaking_changes:
        console.print("[dim]Non-breaking Changes:[/dim]")
        for change in diff.non_breaking_changes:
            console.print(f"  - {change.message}")

    console.print(f"\n[dim]Suggested version bump: {diff.suggest_version_bump()}[/dim]")


def _display_anomaly_report(report) -> None:
    """Display anomaly detection report."""
    if not report.has_anomalies:
        console.print("[green]No anomalies detected[/green]")
        return

    console.print(
        f"[yellow bold]WARNING: {report.anomaly_count} anomalies detected[/yellow bold]\n"
    )

    table = Table(title="Anomalies")
    table.add_column("Column", style="cyan")
    table.add_column("Type", style="magenta")
    table.add_column("Score", justify="right")
    table.add_column("Message")

    for anomaly in report.get_anomalies():
        table.add_row(
            anomaly.column or "-",
            anomaly.anomaly_type.value,
            f"{anomaly.score:.2f}",
            anomaly.message[:50],
        )

    console.print(table)


def _save_results(output: str, dataset, results) -> None:
    """Save results to file."""
    import json

    data = {
        "source": dataset.source,
        "row_count": dataset.row_count,
        "column_count": dataset.column_count,
        "columns": dataset.columns,
    }

    if results:
        data["checks"] = [{"name": r[0], "passed": r[1], "details": r[2]} for r in results]

    Path(output).write_text(json.dumps(data, indent=2))


@app.command()
def history(
    source: str | None = typer.Argument(None, help="Data source to query history for (optional)"),
    last: str = typer.Option("30d", "--last", "-l", help="Time period: 7d, 30d, 90d"),
    output_format: str = typer.Option("table", "--format", "-f", help="Output format: table, json"),
    trend: bool = typer.Option(False, "--trend", "-t", help="Show quality trend analysis"),
    db_path: str | None = typer.Option(None, "--db", help="Path to history database"),
) -> None:
    """
    Query historical validation results.

    Shows past validation runs and quality score trends over time.

    [bold]Examples:[/bold]
        duckguard history                        # Show all recent runs
        duckguard history data.csv               # Show runs for specific source
        duckguard history data.csv --last 7d    # Last 7 days
        duckguard history data.csv --trend      # Show trend analysis
        duckguard history --format json         # Output as JSON
    """
    import json as json_module

    from duckguard.history import HistoryStorage, TrendAnalyzer

    try:
        storage = HistoryStorage(db_path=db_path)

        # Parse time period
        days = int(last.rstrip("d"))

        if trend and source:
            # Show trend analysis
            console.print(
                f"\n[bold blue]DuckGuard[/bold blue] Trend Analysis: [cyan]{source}[/cyan]\n"
            )

            analyzer = TrendAnalyzer(storage)
            analysis = analyzer.analyze(source, days=days)

            if analysis.total_runs == 0:
                console.print("[yellow]No historical data found for this source.[/yellow]")
                console.print("[dim]Run some validations first, then check history.[/dim]")
                return

            # Display trend summary
            trend_color = {
                "improving": "green",
                "declining": "red",
                "stable": "yellow",
            }.get(analysis.score_trend, "white")

            trend_symbol = {
                "improving": "[+]",
                "declining": "[-]",
                "stable": "[=]",
            }.get(analysis.score_trend, "[=]")

            console.print(
                Panel(
                    f"[bold]Quality Trend: [{trend_color}]{trend_symbol} {analysis.score_trend.upper()}[/{trend_color}][/bold]\n\n"
                    f"Current Score: [cyan]{analysis.current_score:.1f}%[/cyan]\n"
                    f"Average Score: [cyan]{analysis.average_score:.1f}%[/cyan]\n"
                    f"Min/Max: [dim]{analysis.min_score:.1f}% - {analysis.max_score:.1f}%[/dim]\n"
                    f"Change: [{trend_color}]{analysis.trend_change:+.1f}%[/{trend_color}]\n"
                    f"Total Runs: [cyan]{analysis.total_runs}[/cyan]\n"
                    f"Pass Rate: [cyan]{analysis.pass_rate:.1f}%[/cyan]",
                    title=f"Last {days} Days",
                    border_style=trend_color,
                )
            )

            if analysis.anomalies:
                console.print(
                    f"\n[yellow]Anomalies detected on: {', '.join(analysis.anomalies)}[/yellow]"
                )

            # Show daily data if available
            if analysis.daily_data and len(analysis.daily_data) <= 14:
                console.print()
                table = Table(title="Daily Quality Scores")
                table.add_column("Date", style="cyan")
                table.add_column("Score", justify="right")
                table.add_column("Runs", justify="right")
                table.add_column("Pass Rate", justify="right")

                for day in analysis.daily_data:
                    pass_rate = (day.passed_count / day.run_count * 100) if day.run_count > 0 else 0
                    score_style = (
                        "green"
                        if day.avg_score >= 80
                        else "yellow" if day.avg_score >= 60 else "red"
                    )
                    table.add_row(
                        day.date,
                        f"[{score_style}]{day.avg_score:.1f}%[/{score_style}]",
                        str(day.run_count),
                        f"{pass_rate:.0f}%",
                    )

                console.print(table)

        else:
            # Show run history
            if source:
                console.print(
                    f"\n[bold blue]DuckGuard[/bold blue] History: [cyan]{source}[/cyan]\n"
                )
                runs = storage.get_runs(source, limit=20)
            else:
                console.print("\n[bold blue]DuckGuard[/bold blue] Recent Validation History\n")
                runs = storage.get_runs(limit=20)

            if not runs:
                console.print("[yellow]No historical data found.[/yellow]")
                console.print("[dim]Run some validations first, then check history.[/dim]")
                return

            if output_format == "json":
                # JSON output
                data = [
                    {
                        "run_id": run.run_id,
                        "source": run.source,
                        "started_at": run.started_at.isoformat(),
                        "quality_score": run.quality_score,
                        "passed": run.passed,
                        "total_checks": run.total_checks,
                        "passed_count": run.passed_count,
                        "failed_count": run.failed_count,
                        "warning_count": run.warning_count,
                    }
                    for run in runs
                ]
                console.print(json_module.dumps(data, indent=2))
            else:
                # Table output
                table = Table(title=f"Validation Runs (Last {days} days)")
                table.add_column("Date", style="cyan")
                table.add_column("Source", style="dim", max_width=40)
                table.add_column("Score", justify="right")
                table.add_column("Status", justify="center")
                table.add_column("Checks", justify="right")

                for run in runs:
                    score_style = (
                        "green"
                        if run.quality_score >= 80
                        else "yellow" if run.quality_score >= 60 else "red"
                    )
                    status = "[green]PASS[/green]" if run.passed else "[red]FAIL[/red]"

                    table.add_row(
                        run.started_at.strftime("%Y-%m-%d %H:%M"),
                        run.source[:40],
                        f"[{score_style}]{run.quality_score:.1f}%[/{score_style}]",
                        status,
                        f"{run.passed_count}/{run.total_checks}",
                    )

                console.print(table)

                # Show sources summary
                sources = storage.get_sources()
                if len(sources) > 1:
                    console.print(f"\n[dim]Tracked sources: {len(sources)}[/dim]")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def report(
    source: str = typer.Argument(..., help="Data source path or connection string"),
    config: str | None = typer.Option(
        None, "--config", "-c", help="Path to duckguard.yaml rules file"
    ),
    table: str | None = typer.Option(None, "--table", "-t", help="Table name (for databases)"),
    output_format: str = typer.Option("html", "--format", "-f", help="Output format: html, pdf"),
    output: str = typer.Option("report.html", "--output", "-o", help="Output file path"),
    title: str = typer.Option("DuckGuard Data Quality Report", "--title", help="Report title"),
    include_passed: bool = typer.Option(
        True, "--include-passed/--no-passed", help="Include passed checks"
    ),
    store: bool = typer.Option(False, "--store", "-s", help="Store results in history"),
) -> None:
    """
    Generate a data quality report (HTML or PDF).

    Runs validation checks and generates a beautiful, shareable report.

    [bold]Examples:[/bold]
        duckguard report data.csv
        duckguard report data.csv --format pdf --output report.pdf
        duckguard report data.csv --config rules.yaml --title "Orders Quality"
        duckguard report data.csv --store  # Also save to history
    """
    from duckguard.connectors import connect
    from duckguard.reports import generate_html_report, generate_pdf_report
    from duckguard.rules import execute_rules, generate_rules, load_rules

    # Determine output path based on format
    if output == "report.html" and output_format == "pdf":
        output = "report.pdf"

    console.print(f"\n[bold blue]DuckGuard[/bold blue] Generating {output_format.upper()} report\n")

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True,
        ) as progress:
            progress.add_task("Connecting to data source...", total=None)
            dataset = connect(source, table=table)

        console.print(f"[dim]Source: {source}[/dim]")
        console.print(f"[dim]Rows: {dataset.row_count:,} | Columns: {dataset.column_count}[/dim]\n")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True,
        ) as progress:
            progress.add_task("Running validation checks...", total=None)

            if config:
                ruleset = load_rules(config)
            else:
                ruleset = generate_rules(dataset, as_yaml=False)

            result = execute_rules(ruleset, dataset=dataset)

        # Store in history if requested
        if store:
            from duckguard.history import HistoryStorage

            storage = HistoryStorage()
            run_id = storage.store(result)
            console.print(f"[dim]Stored in history: {run_id[:8]}...[/dim]\n")

        # Display summary
        status = "[green]PASSED[/green]" if result.passed else "[red]FAILED[/red]"
        console.print(f"Validation: {status}")
        console.print(f"Quality Score: [cyan]{result.quality_score:.1f}%[/cyan]")
        console.print(f"Checks: {result.passed_count}/{result.total_checks} passed\n")

        # Generate report
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True,
        ) as progress:
            progress.add_task(f"Generating {output_format.upper()} report...", total=None)

            if output_format.lower() == "pdf":
                generate_pdf_report(result, output, title=title, include_passed=include_passed)
            else:
                generate_html_report(result, output, title=title, include_passed=include_passed)

        console.print(f"[green]SAVED[/green] Report saved to [cyan]{output}[/cyan]")
        console.print("[dim]Open in browser to view the report[/dim]")

    except ImportError as e:
        if "weasyprint" in str(e).lower():
            console.print("[red]Error:[/red] PDF generation requires weasyprint.")
            console.print("[dim]Install with: pip install duckguard[reports][/dim]")
        else:
            console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def freshness(
    source: str = typer.Argument(..., help="Data source path"),
    column: str | None = typer.Option(None, "--column", "-c", help="Timestamp column to check"),
    max_age: str = typer.Option(
        "24h", "--max-age", "-m", help="Maximum acceptable age: 1h, 6h, 24h, 7d"
    ),
    output_format: str = typer.Option("table", "--format", "-f", help="Output format: table, json"),
) -> None:
    """
    Check data freshness.

    Monitors how recently data was updated using file modification time
    or timestamp columns.

    [bold]Examples:[/bold]
        duckguard freshness data.csv
        duckguard freshness data.csv --max-age 6h
        duckguard freshness data.csv --column updated_at
        duckguard freshness data.csv --format json
    """
    import json as json_module

    from duckguard.connectors import connect
    from duckguard.freshness import FreshnessMonitor
    from duckguard.freshness.monitor import parse_age_string

    console.print(f"\n[bold blue]DuckGuard[/bold blue] Checking freshness: [cyan]{source}[/cyan]\n")

    try:
        threshold = parse_age_string(max_age)
        monitor = FreshnessMonitor(threshold=threshold)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True,
        ) as progress:
            progress.add_task("Checking freshness...", total=None)

            if column:
                dataset = connect(source)
                result = monitor.check_column_timestamp(dataset, column)
            else:
                # Try file mtime first, fallback to dataset
                from pathlib import Path

                if Path(source).exists():
                    result = monitor.check_file_mtime(source)
                else:
                    dataset = connect(source)
                    result = monitor.check(dataset)

        if output_format == "json":
            console.print(json_module.dumps(result.to_dict(), indent=2))
        else:
            # Display table
            status_color = "green" if result.is_fresh else "red"
            status_text = "FRESH" if result.is_fresh else "STALE"

            console.print(
                Panel(
                    f"[bold {status_color}]{status_text}[/bold {status_color}]\n\n"
                    f"Last Modified: [cyan]{result.last_modified.strftime('%Y-%m-%d %H:%M:%S') if result.last_modified else 'Unknown'}[/cyan]\n"
                    f"Age: [cyan]{result.age_human}[/cyan]\n"
                    f"Threshold: [dim]{max_age}[/dim]\n"
                    f"Method: [dim]{result.method.value}[/dim]",
                    title="Freshness Check",
                    border_style=status_color,
                )
            )

        if not result.is_fresh:
            raise typer.Exit(1)

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def schema(
    source: str = typer.Argument(..., help="Data source path"),
    action: str = typer.Option(
        "show", "--action", "-a", help="Action: show, capture, history, changes"
    ),
    table: str | None = typer.Option(None, "--table", "-t", help="Table name (for databases)"),
    output_format: str = typer.Option("table", "--format", "-f", help="Output format: table, json"),
    limit: int = typer.Option(10, "--limit", "-l", help="Number of results to show"),
) -> None:
    """
    Track schema evolution over time.

    Captures schema snapshots and detects changes between versions.

    [bold]Actions:[/bold]
        show     - Show current schema
        capture  - Capture a schema snapshot
        history  - Show schema snapshot history
        changes  - Detect changes from last snapshot

    [bold]Examples:[/bold]
        duckguard schema data.csv                    # Show current schema
        duckguard schema data.csv --action capture  # Capture snapshot
        duckguard schema data.csv --action history  # View history
        duckguard schema data.csv --action changes  # Detect changes
    """
    import json as json_module

    from duckguard.connectors import connect
    from duckguard.schema_history import SchemaChangeAnalyzer, SchemaTracker

    console.print(f"\n[bold blue]DuckGuard[/bold blue] Schema: [cyan]{source}[/cyan]\n")

    try:
        dataset = connect(source, table=table)
        tracker = SchemaTracker()
        analyzer = SchemaChangeAnalyzer()

        if action == "show":
            # Display current schema
            col_table = Table(title="Current Schema")
            col_table.add_column("Column", style="cyan")
            col_table.add_column("Type", style="magenta")
            col_table.add_column("Position", justify="right")

            ref = dataset.engine.get_source_reference(dataset.source)
            result = dataset.engine.execute(f"DESCRIBE {ref}")

            for i, row in enumerate(result.fetchall()):
                col_table.add_row(row[0], row[1], str(i))

            console.print(col_table)
            console.print(f"\n[dim]Total columns: {dataset.column_count}[/dim]")

        elif action == "capture":
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
                transient=True,
            ) as progress:
                progress.add_task("Capturing schema snapshot...", total=None)
                snapshot = tracker.capture(dataset)

            console.print(
                f"[green]CAPTURED[/green] Schema snapshot: [cyan]{snapshot.snapshot_id[:8]}...[/cyan]"
            )
            console.print(
                f"[dim]Columns: {snapshot.column_count} | Rows: {snapshot.row_count:,}[/dim]"
            )
            console.print(
                f"[dim]Captured at: {snapshot.captured_at.strftime('%Y-%m-%d %H:%M:%S')}[/dim]"
            )

        elif action == "history":
            history = tracker.get_history(source, limit=limit)

            if not history:
                console.print("[yellow]No schema history found for this source.[/yellow]")
                console.print("[dim]Use --action capture to create a snapshot first.[/dim]")
                return

            if output_format == "json":
                data = [s.to_dict() for s in history]
                console.print(json_module.dumps(data, indent=2))
            else:
                table_obj = Table(title="Schema History")
                table_obj.add_column("Snapshot ID", style="cyan")
                table_obj.add_column("Captured At", style="dim")
                table_obj.add_column("Columns", justify="right")
                table_obj.add_column("Rows", justify="right")

                for snapshot in history:
                    table_obj.add_row(
                        snapshot.snapshot_id[:8] + "...",
                        snapshot.captured_at.strftime("%Y-%m-%d %H:%M"),
                        str(snapshot.column_count),
                        f"{snapshot.row_count:,}" if snapshot.row_count else "-",
                    )

                console.print(table_obj)

        elif action == "changes":
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
                transient=True,
            ) as progress:
                progress.add_task("Detecting schema changes...", total=None)
                report = analyzer.detect_changes(dataset)

            if not report.has_changes:
                console.print("[green]No schema changes detected[/green]")
                console.print(
                    f"[dim]Snapshot captured: {report.current_snapshot.snapshot_id[:8]}...[/dim]"
                )
                return

            # Display changes
            console.print(
                f"[yellow bold]{len(report.changes)} schema changes detected[/yellow bold]\n"
            )

            if report.has_breaking_changes:
                console.print("[red bold]BREAKING CHANGES:[/red bold]")
                for change in report.breaking_changes:
                    console.print(f"  [red]X[/red] {change}")
                console.print()

            non_breaking = report.non_breaking_changes
            if non_breaking:
                console.print("[dim]Non-breaking changes:[/dim]")
                for change in non_breaking:
                    console.print(f"  - {change}")

            if report.has_breaking_changes:
                raise typer.Exit(1)

        else:
            console.print(f"[red]Error:[/red] Unknown action: {action}")
            console.print("[dim]Valid actions: show, capture, history, changes[/dim]")
            raise typer.Exit(1)

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
