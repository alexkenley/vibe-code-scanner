import argparse
import os
import sys
import logging
import uvicorn
from fastapi import FastAPI, HTTPException, Depends, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any, Union
import json
import uuid
from datetime import datetime
import asyncio

# Import the existing scanner functionality
from scan import (
    detect_language, 
    run_tools, 
    find_files_by_extension,
    check_supabase_integration,
    check_prerequisite
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("vibe_mcp_server.log", mode='a'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("vibe_mcp_server")

# Create FastAPI app
app = FastAPI(
    title="Vibe Code Scanner MCP Server",
    description="A Model-Code-Proxy server for code quality and security scanning",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this to specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory cache for scan results
scan_cache = {}
active_scans = {}

# Models for API requests and responses
class ScanRequest(BaseModel):
    project_path: str = Field(..., description="Path to the project directory to scan")
    language: Optional[str] = Field(None, description="Specify language to scan (python, javascript, typescript, go, ruby)")
    scan_id: Optional[str] = Field(None, description="Optional client-provided scan ID")

class FileContent(BaseModel):
    path: str = Field(..., description="Path to the file")
    content: str = Field(..., description="Content of the file")

class FileScanRequest(BaseModel):
    file_content: FileContent
    language: str = Field(..., description="Language of the file (python, javascript, typescript, go, ruby)")

class ScanStatus(BaseModel):
    scan_id: str
    status: str  # "pending", "running", "completed", "failed"
    progress: Optional[float] = None
    message: Optional[str] = None
    start_time: datetime
    end_time: Optional[datetime] = None

class ScanResult(BaseModel):
    scan_id: str
    status: str
    report: Optional[Dict[str, Any]] = None
    raw_outputs: Optional[Dict[str, str]] = None
    summary: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "ok", "service": "Vibe Code Scanner MCP Server"}

@app.get("/health")
async def health_check():
    """Detailed health check endpoint"""
    # Check if essential tools are available
    tools_status = {
        "python": is_tool_installed("python"),
        "node": is_tool_installed("node"),
        "npx": is_tool_installed("npx"),
        "go": is_tool_installed("go"),
        "ruby": is_tool_installed("ruby")
    }
    
    return {
        "status": "healthy",
        "version": "1.0.0",
        "tools": tools_status,
        "active_scans": len(active_scans),
        "cached_results": len(scan_cache)
    }

@app.post("/scan/project", response_model=ScanStatus)
async def scan_project(request: ScanRequest, background_tasks: BackgroundTasks):
    """
    Start a scan of a project directory.
    Returns a scan ID that can be used to check the status and get results.
    """
    # Validate project path
    if not os.path.isdir(request.project_path):
        raise HTTPException(status_code=400, detail=f"Project path does not exist: {request.project_path}")
    
    # Generate scan ID if not provided
    scan_id = request.scan_id or str(uuid.uuid4())
    
    # Check if scan with this ID already exists
    if scan_id in active_scans:
        return active_scans[scan_id]
    
    # Create scan status
    scan_status = ScanStatus(
        scan_id=scan_id,
        status="pending",
        message="Scan queued",
        start_time=datetime.now()
    )
    
    # Store in active scans
    active_scans[scan_id] = scan_status
    
    # Start scan in background
    background_tasks.add_task(
        run_project_scan,
        scan_id,
        request.project_path,
        request.language
    )
    
    return scan_status

async def run_project_scan(scan_id: str, project_path: str, language: Optional[str] = None):
    """Run a project scan in the background"""
    try:
        # Update status to running
        active_scans[scan_id].status = "running"
        active_scans[scan_id].message = "Scan in progress"
        
        # Detect language if not specified
        if not language:
            detected_language = detect_language(project_path, None)
            if not detected_language:
                raise Exception("Could not detect project language")
            language = detected_language
        
        # Run tools
        results = run_tools(project_path, language)
        
        # Generate report
        temp_output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp_reports", scan_id)
        os.makedirs(temp_output_dir, exist_ok=True)
        
        report_path = generate_report(results, temp_output_dir)
        
        # Read the generated report
        with open(os.path.join(temp_output_dir, "vibe_scan_report.json"), "r") as f:
            report = json.load(f)
        
        # Read raw outputs
        raw_outputs = {}
        for tool, result in results.items():
            if result.get("raw_output_file") and os.path.exists(result["raw_output_file"]):
                with open(result["raw_output_file"], "r", encoding="utf-8") as f:
                    raw_outputs[tool] = f.read()
        
        # Create scan result
        scan_result = ScanResult(
            scan_id=scan_id,
            status="completed",
            report=report,
            raw_outputs=raw_outputs,
            summary={
                "language": language,
                "tools_run": list(results.keys()),
                "issues_found": sum(1 for tool in results.values() for issue in tool.get("issues", []))
            }
        )
        
        # Cache the result
        scan_cache[scan_id] = scan_result
        
        # Update status
        active_scans[scan_id].status = "completed"
        active_scans[scan_id].message = "Scan completed successfully"
        active_scans[scan_id].end_time = datetime.now()
        
    except Exception as e:
        logger.error(f"Scan {scan_id} failed: {str(e)}", exc_info=True)
        
        # Create error result
        scan_result = ScanResult(
            scan_id=scan_id,
            status="failed",
            error=str(e)
        )
        
        # Cache the result
        scan_cache[scan_id] = scan_result
        
        # Update status
        active_scans[scan_id].status = "failed"
        active_scans[scan_id].message = f"Scan failed: {str(e)}"
        active_scans[scan_id].end_time = datetime.now()

@app.post("/scan/file", response_model=ScanResult)
async def scan_file(request: FileScanRequest):
    """
    Scan a single file provided in the request.
    Returns the scan results directly.
    """
    try:
        # Create a temporary directory for the file
        temp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp_files", str(uuid.uuid4()))
        os.makedirs(temp_dir, exist_ok=True)
        
        # Write the file to the temporary directory
        file_path = os.path.join(temp_dir, os.path.basename(request.file_content.path))
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(request.file_content.content)
        
        # Run tools on the file
        results = run_tools(temp_dir, request.language)
        
        # Generate report
        temp_output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp_reports", str(uuid.uuid4()))
        os.makedirs(temp_output_dir, exist_ok=True)
        
        report_path = generate_report(results, temp_output_dir)
        
        # Read the generated report
        with open(os.path.join(temp_output_dir, "vibe_scan_report.json"), "r") as f:
            report = json.load(f)
        
        # Read raw outputs
        raw_outputs = {}
        for tool, result in results.items():
            if result.get("raw_output_file") and os.path.exists(result["raw_output_file"]):
                with open(result["raw_output_file"], "r", encoding="utf-8") as f:
                    raw_outputs[tool] = f.read()
        
        # Create scan result
        scan_result = ScanResult(
            scan_id=str(uuid.uuid4()),
            status="completed",
            report=report,
            raw_outputs=raw_outputs,
            summary={
                "language": request.language,
                "tools_run": list(results.keys()),
                "issues_found": sum(1 for tool in results.values() for issue in tool.get("issues", []))
            }
        )
        
        return scan_result
        
    except Exception as e:
        logger.error(f"File scan failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Clean up temporary files
        if 'temp_dir' in locals() and os.path.exists(temp_dir):
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

@app.get("/scan/{scan_id}/status", response_model=ScanStatus)
async def get_scan_status(scan_id: str):
    """Get the status of a scan"""
    if scan_id not in active_scans:
        raise HTTPException(status_code=404, detail=f"Scan with ID {scan_id} not found")
    
    return active_scans[scan_id]

@app.get("/scan/{scan_id}/result", response_model=ScanResult)
async def get_scan_result(scan_id: str):
    """Get the results of a completed scan"""
    # Check if scan is still running
    if scan_id in active_scans and active_scans[scan_id].status in ["pending", "running"]:
        raise HTTPException(status_code=202, detail="Scan is still in progress")
    
    # Check if result is in cache
    if scan_id not in scan_cache:
        raise HTTPException(status_code=404, detail=f"Results for scan {scan_id} not found")
    
    return scan_cache[scan_id]

@app.delete("/scan/{scan_id}")
async def cancel_scan(scan_id: str):
    """Cancel a running scan and clean up resources"""
    if scan_id not in active_scans:
        raise HTTPException(status_code=404, detail=f"Scan with ID {scan_id} not found")
    
    # Update status
    active_scans[scan_id].status = "cancelled"
    active_scans[scan_id].message = "Scan cancelled by user"
    active_scans[scan_id].end_time = datetime.now()
    
    # Clean up resources
    if scan_id in scan_cache:
        del scan_cache[scan_id]
    
    return {"status": "cancelled", "scan_id": scan_id}

@app.get("/capabilities")
async def get_capabilities():
    """Get the capabilities of the server"""
    return {
        "languages": ["python", "javascript", "typescript", "go", "ruby"],
        "tools": {
            "python": ["flake8", "bandit"],
            "javascript": ["eslint", "retirejs"],
            "typescript": ["eslint", "tsc", "retirejs"],
            "go": ["golangci-lint", "gosec"],
            "ruby": ["rubocop", "brakeman"]
        },
        "features": [
            "project_scanning",
            "file_scanning",
            "background_scanning",
            "status_tracking",
            "result_caching"
        ]
    }

def start_server(host: str = "127.0.0.1", port: int = 8000, log_level: str = "info"):
    """Start the FastAPI server"""
    uvicorn.run("server:app", host=host, port=port, log_level=log_level, reload=True)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Start the Vibe Code Scanner MCP Server")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind the server to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind the server to")
    parser.add_argument("--log-level", default="info", choices=["debug", "info", "warning", "error", "critical"], 
                        help="Logging level")
    
    args = parser.parse_args()
    
    print(f"\n{'=' * 80}")
    print(f" VIBE CODE SCANNER MCP SERVER ".center(80, "="))
    print(f"{'=' * 80}")
    print(f" Starting server at http://{args.host}:{args.port} ".center(80))
    print(f"{'=' * 80}\n")
    
    start_server(args.host, args.port, args.log_level)
