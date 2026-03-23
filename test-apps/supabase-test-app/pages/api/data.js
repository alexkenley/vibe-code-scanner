import supabase from '../../lib/supabase'

// API route with Supabase-specific security issues
export default async function handler(req, res) {
  if (req.method === 'GET') {
    const { id } = req.query
    
    try {
      // SECURITY ISSUE: Direct SQL injection vulnerability with Supabase
      // This will trigger the VIBE_DETECTED_SUPABASE flag in the scanner
      const { data, error } = await supabase.rpc(
        'execute_sql',
        { sql_query: `SELECT * FROM users WHERE id = ${id}` }
      )
      
      if (error) throw error
      
      return res.status(200).json(data)
    } catch (error) {
      return res.status(500).json({ error: error.message })
    }
  } else if (req.method === 'POST') {
    const { table, record } = req.body
    
    try {
      // SECURITY ISSUE: No input validation before inserting
      const { data, error } = await supabase
        .from(table)
        .insert([record])
      
      if (error) throw error
      
      return res.status(201).json(data)
    } catch (error) {
      return res.status(500).json({ error: error.message })
    }
  }
  
  res.status(405).json({ error: 'Method not allowed' })
}
