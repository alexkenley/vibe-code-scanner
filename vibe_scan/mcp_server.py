"""MCP server for AI assistant integration (optional dependency).

Install with: pip install vibe-scan[mcp]
Run with: vibe-scan-mcp
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def main():
    """Entry point for vibe-scan-mcp command."""
    try:
        import uvicorn
        from fastapi import FastAPI, HTTPException, Request
        from fastapi.middleware.cors import CORSMiddleware
        from pydantic import BaseModel, Field
    except ImportError:
        print("MCP server requires extra dependencies.")
        print("Install with: pip install vibe-scan[mcp]")
        raise SystemExit(1)

    parser = argparse.ArgumentParser(description="Vibe Scan MCP Server")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--port", type=int, default=7654, help="Port to bind to")
    args = parser.parse_args()

    # --- Models ---

    class ScanRequest(BaseModel):
        project_path: str = Field(..., description="Path to project directory")
        skip_semgrep: bool = False
        skip_gitleaks: bool = False
        skip_trivy: bool = False
        min_severity: str = "low"

    class ScanStatusResponse(BaseModel):
        scan_id: str
        status: str
        message: str | None = None
        started_at: str | None = None
        finished_at: str | None = None

    class ToolInfo(BaseModel):
        name: str
        description: str
        parameters: dict[str, Any]

    # --- State ---
    scan_results: dict[str, dict] = {}
    scan_statuses: dict[str, dict] = {}

    # --- App ---
    app = FastAPI(
        title="Vibe Scan MCP Server",
        description="Security scanner for AI-generated code",
        version="0.3.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/")
    async def root():
        return {"status": "ok", "service": "Vibe Scan MCP Server", "version": "0.3.0"}

    @app.get("/health")
    async def health():
        return {
            "status": "healthy",
            "active_scans": sum(
                1 for s in scan_statuses.values() if s["status"] == "running"
            ),
        }

    @app.get("/tools")
    async def list_tools():
        """List available MCP tools."""
        return {
            "tools": [
                {
                    "name": "scan_project",
                    "description": "Scan a project for security issues, secrets, and dependency vulnerabilities",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "project_path": {
                                "type": "string",
                                "description": "Path to the project directory to scan",
                            },
                            "skip_semgrep": {
                                "type": "boolean",
                                "description": "Skip SAST scan",
                                "default": False,
                            },
                            "skip_gitleaks": {
                                "type": "boolean",
                                "description": "Skip secret detection",
                                "default": False,
                            },
                            "skip_trivy": {
                                "type": "boolean",
                                "description": "Skip dependency scan",
                                "default": False,
                            },
                        },
                        "required": ["project_path"],
                    },
                },
                {
                    "name": "get_scan_status",
                    "description": "Get the status of a running or completed scan",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "scan_id": {
                                "type": "string",
                                "description": "The scan ID returned by scan_project",
                            },
                        },
                        "required": ["scan_id"],
                    },
                },
                {
                    "name": "get_scan_results",
                    "description": "Get the full results of a completed scan",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "scan_id": {
                                "type": "string",
                                "description": "The scan ID returned by scan_project",
                            },
                        },
                        "required": ["scan_id"],
                    },
                },
            ]
        }

    @app.post("/tools/scan_project")
    async def scan_project(request: ScanRequest):
        """Start a scan. Returns scan_id for status polling."""
        target = Path(request.project_path)
        if not target.is_dir():
            raise HTTPException(status_code=400, detail=f"Not a directory: {request.project_path}")

        scan_id = str(uuid.uuid4())[:8]
        scan_statuses[scan_id] = {
            "status": "running",
            "message": "Scan started",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "finished_at": None,
        }

        # Run scan in background
        asyncio.create_task(_run_scan_async(
            scan_id, target, request, scan_results, scan_statuses
        ))

        return {"scan_id": scan_id, "status": "running"}

    @app.get("/tools/get_scan_status/{scan_id}")
    async def get_scan_status(scan_id: str):
        if scan_id not in scan_statuses:
            raise HTTPException(status_code=404, detail="Scan not found")
        return {"scan_id": scan_id, **scan_statuses[scan_id]}

    @app.get("/tools/get_scan_results/{scan_id}")
    async def get_scan_results(scan_id: str):
        if scan_id not in scan_statuses:
            raise HTTPException(status_code=404, detail="Scan not found")
        if scan_statuses[scan_id]["status"] == "running":
            raise HTTPException(status_code=202, detail="Scan still running")
        if scan_id not in scan_results:
            raise HTTPException(status_code=404, detail="Results not found")
        return scan_results[scan_id]

    # SSE endpoint for MCP protocol
    @app.get("/sse")
    async def sse_endpoint(request: Request):
        try:
            from sse_starlette.sse import EventSourceResponse
        except ImportError:
            raise HTTPException(
                status_code=501,
                detail="SSE support requires sse-starlette. pip install vibe-scan[mcp]",
            )

        async def event_generator():
            yield {"event": "ready", "data": json.dumps({"type": "ready"})}
            while True:
                if await request.is_disconnected():
                    break
                yield {"event": "ping", "data": json.dumps({"type": "ping"})}
                await asyncio.sleep(30)

        return EventSourceResponse(event_generator())

    print(f"\nVibe Scan MCP Server starting at http://{args.host}:{args.port}")
    print(f"Tools endpoint: http://{args.host}:{args.port}/tools\n")

    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


async def _run_scan_async(
    scan_id: str,
    target: Path,
    request: Any,
    scan_results: dict,
    scan_statuses: dict,
):
    """Run scan in a thread pool to avoid blocking the event loop."""
    import asyncio
    from vibe_scan.scanner import Scanner, ScanOptions

    def _do_scan():
        options = ScanOptions(
            output_dir=target / "reports",
            skip_semgrep=request.skip_semgrep,
            skip_gitleaks=request.skip_gitleaks,
            skip_trivy=request.skip_trivy,
            min_severity=request.min_severity,
        )
        scanner = Scanner()
        return scanner.run(target, options)

    try:
        result = await asyncio.get_event_loop().run_in_executor(None, _do_scan)

        scan_results[scan_id] = {
            "scan_id": scan_id,
            "status": "completed",
            "summary": {
                "total_findings": len(result.findings),
                "languages": result.project_info.languages,
                "frameworks": result.project_info.frameworks,
                "duration_seconds": round(result.duration_seconds, 2),
            },
            "findings": [f.to_dict() for f in result.findings],
            "fix_prompts": [f.fix_prompt for f in result.findings if f.fix_prompt],
        }
        scan_statuses[scan_id]["status"] = "completed"
        scan_statuses[scan_id]["message"] = f"Found {len(result.findings)} issues"
        scan_statuses[scan_id]["finished_at"] = datetime.now(timezone.utc).isoformat()

    except Exception as e:
        scan_statuses[scan_id]["status"] = "failed"
        scan_statuses[scan_id]["message"] = str(e)
        scan_statuses[scan_id]["finished_at"] = datetime.now(timezone.utc).isoformat()


if __name__ == "__main__":
    main()
