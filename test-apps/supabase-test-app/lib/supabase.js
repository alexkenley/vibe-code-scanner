import { createClient } from '@supabase/supabase-js'

// Hardcoded Supabase credentials (security issue)
const supabaseUrl = 'https://xyzcompany.supabase.co'
const supabaseKey = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InhtdGJyaGF5dWt5aHBzZnZlaXp5Iiwicm9sZSI6ImFub24iLCJpYXQiOjE2NjY2MzQ5MDAsImV4cCI6MTk4MjIxMDkwMH0.EXAMPLE_KEY'

// Create a single supabase client for interacting with your database
const supabase = createClient(supabaseUrl, supabaseKey)

export default supabase
