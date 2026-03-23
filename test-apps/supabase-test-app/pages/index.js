import { useState, useEffect } from 'react'
import Head from 'next/head'
import supabase from '../lib/supabase'

export default function Home() {
  const [user, setUser] = useState(null)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [posts, setPosts] = useState([])
  const [newPost, setNewPost] = useState('')
  
  // Unused variable (code quality issue)
  const unusedConfig = { theme: 'dark', debug: true }
  
  useEffect(() => {
    // Console log in production code (code quality issue)
    console.log('Component mounted')
    
    // Check for existing session
    checkUser()
    
    // Fetch posts
    fetchPosts()
  }, [])
  
  const checkUser = async () => {
    // Get current user
    const { data: { session } } = await supabase.auth.getSession()
    setUser(session?.user || null)
    
    // Listen for auth changes
    const { data: { subscription } } = await supabase.auth.onAuthStateChange(
      (_event, session) => {
        setUser(session?.user || null)
      }
    )
    
    // No cleanup for subscription (memory leak - code quality issue)
  }
  
  const handleSignUp = async (e) => {
    e.preventDefault()
    setLoading(true)
    
    try {
      // No input validation (security issue)
      const { data, error } = await supabase.auth.signUp({
        email,
        password, // No password strength requirements (security issue)
      })
      
      if (error) throw error
      
      // Console log sensitive information (security issue)
      console.log('User signed up:', data)
    } catch (error) {
      // Exposing error details to client (security issue)
      setError(error.message)
      console.error('Error signing up:', error)
    } finally {
      setLoading(false)
    }
  }
  
  const handleSignIn = async (e) => {
    e.preventDefault()
    setLoading(true)
    
    try {
      // No rate limiting (security issue)
      const { data, error } = await supabase.auth.signInWithPassword({
        email,
        password,
      })
      
      if (error) throw error
    } catch (error) {
      setError(error.message)
    } finally {
      setLoading(false)
    }
  }
  
  const handleSignOut = async () => {
    await supabase.auth.signOut()
  }
  
  const fetchPosts = async () => {
    try {
      // No error handling (code quality issue)
      const { data } = await supabase
        .from('posts')
        .select('*')
        .order('created_at', { ascending: false })
      
      setPosts(data || [])
    } catch (error) {
      console.error('Error fetching posts:', error)
    }
  }
  
  const createPost = async (e) => {
    e.preventDefault()
    
    if (!user) return
    
    try {
      // No input sanitization (security issue)
      const { data, error } = await supabase
        .from('posts')
        .insert([
          { 
            content: newPost,
            user_id: user.id,
            // SQL injection vulnerability (security issue)
            raw_query: `SELECT * FROM users WHERE id = ${user.id}`
          }
        ])
      
      if (error) throw error
      
      // Optimistic update without checking response (code quality issue)
      setNewPost('')
      fetchPosts()
    } catch (error) {
      console.error('Error creating post:', error)
    }
  }
  
  // Potential RLS bypass (security issue)
  const adminFetchAllUsers = async () => {
    // This function attempts to bypass Row Level Security
    const { data } = await supabase
      .from('users')
      .select('*')
      .rpc('bypass_rls', {})
    
    console.log('All users:', data)
  }
  
  return (
    <div>
      <Head>
        <title>Supabase Test App</title>
        <meta name="description" content="A test app for Vibe Code Scanner" />
        <link rel="icon" href="/favicon.ico" />
      </Head>

      <main>
        <h1>Supabase Test App</h1>
        
        {!user ? (
          <div>
            <h2>Sign In / Sign Up</h2>
            {error && <p style={{ color: 'red' }}>{error}</p>}
            
            <form onSubmit={handleSignIn}>
              <div>
                <label htmlFor="email">Email</label>
                <input
                  id="email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                />
              </div>
              
              <div>
                <label htmlFor="password">Password</label>
                <input
                  id="password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                />
              </div>
              
              <div>
                <button type="submit" disabled={loading}>
                  {loading ? 'Loading...' : 'Sign In'}
                </button>
                <button type="button" onClick={handleSignUp} disabled={loading}>
                  Sign Up
                </button>
              </div>
            </form>
          </div>
        ) : (
          <div>
            <h2>Welcome, {user.email}</h2>
            <button onClick={handleSignOut}>Sign Out</button>
            
            <div>
              <h3>Create Post</h3>
              <form onSubmit={createPost}>
                <textarea
                  value={newPost}
                  onChange={(e) => setNewPost(e.target.value)}
                  placeholder="What's on your mind?"
                  required
                />
                <button type="submit">Post</button>
              </form>
            </div>
            
            <div>
              <h3>Posts</h3>
              {posts.length === 0 ? (
                <p>No posts yet.</p>
              ) : (
                <ul>
                  {posts.map((post) => (
                    <li key={post.id}>
                      {/* Potential XSS vulnerability (security issue) */}
                      <div dangerouslySetInnerHTML={{ __html: post.content }} />
                      <small>Posted at: {new Date(post.created_at).toLocaleString()}</small>
                    </li>
                  ))}
                </ul>
              )}
            </div>
            
            {/* Admin button visible to all users (security issue) */}
            <button onClick={adminFetchAllUsers}>
              Admin: Fetch All Users
            </button>
          </div>
        )}
      </main>
    </div>
  )
}
