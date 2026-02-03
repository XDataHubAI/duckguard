"""Message formatting utilities for notifications."""

from __future__ import annotations

from datetime import datetime

from duckguard.rules.executor import ExecutionResult


def format_results_text(result: ExecutionResult, include_passed: bool = False) -> str:
    """Format execution results as plain text.

    Args:
        result: ExecutionResult from rule execution
        include_passed: Whether to include passed checks

    Returns:
        Formatted text string
    """
    lines = []

    status = "PASSED" if result.passed else "FAILED"
    lines.append(f"DuckGuard Validation {status}")
    lines.append("=" * 40)
    lines.append(f"Source: {result.source}")
    lines.append(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"Checks: {result.passed_count}/{result.total_checks} passed")
    lines.append(f"Score: {result.quality_score:.1f}%")
    lines.append("")

    failures = result.get_failures()
    if failures:
        lines.append("FAILURES:")
        lines.append("-" * 20)
        for f in failures:
            col = f"[{f.column}]" if f.column else "[table]"
            lines.append(f"  {col} {f.message}")
            if f.details.get("failed_rows"):
                lines.append(f"    Sample: {f.details['failed_rows'][:3]}")
        lines.append("")

    warnings = result.get_warnings()
    if warnings:
        lines.append("WARNINGS:")
        lines.append("-" * 20)
        for w in warnings:
            col = f"[{w.column}]" if w.column else "[table]"
            lines.append(f"  {col} {w.message}")
        lines.append("")

    if include_passed:
        passed = [r for r in result.results if r.passed]
        if passed:
            lines.append("PASSED:")
            lines.append("-" * 20)
            for p in passed:
                col = f"[{p.column}]" if p.column else "[table]"
                lines.append(f"  {col} {p.message}")

    return "\n".join(lines)


def format_results_markdown(result: ExecutionResult, include_passed: bool = False) -> str:
    """Format execution results as Markdown.

    Args:
        result: ExecutionResult from rule execution
        include_passed: Whether to include passed checks

    Returns:
        Formatted Markdown string
    """
    lines = []

    emoji = ":white_check_mark:" if result.passed else ":x:"
    status = "PASSED" if result.passed else "FAILED"
    lines.append(f"# {emoji} DuckGuard Validation {status}")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|--------|-------|")
    lines.append(f"| Source | `{result.source}` |")
    lines.append(f"| Time | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} |")
    lines.append(f"| Checks | {result.passed_count}/{result.total_checks} passed |")
    lines.append(f"| Score | {result.quality_score:.1f}% |")
    lines.append("")

    failures = result.get_failures()
    if failures:
        lines.append("## :rotating_light: Failures")
        lines.append("")
        for f in failures:
            col = f"`{f.column}`" if f.column else "_table_"
            lines.append(f"- **{col}**: {f.message}")
            if f.details.get("failed_rows"):
                sample = f.details["failed_rows"][:3]
                lines.append(f"  - _Sample values: {sample}_")
        lines.append("")

    warnings = result.get_warnings()
    if warnings:
        lines.append("## :warning: Warnings")
        lines.append("")
        for w in warnings:
            col = f"`{w.column}`" if w.column else "_table_"
            lines.append(f"- **{col}**: {w.message}")
        lines.append("")

    if include_passed:
        passed = [r for r in result.results if r.passed]
        if passed:
            lines.append("## :white_check_mark: Passed")
            lines.append("")
            for p in passed:
                col = f"`{p.column}`" if p.column else "_table_"
                lines.append(f"- **{col}**: {p.message}")
            lines.append("")

    return "\n".join(lines)
