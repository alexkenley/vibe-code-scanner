"""Tests for report generation."""

import json
from pathlib import Path

from vibe_scan.language import ProjectInfo
from vibe_scan.report import write_json_report, write_fix_prompts, _build_summary
from vibe_scan.scanner import ScanResult
from vibe_scan.tools import Category, Finding, Severity, ToolResult


def _make_finding(**kwargs):
    defaults = dict(
        tool="semgrep",
        rule_id="test.rule",
        category=Category.SECURITY,
        severity=Severity.HIGH,
        confidence="high",
        file="main.py",
        line_start=10,
        line_end=10,
        column_start=1,
        column_end=20,
        message="Test finding",
        fix_prompt="## Fix this",
    )
    defaults.update(kwargs)
    return Finding(**defaults)


def _make_scan_result(findings=None):
    info = ProjectInfo(path=Path("/tmp/test"))
    info.languages = ["python"]
    tr = ToolResult(
        tool_name="semgrep", version="1.0.0", success=True,
        findings=findings or [],
    )
    return ScanResult(
        project_info=info,
        tool_results=[tr],
        findings=findings or [],
        duration_seconds=5.0,
    )


def test_json_report_structure(tmp_path):
    finding = _make_finding()
    result = _make_scan_result([finding])

    path = tmp_path / "report.json"
    write_json_report(result, path)

    report = json.loads(path.read_text())
    assert report["version"] == "0.3.0"
    assert "scan_metadata" in report
    assert "summary" in report
    assert "findings" in report
    assert len(report["findings"]) == 1
    assert report["findings"][0]["severity"] == "high"


def test_json_report_empty(tmp_path):
    result = _make_scan_result([])
    path = tmp_path / "report.json"
    write_json_report(result, path)

    report = json.loads(path.read_text())
    assert report["summary"]["total_findings"] == 0
    assert report["findings"] == []


def test_fix_prompts_markdown(tmp_path):
    finding = _make_finding(fix_prompt="## HIGH: Fix this issue")
    result = _make_scan_result([finding])

    path = tmp_path / "fix-prompts.md"
    write_fix_prompts(result, path)

    content = path.read_text()
    assert "# Vibe Scan Fix Prompts" in content
    assert "Fix all the security issues" in content
    assert "## HIGH: Fix this issue" in content


def test_fix_prompts_no_findings(tmp_path):
    result = _make_scan_result([])

    path = tmp_path / "fix-prompts.md"
    write_fix_prompts(result, path)

    content = path.read_text()
    assert "No issues found" in content


def test_build_summary():
    findings = [
        _make_finding(severity=Severity.HIGH, category=Category.SECURITY, tool="semgrep"),
        _make_finding(severity=Severity.MEDIUM, category=Category.DEPENDENCY, tool="trivy"),
        _make_finding(severity=Severity.HIGH, category=Category.SECRET, tool="gitleaks"),
    ]
    result = _make_scan_result(findings)

    summary = _build_summary(result)
    assert summary["total_findings"] == 3
    assert summary["by_severity"]["high"] == 2
    assert summary["by_severity"]["medium"] == 1
    assert summary["by_tool"]["semgrep"] == 1
    assert summary["by_tool"]["trivy"] == 1
    assert summary["by_tool"]["gitleaks"] == 1
