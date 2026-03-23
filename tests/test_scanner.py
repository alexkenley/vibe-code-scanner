"""Tests for scanner orchestrator."""

from vibe_scan.scanner import _generate_fix_prompt
from vibe_scan.tools import Category, Finding, Severity


def test_generate_fix_prompt_basic():
    finding = Finding(
        tool="semgrep",
        rule_id="python.security.eval",
        category=Category.SECURITY,
        severity=Severity.HIGH,
        confidence="high",
        file="main.py",
        line_start=42,
        line_end=42,
        column_start=1,
        column_end=20,
        message="Use of eval() detected",
        code_snippet="result = eval(user_input)",
    )
    prompt = _generate_fix_prompt(finding)

    assert "HIGH" in prompt
    assert "main.py" in prompt
    assert "line 42" in prompt
    assert "eval()" in prompt
    assert "### Code" in prompt
    assert "eval(user_input)" in prompt
    assert "### Action Required" in prompt


def test_generate_fix_prompt_with_cwe():
    finding = Finding(
        tool="semgrep",
        rule_id="test.rule",
        category=Category.SECURITY,
        severity=Severity.CRITICAL,
        confidence="high",
        file="app.py",
        line_start=10,
        line_end=10,
        column_start=1,
        column_end=10,
        message="SQL injection",
        cwe=["CWE-89"],
        owasp=["A03:2021"],
        references=["https://example.com/fix"],
    )
    prompt = _generate_fix_prompt(finding)

    assert "CWE-89" in prompt
    assert "A03:2021" in prompt
    assert "https://example.com/fix" in prompt


def test_generate_fix_prompt_no_code_snippet():
    finding = Finding(
        tool="trivy",
        rule_id="CVE-2024-1234",
        category=Category.DEPENDENCY,
        severity=Severity.MEDIUM,
        confidence="high",
        file="package-lock.json",
        line_start=0,
        line_end=0,
        column_start=0,
        column_end=0,
        message="lodash 4.17.20 has vulnerability",
    )
    prompt = _generate_fix_prompt(finding)

    assert "MEDIUM" in prompt
    assert "### Code" not in prompt  # No code snippet
    assert "dependency" in prompt
