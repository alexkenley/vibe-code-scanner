#!/usr/bin/env python
"""
Vibe Code Scanner MCP Server Launcher
This script helps launch the MCP server in the most appropriate way for your system.
"""

import os
import sys
import platform
import subprocess
import argparse
import shutil
import logging
import webbrowser
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("vibe_mcp_launcher")

def check_prerequisites():
    """Check if all prerequisites are installed"""
    missing = []
    
    # Check Python packages
    try:
        import fastapi
        import uvicorn
        import pydantic
    except ImportError as e:
        missing.append(f"Python package: {str(e).split()[-1]}")
    
    # Check if Docker is installed (for Docker mode)
    if not shutil.which("docker"):
        logger.warning("Docker is not installed. Docker mode will not be available.")
    
    if missing:
        logger.warning("Missing prerequisites: %s", ", ".join(missing))
        logger.info("Installing missing prerequisites...")
        
        # Install missing Python packages
        subprocess.run([
            sys.executable, "-m", "pip", "install", "-r", "requirements-server.txt"
        ], check=True)
        
        logger.info("Prerequisites installed successfully.")
    
    return True

def start_server_direct(host, port, log_level):
    """Start the server directly using Python"""
    logger.info(f"Starting MCP server directly at http://{host}:{port}")
    
    # Check if server.py exists
    if not os.path.exists("server.py"):
        logger.error("server.py not found. Make sure you're in the correct directory.")
        sys.exit(1)
    
    # Start the server
    cmd = [sys.executable, "server.py", "--host", host, "--port", str(port), "--log-level", log_level]
    
    try:
        # Open the URL in a browser after a short delay
        def open_browser():
            time.sleep(2)  # Give the server time to start
            webbrowser.open(f"http://{host}:{port}")
        
        import threading
        browser_thread = threading.Thread(target=open_browser)
        browser_thread.daemon = True
        browser_thread.start()
        
        # Run the server (this will block until the server is stopped)
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        logger.info("Server stopped by user.")
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        sys.exit(1)

def start_server_docker(host, port, build=False):
    """Start the server using Docker"""
    # Check if Docker is installed
    if not shutil.which("docker"):
        logger.error("Docker is not installed. Please install Docker to use this mode.")
        sys.exit(1)
    
    # Check if Dockerfile.mcp exists
    if not os.path.exists("Dockerfile.mcp"):
        logger.error("Dockerfile.mcp not found. Make sure you're in the correct directory.")
        sys.exit(1)
    
    # Build the Docker image if requested
    if build:
        logger.info("Building Docker image...")
        try:
            subprocess.run(["docker", "build", "-t", "vibe-mcp-server", "-f", "Dockerfile.mcp", "."], check=True)
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to build Docker image: {e}")
            sys.exit(1)
    
    # Run the Docker container
    logger.info(f"Starting MCP server in Docker at http://{host}:{port}")
    
    # Stop any existing container
    try:
        subprocess.run(["docker", "stop", "vibe-mcp-server"], stderr=subprocess.DEVNULL)
    except:
        pass  # Ignore errors if container doesn't exist
    
    # Start the container
    cmd = [
        "docker", "run", "--rm", "-it",
        "-p", f"{port}:8000",
        "--name", "vibe-mcp-server",
        "vibe-mcp-server"
    ]
    
    try:
        # Open the URL in a browser after a short delay
        def open_browser():
            time.sleep(5)  # Give the container time to start
            webbrowser.open(f"http://{host}:{port}")
        
        import threading
        browser_thread = threading.Thread(target=open_browser)
        browser_thread.daemon = True
        browser_thread.start()
        
        # Run the container (this will block until the container is stopped)
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        logger.info("Server stopped by user.")
    except Exception as e:
        logger.error(f"Failed to start server in Docker: {e}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Start the Vibe Code Scanner MCP Server")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind the server to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind the server to")
    parser.add_argument("--log-level", default="info", choices=["debug", "info", "warning", "error", "critical"], 
                        help="Logging level")
    parser.add_argument("--docker", action="store_true", help="Run the server in Docker")
    parser.add_argument("--build", action="store_true", help="Build the Docker image before starting (only with --docker)")
    
    args = parser.parse_args()
    
    # Print banner
    print("\n" + "=" * 80)
    print(" VIBE CODE SCANNER MCP SERVER ".center(80, "="))
    print("=" * 80)
    print(" Starting server... ".center(80))
    print("=" * 80 + "\n")
    
    # Check prerequisites for direct mode
    if not args.docker:
        check_prerequisites()
    
    # Start the server
    if args.docker:
        start_server_docker(args.host, args.port, args.build)
    else:
        start_server_direct(args.host, args.port, args.log_level)

if __name__ == "__main__":
    main()
