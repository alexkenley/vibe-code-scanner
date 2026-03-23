"""CLI entry point for vibe-scan."""

import click
from rich.console import Console

from vibe_scan import __version__

console = Console()


@click.group(invoke_without_command=True)
@click.argument("target", default=".", type=click.Path(exists=True), required=False)
@click.option("--output", "-o", default="./reports", help="Output directory for reports.")
@click.option(
    "--format", "-f", "output_format",
    type=click.Choice(["json", "markdown", "both"]),
    default="both",
    help="Output format.",
)
@click.option(
    "--severity", "-s",
    type=click.Choice(["critical", "high", "medium", "low", "info"]),
    default="low",
    help="Minimum severity to report.",
)
@click.option("--skip-semgrep", is_flag=True, help="Skip Semgrep SAST scan.")
@click.option("--skip-gitleaks", is_flag=True, help="Skip Gitleaks secret detection.")
@click.option("--skip-trivy", is_flag=True, help="Skip Trivy dependency scan.")
@click.option("--github", "github_url", help="GitHub repo URL to clone and scan.")
@click.option("--branch", "-b", help="Branch to clone (with --github).")
@click.option("--token", help="GitHub token for private repos.")
@click.version_option(version=__version__)
@click.pass_context
def main(ctx, target, output, output_format, severity, skip_semgrep, skip_gitleaks,
         skip_trivy, github_url, branch, token):
    """Vibe Scan -- security scanner for AI-generated code.

    Scans your project for security issues, vulnerable dependencies,
    and hardcoded secrets. Generates AI-ready fix prompts.

    \b
    Examples:
        vibe-scan                     Scan current directory
        vibe-scan ./my-project        Scan a specific directory
        vibe-scan --github https://github.com/user/repo
    """
    if ctx.invoked_subcommand is not None:
        return

    from pathlib import Path
    from vibe_scan.scanner import Scanner, ScanOptions

    options = ScanOptions(
        output_dir=Path(output),
        output_format=output_format,
        min_severity=severity,
        skip_semgrep=skip_semgrep,
        skip_gitleaks=skip_gitleaks,
        skip_trivy=skip_trivy,
        github_url=github_url,
        branch=branch,
        token=token,
    )

    scanner = Scanner()
    scanner.run(Path(target), options)


@main.command()
def tools():
    """Show installed tool versions and status."""
    from vibe_scan.binary_manager import BinaryManager
    import shutil
    import subprocess

    bm = BinaryManager()

    console.print("\n[bold]Vibe Scan Tool Status[/bold]\n")

    # Semgrep
    semgrep_path = shutil.which("semgrep")
    if semgrep_path:
        try:
            result = subprocess.run(
                ["semgrep", "--version"], capture_output=True, text=True, timeout=10
            )
            ver = result.stdout.strip()
            console.print(f"  Semgrep    [green]installed[/green]  v{ver}  (pip)")
        except Exception:
            console.print(f"  Semgrep    [green]installed[/green]  (version unknown)")
    else:
        console.print("  Semgrep    [red]not found[/red]   pip install semgrep")

    # Gitleaks
    try:
        path = bm.ensure_tool("gitleaks")
        result = subprocess.run(
            [str(path), "version"], capture_output=True, text=True, timeout=10
        )
        ver = result.stdout.strip()
        console.print(f"  Gitleaks   [green]installed[/green]  {ver}  ({path})")
    except Exception as e:
        console.print(f"  Gitleaks   [yellow]not cached[/yellow]  will download on first scan")

    # Trivy
    try:
        path = bm.ensure_tool("trivy")
        result = subprocess.run(
            [str(path), "--version"], capture_output=True, text=True, timeout=10
        )
        ver = result.stdout.strip().split("\n")[0]
        console.print(f"  Trivy      [green]installed[/green]  {ver}  ({path})")
    except Exception as e:
        console.print(f"  Trivy      [yellow]not cached[/yellow]  will download on first scan")

    console.print()


@main.command(name="update-tools")
def update_tools():
    """Force re-download of Gitleaks and Trivy binaries."""
    from vibe_scan.binary_manager import BinaryManager

    bm = BinaryManager()
    bm.clear_cache()

    console.print("Cache cleared. Tools will be re-downloaded on next scan.")
