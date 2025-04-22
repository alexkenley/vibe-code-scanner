/**
 * Docker-based MCP Scanner for Vibe Code Scanner
 * 
 * This script modifies the basic_mcp.js to use Docker for the actual scanning,
 * similar to how docker-scan.sh works.
 */

const http = require('http');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');
const url = require('url');
const { execSync } = require('child_process');

// Configuration
const PORT = 7654;
const HOST = '127.0.0.1';

// Create HTTP server
const server = http.createServer((req, res) => {
  // Enable CORS
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  
  // Handle preflight requests
  if (req.method === 'OPTIONS') {
    res.writeHead(204);
    res.end();
    return;
  }
  
  // Parse URL
  const parsedUrl = url.parse(req.url, true);
  const pathname = parsedUrl.pathname;
  
  console.log(`${req.method} ${pathname}`);
  
  // Root endpoint
  if (req.method === 'GET' && pathname === '/') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ status: 'ok', service: 'Docker-based MCP Server for Vibe Code Scanner' }));
    return;
  }
  
  // SSE endpoint required by MCP
  if (req.method === 'GET' && pathname === '/sse') {
    res.writeHead(200, {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'Connection': 'keep-alive'
    });
    
    // Send ready event
    res.write('data: {"type": "ready"}\n\n');
    
    // Keep connection open with ping events
    const interval = setInterval(() => {
      res.write('data: {"type": "ping"}\n\n');
    }, 30000);
    
    // Clean up on close
    req.on('close', () => {
      clearInterval(interval);
    });
    
    return;
  }
  
  // Tools endpoint
  if (req.method === 'GET' && pathname === '/tools') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({
      tools: [
        {
          name: 'scanProject',
          description: 'Scan a project for security and quality issues using Docker',
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
        }
      ]
    }));
    return;
  }
  
  // Tool implementation
  if (req.method === 'POST' && pathname === '/tools/scanProject') {
    let body = '';
    
    req.on('data', chunk => {
      body += chunk.toString();
    });
    
    req.on('end', () => {
      try {
        const params = JSON.parse(body);
        const { projectPath, language } = params;
        
        if (!projectPath) {
          res.writeHead(400, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({ error: 'projectPath is required' }));
          return;
        }
        
        console.log(`Scanning project: ${projectPath}, language: ${language || 'auto-detect'}`);
        
        // Check if Docker is installed
        try {
          execSync('docker --version', { stdio: 'pipe' });
        } catch (error) {
          console.error('Docker is not installed or not in PATH');
          res.writeHead(500, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({ 
            error: 'Docker is not installed or not in PATH. Please install Docker to use this scanner.' 
          }));
          return;
        }
        
        // Build the Docker image if it doesn't exist
        try {
          execSync('docker image inspect vibe-code-scanner', { stdio: 'pipe' });
          console.log('Docker image already exists, skipping build');
        } catch (error) {
          console.log('Building Docker image for Vibe Code Scanner...');
          try {
            execSync('docker build -t vibe-code-scanner .', { 
              stdio: 'inherit',
              cwd: path.dirname(process.argv[1]) // Use the directory of this script
            });
          } catch (buildError) {
            console.error('Failed to build Docker image:', buildError);
            res.writeHead(500, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ 
              error: 'Failed to build Docker image. See server logs for details.' 
            }));
            return;
          }
        }
        
        // Prepare Docker command
        let dockerArgs = ['run', '--rm', '-v', `${projectPath}:/code`, 'vibe-code-scanner', '/code'];
        
        // Add language flag if specified
        if (language) {
          dockerArgs.push('--language', language);
        }
        
        console.log(`Running Docker command: docker ${dockerArgs.join(' ')}`);
        
        // Run the Docker container
        const scanner = spawn('docker', dockerArgs);
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
          
          // Try to read the report file from the project directory
          let report = null;
          try {
            const reportPath = path.join(projectPath, 'reports', 'vibe_scan_report.json');
            if (fs.existsSync(reportPath)) {
              report = JSON.parse(fs.readFileSync(reportPath, 'utf8'));
              console.log('Found scan report at:', reportPath);
            } else {
              console.log('No report file found at:', reportPath);
            }
          } catch (error) {
            console.error('Error reading report file:', error);
          }
          
          res.writeHead(200, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({
            result: {
              success: code === 0,
              output: stdout,
              error: stderr || null,
              report: report
            }
          }));
        });
      } catch (error) {
        console.error('Error processing request:', error);
        res.writeHead(500, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: error.message }));
      }
    });
    
    return;
  }
  
  // Not found
  res.writeHead(404, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify({ error: 'Not found' }));
});

// Start the server
server.listen(PORT, HOST, (err) => {
  if (err) {
    console.error('Server failed to start:', err);
    process.exit(1);
  }
  console.log(`\n==============================================================================\n=========================== DOCKER MCP SERVER ===========================\n==============================================================================\n                 Starting server at http://${HOST}:${PORT}\n==============================================================================\n  `);
});
