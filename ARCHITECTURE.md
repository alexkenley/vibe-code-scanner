# Vibe Code Scanner Architecture

## Overview

Vibe Code Scanner is designed as a command-line Python script (`scan.py`) intended to be run locally by developers to identify code quality and security issues in their projects.

## Docker-Based Execution Model

**Important:** Vibe Code Scanner is designed to be run within a Docker container, not directly on the host system. This design choice ensures:

1. **Consistent Environment:** All required tools and dependencies are pre-installed in the container.
2. **No Local Tool Installation:** Users don't need to install language-specific tools on their machines.
3. **Cross-Platform Compatibility:** Works the same way across Windows, macOS, and Linux.
4. **Isolation:** Scanning operations run in an isolated environment.

The workflow is:
1. Build the Docker image using the provided Dockerfile
2. Run the scanner by mounting the target code directory into the container
3. View the generated reports in the target directory

Direct execution of `scan.py` on the host system is not recommended and will likely fail due to missing dependencies.

## Guiding Principle: Simplicity ("Follow the Bouncing Ball")

**Target Audience:** Developers with less coding experience (e.g., designers who code, "vibe coders").
**Core Goal:** Make code quality and security scanning accessible and easy.
**Implications:**
    *   **Minimal Setup:** Keep dependencies and configuration straightforward.
    *   **Simple Execution:** Single command execution.
    *   **Clear, Jargon-Free Reporting:** Explain findings in plain language.
    *   **Focus:** Prioritize common, high-impact best practice and security issues.
    *   **Actionable Output:** The report should clearly guide the user on potential next steps (e.g., using the report with an IDE AI assistant).

## Core Components

1.  **Command-Line Interface (CLI):**
    *   Uses Python's `argparse` module to accept the target project directory path and optional language specification.
    *   Provides helpful examples and guidance in the help text.
    *   Supports scanning GitHub repositories directly with the `--github` flag.

2.  **Language Detection Module:**
    *   A function within `scan.py` that analyzes the target directory's contents to determine the primary language.
    *   Detects languages based on file extensions and configuration files (e.g., `package.json`, `requirements.txt`, `tsconfig.json`).
    *   Supports Python, JavaScript, TypeScript, Go, and Ruby.
    *   Prioritizes user-specified language over auto-detection.

3.  **GitHub Repository Cloning:**
    *   Clones specified GitHub repositories to temporary directories.
    *   Supports cloning specific branches with the `-b` flag.
    *   Handles authentication for private repositories using personal access tokens.
    *   Automatically cleans up temporary directories after scanning.
    *   Handles errors gracefully with appropriate user feedback.

4.  **Prerequisite Checker:**
    *   Checks if required tools are installed before attempting to run them.
    *   Provides clear, actionable feedback when tools are missing.
    *   Directs users to the README for installation instructions.
    *   Uses `shutil.which()` to verify tool availability in the system PATH.

5.  **Static Analysis Tool Runner:**
    *   Uses Python's `subprocess` module to execute language-specific static analysis tools.
    *   Captures stdout, stderr, and return codes from each tool.
    *   Handles tool execution errors gracefully.
    *   Supported tools:
        *   **Python:** Flake8, Bandit
        *   **JavaScript/TypeScript:** ESLint (via npx)
        *   **Go:** golangci-lint, gosec
        *   **Ruby:** RuboCop (for code quality), Brakeman (for Rails security scanning)

6.  **Output Parsers:**
    *   Dedicated parser functions for each tool's output format.
    *   Handles both plain text and JSON output formats.
    *   Normalizes tool-specific output into a consistent issue format.
    *   Includes robust error handling for parsing failures.
    *   **Note:** While parsers are still included for backward compatibility, the primary approach now focuses on preserving raw tool outputs.

7.  **Report Generator:**
    *   Saves raw tool outputs to individual files for detailed analysis.
    *   Creates a JSON report with file references for AI assistant integration.
    *   Includes a summary of tool execution status.
    *   Provides links to documentation for fixing identified issues.
    *   Handles edge cases like missing tools or empty results.
    *   Focuses on preserving complete, unmodified tool outputs for maximum utility.

## MCP Server Integration

### Overview

Vibe Code Scanner now supports integration with AI coding assistants through the Model Context Protocol (MCP). This integration allows AI assistants to directly trigger code scans and analyze the results, providing a seamless experience for users.

### Architecture Options

#### 1. Native MCP Server

The native MCP server is a Node.js HTTP server that implements the Model Context Protocol and acts as a bridge between AI assistants and the Vibe Code Scanner.

**Components:**
- **HTTP Server:** A lightweight Node.js server (`basic_mcp.js`) that listens on `127.0.0.1:7654`.
- **Endpoint Handlers:**
  - `/` - Health check endpoint
  - `/sse` - Server-Sent Events endpoint required by the MCP protocol
  - `/tools` - Endpoint that exposes available tools (scanProject)
  - `/tools/scanProject` - Tool implementation that runs the Python scanner

**Data Flow:**
1. AI assistant connects to the MCP server via the `/sse` endpoint.
2. AI assistant discovers available tools via the `/tools` endpoint.
3. AI assistant triggers a scan by calling the `/tools/scanProject` endpoint with a project path.
4. MCP server spawns a Python process to run `scan.py` on the specified project.
5. Scan results are captured and returned to the AI assistant.

**Benefits:**
- Simpler setup for most users
- Direct access to the local filesystem
- Lower resource usage
- No Docker dependency

#### 2. Docker-Based MCP Server

The Docker-based approach runs the MCP server inside a container, ensuring all dependencies are pre-installed and isolated.

**Components:**
- **Docker Container:** Built from `Dockerfile.mcp` with all required dependencies.
- **MCP Server:** Same Node.js server as the native approach, but running inside the container.
- **Volume Mounting:** The host filesystem is mounted into the container to allow scanning local projects.

**Data Flow:**
1. User starts the Docker container with port 7654 exposed.
2. AI assistant connects to the MCP server running in the container.
3. When a scan is triggered, the container accesses the mounted filesystem to scan the project.
4. Results are returned through the container's network interface to the AI assistant.

**Benefits:**
- Consistent environment across all platforms
- Pre-installed dependencies
- Isolation from the host system
- Matches the existing Docker-based execution model

### Security Considerations

- The MCP server binds only to `127.0.0.1` to prevent external access.
- No sensitive data is stored or transmitted by the MCP server.
- The server has read-only access to the files it scans.
- For the Docker-based approach, proper volume mounting ensures the container only has access to the directories explicitly shared by the user.

### Future Enhancements

- Support for additional MCP tools beyond basic scanning
- Enhanced error reporting and logging
- Configuration options for the MCP server (port, binding address, etc.)
- Authentication for multi-user environments
- Integration with CI/CD pipelines through the MCP interface

## Data Flow

1.  User executes one of the following:
    *   `python scan.py <project_path> [-l language]` to scan a local directory
    *   `python scan.py --github <repo_url> [-b branch]` to scan a GitHub repository
    *   `python scan.py --github <repo_url> --token <token>` to scan a private GitHub repository
2.  If a GitHub repository is specified:
    *   The script clones the repository to a temporary directory
    *   For private repositories, it uses the provided token for authentication
    *   The temporary directory is used as the project path for scanning
3.  The script validates the project path and detects or uses the specified language.
4.  For each applicable tool:
    *   Checks if the tool is installed and provides feedback if not.
    *   Executes the tool and captures its output.
    *   Saves the raw output to a dedicated file (`raw_<tool>_output.txt`).
5.  A JSON report is generated with:
    *   Tool execution summary
    *   References to raw output files
    *   Resource links
6.  The reports are written to the `reports` directory in the target project:
    *   `vibe_scan_report.json` - JSON report for AI assistants
    *   `raw_<tool>_output.txt` - Raw tool outputs for detailed analysis
7.  If a GitHub repository was cloned, the temporary directory is cleaned up.

## Error Handling

1.  **Missing Prerequisites:**
    *   Clearly identifies missing tools with specific installation instructions.
    *   Continues execution with available tools rather than failing completely.

2.  **Tool Execution Errors:**
    *   Captures and reports non-zero exit codes and stderr output.
    *   Distinguishes between "successful with issues found" and "execution failure" cases.

3.  **Parsing Errors:**
    *   Handles malformed tool output gracefully.
    *   Provides debugging information for troubleshooting.

4.  **Report Generation Errors:**
    *   Catches and reports file I/O errors.
    *   Ensures the user is informed if report generation fails.

## Security Considerations

*   When using GitHub personal access tokens, the token is never logged or displayed in error messages.
*   Temporary directories are securely created and properly cleaned up after scanning.
*   The scanner does not store or transmit any GitHub credentials.
*   Users should follow GitHub's best practices for token management, including:
    *   Using tokens with minimal required permissions (repo scope is sufficient)
    *   Regularly rotating tokens
    *   Not sharing tokens in public repositories or discussions

## Dependencies

*   **Core:** Python 3.x with standard library modules (argparse, os, subprocess, json, re, datetime, shutil, sys)
*   **External CLI tools:** (installed separately by the user)
    *   **Python:** flake8, bandit
    *   **JavaScript/TypeScript:** Node.js with npx (for ESLint)
    *   **Go:** golangci-lint, gosec
    *   **Ruby:** rubocop, brakeman (requires Rails application)

## Future Considerations

*   Configuration file for customizing tool settings and rule sets.
*   Support for additional GitHub features like:
    *   SSH key authentication
    *   Webhook integration for CI/CD pipelines
    *   GitHub Actions integration
*   Additional output formats (HTML, IDE-specific).
*   Automatic installation of missing tools.
*   Support for additional languages and frameworks.
*   Integration with CI/CD pipelines.
*   Custom rule definitions for project-specific standards.
