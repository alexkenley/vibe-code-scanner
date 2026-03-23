# Node.js Test App for Vibe Code Scanner

This test app contains intentional security and code quality issues to demonstrate the capabilities of the Vibe Code Scanner.

## Security Issues

1. **Hardcoded Credentials**
   - JWT secret hardcoded in `server.js`
   - Database credentials hardcoded in `server.js`
   - Admin username and password hardcoded in authentication logic

2. **Command Injection**
   - Direct use of user input in `exec()` command in the `/ping` endpoint
   - No input sanitization before executing shell commands

3. **Path Traversal**
   - Unsanitized file path construction in the `/files` endpoint
   - Direct use of user input in file path

4. **Weak Cryptography**
   - Use of MD5 for password hashing (insecure)
   - No salt used in password hashing

5. **Information Disclosure**
   - Exposing error details to clients
   - Leaking credentials in debug messages
   - Returning detailed error information

6. **Insecure JWT Implementation**
   - No token expiration
   - Weak secret key
   - Insecure cookie settings (missing secure, httpOnly, sameSite flags)

7. **NoSQL Injection**
   - Direct use of user input in database queries
   - No input validation or sanitization

8. **Insecure File Upload**
   - No file type validation
   - No file size limits
   - No virus scanning

9. **Insecure Direct Object Reference**
   - No authorization checks on user data access
   - Direct access to resources via IDs without verification

## Code Quality Issues

1. **Missing Error Handling**
   - Inconsistent error handling patterns
   - Lack of proper try/catch blocks

2. **Console Logs in Production Code**
   - Multiple `console.log` statements throughout the codebase

## How to Use

This app is intended for testing the Vibe Code Scanner. To scan this app, use the following command:

```bash
python scan.py --path /path/to/node-test-app
```

Or using the MCP server:

```bash
curl -X POST http://localhost:7654/tools/scanProject -H "Content-Type: application/json" -d '{"projectPath": "/path/to/node-test-app", "language": "javascript"}'
```
