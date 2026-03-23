# Vibe Scan v2 Architecture

## Overview

Vibe Scan is a lightweight, pip-installable security scanner for AI-generated ("vibe coded") applications. It wraps three best-in-class open-source tools behind a single CLI, producing AI-ready fix prompts that can be pasted directly into Cursor, Claude, or Copilot.

```
pip install vibe-scan
vibe-scan ./my-project
```

No Docker required. Works natively on WSL, macOS, and Linux.

## Design Principles

1. **Zero-friction setup** -- `pip install` and go. No Docker, no Node.js, no language runtimes.
2. **Best tools, not custom tools** -- wrap Semgrep, Gitleaks, and Trivy rather than reinventing analysis.
3. **AI-in-the-loop** -- output is designed to be consumed by AI assistants, not just humans.
4. **Polyglot by default** -- Semgrep covers 30+ languages with one install. No per-language tool setup.

## Core Tools

| Tool | Purpose | Replaces (v1) | Install Method |
|------|---------|---------------|----------------|
| **Semgrep** | SAST -- security, code quality, secrets via rules | ESLint, flake8, bandit, rubocop, brakeman, golangci-lint, gosec | pip dependency |
| **Gitleaks** | Dedicated secret/credential detection | Custom checks | Auto-downloaded binary |
| **Trivy** | Dependency vulnerabilities, misconfigurations, license scanning | RetireJS, license_scanner.py | Auto-downloaded binary |

### Why These Tools

- **Semgrep** replaces 7 language-specific tools with a single engine. One rule syntax works across Python, JavaScript, TypeScript, Go, Ruby, Java, Rust, and more. It has curated rulesets for OWASP Top 10, secrets, and framework-specific patterns (Next.js, Django, Rails, Express).
- **Gitleaks** is the industry standard for secret detection. 150+ built-in rules covering AWS keys, Supabase JWTs, Stripe tokens, and more. Single Go binary, no dependencies.
- **Trivy** handles dependency scanning (CVEs in npm, pip, gem, go.mod, etc.), IaC misconfiguration detection, and license compliance -- replacing both RetireJS and the custom license scanner.

## Package Structure

```
pyproject.toml                  # Build config, dependencies, entry points
vibe_scan/
  __init__.py                   # Package version
  cli.py                        # Click CLI: vibe-scan command + subcommands
  scanner.py                    # Orchestrator: runs tools, merges results, deduplicates
  language.py                   # Project detection: languages, frameworks, package managers
  binary_manager.py             # Auto-download/cache Gitleaks and Trivy binaries
  report.py                     # JSON report + AI fix-prompts.md + terminal summary
  mcp_server.py                 # FastAPI MCP server (optional dependency)
  tools/
    __init__.py                 # Finding dataclass, Severity/Category enums, ToolResult
    semgrep.py                  # Semgrep CLI wrapper with ruleset selection
    gitleaks.py                 # Gitleaks wrapper
    trivy.py                    # Trivy wrapper
  rules/
    supabase.yml                # Custom Semgrep rules for Supabase patterns
    nextjs.yml                  # Custom Semgrep rules for Next.js patterns
tests/
  conftest.py                   # Fixtures: paths to test-apps
  test_language.py
  test_scanner.py
  test_binary_manager.py
  test_report.py
test-apps/                      # 9 intentionally-vulnerable apps for validation
```

## Data Flow

```
User runs: vibe-scan ./my-project
                |
                v
        +-------+--------+
        |   cli.py        |   Parse args, resolve target path
        +-------+--------+
                |
                v
        +-------+--------+
        |  language.py    |   Walk file tree, detect languages + frameworks
        |                 |   Returns: ProjectInfo(languages, frameworks, ...)
        +-------+--------+
                |
                v
        +-------+--------+
        |  scanner.py     |   Orchestrate tool execution
        |  (orchestrator) |
        +---+---+---+----+
            |   |   |
            v   v   v
     Semgrep  Gitleaks  Trivy      (run in sequence, each ~2-10s)
            |   |   |
            v   v   v
        +-------+--------+
        | scanner.py      |   Merge findings, deduplicate, sort by severity
        | (merge/dedup)   |   Generate fix_prompt for each finding
        +-------+--------+
                |
                v
        +-------+--------+
        |  report.py      |   Write JSON report
        |                 |   Write fix-prompts.md (AI-ready)
        |                 |   Print rich terminal summary
        +----------------+
```

## Key Components

### CLI (`cli.py`)

Built with Click. Entry point registered as `vibe-scan` console script.

```
vibe-scan [TARGET] [OPTIONS]

Arguments:
  TARGET              Path to scan (default: current directory)

Options:
  -o, --output DIR    Output directory (default: ./reports)
  -f, --format FMT    Output format: json, markdown, both (default: both)
  -s, --severity LVL  Minimum severity to report (default: low)
  --skip-semgrep      Skip SAST scan
  --skip-gitleaks     Skip secret detection
  --skip-trivy        Skip dependency scanning
  --github URL        Clone and scan a GitHub repo
  -b, --branch NAME   Branch to clone (with --github)
  --token TOKEN       GitHub token for private repos

Subcommands:
  vibe-scan tools          Show installed tool versions and status
  vibe-scan update-tools   Force re-download of Gitleaks/Trivy
```

### Language Detection (`language.py`)

Returns a `ProjectInfo` dataclass describing the project:

```python
@dataclass
class ProjectInfo:
    path: Path
    languages: list[str]        # ["python", "javascript", "typescript"]
    frameworks: list[str]       # ["nextjs", "supabase"]
    package_managers: list[str] # ["npm", "pip"]
    has_dockerfile: bool
    has_git: bool
```

Key differences from v1:
- Returns ALL detected languages (Semgrep is polyglot, no need to pick one)
- "nextjs" and "node" are frameworks, not languages
- Respects `.gitignore` and common exclusion patterns

### Binary Manager (`binary_manager.py`)

Handles auto-downloading Gitleaks and Trivy on first run.

**Resolution order:**
1. Check environment variable override (`VIBE_SCAN_GITLEAKS_PATH`)
2. Check system PATH (`shutil.which()`)
3. Check local cache (`~/.cache/vibe-scan/bin/`)
4. Download from GitHub Releases, extract, cache, make executable

**Platform detection:** `platform.system()` + `platform.machine()` mapped to release asset names.

**Version pinning:** Hardcoded versions as constants, overridable via `VIBE_SCAN_GITLEAKS_VERSION` / `VIBE_SCAN_TRIVY_VERSION` environment variables.

**Cache layout:**
```
~/.cache/vibe-scan/bin/
  gitleaks-8.18.2
  trivy-0.50.1
```

**First-run UX:**
```
Downloading gitleaks v8.18.2 for linux/x86_64... [################] 100%
Cached at ~/.cache/vibe-scan/bin/gitleaks-8.18.2
```

### Tool Wrappers (`tools/`)

Each wrapper follows the same interface:

```python
class SemgrepScanner:
    def scan(self, target: Path, project_info: ProjectInfo) -> ToolResult: ...

class GitleaksScanner:
    def __init__(self, binary_manager: BinaryManager): ...
    def scan(self, target: Path) -> ToolResult: ...

class TrivyScanner:
    def __init__(self, binary_manager: BinaryManager): ...
    def scan(self, target: Path) -> ToolResult: ...
```

Each returns a `ToolResult` containing a list of `Finding` objects:

```python
@dataclass
class Finding:
    tool: str              # "semgrep", "gitleaks", "trivy"
    rule_id: str           # e.g. "python.lang.security.audit.exec-detected"
    category: Category     # SECURITY, CODE_QUALITY, DEPENDENCY, SECRET, LICENSE, MISCONFIGURATION
    severity: Severity     # CRITICAL, HIGH, MEDIUM, LOW, INFO
    confidence: str        # "high", "medium", "low"
    file: str
    line_start: int
    line_end: int
    column_start: int
    column_end: int
    message: str
    code_snippet: str
    cwe: list[str]         # ["CWE-95"]
    owasp: list[str]       # ["A03:2021"]
    fix_prompt: str        # AI-ready fix prompt (generated post-scan)
    references: list[str]
```

### Semgrep Rulesets

Rulesets are selected dynamically based on detected languages and frameworks:

| Always enabled | Per-language | Per-framework |
|---------------|-------------|---------------|
| `p/security-audit` | `p/python` | `p/nextjs` |
| `p/owasp-top-ten` | `p/javascript` | `p/django` |
| `p/secrets` | `p/typescript` | `p/flask` |
| | `p/golang` | `p/expressjs` |
| | `p/ruby` | `p/react` |
| | `p/java` | `p/ruby` (Rails) |

Custom rules in `vibe_scan/rules/` are always loaded (Supabase patterns, Next.js API route checks, etc.).

### Report Generation (`report.py`)

Produces three outputs:

**1. JSON Report** (`reports/vibe-scan-report.json`)
```json
{
  "version": "0.3.0",
  "scan_metadata": {
    "timestamp": "2026-03-23T10:30:00Z",
    "target": "/path/to/project",
    "languages_detected": ["javascript", "typescript"],
    "duration_seconds": 5.4,
    "tools_executed": { ... }
  },
  "summary": {
    "total_findings": 15,
    "by_severity": {"critical": 1, "high": 3, "medium": 7, "low": 4},
    "by_tool": {"semgrep": 10, "gitleaks": 2, "trivy": 3},
    "by_category": {"security": 8, "code-quality": 4, "dependency": 3}
  },
  "findings": [ ... ]
}
```

**2. AI Fix Prompts** (`reports/fix-prompts.md`)

A single markdown file designed to be pasted into an AI assistant:

```markdown
# Vibe Scan Fix Prompts

Copy this file into Cursor, Claude, or Copilot and ask:
**"Fix all the security issues listed below."**

---

## Issue 1: Hardcoded Secret Detected [HIGH]
**File:** lib/supabase.js (line 5)
**Rule:** generic.secrets.security.detected-jwt-token

### What was found
A hardcoded JWT token was detected in the source code.

### Suggested fix
Move this secret to an environment variable and add .env to .gitignore.

---
(... more issues ...)
```

**3. Terminal Summary** (via `rich`)
```
Vibe Scan Results -- ./my-project
-------------------------------------
 Tool       Status  Findings  Time
-------------------------------------
 Semgrep      ok      10      3.2s
 Gitleaks     ok       2      0.8s
 Trivy        ok       3      1.4s
-------------------------------------
 Total                15      5.4s

 By severity: 1 critical, 3 high, 7 medium, 4 low

 Reports saved to: ./reports/
```

### MCP Server (`mcp_server.py`)

Optional install: `pip install vibe-scan[mcp]`

Single FastAPI server implementing MCP protocol (JSON-RPC 2.0 over SSE + HTTP). Replaces the 8 server implementations from v1.

**Tools exposed:**
- `scan_project(path, options)` -- trigger a scan, returns scan_id
- `get_scan_status(scan_id)` -- poll status
- `get_results(scan_id)` -- retrieve findings + fix prompts

**Entry point:** `vibe-scan-mcp` console script (or `python -m vibe_scan.mcp_server`)

## Dependencies

### Required (pip)
- `semgrep >= 1.56.0` -- SAST engine
- `click >= 8.1.0` -- CLI framework
- `rich >= 13.0.0` -- Terminal output (tables, progress bars, colors)
- `pydantic >= 2.0.0` -- Data validation

### Optional (`pip install vibe-scan[mcp]`)
- `fastapi >= 0.104.0`
- `uvicorn[standard] >= 0.24.0`
- `sse-starlette >= 1.6.0`

### External (auto-downloaded)
- Gitleaks (Go binary, ~15MB)
- Trivy (Go binary, ~50MB)

### Development (`pip install vibe-scan[dev]`)
- `pytest >= 7.0.0`
- `pytest-cov >= 4.0.0`

## Docker (Optional)

For CI/CD or users who prefer containers:

```dockerfile
FROM python:3.11-slim
RUN pip install vibe-scan
ENTRYPOINT ["vibe-scan"]
```

Gitleaks and Trivy are auto-downloaded on first container run and cached in the image layer if the image is committed.

## Comparison with v1

| Aspect | v1 | v2 |
|--------|----|----|
| Install | Docker build (~5 min) | `pip install vibe-scan` |
| Tools | 7+ language-specific (ESLint, flake8, bandit...) | 3 polyglot (Semgrep, Gitleaks, Trivy) |
| Languages | 5 (Python, JS, TS, Go, Ruby) | 30+ (via Semgrep) |
| Secret detection | Heuristic checks | Gitleaks (150+ rules) |
| Dependency scanning | RetireJS (JS only) | Trivy (all ecosystems) |
| License scanning | Custom Python module | Trivy |
| Output | JSON report | JSON + AI fix prompts + rich terminal |
| MCP servers | 8 implementations | 1 clean FastAPI server |
| Docker required | Yes | No (optional) |
| scan.py size | 1,535 lines | ~200 lines (scanner.py orchestrator) |

## Security Considerations

- Gitleaks/Trivy binaries are downloaded over HTTPS from official GitHub Releases
- SHA256 checksum verification on downloaded binaries
- MCP server binds to `127.0.0.1` only by default
- GitHub tokens passed via `--token` are never logged or written to reports
- Semgrep runs with `--metrics off` by default (no telemetry)
- Temporary directories for GitHub clones are cleaned up in a `finally` block
