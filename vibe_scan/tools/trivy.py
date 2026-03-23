"""Trivy dependency and misconfiguration scanner wrapper."""

import json
import subprocess
import time
from pathlib import Path

from vibe_scan.binary_manager import BinaryManager
from vibe_scan.tools import Category, Finding, Severity, ToolResult

SEVERITY_MAP = {
    "CRITICAL": Severity.CRITICAL,
    "HIGH": Severity.HIGH,
    "MEDIUM": Severity.MEDIUM,
    "LOW": Severity.LOW,
    "UNKNOWN": Severity.INFO,
}


class TrivyScanner:
    """Wraps Trivy for dependency vulnerability and misconfiguration scanning."""

    def __init__(self, binary_manager: BinaryManager):
        self.binary_manager = binary_manager

    def scan(self, target: Path) -> ToolResult:
        """Run Trivy filesystem scan on the target directory."""
        start = time.time()

        try:
            binary = self.binary_manager.ensure_tool("trivy")
        except Exception as e:
            return ToolResult(
                tool_name="trivy",
                version="unknown",
                success=False,
                error_message=str(e),
                duration_seconds=time.time() - start,
            )

        cmd = [
            str(binary),
            "fs",
            "--format", "json",
            "--scanners", "vuln,misconfig,license",
            "--severity", "UNKNOWN,LOW,MEDIUM,HIGH,CRITICAL",
            "--exit-code", "0",
            "--skip-db-update",  # Use cached DB if available
            str(target),
        ]

        # First run may need to download the vulnerability DB
        # Try without --skip-db-update if it fails
        result = self._run_trivy(cmd, binary, start)
        if not result.success and "database" in result.error_message.lower():
            cmd.remove("--skip-db-update")
            result = self._run_trivy(cmd, binary, start)

        return result

    def _run_trivy(self, cmd: list[str], binary: Path, start: float) -> ToolResult:
        """Execute trivy and parse results."""
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600,
            )
        except subprocess.TimeoutExpired:
            return ToolResult(
                tool_name="trivy",
                version=self._get_version(binary),
                success=False,
                error_message="Trivy timed out after 600 seconds",
                duration_seconds=time.time() - start,
            )

        duration = time.time() - start

        if proc.returncode != 0 and not proc.stdout.strip():
            return ToolResult(
                tool_name="trivy",
                version=self._get_version(binary),
                success=False,
                error_message=proc.stderr.strip()[:500],
                duration_seconds=duration,
            )

        try:
            output = json.loads(proc.stdout)
        except json.JSONDecodeError:
            return ToolResult(
                tool_name="trivy",
                version=self._get_version(binary),
                success=False,
                error_message=f"Failed to parse Trivy JSON: {proc.stderr[:300]}",
                duration_seconds=duration,
            )

        findings = self._parse_results(output)

        return ToolResult(
            tool_name="trivy",
            version=self._get_version(binary),
            success=True,
            findings=findings,
            duration_seconds=duration,
        )

    def _parse_results(self, output: dict) -> list[Finding]:
        """Parse Trivy JSON output into Finding objects."""
        findings = []

        for result in output.get("Results", []):
            target_name = result.get("Target", "")

            # Vulnerability findings
            for vuln in result.get("Vulnerabilities") or []:
                severity = SEVERITY_MAP.get(
                    vuln.get("Severity", "UNKNOWN"), Severity.INFO
                )
                pkg = vuln.get("PkgName", "unknown")
                installed = vuln.get("InstalledVersion", "?")
                fixed = vuln.get("FixedVersion", "")
                vuln_id = vuln.get("VulnerabilityID", "")
                title = vuln.get("Title", "")

                message = f"{pkg} {installed} has vulnerability {vuln_id}"
                if title:
                    message += f": {title}"
                if fixed:
                    message += f" (fixed in {fixed})"

                findings.append(Finding(
                    tool="trivy",
                    rule_id=vuln_id,
                    category=Category.DEPENDENCY,
                    severity=severity,
                    confidence="high",
                    file=target_name,
                    line_start=0,
                    line_end=0,
                    column_start=0,
                    column_end=0,
                    message=message,
                    cwe=vuln.get("CweIDs") or [],
                    references=(vuln.get("References") or [])[:3],
                ))

            # Misconfiguration findings
            for misconfig in result.get("Misconfigurations") or []:
                severity = SEVERITY_MAP.get(
                    misconfig.get("Severity", "UNKNOWN"), Severity.INFO
                )
                findings.append(Finding(
                    tool="trivy",
                    rule_id=misconfig.get("ID", ""),
                    category=Category.MISCONFIGURATION,
                    severity=severity,
                    confidence="high",
                    file=target_name,
                    line_start=misconfig.get("CauseMetadata", {}).get("StartLine", 0),
                    line_end=misconfig.get("CauseMetadata", {}).get("EndLine", 0),
                    column_start=0,
                    column_end=0,
                    message=misconfig.get("Message", misconfig.get("Title", "")),
                    references=[misconfig.get("PrimaryURL", "")]
                    if misconfig.get("PrimaryURL")
                    else [],
                ))

            # License findings
            for lic in result.get("Licenses") or []:
                severity = SEVERITY_MAP.get(
                    lic.get("Severity", "UNKNOWN"), Severity.LOW
                )
                findings.append(Finding(
                    tool="trivy",
                    rule_id=f"license:{lic.get('Name', 'unknown')}",
                    category=Category.LICENSE,
                    severity=severity,
                    confidence="high",
                    file=target_name,
                    line_start=0,
                    line_end=0,
                    column_start=0,
                    column_end=0,
                    message=(
                        f"Package {lic.get('PkgName', '?')} uses license "
                        f"{lic.get('Name', 'unknown')}: {lic.get('Category', '')}"
                    ),
                ))

        return findings

    @staticmethod
    def _get_version(binary: Path) -> str:
        """Get the installed Trivy version."""
        try:
            result = subprocess.run(
                [str(binary), "--version"],
                capture_output=True, text=True, timeout=10,
            )
            # Output is like "Version: 0.50.1"
            for line in result.stdout.strip().split("\n"):
                if "version" in line.lower():
                    return line.split(":")[-1].strip() if ":" in line else line.strip()
            return result.stdout.strip().split("\n")[0]
        except Exception:
            return "unknown"
