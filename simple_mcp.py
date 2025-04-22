#!/usr/bin/env python3
"""
Simple MCP Server for Vibe Code Scanner
This implements a minimal MCP server that follows the protocol exactly.
"""

import os
import sys
import json
import logging
import subprocess
import uvicorn
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any, List, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("simple_mcp")

# Create FastAPI app
app = FastAPI(title="Simple MCP Server")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MCP Endpoints
@app.get("/")
async def root():
    """Root endpoint"""
    return {"status": "ok", "service": "Simple MCP Server for Vibe Code Scanner"}

@app.get("/sse")
async def sse():
    """Server-Sent Events endpoint required by MCP protocol"""
    return Response(
        content="data: {\"type\": \"ready\"}\n\n",
        media_type="text/event-stream"
    )

@app.get("/tools")
async def get_tools():
    """Return available tools"""
    return {
        "tools": [
            {
                "name": "scanCode",
                "description": "Scan code for security and quality issues",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Path to the project or file to scan"
                        },
                        "language": {
                            "type": "string",
                            "description": "Optional language to scan (python, javascript, typescript, go, ruby, nextjs, node)"
                        }
                    },
                    "required": ["path"]
                }
            }
        ]
    }

@app.post("/tools/scanCode")
async def scan_code(request: Request):
    """Handle scan code requests"""
    try:
        # Parse request body
        body = await request.json()
        path = body.get("path", "")
        language = body.get("language", None)
        
        logger.info(f"Scanning path: {path}, language: {language}")
        
        # Build command
        cmd = [sys.executable, "scan.py", path]
        if language:
            cmd.extend(["--language", language])
        
        # Run scanner
        logger.info(f"Running command: {' '.join(cmd)}")
        process = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.abspath(__file__))
        )
        
        # Process results
        stdout = process.stdout
        stderr = process.stderr
        returncode = process.returncode
        
        # Try to load report file if it exists
        report_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vibe_scan_report.json")
        report_data = None
        if os.path.exists(report_file):
            try:
                with open(report_file, "r") as f:
                    report_data = json.load(f)
            except Exception as e:
                logger.error(f"Error loading report file: {e}")
        
        # Return results
        return {
            "result": {
                "success": returncode == 0,
                "output": stdout,
                "errors": stderr if stderr else None,
                "report": report_data
            }
        }
    except Exception as e:
        logger.error(f"Error processing scan request: {e}", exc_info=True)
        return {"error": str(e)}

if __name__ == "__main__":
    port = 8765  # Use a different port to avoid conflicts
    print(f"\n{'=' * 80}")
    print(f" SIMPLE MCP SERVER ".center(80, "="))
    print(f"{'=' * 80}")
    print(f" Starting server at http://127.0.0.1:{port} ".center(80))
    print(f"{'=' * 80}\n")
    
    uvicorn.run("simple_mcp:app", host="127.0.0.1", port=port, log_level="info")
