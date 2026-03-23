"""Gitleaks secret detection wrapper."""

import json
import subprocess
import time
from pathlib import Path

from vibe_scan.binary_manager import BinaryManager
from vibe_scan.tools import Category, Finding, Severity, ToolResult


class GitleaksScanner:
    """Wraps Gitleaks for secret detection in source code."""

    def __init__(self, binary_manager: BinaryManager):
        self.binary_manager = binary_manager

    def scan(self, target: Path) -> ToolResult:
        """Run Gitleaks on the target directory."""
        start = time.time()

        try:
            binary = self.binary_manager.ensure_tool("gitleaks")
        except Exception as e:
            return ToolResult(
                tool_name="gitleaks",
                version="unknown",
                success=False,
                error_message=str(e),
                duration_seconds=time.time() - start,
            )

        # Write report to a temp file since gitleaks doesn't reliably output to stdout
        import tempfile
        report_file = Path(tempfile.mktemp(suffix=".json"))

        cmd = [
            str(binary),
            "detect",
            "--source", str(target),
            "--report-format", "json",
            "--report-path", str(report_file),
            "--no-banner",
            "--exit-code", "0",  # Don't use exit code for findings
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
            )
        except subprocess.TimeoutExpired:
            return ToolResult(
                tool_name="gitleaks",
                version=self._get_version(binary),
                success=False,
                error_message="Gitleaks timed out after 300 seconds",
                duration_seconds=time.time() - start,
            )

        duration = time.time() - start

        # Parse results from the report file
        findings = []
        if report_file.exists():
            try:
                raw = report_file.read_text()
                if raw.strip():
                    leaks = json.loads(raw)
                    findings = self._parse_results(leaks, target)
            except (json.JSONDecodeError, OSError):
                pass
            finally:
                report_file.unlink(missing_ok=True)
        else:
            report_file.unlink(missing_ok=True)

        return ToolResult(
            tool_name="gitleaks",
            version=self._get_version(binary),
            success=True,
            findings=findings,
            duration_seconds=duration,
        )

    def _parse_results(self, leaks: list[dict], target: Path) -> list[Finding]:
        """Parse Gitleaks JSON output into Finding objects."""
        findings = []

        for leak in leaks:
            # Make file path relative to target
            file_path = leak.get("File", "")
            try:
                file_path = str(Path(file_path).relative_to(target))
            except ValueError:
                pass

            # Truncate the matched secret for safety
            match = leak.get("Match", "")
            if len(match) > 50:
                match = match[:20] + "..." + match[-10:]

            findings.append(Finding(
                tool="gitleaks",
                rule_id=leak.get("RuleID", "unknown"),
                category=Category.SECRET,
                severity=Severity.HIGH,
                confidence="high",
                file=file_path,
                line_start=leak.get("StartLine", 0),
                line_end=leak.get("EndLine", 0),
                column_start=leak.get("StartColumn", 0),
                column_end=leak.get("EndColumn", 0),
                message=leak.get("Description", "Secret or credential detected"),
                code_snippet=match,
            ))

        return findings

    @staticmethod
    def _get_version(binary: Path) -> str:
        """Get the installed Gitleaks version."""
        try:
            result = subprocess.run(
                [str(binary), "version"],
                capture_output=True, text=True, timeout=10,
            )
            return result.stdout.strip()
        except Exception:
            return "unknown"
