# Vibe Scan

A lightweight security scanner for AI-generated code. Finds vulnerabilities, hardcoded secrets, and dependency issues in your vibe-coded projects.

## Install

```bash
pip install vibe-scan
```

That's it. No Docker, no Node.js, no language runtimes needed.

## Usage

```bash
# Scan current directory
vibe-scan

# Scan a specific project
vibe-scan ./my-project

# Scan a GitHub repo
vibe-scan --github https://github.com/user/repo

# Skip specific tools
vibe-scan --skip-trivy --skip-gitleaks
```

## What It Scans

| Tool | What It Finds | Languages |
|------|--------------|-----------|
| **Semgrep** | Security bugs, code quality, OWASP Top 10 | 30+ languages |
| **Gitleaks** | Hardcoded secrets, API keys, tokens | Any |
| **Trivy** | Vulnerable dependencies, misconfigurations, licenses | npm, pip, gem, go, cargo, etc. |

Gitleaks and Trivy are auto-downloaded on first run (~50MB each, cached locally).

## Output

Vibe Scan generates two files in `./reports/`:

- **`vibe-scan-report.json`** -- Full structured JSON report
- **`fix-prompts.md`** -- AI-ready fix prompts you can paste into Cursor, Claude, or Copilot

```
Vibe Scan Results -- ./my-project
---------------------------------------------
 Tool         Status    Findings       Time
---------------------------------------------
 semgrep      ok             10       3.2s
 gitleaks     ok              2       0.8s
 trivy        ok              3       1.4s
---------------------------------------------
 Total                       15       5.4s

 By severity: 1 critical, 3 high, 7 medium, 4 low
```

## Using Fix Prompts with AI

After scanning, open `reports/fix-prompts.md` and paste it into your AI assistant:

> "Fix all the security issues listed below."

The prompts include file locations, code context, CWE references, and suggested fixes.

## Options

```
vibe-scan [TARGET] [OPTIONS]

  TARGET                Path to scan (default: current directory)

  -o, --output DIR      Output directory (default: ./reports)
  -f, --format FMT      json, markdown, or both (default: both)
  -s, --severity LVL    Minimum severity: critical, high, medium, low, info
  --skip-semgrep        Skip SAST scan
  --skip-gitleaks       Skip secret detection
  --skip-trivy          Skip dependency scan
  --github URL          Clone and scan a GitHub repo
  -b, --branch NAME     Branch to clone
  --token TOKEN         GitHub token for private repos

Subcommands:
  vibe-scan tools          Show installed tool versions
  vibe-scan update-tools   Re-download Gitleaks/Trivy
```

## Custom Rules

Vibe Scan includes custom Semgrep rules for common AI-generated code patterns:

- **Supabase**: Hardcoded keys, service role exposure, missing RLS filters
- **Next.js**: API routes without auth, XSS via dangerouslySetInnerHTML, exposed server env vars

Custom rules live in `vibe_scan/rules/` and are automatically loaded.

## MCP Server (AI Assistant Integration)

For integration with Windsurf, Cursor, or other MCP-compatible tools:

```bash
pip install vibe-scan[mcp]
vibe-scan-mcp
```

This starts an MCP server at `http://127.0.0.1:7654` with tools for scanning projects programmatically.

## Development

```bash
git clone https://github.com/alexkenley/vibe-code-scanner.git
cd vibe-code-scanner
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full design.

## License

MIT
