"""Report generation -- JSON, AI fix prompts, terminal summary."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

from rich.console import Console
from rich.table import Table

from vibe_scan import __version__

if TYPE_CHECKING:
    from vibe_scan.scanner import ScanResult

console = Console()


def write_json_report(scan_result: ScanResult, path: Path) -> None:
    """Write the full scan result as a JSON report."""
    report = {
        "version": __version__,
        "scan_metadata": {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "target": str(scan_result.project_info.path),
            "languages_detected": scan_result.project_info.languages,
            "frameworks_detected": scan_result.project_info.frameworks,
            "duration_seconds": round(scan_result.duration_seconds, 2),
            "tools_executed": {
                tr.tool_name: {
                    "version": tr.version,
                    "status": "success" if tr.success else "failed",
                    "findings_count": len(tr.findings),
                    "duration_seconds": round(tr.duration_seconds, 2),
                    "error": tr.error_message or None,
                }
                for tr in scan_result.tool_results
            },
        },
        "summary": _build_summary(scan_result),
        "findings": [f.to_dict() for f in scan_result.findings],
    }

    path.write_text(json.dumps(report, indent=2))


def write_fix_prompts(scan_result: ScanResult, path: Path) -> None:
    """Write AI-ready fix prompts as a markdown file."""
    lines = []
    lines.append("# Vibe Scan Fix Prompts\n")
    lines.append(
        f"Scanned: `{scan_result.project_info.path}` | "
        f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}\n"
    )
    lines.append(f"Total findings: **{len(scan_result.findings)}**\n")
    lines.append("---\n")
    lines.append(
        "Copy this file into **Cursor**, **Claude**, or **Copilot Chat** and ask:\n"
    )
    lines.append('> **"Fix all the security issues listed below."**\n')
    lines.append("---\n")

    if not scan_result.findings:
        lines.append("\nNo issues found. Your code looks clean!\n")
    else:
        for i, finding in enumerate(scan_result.findings, 1):
            lines.append(f"\n### Issue {i}\n")
            lines.append(finding.fix_prompt)
            lines.append("\n---\n")

    path.write_text("\n".join(lines))


def print_summary(scan_result: ScanResult, output_dir: Path) -> None:
    """Print a rich terminal summary of scan results."""
    console.print()

    # Tool results table
    table = Table(
        title=f"Vibe Scan Results -- {scan_result.project_info.path}",
        show_header=True,
        header_style="bold",
    )
    table.add_column("Tool", style="cyan", width=12)
    table.add_column("Status", width=8)
    table.add_column("Findings", justify="right", width=10)
    table.add_column("Time", justify="right", width=8)

    for tr in scan_result.tool_results:
        status = "[green]ok[/green]" if tr.success else "[red]fail[/red]"
        count = str(len(tr.findings))
        elapsed = f"{tr.duration_seconds:.1f}s"
        table.add_row(tr.tool_name, status, count, elapsed)

    total_findings = len(scan_result.findings)
    table.add_section()
    table.add_row(
        "[bold]Total[/bold]",
        "",
        f"[bold]{total_findings}[/bold]",
        f"[bold]{scan_result.duration_seconds:.1f}s[/bold]",
    )

    console.print(table)
    console.print()

    # Severity breakdown
    summary = _build_summary(scan_result)
    by_sev = summary["by_severity"]
    parts = []
    if by_sev.get("critical", 0):
        parts.append(f"[bold red]{by_sev['critical']} critical[/bold red]")
    if by_sev.get("high", 0):
        parts.append(f"[red]{by_sev['high']} high[/red]")
    if by_sev.get("medium", 0):
        parts.append(f"[yellow]{by_sev['medium']} medium[/yellow]")
    if by_sev.get("low", 0):
        parts.append(f"[blue]{by_sev['low']} low[/blue]")
    if by_sev.get("info", 0):
        parts.append(f"{by_sev['info']} info")

    if parts:
        console.print(f"  By severity: {', '.join(parts)}")
    elif total_findings == 0:
        console.print("  [green]No issues found![/green]")

    console.print()
    console.print(f"  Reports saved to: [bold]{output_dir}/[/bold]")
    console.print()


def _build_summary(scan_result: ScanResult) -> dict:
    """Build a summary dict from scan results."""
    by_severity: dict[str, int] = {}
    by_tool: dict[str, int] = {}
    by_category: dict[str, int] = {}

    for f in scan_result.findings:
        sev = f.severity.value
        by_severity[sev] = by_severity.get(sev, 0) + 1

        by_tool[f.tool] = by_tool.get(f.tool, 0) + 1

        cat = f.category.value
        by_category[cat] = by_category.get(cat, 0) + 1

    return {
        "total_findings": len(scan_result.findings),
        "by_severity": by_severity,
        "by_tool": by_tool,
        "by_category": by_category,
    }
