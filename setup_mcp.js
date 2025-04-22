#!/usr/bin/env node

/**
 * Vibe Code Scanner MCP Server Setup Script
 * 
 * This script checks for and installs required dependencies for running
 * the Vibe Code Scanner MCP server natively (without Docker).
 */

const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');
const readline = require('readline');

// Create interface for user input
const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout
});

// ANSI color codes for better readability
const colors = {
  reset: '\x1b[0m',
  bright: '\x1b[1m',
  dim: '\x1b[2m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  red: '\x1b[31m',
  cyan: '\x1b[36m'
};

console.log(`
${colors.bright}${colors.cyan}===============================================${colors.reset}
${colors.bright}${colors.cyan}   Vibe Code Scanner MCP Server Setup Tool    ${colors.reset}
${colors.bright}${colors.cyan}===============================================${colors.reset}

This script will check for and install required dependencies
for running the Vibe Code Scanner MCP server.
`);

// Check if Node.js is installed
function checkNodeVersion() {
  try {
    const nodeVersion = execSync('node --version').toString().trim();
    console.log(`${colors.green}✓ Node.js ${nodeVersion} is installed${colors.reset}`);
    return true;
  } catch (error) {
    console.log(`${colors.red}✗ Node.js is not installed or not in PATH${colors.reset}`);
    console.log(`  Please install Node.js from https://nodejs.org/ (version 14+ recommended)`);
    return false;
  }
}

// Check if Python is installed
function checkPythonVersion() {
  try {
    // Try python3 first, then fall back to python
    let pythonCommand = 'python3';
    try {
      execSync(`${pythonCommand} --version`);
    } catch (error) {
      pythonCommand = 'python';
      execSync(`${pythonCommand} --version`);
    }
    
    const pythonVersion = execSync(`${pythonCommand} --version`).toString().trim();
    console.log(`${colors.green}✓ ${pythonVersion} is installed${colors.reset}`);
    return { success: true, command: pythonCommand };
  } catch (error) {
    console.log(`${colors.red}✗ Python is not installed or not in PATH${colors.reset}`);
    console.log(`  Please install Python from https://www.python.org/downloads/ (version 3.6+ recommended)`);
    return { success: false };
  }
}

// Install Node.js dependencies
function installNodeDependencies() {
  console.log(`\n${colors.cyan}Installing Node.js dependencies...${colors.reset}`);
  try {
    execSync('npm install', { stdio: 'inherit' });
    console.log(`${colors.green}✓ Node.js dependencies installed successfully${colors.reset}`);
    return true;
  } catch (error) {
    console.log(`${colors.red}✗ Failed to install Node.js dependencies${colors.reset}`);
    console.log(`  Error: ${error.message}`);
    return false;
  }
}

// Install Python dependencies
function installPythonDependencies(pythonCommand) {
  console.log(`\n${colors.cyan}Installing Python dependencies...${colors.reset}`);
  try {
    execSync(`${pythonCommand} -m pip install -r requirements-server.txt`, { stdio: 'inherit' });
    console.log(`${colors.green}✓ Python dependencies installed successfully${colors.reset}`);
    return true;
  } catch (error) {
    console.log(`${colors.red}✗ Failed to install Python dependencies${colors.reset}`);
    console.log(`  Error: ${error.message}`);
    return false;
  }
}

// Create MCP config file
function createMcpConfig() {
  console.log(`\n${colors.cyan}Setting up MCP configuration...${colors.reset}`);
  
  // Determine home directory
  const homeDir = process.env.HOME || process.env.USERPROFILE;
  const codeiumDir = path.join(homeDir, '.codeium');
  const windsurfDir = path.join(codeiumDir, 'windsurf');
  const configPath = path.join(windsurfDir, 'mcp_config.json');
  
  try {
    // Create directories if they don't exist
    if (!fs.existsSync(codeiumDir)) {
      fs.mkdirSync(codeiumDir);
    }
    if (!fs.existsSync(windsurfDir)) {
      fs.mkdirSync(windsurfDir);
    }
    
    // Create or update config file
    const config = {
      mcpServers: {
        vibeCodeScanner: {
          command: "node",
          args: [
            "basic_mcp.js"
          ],
          cwd: "${workspaceFolder:VibeCodeScanner}",
          baseUrl: "http://127.0.0.1:7654",
          transport: "sse"
        }
      }
    };
    
    fs.writeFileSync(configPath, JSON.stringify(config, null, 2));
    console.log(`${colors.green}✓ MCP configuration created at ${configPath}${colors.reset}`);
    return true;
  } catch (error) {
    console.log(`${colors.red}✗ Failed to create MCP configuration${colors.reset}`);
    console.log(`  Error: ${error.message}`);
    console.log(`  You'll need to manually create the configuration file at ${configPath}`);
    return false;
  }
}

// Main function
async function main() {
  // Check Node.js
  const nodeInstalled = checkNodeVersion();
  if (!nodeInstalled) {
    console.log(`\n${colors.yellow}Please install Node.js and run this script again.${colors.reset}`);
    rl.close();
    return;
  }
  
  // Check Python
  const pythonCheck = checkPythonVersion();
  if (!pythonCheck.success) {
    console.log(`\n${colors.yellow}Please install Python and run this script again.${colors.reset}`);
    rl.close();
    return;
  }
  
  // Ask for confirmation before installing dependencies
  rl.question(`\n${colors.yellow}Do you want to install the required dependencies? (y/n) ${colors.reset}`, (answer) => {
    if (answer.toLowerCase() === 'y' || answer.toLowerCase() === 'yes') {
      // Install dependencies
      const nodeSuccess = installNodeDependencies();
      const pythonSuccess = installPythonDependencies(pythonCheck.command);
      
      if (nodeSuccess && pythonSuccess) {
        // Create MCP config
        rl.question(`\n${colors.yellow}Do you want to create/update the MCP configuration file? (y/n) ${colors.reset}`, (configAnswer) => {
          if (configAnswer.toLowerCase() === 'y' || configAnswer.toLowerCase() === 'yes') {
            createMcpConfig();
            showNextSteps();
            rl.close();
          } else {
            showNextSteps();
            rl.close();
          }
        });
      } else {
        console.log(`\n${colors.red}Some dependencies could not be installed. Please check the errors above.${colors.reset}`);
        rl.close();
      }
    } else {
      console.log(`\n${colors.yellow}Setup cancelled. No dependencies were installed.${colors.reset}`);
      rl.close();
    }
  });
}

// Show next steps
function showNextSteps() {
  console.log(`
${colors.bright}${colors.cyan}===============================================${colors.reset}
${colors.bright}${colors.cyan}              Setup Complete!                 ${colors.reset}
${colors.bright}${colors.cyan}===============================================${colors.reset}

${colors.bright}Next steps:${colors.reset}

1. Start the MCP server:
   ${colors.cyan}node basic_mcp.js${colors.reset}

2. The server will be available at http://127.0.0.1:7654

3. Use your AI assistant (Windsurf, Cursor, etc.) to:
   - Scan your project for security vulnerabilities
   - Check code quality
   - Analyze specific files or directories

${colors.bright}${colors.yellow}Thank you for using Vibe Code Scanner!${colors.reset}
`);
}

// Run the main function
main();
