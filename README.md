# Vibe Code Scanner

A simple tool to scan your code for security vulnerabilities and quality issues, designed for developers of all experience levels.

## Setup Options

Vibe Code Scanner can be used in several ways. Choose the option that works best for you:

### Option 1: Docker Container (Simplest for One-off Scans)

This option is best if you just want to scan your code once in a while and don't need AI assistant integration.

#### Step 1: Install Docker Desktop

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

#### Step 2: Get the Vibe Code Scanner

1. **Download the code**:
   - Go to https://github.com/alexkenley/vibe-code-scanner
   - Click the green "Code" button
   - Select "Download ZIP"
   - Extract the ZIP file to a location on your computer (e.g., your Documents folder)

   Alternatively, if you're familiar with Git:
   ```bash
   git clone https://github.com/alexkenley/vibe-code-scanner.git
   ```

#### Step 3: Build the Scanner

> **What is this step doing?** This step creates a special container with all the scanning tools pre-installed. You only need to do this once.

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
   docker build -t vibe-code-scanner .
   ```
   (Note: Don't forget the period at the end!)

4. **Wait for the build to complete**:
   - This may take a few minutes the first time
   - You'll see a lot of text scrolling as Docker downloads and installs all the necessary tools
   - The build is complete when you see your command prompt again

#### Step 4: Scan Your Project

1. **Navigate to your project directory** in the terminal:
   ```bash
   cd path/to/your/project
   ```
   Replace "path/to/your/project" with the path to the code you want to scan
   
   For example:
   - Windows: `cd C:\Users\YourName\Documents\my-website`
   - Mac/Linux: `cd /Users/YourName/Documents/my-website`

2. **Run the scanner** with one of these commands (choose the one for your operating system):

   **Windows (PowerShell):**
   ```powershell
   docker run -v "${PWD}:/code" vibe-code-scanner /code
   ```

   **Windows (Command Prompt):**
   ```cmd
   docker run -v "%cd%:/code" vibe-code-scanner /code
   ```

   **Mac/Linux:**
   ```bash
   docker run -v "$(pwd):/code" vibe-code-scanner /code
   ```

#### Step 5: View the Results

After scanning your code, the scanner creates reports with raw tool outputs for detailed analysis.

1. **Find the reports** - After the scan completes, the results will be saved in a new `reports` directory inside your project folder:
   - `reports/raw_*_output.txt` - Raw output files from each scanning tool (e.g., `raw_eslint_output.txt`, `raw_flake8_output.txt`)
   - `reports/vibe_scan_report.json` - Machine-readable JSON data for AI assistants

2. **Examine the raw tool outputs**:
   - Navigate to your project folder in File Explorer/Finder
   - Open the `reports` folder
   - Open any of the raw output files (e.g., `raw_eslint_output.txt`) in any text editor

### Option 2: Native MCP Server (Best for AI Assistant Integration)

This option allows AI assistants like Windsurf, Cursor, or Codeium to directly use Vibe Code Scanner to check your code.

#### Step 1: Install Required Software

1. **Install Node.js**:
   - Go to [nodejs.org](https://nodejs.org/)
   - Download the "LTS" (Long Term Support) version
   - Run the installer and follow the prompts
   - Make sure to check the box that says "Automatically install the necessary tools"
   - After installation, restart your computer

2. **Install Python**:
   - Go to [python.org/downloads](https://www.python.org/downloads/)
   - Download the latest Python 3 version
   - Run the installer
   - **IMPORTANT:** Check the box that says "Add Python to PATH"
   - Click "Install Now"
   - After installation, restart your computer

#### Step 2: Get the Vibe Code Scanner

1. **Download the code**:
   - Go to https://github.com/alexkenley/vibe-code-scanner
   - Click the green "Code" button
   - Select "Download ZIP"
   - Extract the ZIP file to a location on your computer (e.g., your Documents folder)

   Alternatively, if you're familiar with Git:
   ```bash
   git clone https://github.com/alexkenley/vibe-code-scanner.git
   ```

#### Step 3: Run the Setup Script

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

3. **Run the setup script**:
   ```bash
   node setup_mcp.js
   ```

4. **Follow the prompts**:
   - The script will check if you have Node.js and Python installed
   - It will ask if you want to install the required dependencies - type `y` and press Enter
   - It will ask if you want to create/update the MCP configuration file - type `y` and press Enter
   - Wait for the script to complete

#### Step 4: Start the MCP Server

1. **In the same terminal window, start the server**:
   ```bash
   node basic_mcp.js
   ```

2. **Keep this terminal window open**:
   - The server needs to keep running while you use your AI assistant
   - You'll see a message saying the server is running at http://127.0.0.1:7654
   - Do not close this window or press Ctrl+C unless you want to stop the server

#### Step 5: Configure Your AI Assistant

1. **For Windsurf**:
   - The setup script should have already created the configuration file for you
   - Open Windsurf
   - Click on the MCP servers panel
   - Click the refresh button
   - You should see "vibeCodeScanner" in the list of available MCP servers

2. **For other AI assistants**:
   - Check their documentation for how to connect to an MCP server
   - Use the URL: http://127.0.0.1:7654
   - Use the transport type: sse

#### Step 6: Use the Scanner with Your AI Assistant

Now you can ask your AI assistant to scan your code with commands like:

- "Scan this project for security vulnerabilities"
- "Run a code quality check on this repository"
- "Analyze this JavaScript code for issues"

The AI assistant will use the MCP server to run the scan and interpret the results for you.

### Option 3: Docker-Based MCP Server

This option combines the benefits of Docker (no manual dependency installation) with AI assistant integration.

#### Step 1: Install Docker Desktop

Follow the same Docker installation steps as in Option 1 (Steps 1-3).

#### Step 2: Get the Vibe Code Scanner

Follow the same steps to download the code as in Option 1 (Step 2) or Option 2 (Step 2).

#### Step 3: Build the MCP Docker Image

1. **Open a terminal/command prompt**:
   - On Windows: Press Win+R, type "cmd" and press Enter
   - On Mac: Open Terminal from Applications > Utilities
   - On Linux: Open your terminal application

2. **Navigate to the Vibe Code Scanner directory**:
   ```bash
   cd path/to/vibe-code-scanner
   ```
   Replace "path/to/vibe-code-scanner" with the actual path where you extracted the ZIP file

3. **Build the MCP Docker image**:
   ```bash
   docker build -f Dockerfile.mcp -t vibe-code-scanner-mcp .
   ```
   (Note: Don't forget the period at the end!)

4. **Wait for the build to complete**:
   - This may take a few minutes
   - The build is complete when you see your command prompt again

#### Step 4: Start the MCP Server

1. **Run the Docker container**:
   ```bash
   docker run -p 7654:7654 vibe-code-scanner-mcp
   ```

2. **Keep this terminal window open**:
   - The server needs to keep running while you use your AI assistant
   - Do not close this window or press Ctrl+C unless you want to stop the server

#### Step 5: Configure Your AI Assistant

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

2. **Open Windsurf**:
   - Click on the MCP servers panel
   - Click the refresh button
   - You should see "vibeCodeScanner" in the list of available MCP servers

#### Step 6: Use the Scanner with Your AI Assistant

Now you can ask your AI assistant to scan your code with commands like:

- "Scan this project for security vulnerabilities"
- "Run a code quality check on this repository"
- "Analyze this JavaScript code for issues"

The AI assistant will use the MCP server to run the scan and interpret the results for you.

## Troubleshooting

### Docker Issues

If you encounter issues with Docker:

1. **Docker not starting**: 
   - Ensure virtualization is enabled in your BIOS/UEFI settings
   - On Windows, make sure Hyper-V is enabled

2. **Permission errors**: 
   - On Linux, you may need to add your user to the docker group
   - On Windows, try running your terminal as Administrator

3. **Volume mounting issues**: 
   - Make sure you're using the correct syntax for your operating system
   - Check that your current directory contains the code you want to scan

4. **Docker Desktop not running**: 
   - Look for the Docker icon in your system tray and ensure it's running
   - If the icon is there but has a warning symbol, click it to see the error

### MCP Server Issues

If you have problems with the MCP server:

1. **Server won't start**:
   - Make sure you have Node.js and Python installed
   - Check that you're in the vibe-code-scanner directory
   - Try running `npm install` to make sure all dependencies are installed

2. **AI assistant can't connect**:
   - Make sure the server is running (you should see it in your terminal)
   - Check that the configuration file has the correct URL (http://127.0.0.1:7654)
   - Try restarting your AI assistant

3. **Scan fails**:
   - Check the terminal where the MCP server is running for error messages
   - Make sure the project path is correct
   - For specific language scanning, make sure that language is supported

## Common Questions

**Q: Do I need to install programming languages on my computer?**  
A: For Option 1 and Option 3 (Docker), no! For Option 2 (Native MCP), you need Node.js and Python.

**Q: How do I scan a different project?**  
A: For Option 1, navigate to that project's directory and run the Docker command again. For Options 2 and 3, just ask your AI assistant to scan the new project.

**Q: Can I scan just part of my project?**  
A: Yes, with Option 1, navigate to the specific subdirectory before running the Docker command. With Options 2 and 3, ask your AI assistant to scan a specific directory.

**Q: Where are my scan results saved?**  
A: In a `reports` folder inside the project you scanned.

**Q: How do I read the scan results?**  
A: For Option 1, open the raw output files in a text editor. For Options 2 and 3, your AI assistant will interpret the results for you.

**Q: Do I need to keep the MCP server running all the time?**  
A: Only when you want to use your AI assistant to scan code. You can close it when you're done and start it again later.

{{ ... }}
