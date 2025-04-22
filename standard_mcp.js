// Standard MCP Server for Vibe Code Scanner
const express = require('express');
const cors = require('cors');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

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
      }
    ]
  });
});

// Tool implementation
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
      const reportPath = path.join(__dirname, 'vibe_scan_report.json');
      if (fs.existsSync(reportPath)) {
        report = JSON.parse(fs.readFileSync(reportPath, 'utf8'));
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

// Start the server
app.listen(PORT, () => {
  console.log(`
================================================================================
========================= STANDARD MCP SERVER =========================
================================================================================
                 Starting server at http://localhost:${PORT}
================================================================================
  `);
});
