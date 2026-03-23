"""MCP server for AI assistant integration (optional dependency)."""


def main():
    """Entry point for vibe-scan-mcp command."""
    try:
        from fastapi import FastAPI
    except ImportError:
        print("MCP server requires extra dependencies.")
        print("Install with: pip install vibe-scan[mcp]")
        raise SystemExit(1)

    print("MCP server not yet implemented.")
    raise SystemExit(1)
