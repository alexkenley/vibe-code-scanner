#!/usr/bin/env python3
"""
Minimal MCP Server
This implements the absolute minimum required for an MCP server to work with Windsurf.
"""

import os
import sys
import json
import logging
import uvicorn
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("minimal_mcp")

# Create FastAPI app
app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """Root endpoint"""
    logger.info("Root endpoint called")
    return {"status": "ok", "service": "Minimal MCP Server"}

@app.get("/sse")
async def sse():
    """Server-Sent Events endpoint required by MCP protocol"""
    logger.info("SSE endpoint called")
    return Response(
        content="data: {\"type\": \"ready\"}\n\n",
        media_type="text/event-stream"
    )

@app.get("/tools")
async def get_tools():
    """Return available tools"""
    logger.info("Tools endpoint called")
    return {
        "tools": [
            {
                "name": "hello",
                "description": "A simple hello world tool",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Name to greet"
                        }
                    },
                    "required": ["name"]
                }
            }
        ]
    }

@app.post("/tools/hello")
async def hello(request: Request):
    """Simple hello world tool"""
    try:
        body = await request.json()
        name = body.get("name", "World")
        logger.info(f"Hello tool called with name: {name}")
        return {"result": f"Hello, {name}!"}
    except Exception as e:
        logger.error(f"Error in hello tool: {e}")
        return {"error": str(e)}

if __name__ == "__main__":
    port = 9876  # Use a different port
    print(f"\n{'=' * 80}")
    print(f" MINIMAL MCP SERVER ".center(80, "="))
    print(f"{'=' * 80}")
    print(f" Starting server at http://127.0.0.1:{port} ".center(80))
    print(f"{'=' * 80}\n")
    
    uvicorn.run("minimal_mcp:app", host="127.0.0.1", port=port, log_level="debug")
