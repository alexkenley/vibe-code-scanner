"""Scanner orchestrator -- runs tools, merges results, generates reports."""

import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path

from rich.console import Console

from vibe_scan.binary_manager import BinaryManager
from vibe_scan.language import ProjectInfo, detect_project
from vibe_scan.report import write_json_report, write_fix_prompts, print_summary
from vibe_scan.tools import Finding, Severity, ToolResult
from vibe_scan.tools.gitleaks import GitleaksScanner
from vibe_scan.tools.semgrep import SemgrepScanner
from vibe_scan.tools.trivy import TrivyScanner

console = Console(stderr=True)

SEVERITY_ORDER = {
    Severity.CRITICAL: 0,
    Severity.HIGH: 1,
    Severity.MEDIUM: 2,
    Severity.LOW: 3,
    Severity.INFO: 4,
}


@dataclass
class ScanOptions:
    output_dir: Path = Path("./reports")
    output_format: str = "both"
    min_severity: str = "low"
    skip_semgrep: bool = False
    skip_gitleaks: bool = False
    skip_trivy: bool = False
    github_url: str | None = None
    branch: str | None = None
    token: str | None = None


@dataclass
class ScanResult:
    project_info: ProjectInfo
    tool_results: list[ToolResult] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)
    duration_seconds: float = 0.0


class Scanner:
    """Orchestrates scanning tools and produces unified results."""

    def __init__(self):
        self.binary_manager = BinaryManager()
        self.semgrep = SemgrepScanner()
        self.gitleaks = GitleaksScanner(self.binary_manager)
        self.trivy = TrivyScanner(self.binary_manager)

    def run(self, target: Path, options: ScanOptions) -> ScanResult:
        """Run all enabled tools on the target and produce reports."""
        start = time.time()

        # Handle GitHub URL
        temp_dir = None
        if options.github_url:
            target, temp_dir = self._clone_repo(options)

        try:
            return self._scan(target, options, start)
        finally:
            if temp_dir:
                shutil.rmtree(temp_dir, ignore_errors=True)

    def _scan(self, target: Path, options: ScanOptions, start: float) -> ScanResult:
        """Core scanning logic."""
        target = target.resolve()

        console.print(f"\n[bold]Scanning:[/bold] {target}\n")

        # Detect project
        with console.status("Detecting project..."):
            project_info = detect_project(target)

        if project_info.languages:
            console.print(
                f"  Languages:  {', '.join(project_info.languages)}"
            )
        if project_info.frameworks:
            console.print(
                f"  Frameworks: {', '.join(project_info.frameworks)}"
            )
        console.print()

        tool_results: list[ToolResult] = []

        # Run Semgrep
        if not options.skip_semgrep:
            with console.status("[bold]Running Semgrep (SAST)...[/bold]"):
                result = self.semgrep.scan(target, project_info)
                tool_results.append(result)
                self._log_tool_result(result)

        # Run Gitleaks
        if not options.skip_gitleaks:
            with console.status("[bold]Running Gitleaks (secret detection)...[/bold]"):
                result = self.gitleaks.scan(target)
                tool_results.append(result)
                self._log_tool_result(result)

        # Run Trivy
        if not options.skip_trivy:
            with console.status("[bold]Running Trivy (dependency scan)...[/bold]"):
                result = self.trivy.scan(target)
                tool_results.append(result)
                self._log_tool_result(result)

        # Merge and filter findings
        all_findings = self._merge_findings(tool_results)
        all_findings = self._filter_severity(all_findings, options.min_severity)

        # Generate fix prompts
        for finding in all_findings:
            if not finding.fix_prompt:
                finding.fix_prompt = _generate_fix_prompt(finding)

        duration = time.time() - start

        scan_result = ScanResult(
            project_info=project_info,
            tool_results=tool_results,
            findings=all_findings,
            duration_seconds=duration,
        )

        # Write reports
        options.output_dir.mkdir(parents=True, exist_ok=True)

        if options.output_format in ("json", "both"):
            json_path = options.output_dir / "vibe-scan-report.json"
            write_json_report(scan_result, json_path)

        if options.output_format in ("markdown", "both"):
            md_path = options.output_dir / "fix-prompts.md"
            write_fix_prompts(scan_result, md_path)

        # Print terminal summary
        print_summary(scan_result, options.output_dir)

        return scan_result

    def _clone_repo(self, options: ScanOptions) -> tuple[Path, str]:
        """Clone a GitHub repo to a temporary directory."""
        temp_dir = tempfile.mkdtemp(prefix="vibe-scan-")
        console.print(f"[bold]Cloning:[/bold] {options.github_url}")

        cmd = ["git", "clone", "--depth", "1"]

        if options.branch:
            cmd.extend(["--branch", options.branch])

        # Build the URL (with token if provided)
        url = options.github_url
        if options.token and "github.com" in url:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            url = f"{parsed.scheme}://{options.token}@{parsed.netloc}{parsed.path}"

        cmd.extend([url, temp_dir])

        try:
            subprocess.run(
                cmd, check=True, capture_output=True, text=True, timeout=120,
            )
        except subprocess.CalledProcessError as e:
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise RuntimeError(f"Failed to clone: {e.stderr.strip()}") from e

        console.print(f"  Cloned to {temp_dir}\n")
        return Path(temp_dir), temp_dir

    @staticmethod
    def _merge_findings(results: list[ToolResult]) -> list[Finding]:
        """Merge findings from all tools, deduplicate, sort by severity."""
        all_findings = []
        for result in results:
            all_findings.extend(result.findings)

        # Deduplicate: same file + line + similar message = keep the first
        seen = set()
        unique = []
        for f in all_findings:
            key = (f.file, f.line_start, f.category)
            if key not in seen:
                seen.add(key)
                unique.append(f)

        # Sort by severity (critical first)
        unique.sort(key=lambda f: SEVERITY_ORDER.get(f.severity, 99))

        return unique

    @staticmethod
    def _filter_severity(findings: list[Finding], min_severity: str) -> list[Finding]:
        """Filter findings below the minimum severity."""
        threshold = {
            "critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4,
        }.get(min_severity, 3)

        return [
            f for f in findings
            if SEVERITY_ORDER.get(f.severity, 99) <= threshold
        ]

    @staticmethod
    def _log_tool_result(result: ToolResult) -> None:
        """Log a brief status line for a completed tool."""
        if result.success:
            count = len(result.findings)
            console.print(
                f"  {result.tool_name:12s} "
                f"[green]done[/green]  "
                f"{count} finding{'s' if count != 1 else '':4s} "
                f"({result.duration_seconds:.1f}s)"
            )
        else:
            console.print(
                f"  {result.tool_name:12s} "
                f"[red]failed[/red]  "
                f"{result.error_message[:60]}"
            )


def _generate_fix_prompt(finding: Finding) -> str:
    """Generate an AI-ready fix prompt for a finding."""
    lines = []
    lines.append(f"## {finding.severity.value.upper()}: {finding.message}")
    lines.append("")
    lines.append(f"**File:** `{finding.file}`" + (
        f" (line {finding.line_start})" if finding.line_start else ""
    ))
    lines.append(f"**Rule:** `{finding.rule_id}`")
    lines.append(f"**Tool:** {finding.tool}")
    lines.append(f"**Category:** {finding.category.value}")

    if finding.cwe:
        lines.append(f"**CWE:** {', '.join(finding.cwe)}")
    if finding.owasp:
        owasp = finding.owasp if isinstance(finding.owasp, list) else [finding.owasp]
        lines.append(f"**OWASP:** {', '.join(str(o) for o in owasp)}")

    if finding.code_snippet:
        lines.append("")
        lines.append("### Code")
        lines.append("```")
        lines.append(finding.code_snippet)
        lines.append("```")

    lines.append("")
    lines.append("### Action Required")
    lines.append(f"Fix the {finding.category.value} issue described above.")

    if finding.references:
        lines.append("")
        lines.append("### References")
        for ref in finding.references:
            lines.append(f"- {ref}")

    return "\n".join(lines)
