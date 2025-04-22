# Vibe Code Scanner

A simple tool to scan your code for security vulnerabilities and quality issues, designed for developers of all experience levels.

## Quick Setup Guide

Vibe Code Scanner is designed to run in Docker, with a simple setup process:

### Step 1: Install Docker Desktop

> **What is Docker?** Docker is a tool that packages all the scanning tools into a container that works the same way on any computer. You don't need to install any programming languages - everything runs inside Docker!

1. **Download Docker Desktop**:
   - Go to [docker.com](https://www.docker.com/products/docker-desktop/)
   - Click "Download for Windows" (or Mac/Linux depending on your system)
   - Create a free Docker account if prompted during download

2. **Install Docker Desktop**:
   - Run the installer you downloaded
   - Follow the installation prompts
   - On Windows: Select the option to use WSL 2 if prompted
   - After installation completes, restart your computer if required

3. **Start Docker Desktop**:
   - Launch Docker Desktop from your applications/programs menu
   - Wait for Docker to fully start (the whale icon in the taskbar will stop animating)
   - Sign in to Docker Desktop if prompted

### Step 2: Get the Vibe Code Scanner

1. **Download the code**:
   - Go to https://github.com/alexkenley/vibe-code-scanner
   - Click the green "Code" button
   - Select "Download ZIP"
   - Extract the ZIP file to a location on your computer (e.g., your Documents folder)

   Alternatively, if you're familiar with Git:
   ```bash
   git clone https://github.com/alexkenley/vibe-code-scanner.git
   ```

### Step 3: Build the Docker Image

1. **Open a terminal/command prompt**:
   - On Windows: Press Win+R, type "cmd" and press Enter
   - On Mac: Open Terminal from Applications > Utilities
   - On Linux: Open your terminal application

2. **Navigate to the Vibe Code Scanner directory**:
   ```bash
   cd path/to/vibe-code-scanner
   ```
   Replace "path/to/vibe-code-scanner" with the actual path where you extracted the ZIP file
   
   For example:
   - Windows: `cd C:\Users\YourName\Documents\vibe-code-scanner`
   - Mac/Linux: `cd /Users/YourName/Documents/vibe-code-scanner`

3. **Build the Docker image**:
   ```bash
   docker build -f Dockerfile.mcp -t vibe-code-scanner-mcp .
   ```
   (Note: Don't forget the period at the end!)

4. **Wait for the build to complete**:
   - This may take a few minutes
   - The build is complete when you see your command prompt again

### Step 4: Start the MCP Server

1. **Run the Docker container**:
   ```bash
   docker run -p 7654:7654 vibe-code-scanner-mcp
   ```

2. **Keep this terminal window open**:
   - The server needs to keep running while you use your AI assistant
   - Do not close this window or press Ctrl+C unless you want to stop the server

### Step 5: Configure Your AI Assistant

1. **For Windsurf**:
   - Create or update the file at `~/.codeium/windsurf/mcp_config.json`
   - If you're not sure where this is:
     - Windows: It's at `C:\Users\YourUsername\.codeium\windsurf\mcp_config.json`
     - Mac/Linux: It's at `/Users/YourUsername/.codeium/windsurf/mcp_config.json`

   - Copy and paste this content into the file:
   ```json
   {
     "mcpServers": {
       "vibeCodeScanner": {
         "baseUrl": "http://127.0.0.1:7654",
         "transport": "sse"
       }
     }
   }
   ```

   > **Important Note:** Windsurf may show a "failed to initialize" error for the MCP server even when it's actually working correctly. This is a known UI issue and doesn't affect functionality. You can still use the MCP server to scan your code despite this error message.

2. **For other AI assistants**:
   - Check their documentation for how to connect to an MCP server
   - Use the URL: http://127.0.0.1:7654
   - Use the transport type: sse

### Step 6: Use the Scanner with Your AI Assistant

Now you can ask your AI assistant to scan your code with commands like:

- "Scan this project for security vulnerabilities"
- "Run a code quality check on this repository"
- "Analyze this JavaScript code for issues"
- "Scan the GitHub repository at https://github.com/username/repository"

The AI assistant will use the MCP server to run the scan and interpret the results for you.

## Scanning GitHub Repositories

You can scan GitHub repositories directly without cloning them manually:

```
Scan the GitHub repository at https://github.com/username/repository
```

For private repositories, you'll need to provide a GitHub personal access token:

```
Scan the private GitHub repository at https://github.com/username/repository using token YOUR_GITHUB_TOKEN
```

## Troubleshooting

### Docker Issues

If you encounter issues with Docker:

1. **Docker not starting**: 
   - Ensure virtualization is enabled in your BIOS/UEFI settings
   - On Windows, make sure Hyper-V is enabled

2. **Permission errors**: 
   - On Linux, you may need to add your user to the docker group
   - On Windows, try running your terminal as Administrator

3. **Docker Desktop not running**: 
   - Look for the Docker icon in your system tray and ensure it's running
   - If the icon is there but has a warning symbol, click it to see the error

### MCP Server Issues

If you have problems with the MCP server:

1. **AI assistant can't connect**:
   - Make sure the server is running (you should see it in your terminal)
   - Check that the configuration file has the correct URL (http://127.0.0.1:7654)
   - Try restarting your AI assistant

2. **Scan fails**:
   - Check the terminal where the MCP server is running for error messages
   - Make sure the project path is correct
   - For specific language scanning, make sure that language is supported

## Common Questions

**Q: Do I need to install programming languages on my computer?**  
A: No! Everything runs inside Docker, so you don't need to install any programming languages or tools on your computer.

**Q: How do I scan a different project?**  
A: Just ask your AI assistant to scan the new project.

**Q: Can I scan just part of my project?**  
A: Yes, ask your AI assistant to scan a specific directory.

**Q: Where are my scan results saved?**  
A: In a `reports` folder inside the project you scanned.

**Q: Do I need to keep the MCP server running all the time?**  
A: Only when you want to use your AI assistant to scan code. You can close it when you're done and start it again later.
