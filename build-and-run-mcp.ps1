# PowerShell script to build and run the Docker MCP server

# Build the Docker image
Write-Host "Building Docker image for Vibe Code Scanner MCP Server..." -ForegroundColor Green
docker build -f Dockerfile.mcp -t vibe-code-scanner-mcp .

# Check if the build was successful
if ($LASTEXITCODE -ne 0) {
    Write-Host "Error building Docker image. Please check the logs above." -ForegroundColor Red
    exit 1
}

Write-Host "Docker image built successfully!" -ForegroundColor Green
Write-Host ""

# Run the Docker container
Write-Host "Starting the MCP server container..." -ForegroundColor Green
Write-Host "The server will be available at http://127.0.0.1:7654" -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Yellow
Write-Host ""

docker run -p 7654:7654 vibe-code-scanner-mcp

# This line will only execute if the docker run command exits
Write-Host "MCP server container stopped." -ForegroundColor Red
