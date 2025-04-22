#!/usr/bin/env python3
"""
MCP Adapter for Vibe Code Scanner
This script creates a Model Context Protocol (MCP) adapter for the Vibe Code Scanner.
"""

import os
import sys
import json
import argparse
import logging
import requests
import uvicorn
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List, Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("vibe_mcp_adapter")

# Configuration - define at module level
SCANNER_URL = "http://127.0.0.1:8000"  # Default URL of the Vibe Code Scanner server

# Create FastAPI app
app = FastAPI(
    title="Vibe Code Scanner MCP Adapter",
    description="MCP adapter for Vibe Code Scanner",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MCP Models
class ToolCall(BaseModel):
    name: str
    parameters: Dict[str, Any]

class ToolResult(BaseModel):
    result: Any
    error: Optional[str] = None

# MCP Endpoints
@app.get("/")
async def root():
    """Root endpoint for health check"""
    return {"status": "ok", "service": "Vibe Code Scanner MCP Adapter"}

@app.get("/sse")
async def sse_endpoint():
    """Server-Sent Events endpoint for MCP"""
    return Response(
        content="data: {\"type\": \"ready\"}\n\n",
        media_type="text/event-stream"
    )

@app.post("/tools/{tool_name}")
async def handle_tool_call(tool_name: str, request: Request):
    """Handle MCP tool calls and translate them to Vibe Code Scanner API calls"""
    try:
        # Parse the request body
        body = await request.json()
        logger.info(f"Received tool call: {tool_name} with parameters: {body}")
        
        # Map MCP tool calls to Vibe Code Scanner API calls
        if tool_name == "scanProject":
            # Call the Vibe Code Scanner API to scan a project
            response = requests.post(
                f"{SCANNER_URL}/scan/project",
                json={
                    "project_path": body.get("projectPath", ""),
                    "language": body.get("language", None)
                }
            )
            
            if response.status_code == 200:
                return {"result": response.json()}
            else:
                return {"error": f"Scan failed with status code: {response.status_code}", "result": None}
                
        elif tool_name == "getScanStatus":
            # Call the Vibe Code Scanner API to get scan status
            scan_id = body.get("scanId", "")
            response = requests.get(f"{SCANNER_URL}/scan/{scan_id}/status")
            
            if response.status_code == 200:
                return {"result": response.json()}
            else:
                return {"error": f"Failed to get scan status with code: {response.status_code}", "result": None}
                
        elif tool_name == "getScanResult":
            # Call the Vibe Code Scanner API to get scan results
            scan_id = body.get("scanId", "")
            response = requests.get(f"{SCANNER_URL}/scan/{scan_id}/result")
            
            if response.status_code == 200:
                return {"result": response.json()}
            else:
                return {"error": f"Failed to get scan results with code: {response.status_code}", "result": None}
        
        else:
            return {"error": f"Unknown tool: {tool_name}", "result": None}
            
    except Exception as e:
        logger.error(f"Error handling tool call: {str(e)}")
        return {"error": str(e), "result": None}

@app.get("/tools")
async def get_tools():
    """Return the list of available tools"""
    return {
        "tools": [
            {
                "name": "scanProject",
                "description": "Scan a project directory for security and quality issues",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "projectPath": {
                            "type": "string",
                            "description": "Path to the project directory to scan"
                        },
                        "language": {
                            "type": "string",
                            "description": "Optional language to scan (python, javascript, typescript, go, ruby, nextjs, node)"
                        }
                    },
                    "required": ["projectPath"]
                }
            },
            {
                "name": "getScanStatus",
                "description": "Get the status of a scan",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "scanId": {
                            "type": "string",
                            "description": "ID of the scan to check"
                        }
                    },
                    "required": ["scanId"]
                }
            },
            {
                "name": "getScanResult",
                "description": "Get the results of a completed scan",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "scanId": {
                            "type": "string",
                            "description": "ID of the scan to get results for"
                        }
                    },
                    "required": ["scanId"]
                }
            }
        ]
    }

def start_server(host: str = "127.0.0.1", port: int = 8001):
    """Start the FastAPI server"""
    logger.info(f"Starting MCP adapter at http://{host}:{port}")
    logger.info(f"Connecting to Vibe Code Scanner at {SCANNER_URL}")
    uvicorn.run("mcp_adapter:app", host=host, port=port, log_level="info")

def update_scanner_url(url: str):
    """Update the scanner URL"""
    global SCANNER_URL
    SCANNER_URL = url
    logger.info(f"Updated scanner URL to {SCANNER_URL}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Start the Vibe Code Scanner MCP Adapter")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind the server to")
    parser.add_argument("--port", type=int, default=8001, help="Port to bind the server to")
    parser.add_argument("--scanner-url", default="http://127.0.0.1:8000", help="URL of the Vibe Code Scanner server")
    
    args = parser.parse_args()
    
    # Update the scanner URL if provided
    if args.scanner_url:
        update_scanner_url(args.scanner_url)
    
    print(f"\n{'=' * 80}")
    print(f" VIBE CODE SCANNER MCP ADAPTER ".center(80, "="))
    print(f"{'=' * 80}")
    print(f" Starting adapter at http://{args.host}:{args.port} ".center(80))
    print(f" Connecting to scanner at {SCANNER_URL} ".center(80))
    print(f"{'=' * 80}\n")
    
    start_server(args.host, args.port)
