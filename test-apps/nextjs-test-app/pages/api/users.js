// API route with security issues

// Missing rate limiting (security issue)
export default function handler(req, res) {
  if (req.method === 'GET') {
    // No authentication check (security issue)
    return getUserData(req, res)
  } else if (req.method === 'POST') {
    // No CSRF protection (security issue)
    return createUser(req, res)
  }
  
  res.status(405).json({ error: 'Method not allowed' })
}

function getUserData(req, res) {
  const { id } = req.query
  
  // No input validation (security issue)
  if (id) {
    // In a real app, this would query a database
    const userData = {
      id,
      name: 'Test User',
      email: 'user@example.com',
      // Sensitive data exposure (security issue)
      ssn: '123-45-6789',
      password_hash: 'bcrypt$10$hashedpasswordwouldbehere'
    }
    
    return res.status(200).json(userData)
  }
  
  // Information disclosure in error message (security issue)
  return res.status(400).json({ 
    error: 'Missing user ID',
    debug: 'Database connection string: postgres://user:password@localhost:5432/userdb'
  })
}

function createUser(req, res) {
  try {
    const { name, email, password } = req.body
    
    // Password stored in plaintext (security issue)
    const newUser = {
      id: Math.floor(Math.random() * 1000),
      name,
      email,
      password, // Should be hashed
      created_at: new Date()
    }
    
    // Log sensitive information (security issue)
    console.log(`Created user with password: ${password}`)
    
    return res.status(201).json({ 
      message: 'User created',
      user: newUser
    })
  } catch (error) {
    // Stack trace exposure (security issue)
    return res.status(500).json({ 
      error: error.message,
      stack: error.stack
    })
  }
}
