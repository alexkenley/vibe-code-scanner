const express = require('express');
const bodyParser = require('body-parser');
const cookieParser = require('cookie-parser');
const jwt = require('jsonwebtoken');
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { exec } = require('child_process');

const app = express();
const PORT = 3000;

// Insecure middleware configuration
app.use(bodyParser.json());
app.use(cookieParser());

// Missing security headers
// app.use(helmet());

// JWT secret hardcoded (security issue)
const JWT_SECRET = 'super_secret_jwt_key_do_not_share';

// Database credentials hardcoded (security issue)
const DB_CONFIG = {
  host: 'localhost',
  user: 'admin',
  password: 'admin123',
  database: 'test_db'
};

// Weak crypto (security issue)
function hashPassword(password) {
  // Using MD5 (insecure)
  return crypto.createHash('md5').update(password).digest('hex');
}

// Insecure authentication (security issue)
app.post('/login', (req, res) => {
  const { username, password } = req.body;
  
  // No input validation (security issue)
  
  // Hardcoded credentials (security issue)
  if (username === 'admin' && password === 'password123') {
    // JWT with no expiration (security issue)
    const token = jwt.sign({ username }, JWT_SECRET);
    
    // Insecure cookie (security issue)
    res.cookie('auth', token, { 
      // Missing secure, httpOnly, sameSite flags
    });
    
    return res.json({ success: true, token });
  }
  
  // Information disclosure (security issue)
  return res.status(401).json({ 
    error: 'Invalid credentials',
    debug: `Attempted login with username: ${username} and password: ${password}`
  });
});

// Command injection vulnerability (security issue)
app.get('/ping', (req, res) => {
  const { host } = req.query;
  
  if (!host) {
    return res.status(400).json({ error: 'Host parameter is required' });
  }
  
  // Command injection vulnerability
  exec(`ping -c 4 ${host}`, (error, stdout, stderr) => {
    if (error) {
      return res.status(500).json({ error: stderr });
    }
    res.json({ result: stdout });
  });
});

// Path traversal vulnerability (security issue)
app.get('/files', (req, res) => {
  const { filename } = req.query;
  
  if (!filename) {
    return res.status(400).json({ error: 'Filename parameter is required' });
  }
  
  // Path traversal vulnerability
  const filePath = path.join(__dirname, 'uploads', filename);
  
  fs.readFile(filePath, 'utf8', (err, data) => {
    if (err) {
      return res.status(500).json({ error: err.message });
    }
    res.send(data);
  });
});

// NoSQL injection vulnerability (security issue)
app.get('/users', (req, res) => {
  const { username } = req.query;
  
  // NoSQL injection vulnerability
  const query = { username: username };
  
  // In a real app, this would query a database
  // db.users.find(query).toArray((err, users) => { ... });
  
  // Simulating database response
  res.json({ 
    query,
    message: `Would execute query: db.users.find(${JSON.stringify(query)})`
  });
});

// Insecure file upload (security issue)
app.post('/upload', (req, res) => {
  // No file type validation
  // No file size limits
  // No virus scanning
  
  res.json({ success: true, message: 'File uploaded successfully' });
});

// Insecure direct object reference (security issue)
app.get('/users/:id', (req, res) => {
  const { id } = req.params;
  
  // No authorization check
  // In a real app, this would check if the user has permission to access this record
  
  res.json({ 
    id,
    username: 'test_user',
    email: 'user@example.com',
    role: 'admin'
  });
});

// Start the server
app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});
