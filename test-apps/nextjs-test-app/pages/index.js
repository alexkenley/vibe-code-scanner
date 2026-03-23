import { useState, useEffect } from 'react'
import axios from 'axios'
import Head from 'next/head'

// Hardcoded API key (security issue)
const API_KEY = "sk_test_12345abcdefghijklmnopqrstuvwxyz"

export default function Home() {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [userInput, setUserInput] = useState('')
  
  // Unused variable (code quality issue)
  const unusedVariable = "This variable is never used"
  
  useEffect(() => {
    // Console log in production code (code quality issue)
    console.log("Component mounted")
    
    // Fetch data on component mount
    fetchData()
  }, [])
  
  const fetchData = async () => {
    try {
      const response = await axios.get(`https://api.example.com/data?key=${API_KEY}`)
      setData(response.data)
    } catch (err) {
      // Exposing error details to client (security issue)
      setError(err.message)
      console.error(err)
    }
  }
  
  // Potential XSS vulnerability (security issue)
  const renderHTML = (html) => {
    return { __html: html }
  }
  
  // SQL injection vulnerability (security issue)
  const fetchUserData = async (userId) => {
    try {
      // This is simulating a direct SQL query construction
      const query = `SELECT * FROM users WHERE id = ${userId}`
      console.log(`Executing query: ${query}`)
      // In a real app, this would be sent to the server
    } catch (err) {
      console.error(err)
    }
  }
  
  return (
    <div>
      <Head>
        <title>Next.js Test App</title>
        <meta name="description" content="A test app for Vibe Code Scanner" />
        <link rel="icon" href="/favicon.ico" />
      </Head>

      <main>
        <h1>Next.js Test App</h1>
        
        <div>
          <input 
            type="text" 
            value={userInput} 
            onChange={(e) => setUserInput(e.target.value)}
            placeholder="Enter user ID"
          />
          <button onClick={() => fetchUserData(userInput)}>Fetch User</button>
        </div>
        
        {data && (
          // Potential XSS vulnerability
          <div dangerouslySetInnerHTML={renderHTML(data.html)} />
        )}
        
        {error && (
          // Exposing error details to client
          <div className="error">Error: {error}</div>
        )}
      </main>
    </div>
  )
}
