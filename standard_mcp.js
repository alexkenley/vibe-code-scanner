// Standard MCP Server for Vibe Code Scanner
const express = require('express');
const cors = require('cors');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');
const os = require('os');
const { execSync } = require('child_process');

const app = express();
const PORT = 7654;

// Enable CORS
app.use(cors());
app.use(express.json());

// Root endpoint
app.get('/', (req, res) => {
  console.log('Root endpoint called');
  res.json({ status: 'ok', service: 'Standard MCP Server for Vibe Code Scanner' });
});

// SSE endpoint required by MCP
app.get('/sse', (req, res) => {
  console.log('SSE endpoint called');
  res.setHeader('Content-Type', 'text/event-stream');
  res.setHeader('Cache-Control', 'no-cache');
  res.setHeader('Connection', 'keep-alive');
  
  // Send ready event
  res.write('data: {"type": "ready"}\n\n');
  
  // Keep connection open
  const interval = setInterval(() => {
    res.write('data: {"type": "ping"}\n\n');
  }, 30000);
  
  // Clean up on close
  req.on('close', () => {
    clearInterval(interval);
  });
});

// Tools endpoint
app.get('/tools', (req, res) => {
  console.log('Tools endpoint called');
  res.json({
    tools: [
      {
        name: 'scanProject',
        description: 'Scan a project for security and quality issues',
        parameters: {
          type: 'object',
          properties: {
            projectPath: {
              type: 'string',
              description: 'Path to the project directory to scan'
            },
            language: {
              type: 'string',
              description: 'Optional language to scan (python, javascript, typescript, go, ruby, nextjs, node)'
            }
          },
          required: ['projectPath']
        }
      },
      {
        name: 'scanGitHubRepo',
        description: 'Scan a GitHub repository for security and quality issues',
        parameters: {
          type: 'object',
          properties: {
            repoUrl: {
              type: 'string',
              description: 'URL of the GitHub repository to scan'
            },
            token: {
              type: 'string',
              description: 'GitHub personal access token for private repositories'
            },
            branch: {
              type: 'string',
              description: 'Branch to scan (defaults to main/master)'
            },
            language: {
              type: 'string',
              description: 'Optional language to scan (python, javascript, typescript, go, ruby, nextjs, node)'
            }
          },
          required: ['repoUrl']
        }
      }
    ]
  });
});

// Tool implementation for scanning local projects
app.post('/tools/scanProject', (req, res) => {
  console.log('scanProject tool called with params:', req.body);
  const { projectPath, language } = req.body;
  
  if (!projectPath) {
    return res.json({ error: 'projectPath is required' });
  }
  
  // Build command to run the Python scanner
  const pythonPath = process.env.PYTHON_PATH || 'python';
  const args = [path.join(__dirname, 'scan.py'), projectPath];
  
  if (language) {
    args.push('--language', language);
  }
  
  console.log(`Running command: ${pythonPath} ${args.join(' ')}`);
  
  // Run the scanner
  const scanner = spawn(pythonPath, args);
  let stdout = '';
  let stderr = '';
  
  scanner.stdout.on('data', (data) => {
    stdout += data.toString();
    console.log(`Scanner output: ${data}`);
  });
  
  scanner.stderr.on('data', (data) => {
    stderr += data.toString();
    console.error(`Scanner error: ${data}`);
  });
  
  scanner.on('close', (code) => {
    console.log(`Scanner exited with code ${code}`);
    
    // Try to read the report file
    let report = null;
    try {
      // Look for the report in the project's reports directory
      const reportPath = path.join(projectPath, 'reports', 'vibe_scan_report.json');
      if (fs.existsSync(reportPath)) {
        report = JSON.parse(fs.readFileSync(reportPath, 'utf8'));
        console.log(`Successfully read report from ${reportPath}`);
      } else {
        console.error(`Report file not found at ${reportPath}`);
      }
    } catch (error) {
      console.error('Error reading report file:', error);
    }
    
    res.json({
      result: {
        success: code === 0,
        output: stdout,
        error: stderr || null,
        report: report
      }
    });
  });
});

// Tool implementation for scanning GitHub repositories
app.post('/tools/scanGitHubRepo', (req, res) => {
  console.log('scanGitHubRepo tool called with params:', JSON.stringify({
    ...req.body,
    token: req.body.token ? '***REDACTED***' : undefined
  }));
  
  const { repoUrl, token, branch, language } = req.body;
  
  if (!repoUrl) {
    return res.json({ error: 'repoUrl is required' });
  }
  
  // Create a temporary directory for cloning
  const tempDir = path.join(os.tmpdir(), `vibe-scan-${Date.now()}`);
  fs.mkdirSync(tempDir, { recursive: true });
  
  console.log(`Created temporary directory: ${tempDir}`);
  
  // Clone the repository
  let cloneCommand = `git clone ${repoUrl}`;
  if (branch) {
    cloneCommand += ` --branch ${branch}`;
  }
  cloneCommand += ` ${tempDir}`;
  
  // If token is provided, use it for authentication
  let cloneEnv = { ...process.env };
  if (token) {
    // Extract the repo path from the URL
    const repoPath = new URL(repoUrl).pathname;
    // Create the authenticated URL
    const authUrl = `https://${token}:x-oauth-basic@github.com${repoPath}`;
    cloneCommand = `git clone ${authUrl}`;
    if (branch) {
      cloneCommand += ` --branch ${branch}`;
    }
    cloneCommand += ` ${tempDir}`;
  }
  
  console.log(`Cloning repository: ${repoUrl}${branch ? ` (branch: ${branch})` : ''}`);
  
  try {
    // Execute the clone command
    execSync(cloneCommand, { 
      stdio: ['ignore', 'pipe', 'pipe'],
      env: cloneEnv
    });
    
    console.log('Repository cloned successfully');
    
    // Build command to run the Python scanner
    const pythonPath = process.env.PYTHON_PATH || 'python';
    const args = [path.join(__dirname, 'scan.py'), tempDir];
    
    if (language) {
      args.push('--language', language);
    }
    
    console.log(`Running command: ${pythonPath} ${args.join(' ')}`);
    
    // Run the scanner
    const scanner = spawn(pythonPath, args);
    let stdout = '';
    let stderr = '';
    
    scanner.stdout.on('data', (data) => {
      stdout += data.toString();
      console.log(`Scanner output: ${data}`);
    });
    
    scanner.stderr.on('data', (data) => {
      stderr += data.toString();
      console.error(`Scanner error: ${data}`);
    });
    
    scanner.on('close', (code) => {
      console.log(`Scanner exited with code ${code}`);
      
      // Try to read the report file
      let report = null;
      try {
        // Look for the report in the temp directory's reports folder
        const reportPath = path.join(tempDir, 'reports', 'vibe_scan_report.json');
        if (fs.existsSync(reportPath)) {
          report = JSON.parse(fs.readFileSync(reportPath, 'utf8'));
          console.log(`Successfully read report from ${reportPath}`);
        } else {
          console.error(`Report file not found at ${reportPath}`);
        }
      } catch (error) {
        console.error('Error reading report file:', error);
      }
      
      // Clean up the temporary directory
      try {
        console.log(`Cleaning up temporary directory: ${tempDir}`);
        fs.rmSync(tempDir, { recursive: true, force: true });
      } catch (error) {
        console.error(`Error cleaning up temporary directory: ${error}`);
      }
      
      res.json({
        result: {
          success: code === 0,
          output: stdout,
          error: stderr || null,
          report: report,
          repository: {
            url: repoUrl,
            branch: branch || 'default'
          }
        }
      });
    });
  } catch (error) {
    console.error(`Error cloning repository: ${error.message}`);
    
    // Clean up the temporary directory
    try {
      fs.rmSync(tempDir, { recursive: true, force: true });
    } catch (cleanupError) {
      console.error(`Error cleaning up temporary directory: ${cleanupError}`);
    }
    
    res.json({
      result: {
        success: false,
        error: `Failed to clone repository: ${error.message}`,
        output: null,
        report: null
      }
    });
  }
});

// Start the server
app.listen(PORT, '0.0.0.0', () => {
  console.log(`
================================================================================
========================= STANDARD MCP SERVER =========================
================================================================================
                 Starting server at http://0.0.0.0:${PORT}
================================================================================
  `);
});
