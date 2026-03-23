"""Tool wrappers and shared data types for scan findings."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class Category(str, Enum):
    SECURITY = "security"
    CODE_QUALITY = "code-quality"
    DEPENDENCY = "dependency"
    SECRET = "secret"
    LICENSE = "license"
    MISCONFIGURATION = "misconfiguration"


@dataclass
class Finding:
    tool: str
    rule_id: str
    category: Category
    severity: Severity
    confidence: str
    file: str
    line_start: int
    line_end: int
    column_start: int
    column_end: int
    message: str
    code_snippet: str = ""
    cwe: list[str] = field(default_factory=list)
    owasp: list[str] = field(default_factory=list)
    fix_prompt: str = ""
    references: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "tool": self.tool,
            "rule_id": self.rule_id,
            "category": self.category.value,
            "severity": self.severity.value,
            "confidence": self.confidence,
            "file": self.file,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "column_start": self.column_start,
            "column_end": self.column_end,
            "message": self.message,
            "code_snippet": self.code_snippet,
            "cwe": self.cwe,
            "owasp": self.owasp,
            "fix_prompt": self.fix_prompt,
            "references": self.references,
        }


@dataclass
class ToolResult:
    tool_name: str
    version: str
    success: bool
    findings: list[Finding] = field(default_factory=list)
    error_message: str = ""
    duration_seconds: float = 0.0
    rules_loaded: int = 0
