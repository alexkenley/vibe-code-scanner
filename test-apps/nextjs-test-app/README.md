# Next.js Test App for Vibe Code Scanner

This test app contains intentional security and code quality issues to demonstrate the capabilities of the Vibe Code Scanner.

## Security Issues

1. **Hardcoded API Keys**
   - Hardcoded API key in `pages/index.js`

2. **XSS Vulnerabilities**
   - Use of `dangerouslySetInnerHTML` without sanitization in `pages/index.js`
   - Rendering HTML directly from external sources

3. **SQL Injection**
   - Direct string concatenation in SQL queries in `pages/index.js`

4. **Information Disclosure**
   - Exposing error details to clients in `pages/index.js` and `pages/api/users.js`
   - Leaking sensitive information in error responses
   - Debug information in API responses

5. **Sensitive Data Exposure**
   - Returning sensitive user data including SSN and password hashes in `pages/api/users.js`

6. **Authentication Issues**
   - Missing authentication checks in API routes
   - Plaintext password storage in `pages/api/users.js`

7. **Missing Security Headers**
   - No CSRF protection in API routes
   - No rate limiting

## Code Quality Issues

1. **Unused Variables**
   - Declared but never used in `pages/index.js`

2. **Console Logs in Production Code**
   - Multiple `console.log` statements throughout the codebase

3. **Improper Error Handling**
   - Exposing stack traces to users
   - Inconsistent error handling patterns

## How to Use

This app is intended for testing the Vibe Code Scanner. To scan this app, use the following command:

```bash
python scan.py --path /path/to/nextjs-test-app
```

Or using the MCP server:

```bash
curl -X POST http://localhost:7654/tools/scanProject -H "Content-Type: application/json" -d '{"projectPath": "/path/to/nextjs-test-app", "language": "javascript"}'
```
