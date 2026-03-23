# Vibe Scan Usage Guide

## Installation

```bash
pip install vibe-scan
```

Requires Python 3.9 or higher. Works on Linux, macOS, and WSL.

## Quick Start

Open a terminal in the project you want to scan and run:

```bash
vibe-scan
```

That's it. Results appear in `./reports/`.

## Scanning Your Project

### From your IDE

1. Open your project in VS Code, Cursor, Windsurf, or any editor
2. Open the integrated terminal
3. Run `vibe-scan`

### From any terminal

```bash
# Scan the current directory
vibe-scan

# Scan a specific directory
vibe-scan ./path/to/project

# Scan a GitHub repo directly
vibe-scan --github https://github.com/username/repo

# Scan a specific branch
vibe-scan --github https://github.com/username/repo --branch develop

# Scan a private repo
vibe-scan --github https://github.com/username/repo --token ghp_your_token
```

## Understanding the Output

### Terminal Summary

After a scan, you'll see a summary like this:

```
Scanning: /home/user/my-app

  Languages:  javascript, typescript
  Frameworks: nextjs, supabase

  semgrep      done  10 findings  (3.2s)
  gitleaks     done   2 findings  (0.8s)
  trivy        done   3 findings  (1.4s)

┌──────────────┬──────────┬────────────┬──────────┐
│ Tool         │ Status   │   Findings │     Time │
├──────────────┼──────────┼────────────┼──────────┤
│ semgrep      │ ok       │         10 │     3.2s │
│ gitleaks     │ ok       │          2 │     0.8s │
│ trivy        │ ok       │          3 │     1.4s │
├──────────────┼──────────┼────────────┼──────────┤
│ Total        │          │         15 │     5.4s │
└──────────────┴──────────┴────────────┴──────────┘

  By severity: 1 critical, 3 high, 7 medium, 4 low

  Reports saved to: ./reports/
```

### Report Files

Two files are generated in `./reports/` (or wherever you specify with `--output`):

**`vibe-scan-report.json`** — Structured JSON with all findings, metadata, and severity breakdowns. Useful for CI/CD integration or programmatic analysis.

**`fix-prompts.md`** — Markdown file designed to be pasted directly into an AI assistant. Each finding includes the file, line number, code context, and a description of what to fix.

## Fixing Issues with AI

This is the recommended workflow:

1. Run `vibe-scan` on your project
2. Open `reports/fix-prompts.md`
3. Copy the entire file
4. Paste it into Cursor, Claude, Copilot, or ChatGPT
5. Tell it: **"Fix all the security issues listed below."**

The fix prompts include enough context (file paths, line numbers, code snippets, CWE references) for the AI to make targeted fixes.

## Controlling What Gets Scanned

### Skip specific tools

```bash
# Only run Semgrep (SAST) — skip secrets and dependency scanning
vibe-scan --skip-gitleaks --skip-trivy

# Only check for secrets
vibe-scan --skip-semgrep --skip-trivy

# Only check dependencies
vibe-scan --skip-semgrep --skip-gitleaks
```

### Filter by severity

```bash
# Only show critical and high issues
vibe-scan --severity high

# Only show critical issues
vibe-scan --severity critical

# Show everything including informational
vibe-scan --severity info
```

### Change output format

```bash
# JSON only (no markdown)
vibe-scan --format json

# Markdown only (no JSON)
vibe-scan --format markdown

# Both (default)
vibe-scan --format both
```

### Change output directory

```bash
vibe-scan --output ./my-reports
```

## What Each Tool Finds

### Semgrep (SAST)

Static analysis covering 30+ languages. Finds:
- SQL injection, XSS, command injection
- Hardcoded credentials in code
- Insecure use of eval(), exec(), subprocess
- Missing authentication on API routes
- OWASP Top 10 vulnerabilities
- Framework-specific issues (Next.js, Django, Flask, Express, Rails)
- Supabase misconfigurations (missing RLS, exposed service keys)

### Gitleaks (Secret Detection)

Scans for 150+ types of secrets:
- AWS access keys and secrets
- GitHub/GitLab tokens
- Supabase JWT tokens
- Stripe API keys
- Database connection strings
- Private keys and certificates
- Generic passwords and API keys

### Trivy (Dependency Scanning)

Checks your dependency files for known vulnerabilities:
- `package.json` / `package-lock.json` (npm)
- `requirements.txt` / `Pipfile.lock` (pip)
- `Gemfile.lock` (Ruby)
- `go.sum` (Go)
- `Cargo.lock` (Rust)
- Dockerfile misconfigurations
- License compliance issues

## First Run

On the very first scan, Gitleaks and Trivy will be automatically downloaded:

```
Downloading gitleaks v8.24.3 for linux/x86_64...
Cached at ~/.cache/vibe-scan/bin/gitleaks-8.24.3/gitleaks

Downloading trivy v0.62.1 for linux/x86_64...
Cached at ~/.cache/vibe-scan/bin/trivy-0.62.1/trivy
```

This is a one-time download (~50MB each). After that, they're cached locally and scans start instantly.

## Managing Tools

```bash
# Check what's installed and where
vibe-scan tools

# Force re-download of Gitleaks and Trivy
vibe-scan update-tools
```

### Using your own tool installations

If you already have Gitleaks or Trivy installed, vibe-scan will use them automatically (it checks your PATH first). You can also point to specific binaries:

```bash
export VIBE_SCAN_GITLEAKS_PATH=/usr/local/bin/gitleaks
export VIBE_SCAN_TRIVY_PATH=/usr/local/bin/trivy
vibe-scan
```

## MCP Server (AI Assistant Integration)

If your IDE supports MCP (Model Context Protocol), you can integrate vibe-scan directly so your AI assistant can trigger scans:

```bash
# Install with MCP dependencies
pip install vibe-scan[mcp]

# Start the server
vibe-scan-mcp
```

The server runs at `http://127.0.0.1:7654`. Configure your IDE's MCP settings to point to this URL.

### Windsurf Configuration

Create or edit `~/.codeium/windsurf/mcp_config.json`:

```json
{
  "mcpServers": {
    "vibeScan": {
      "baseUrl": "http://127.0.0.1:7654",
      "transport": "sse"
    }
  }
}
```

Then ask your AI assistant: "Scan this project for security vulnerabilities."

## Troubleshooting

**"semgrep not found"** — Semgrep should have been installed with vibe-scan. Try `pip install semgrep` directly.

**Gitleaks/Trivy download fails** — You may be behind a corporate proxy. Install them manually and set the environment variables:
```bash
export VIBE_SCAN_GITLEAKS_PATH=/path/to/gitleaks
export VIBE_SCAN_TRIVY_PATH=/path/to/trivy
```

**Scan is slow** — First Semgrep run downloads rule packs (~30 seconds). Subsequent runs are faster. You can also skip tools you don't need with `--skip-*` flags.

**No findings on a project I know has issues** — Check that the language was detected correctly (shown at the top of the output). You can also try lowering the severity filter: `vibe-scan --severity info`.

**Permission denied on cached binaries** — Clear the cache and re-download:
```bash
vibe-scan update-tools
```
