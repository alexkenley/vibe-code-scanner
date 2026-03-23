# Supabase Test App for Vibe Code Scanner

This test app contains intentional security and code quality issues specific to Supabase integration to demonstrate the capabilities of the Vibe Code Scanner.

## Security Issues

1. **Hardcoded Supabase Credentials**
   - Supabase URL and API key hardcoded in `lib/supabase.js`
   - Should be using environment variables instead

2. **SQL Injection in Supabase Queries**
   - Direct string concatenation in SQL queries in `pages/index.js`
   - Unsafe use of `rpc` with user-controlled SQL in `pages/api/data.js`

3. **Row Level Security (RLS) Bypass Attempts**
   - Function attempting to bypass RLS in `pages/index.js`
   - Improper use of RPC functions to execute privileged operations

4. **XSS Vulnerabilities**
   - Use of `dangerouslySetInnerHTML` with unsanitized content from database
   - Rendering post content directly without sanitization

5. **Sensitive Data Exposure**
   - Logging sensitive user information to console
   - Exposing error details to clients

6. **Authentication Issues**
   - No password strength requirements
   - No rate limiting on authentication endpoints
   - Logging of authentication details

7. **Missing Input Validation**
   - No validation before inserting data into Supabase tables
   - No sanitization of user inputs

## Code Quality Issues

1. **Unused Variables**
   - Declared but never used in `pages/index.js`

2. **Console Logs in Production Code**
   - Multiple `console.log` statements throughout the codebase
   - Logging of sensitive information

3. **Memory Leaks**
   - No cleanup for Supabase subscriptions
   - Missing unsubscribe in useEffect

4. **Improper Error Handling**
   - Inconsistent error handling patterns
   - Missing error handling in some async functions

## Supabase-Specific Detection

This test app is specifically designed to trigger the `VIBE_DETECTED_SUPABASE` flag in the Vibe Code Scanner. The scanner should detect:

1. The use of Supabase libraries (`@supabase/supabase-js`)
2. Supabase-specific security vulnerabilities
3. Improper use of Supabase features like RLS and RPC

## How to Use

This app is intended for testing the Vibe Code Scanner. To scan this app, use the following command:

```bash
python scan.py --path /path/to/supabase-test-app
```

Or using the MCP server:

```bash
curl -X POST http://localhost:7654/tools/scanProject -H "Content-Type: application/json" -d '{"projectPath": "/path/to/supabase-test-app", "language": "javascript"}'
```
