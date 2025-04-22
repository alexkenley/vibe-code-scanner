# Vibe Code Scanner MCP Integration Guide

This guide explains how to use the Vibe Code Scanner as a Model-Code-Proxy (MCP) server with code editors like Cursor and Windsurf.

## What is an MCP Server?

A Model-Code-Proxy (MCP) server is a service that provides code analysis capabilities to AI-powered code editors. It acts as a bridge between the editor and various code analysis tools, providing structured data that can be used by AI assistants to give better recommendations and insights.

## Getting Started

### Prerequisites

- Python 3.8 or higher
- Required Python packages (installed automatically by the launcher script):
  - FastAPI
  - Uvicorn
  - Pydantic
- For Docker mode (optional):
  - Docker Desktop

### Starting the MCP Server

#### Option 1: Direct Mode (Recommended for Development)

This mode runs the server directly on your machine:

```bash
# Windows
python start_mcp_server.py

# Linux/macOS
python3 start_mcp_server.py
```

#### Option 2: Docker Mode (Recommended for Production)

This mode runs the server in a Docker container with all dependencies pre-installed:

```bash
# Build and start the Docker container
python start_mcp_server.py --docker --build

# Start an existing Docker container (skip build)
python start_mcp_server.py --docker
```

### Verifying the Server is Running

Once started, the server will be available at http://127.0.0.1:8000 by default. You can verify it's running by:

1. Opening a web browser and navigating to http://127.0.0.1:8000/health
2. Using the client to check server health:
   ```python
   from mcp_client import VibeCodeScannerClient
   
   client = VibeCodeScannerClient()
   health = client.check_server_health()
   print(health)
   ```

## Integrating with Cursor

### Setup in Cursor

1. Open Cursor and go to Settings (gear icon)
2. Navigate to "Extensions" or "Integrations"
3. Look for "Custom MCP Servers" or similar
4. Add a new MCP server with:
   - Name: "Vibe Code Scanner"
   - URL: "http://127.0.0.1:8000"
   - (Optional) API Key: Leave blank unless you've configured authentication

### Using in Cursor

Once configured, Cursor will automatically use the Vibe Code Scanner for code analysis:

1. As you code, the scanner will analyze your files in real-time
2. Issues will be highlighted directly in the editor
3. The AI assistant will have access to scan results to provide context-aware suggestions
4. You can explicitly ask the AI about code quality or security issues

Example prompts to use with Cursor:

- "What security issues exist in this file?"
- "Check this code for best practices"
- "How can I fix the quality issues in this function?"

## Integrating with Windsurf

### Setup in Windsurf

1. Open Windsurf and go to Settings
2. Navigate to "Integrations" or "Extensions"
3. Find "Code Analysis" or "MCP Servers"
4. Add a new server with:
   - Name: "Vibe Code Scanner"
   - URL: "http://127.0.0.1:8000"
   - (Optional) Authentication: Configure if needed

### Using in Windsurf

Windsurf will integrate the scanner results into its AI capabilities:

1. The AI will have access to code quality and security information
2. You can request specific analyses through the chat interface
3. Scan results will enhance the AI's understanding of your codebase

Example prompts for Windsurf:

- "Analyze this file for security vulnerabilities"
- "What code quality issues exist in this project?"
- "Help me understand and fix the issues found by the scanner"

## Advanced Configuration

### Changing the Host and Port

```bash
python start_mcp_server.py --host 0.0.0.0 --port 9000
```

### Setting Log Level

```bash
python start_mcp_server.py --log-level debug
```

### Securing the Server (Production Use)

For production environments, consider:

1. Implementing proper authentication
2. Using HTTPS with a valid certificate
3. Restricting CORS to specific origins
4. Running behind a reverse proxy like Nginx

## Using the Client Library

The `mcp_client.py` module provides a Python client for interacting with the MCP server programmatically:

```python
from mcp_client import VibeCodeScannerClient

# Initialize client
client = VibeCodeScannerClient("http://127.0.0.1:8000")

# Check server health
health = client.check_server_health()
print(f"Server status: {health['status']}")

# Scan a project
scan_id = client.scan_project("/path/to/project", language="python")
result = client.wait_for_scan_completion(scan_id)
print(f"Issues found: {result['summary']['issues_found']}")

# Scan a single file
file_result = client.scan_file("/path/to/file.js", language="javascript")
print(f"Issues found: {file_result['summary']['issues_found']}")
```

## API Reference

The MCP server exposes the following REST API endpoints:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Health check |
| `/health` | GET | Detailed health information |
| `/capabilities` | GET | Server capabilities |
| `/scan/project` | POST | Start a project scan |
| `/scan/file` | POST | Scan a single file |
| `/scan/{scan_id}/status` | GET | Get scan status |
| `/scan/{scan_id}/result` | GET | Get scan results |
| `/scan/{scan_id}` | DELETE | Cancel a scan |

## Troubleshooting

### Common Issues

1. **Server won't start**:
   - Check Python version (`python --version`)
   - Ensure all dependencies are installed (`pip install -r requirements-server.txt`)
   - Verify port is not in use by another application

2. **Docker mode fails**:
   - Ensure Docker is running
   - Check Docker logs (`docker logs vibe-mcp-server`)
   - Rebuild the image with `--build` flag

3. **Editor integration not working**:
   - Verify server is running (http://127.0.0.1:8000/health)
   - Check editor logs for connection errors
   - Ensure correct URL is configured in editor settings

### Getting Help

If you encounter issues:

1. Check the server logs (`vibe_mcp_server.log`)
2. Increase log level for more details (`--log-level debug`)
3. Open an issue on the GitHub repository with detailed information

## Security Considerations

The MCP server has access to your code and runs various tools on it. To ensure security:

1. Only run the server on trusted networks
2. Don't expose the server to the internet without proper security measures
3. Review the code and tools being used
4. Keep all components updated

## Performance Optimization

For large projects:

1. Increase available memory for the server
2. Use incremental scanning when possible
3. Consider running resource-intensive tools in separate processes
4. Use the Docker mode for better isolation and resource management
