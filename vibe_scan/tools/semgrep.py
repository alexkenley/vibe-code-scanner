"""Semgrep SAST scanner wrapper."""

import json
import subprocess
import time
from pathlib import Path

from vibe_scan.language import ProjectInfo
from vibe_scan.tools import Category, Finding, Severity, ToolResult

# Always-enabled rulesets
DEFAULT_RULESETS = [
    "p/security-audit",
    "p/owasp-top-ten",
    "p/secrets",
]

# Rulesets enabled when specific languages are detected
LANGUAGE_RULESETS = {
    "python": ["p/python"],
    "javascript": ["p/javascript"],
    "typescript": ["p/typescript"],
    "go": ["p/golang"],
    "ruby": ["p/ruby"],
    "java": ["p/java"],
}

# Rulesets enabled when specific frameworks are detected
FRAMEWORK_RULESETS = {
    "nextjs": ["p/nextjs"],
    "react": ["p/react"],
    "django": ["p/django"],
    "flask": ["p/flask"],
    "express": ["p/expressjs"],
}

# Map Semgrep severity strings to our Severity enum
SEVERITY_MAP = {
    "ERROR": Severity.HIGH,
    "WARNING": Severity.MEDIUM,
    "INFO": Severity.LOW,
    "INVENTORY": Severity.INFO,
    "EXPERIMENT": Severity.INFO,
}

# Map Semgrep metadata categories to our Category enum
CATEGORY_KEYWORDS = {
    "security": Category.SECURITY,
    "correctness": Category.CODE_QUALITY,
    "best-practice": Category.CODE_QUALITY,
    "maintainability": Category.CODE_QUALITY,
    "performance": Category.CODE_QUALITY,
}


class SemgrepScanner:
    """Wraps Semgrep CLI for SAST scanning."""

    def scan(self, target: Path, project_info: ProjectInfo) -> ToolResult:
        """Run Semgrep with rulesets selected based on detected project info."""
        start = time.time()

        rulesets = self._select_rulesets(project_info)
        custom_rules = Path(__file__).parent.parent / "rules"

        cmd = [
            "semgrep", "scan",
            "--json",
            "--metrics", "off",
            "--timeout", "300",
            "--max-target-bytes", "1000000",
            "--quiet",
        ]

        for ruleset in rulesets:
            cmd.extend(["--config", ruleset])

        # Add custom rules directory if it exists and has files
        if custom_rules.is_dir() and any(custom_rules.glob("*.yml")):
            cmd.extend(["--config", str(custom_rules)])

        cmd.append(str(target))

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600,
            )
        except FileNotFoundError:
            return ToolResult(
                tool_name="semgrep",
                version="unknown",
                success=False,
                error_message=(
                    "Semgrep not found. Install with: pip install semgrep"
                ),
                duration_seconds=time.time() - start,
            )
        except subprocess.TimeoutExpired:
            return ToolResult(
                tool_name="semgrep",
                version="unknown",
                success=False,
                error_message="Semgrep timed out after 600 seconds",
                duration_seconds=time.time() - start,
            )

        duration = time.time() - start

        # Semgrep exits 0 for clean, 1 for findings, other codes for errors
        if result.returncode not in (0, 1):
            return ToolResult(
                tool_name="semgrep",
                version=self._get_version(),
                success=False,
                error_message=result.stderr.strip(),
                duration_seconds=duration,
            )

        try:
            output = json.loads(result.stdout)
        except json.JSONDecodeError:
            return ToolResult(
                tool_name="semgrep",
                version=self._get_version(),
                success=False,
                error_message=f"Failed to parse Semgrep JSON output: {result.stdout[:500]}",
                duration_seconds=duration,
            )

        findings = self._parse_results(output, target)
        rules_loaded = len(output.get("paths", {}).get("scanned", []))

        return ToolResult(
            tool_name="semgrep",
            version=self._get_version(),
            success=True,
            findings=findings,
            duration_seconds=duration,
            rules_loaded=rules_loaded,
        )

    def _select_rulesets(self, project_info: ProjectInfo) -> list[str]:
        """Select Semgrep rulesets based on detected languages and frameworks."""
        rulesets = list(DEFAULT_RULESETS)

        for lang in project_info.languages:
            if lang in LANGUAGE_RULESETS:
                rulesets.extend(LANGUAGE_RULESETS[lang])

        for framework in project_info.frameworks:
            if framework in FRAMEWORK_RULESETS:
                rulesets.extend(FRAMEWORK_RULESETS[framework])

        # Deduplicate while preserving order
        seen = set()
        unique = []
        for r in rulesets:
            if r not in seen:
                seen.add(r)
                unique.append(r)
        return unique

    def _parse_results(self, output: dict, target: Path) -> list[Finding]:
        """Parse Semgrep JSON output into Finding objects."""
        findings = []

        for result in output.get("results", []):
            extra = result.get("extra", {})
            metadata = extra.get("metadata", {})

            # Make file path relative to target
            file_path = result.get("path", "")
            try:
                file_path = str(Path(file_path).relative_to(target))
            except ValueError:
                pass

            severity = SEVERITY_MAP.get(
                extra.get("severity", "WARNING"), Severity.MEDIUM
            )
            category = self._categorize(metadata)

            findings.append(Finding(
                tool="semgrep",
                rule_id=result.get("check_id", "unknown"),
                category=category,
                severity=severity,
                confidence=metadata.get("confidence", "MEDIUM").lower(),
                file=file_path,
                line_start=result.get("start", {}).get("line", 0),
                line_end=result.get("end", {}).get("line", 0),
                column_start=result.get("start", {}).get("col", 0),
                column_end=result.get("end", {}).get("col", 0),
                message=extra.get("message", ""),
                code_snippet=extra.get("lines", "").strip(),
                cwe=[c if isinstance(c, str) else c.get("cweId", str(c))
                     for c in metadata.get("cwe", [])],
                owasp=metadata.get("owasp", []),
                references=metadata.get("references", [])[:5],
            ))

        return findings

    @staticmethod
    def _categorize(metadata: dict) -> Category:
        """Determine category from Semgrep rule metadata."""
        cat = metadata.get("category", "").lower()
        for keyword, category in CATEGORY_KEYWORDS.items():
            if keyword in cat:
                return category

        # Check subcategories
        subcategory = metadata.get("subcategory", [])
        if isinstance(subcategory, list):
            for sub in subcategory:
                if "vuln" in sub.lower() or "security" in sub.lower():
                    return Category.SECURITY

        # Default to security since most semgrep rules are security-focused
        return Category.SECURITY

    @staticmethod
    def _get_version() -> str:
        """Get the installed Semgrep version."""
        try:
            result = subprocess.run(
                ["semgrep", "--version"],
                capture_output=True, text=True, timeout=10,
            )
            return result.stdout.strip()
        except Exception:
            return "unknown"
