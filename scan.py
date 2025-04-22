#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import threading
from urllib.parse import urlparse
from datetime import datetime
from license_scanner import LicenseScanner

# Supported languages (lowercase)
SUPPORTED_LANGUAGES = ["python", "javascript", "typescript", "ruby", "nextjs", "node"]
JSON_REPORT_FILENAME = "vibe_scan_report.json"
LOG_FILENAME = "vibe_scan_log.txt"

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILENAME, mode='w'),
        logging.StreamHandler(sys.stderr)
    ]
)
logger = logging.getLogger("vibe_scanner")

# --- Progress Indicator ---

class Spinner:
    """Simple spinner to show progress during long-running operations."""
    def __init__(self, message="Processing"):
        self.message = message
        self.spinning = False
        self.spinner_chars = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
        self.spinner_thread = None

    def spin(self):
        i = 0
        while self.spinning:
            sys.stdout.write(f"\r{self.message} {self.spinner_chars[i]} ")
            sys.stdout.flush()
            time.sleep(0.1)
            i = (i + 1) % len(self.spinner_chars)

    def start(self, message=None):
        if message:
            self.message = message
        self.spinning = True
        self.spinner_thread = threading.Thread(target=self.spin)
        self.spinner_thread.daemon = True
        self.spinner_thread.start()

    def stop(self, message=None):
        self.spinning = False
        if self.spinner_thread:
            self.spinner_thread.join()
        if message:
            sys.stdout.write(f"\r{message}{' ' * 20}\n")
        else:
            sys.stdout.write(f"\r{' ' * (len(self.message) + 10)}\r")
        sys.stdout.flush()

# Global spinner instance
spinner = Spinner()

def print_section(title):
    """Print a section header with formatting to make it stand out."""
    width = 80
    print("\n" + "=" * width)
    print(f" {title} ".center(width, "="))
    print("=" * width + "\n")

# --- Tool Execution Helpers ---

def is_tool_installed(name):
    """Check whether `name` is on PATH and marked as executable."""
    return shutil.which(name) is not None

def check_prerequisite(command, install_guide, language=None):
    """
    Check if a prerequisite tool is installed and provide helpful feedback if not.
    Returns True if installed, False otherwise.
    """
    if not shutil.which(command):
        logger.error(f"\nERROR: Required tool '{command}' not found.")
        logger.error(f"  {install_guide}")
        if language:
            logger.error(f"  This tool is required for {language} code scanning.")
        logger.error("  Please see README.md for more information on setting up prerequisites.")
        return False
    return True

def _run_command_and_capture(command, cwd):
    """Runs a command and returns its stdout, stderr, and return code."""
    print(f"Running command: {' '.join(command)}")
    
    # Create a copy of the current environment
    env = os.environ.copy()
    
    # Add common Node.js installation paths to PATH if running Node.js tools
    if command[0] in ["npx", "npm", "node", "retire"]:
        nodejs_paths = [
            r"C:\Program Files\nodejs",
            r"C:\Program Files (x86)\nodejs",
            os.path.expanduser(r"~\AppData\Roaming\npm")
        ]
        
        # Add these paths to the PATH environment variable
        path_sep = os.pathsep  # ; on Windows, : on Unix
        for nodejs_path in nodejs_paths:
            if os.path.exists(nodejs_path) and nodejs_path not in env["PATH"]:
                env["PATH"] = nodejs_path + path_sep + env["PATH"]
    
    try:
        # Run the command and capture output
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=cwd,
            env=env  # Use our modified environment
        )
        stdout, stderr = process.communicate()
        return {"stdout": stdout, "stderr": stderr, "returncode": process.returncode}
    except FileNotFoundError:
        logger.error(f"ERROR: Command not found - '{command[0]}'. Please ensure it is installed and in your PATH.")
        return {"stdout": None, "stderr": None, "returncode": -1}
    except Exception as e:
        logger.error(f"ERROR: Failed to run command: {e}")
        return {"stdout": None, "stderr": str(e), "returncode": -1}

# --- Core Logic Functions ---

def detect_language(project_path, specified_language):
    """
    Detect the primary language of the project.
    """
    if specified_language:
        print(f"Using specified language: {specified_language}")
        return specified_language
    
    print("Detecting project language...")
    
    # List all files in the project directory
    items = os.listdir(project_path)
    
    # Check for Next.js
    if "next.config.js" in items or "next.config.mjs" in items:
        print("Detected Next.js (found next.config.js/mjs).")
        return "nextjs"
    
    # Check for package.json to detect Node.js or JS/TS
    if "package.json" in items:
        # Read package.json to determine if it's Node.js, Next.js or regular JS/TS
        try:
            with open(os.path.join(project_path, "package.json"), "r") as f:
                package_data = json.load(f)
                
                # Check for Next.js in dependencies
                dependencies = {**package_data.get("dependencies", {}), **package_data.get("devDependencies", {})}
                if "next" in dependencies:
                    print("Detected Next.js (found in package.json dependencies).")
                    return "nextjs"
                
                # Check if it's a Node.js project (has main, bin, or type: module)
                if "main" in package_data or "bin" in package_data or package_data.get("type") == "module":
                    print("Detected Node.js project.")
                    
                    # Check for Supabase integration
                    if "@supabase/supabase-js" in dependencies:
                        print("Detected Supabase integration.")
                        os.environ["VIBE_DETECTED_SUPABASE"] = "true"
                    
                    return "node"
                
                # Check if it's a TypeScript project
                if "typescript" in dependencies or "tsconfig.json" in items:
                    print("Detected TypeScript project.")
                    return "typescript"
                
                print("Detected JavaScript project.")
                return "javascript"
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error reading package.json: {e}")
    
    # Check for Python
    py_files = find_files_by_extension(project_path, [".py"])
    if py_files:
        # Check for Supabase integration in Python
        for py_file in py_files:
            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    content = f.read()
                    if "supabase" in content.lower():
                        print("Detected Supabase integration in Python.")
                        os.environ["VIBE_DETECTED_SUPABASE"] = "true"
                        break
            except IOError:
                pass
        
        # Check for requirements.txt with supabase
        requirements_file = os.path.join(project_path, "requirements.txt")
        if os.path.exists(requirements_file):
            try:
                with open(requirements_file, "r") as f:
                    content = f.read()
                    if "supabase" in content:
                        print("Detected Supabase integration in requirements.txt.")
                        os.environ["VIBE_DETECTED_SUPABASE"] = "true"
            except IOError:
                pass
        
        print("Detected Python project.")
        return "python"
    
    # Check for Go
    go_files = find_files_by_extension(project_path, [".go"])
    if go_files or "go.mod" in items:
        print("Detected Go project.")
        return "go"
    
    # Default to JavaScript if we can't determine the language
    print("Could not determine project language. Defaulting to JavaScript.")
    return "javascript"

def find_files_by_extension(directory, extensions):
    """
    Find all files with the given extensions in the directory and its subdirectories.
    
    Args:
        directory (str): The directory to search in
        extensions (list): List of file extensions to look for (e.g., [".js", ".jsx"])
    
    Returns:
        list: List of file paths matching the extensions
    """
    matching_files = []
    
    for root, _, files in os.walk(directory):
        for file in files:
            if any(file.endswith(ext) for ext in extensions):
                matching_files.append(os.path.join(root, file))
    
    return matching_files

def check_supabase_integration(project_path, language):
    """
    Check if the project has Supabase integration.
    
    Args:
        project_path (str): Path to the project
        language (str): Detected language of the project
    
    Returns:
        bool: True if Supabase integration is detected, False otherwise
    """
    # Check if already detected during language detection
    if os.environ.get("VIBE_DETECTED_SUPABASE") == "true":
        return True
    
    # Check package.json for JavaScript-based projects
    if language in ["javascript", "typescript", "nextjs", "node"]:
        package_json_path = os.path.join(project_path, "package.json")
        if os.path.exists(package_json_path):
            try:
                with open(package_json_path, "r") as f:
                    package_data = json.load(f)
                    dependencies = {**package_data.get("dependencies", {}), **package_data.get("devDependencies", {})}
                    if "@supabase/supabase-js" in dependencies:
                        os.environ["VIBE_DETECTED_SUPABASE"] = "true"
                        return True
            except (json.JSONDecodeError, IOError):
                pass
    
    # Check for environment variables related to Supabase
    env_files = [".env", ".env.local", ".env.development", ".env.production"]
    for env_file in env_files:
        env_path = os.path.join(project_path, env_file)
        if os.path.exists(env_path):
            try:
                with open(env_path, "r") as f:
                    content = f.read()
                    # Check for different environment variable patterns based on language
                    if language == "nextjs" and "NEXT_PUBLIC_SUPABASE" in content:
                        os.environ["VIBE_DETECTED_SUPABASE"] = "true"
                        return True
                    elif "SUPABASE_URL" in content or "SUPABASE_KEY" in content:
                        os.environ["VIBE_DETECTED_SUPABASE"] = "true"
                        return True
            except IOError:
                pass
    
    # Check for Supabase imports in code files
    if language in ["javascript", "typescript", "nextjs", "node"]:
        js_files = find_files_by_extension(project_path, [".js", ".jsx", ".ts", ".tsx"])
        for js_file in js_files:
            try:
                with open(js_file, "r", encoding="utf-8") as f:
                    content = f.read()
                    if "supabase" in content.lower() and ("createClient" in content or "from 'supabase'" in content or 'from "supabase"' in content):
                        os.environ["VIBE_DETECTED_SUPABASE"] = "true"
                        return True
            except IOError:
                pass
    elif language == "python":
        py_files = find_files_by_extension(project_path, [".py"])
        for py_file in py_files:
            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    content = f.read()
                    if "supabase" in content.lower() and ("import supabase" in content.lower() or "from supabase" in content.lower()):
                        os.environ["VIBE_DETECTED_SUPABASE"] = "true"
                        return True
            except IOError:
                pass
    
    return False

def run_tools(project_path, language):
    """Runs the appropriate static analysis tools based on the detected language."""
    results = {
        "language": language,
        "security_issues": [],
        "code_quality_issues": [],
        "license_issues": [],
        "timestamp": datetime.now().isoformat()
    }

    print(f"Proceeding with scan for: {language}\n")
    tools_found = False
    original_cwd = os.getcwd()
    os.chdir(project_path) # Change to project directory for tool execution

    # Helper function to find files by extension
    def find_files_by_extension(directory, extensions):
        found_files = []
        for root, _, files in os.walk(directory):
            # Skip node_modules directories
            if "node_modules" in root.split(os.path.sep):
                continue
                
            for file in files:
                if any(file.endswith(ext) for ext in extensions):
                    found_files.append(os.path.join(root, file))
        return found_files

    # Run license scanner
    print_section("Scanning for License Issues")
    license_scanner = LicenseScanner()
    license_results = license_scanner.scan_directory(project_path)
    results["license_scan"] = license_results
    
    # Next.js specific scanning
    if language == "nextjs":
        print_section("Scanning Next.js Project")
        
        # Check if ESLint is available
        if not check_prerequisite("npx", "Install Node.js and npm: https://nodejs.org/", "Next.js"):
            logger.error("#"*80)
            logger.error("# ESLint requires 'npx' which was not found.")
            logger.error("# Please install Node.js and npm to enable ESLint scanning.")
            logger.error("#"*80 + "\n")
            results["eslint"] = {"error": "Tool 'npx' not found.", "stdout": None, "stderr": None, "returncode": -1, "project_path": project_path}
        else:
            tools_found = True
            # Find JS/TS files
            js_files = find_files_by_extension(project_path, [".js", ".jsx", ".ts", ".tsx"])
            
            if js_files:
                # Run ESLint
                results["eslint"] = run_eslint(project_path, js_files)
                results["eslint"]["project_path"] = project_path
                
                # Check for TypeScript files
                ts_files = find_files_by_extension(project_path, [".ts", ".tsx"])
                if ts_files:
                    # Run TypeScript compiler check
                    results["typescript"] = run_typescript_check(project_path)
                    results["typescript"]["project_path"] = project_path
            else:
                results["eslint"] = {"error": "No JavaScript/TypeScript files found.", "stdout": None, "stderr": None, "returncode": 0, "project_path": project_path}
        
        # Check for RetireJS (JavaScript dependency vulnerabilities)
        if not check_prerequisite("retire", "Install RetireJS: npm install -g retire", "Next.js"):
            logger.error("#"*80)
            logger.error("# RetireJS requires 'retire' which was not found.")
            logger.error("# Please install RetireJS to enable JavaScript dependency scanning.")
            logger.error("#"*80 + "\n")
            results["retirejs"] = {"error": "Tool 'retire' not found.", "stdout": None, "stderr": None, "returncode": -1, "project_path": project_path}
        else:
            tools_found = True
            try:
                # RetireJS: 0 = no vulnerabilities, 13 = vulnerabilities found
                results["retirejs"] = run_retirejs(project_path)
                results["retirejs"]["project_path"] = project_path
                # RetireJS returns 13 when it finds vulnerabilities, which is expected and should be treated as success
                if results["retirejs"]["returncode"] == 13:
                    results["retirejs"]["returncode"] = 0
            except Exception as e:
                logger.error(f"Error running RetireJS: {e}")
                results["retirejs"] = {"error": f"Error running RetireJS: {e}", "stdout": None, "stderr": str(e), "returncode": -1, "project_path": project_path}
        
        # Next.js specific checks
        nextjs_issues = []
        
        # Check for next.config.js
        next_config_path = os.path.join(project_path, "next.config.js")
        next_config_mjs_path = os.path.join(project_path, "next.config.mjs")
        
        if not os.path.exists(next_config_path) and not os.path.exists(next_config_mjs_path):
            nextjs_issues.append({
                "file": "N/A",
                "line": 0,
                "column": 0,
                "code": "nextjs-missing-config",
                "message": "Missing next.config.js or next.config.mjs file",
                "severity": "medium",
                "tool": "vibe-nextjs"
            })
        
        # Check for pages or app directory
        pages_dir = os.path.join(project_path, "pages")
        app_dir = os.path.join(project_path, "app")
        
        if not os.path.exists(pages_dir) and not os.path.exists(app_dir):
            nextjs_issues.append({
                "file": "N/A",
                "line": 0,
                "column": 0,
                "code": "nextjs-missing-pages-app",
                "message": "Missing both 'pages' and 'app' directories. Next.js requires at least one of these directories.",
                "severity": "high",
                "tool": "vibe-nextjs"
            })
        
        # Check for environment variables
        env_files = [".env", ".env.local", ".env.development", ".env.production"]
        env_file_found = False
        
        for env_file in env_files:
            env_path = os.path.join(project_path, env_file)
            if os.path.exists(env_path):
                env_file_found = True
                break
        
        if not env_file_found:
            nextjs_issues.append({
                "file": "N/A",
                "line": 0,
                "column": 0,
                "code": "nextjs-missing-env",
                "message": "No environment files found (.env, .env.local, etc.). Consider adding environment configuration.",
                "severity": "low",
                "tool": "vibe-nextjs"
            })
        
        # Check for proper public directory
        public_dir = os.path.join(project_path, "public")
        if not os.path.exists(public_dir):
            nextjs_issues.append({
                "file": "N/A",
                "line": 0,
                "column": 0,
                "code": "nextjs-missing-public",
                "message": "Missing 'public' directory for static assets",
                "severity": "low",
                "tool": "vibe-nextjs"
            })
        
        # Store Next.js specific issues
        results["nextjs"] = {
            "stdout": json.dumps(nextjs_issues),
            "stderr": None,
            "returncode": 0 if not nextjs_issues else 1,
            "project_path": project_path,
            "issues": nextjs_issues
        }
        
        # If Supabase is detected, check for proper Supabase configuration
        if os.environ.get("VIBE_DETECTED_SUPABASE") == "true":
            print_section("Checking Supabase Integration in Next.js")
            
            supabase_issues = []
            
            # Check for Supabase client initialization
            js_files = find_files_by_extension(project_path, [".js", ".jsx", ".ts", ".tsx"])
            supabase_client_found = False
            
            for js_file in js_files:
                try:
                    with open(js_file, "r", encoding="utf-8") as f:
                        content = f.read()
                        if "createClient" in content and "supabase" in content.lower():
                            supabase_client_found = True
                            break
                except IOError:
                    pass
            
            if not supabase_client_found:
                supabase_issues.append({
                    "file": "N/A",
                    "line": 0,
                    "column": 0,
                    "code": "nextjs-supabase-client",
                    "message": "Supabase integration detected but no Supabase client initialization found",
                    "severity": "medium",
                    "tool": "vibe-nextjs-supabase"
                })
            
            # Check for lib/supabase.js or utils/supabase.js
            supabase_lib_files = [
                os.path.join(project_path, "lib", "supabase.js"),
                os.path.join(project_path, "lib", "supabase.ts"),
                os.path.join(project_path, "utils", "supabase.js"),
                os.path.join(project_path, "utils", "supabase.ts"),
                os.path.join(project_path, "src", "lib", "supabase.js"),
                os.path.join(project_path, "src", "lib", "supabase.ts"),
                os.path.join(project_path, "src", "utils", "supabase.js"),
                os.path.join(project_path, "src", "utils", "supabase.ts")
            ]
            
            supabase_lib_found = False
            for lib_file in supabase_lib_files:
                if os.path.exists(lib_file):
                    supabase_lib_found = True
                    break
            
            if not supabase_lib_found:
                supabase_issues.append({
                    "file": "N/A",
                    "line": 0,
                    "column": 0,
                    "code": "nextjs-supabase-lib",
                    "message": "Supabase integration detected but no dedicated Supabase client file found. Consider creating a lib/supabase.js or utils/supabase.js file for better code organization.",
                    "severity": "low",
                    "tool": "vibe-nextjs-supabase"
                })
            
            # Check for proper environment variables
            env_files = [".env", ".env.local", ".env.development", ".env.production"]
            supabase_env_vars = False
            
            for env_file in env_files:
                env_path = os.path.join(project_path, env_file)
                if os.path.exists(env_path):
                    try:
                        with open(env_path, "r") as f:
                            content = f.read()
                            if "NEXT_PUBLIC_SUPABASE_URL" in content and "NEXT_PUBLIC_SUPABASE_ANON_KEY" in content:
                                supabase_env_vars = True
                                break
                    except IOError:
                        pass
            
            if not supabase_env_vars:
                supabase_issues.append({
                    "file": "N/A",
                    "line": 0,
                    "column": 0,
                    "code": "nextjs-supabase-env",
                    "message": "Supabase integration detected but missing required environment variables (NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY)",
                    "severity": "medium",
                    "tool": "vibe-nextjs-supabase"
                })
            
            # Check for middleware.js for Supabase auth
            middleware_files = [
                os.path.join(project_path, "middleware.js"),
                os.path.join(project_path, "middleware.ts")
            ]
            
            supabase_middleware_found = False
            for middleware_file in middleware_files:
                if os.path.exists(middleware_file):
                    try:
                        with open(middleware_file, "r", encoding="utf-8") as f:
                            content = f.read()
                            if "supabase" in content.lower() or "createMiddlewareClient" in content:
                                supabase_middleware_found = True
                                break
                    except IOError:
                        pass
            
            if not supabase_middleware_found:
                supabase_issues.append({
                    "file": "N/A",
                    "line": 0,
                    "column": 0,
                    "code": "nextjs-supabase-middleware",
                    "message": "Supabase integration detected but no Supabase middleware found. Consider adding middleware for auth session management.",
                    "severity": "low",
                    "tool": "vibe-nextjs-supabase"
                })
            
            # Check for TypeScript types if using TypeScript
            ts_files = find_files_by_extension(project_path, [".ts", ".tsx"])
            if ts_files:
                supabase_types_found = False
                for ts_file in ts_files:
                    try:
                        with open(ts_file, "r", encoding="utf-8") as f:
                            content = f.read()
                            if "Database" in content and "supabase" in content.lower() and "type" in content:
                                supabase_types_found = True
                                break
                    except IOError:
                        pass
                
                if not supabase_types_found:
                    supabase_issues.append({
                        "file": "N/A",
                        "line": 0,
                        "column": 0,
                        "code": "nextjs-supabase-types",
                        "message": "Supabase integration with TypeScript detected but no type definitions found. Consider adding proper TypeScript types for your database schema.",
                        "severity": "medium",
                        "tool": "vibe-nextjs-supabase"
                    })
            
            # Store Supabase specific issues
            results["supabase"] = {
                "stdout": json.dumps(supabase_issues),
                "stderr": None,
                "returncode": 0 if not supabase_issues else 1,
                "project_path": project_path,
                "issues": supabase_issues
            }
    
    # Node.js specific scanning
    elif language == "node":
        print_section("Scanning Node.js Project")
        
        # First, run standard JavaScript/TypeScript tools
        # Check if ESLint is available
        if not check_prerequisite("npx", "Install Node.js and npm: https://nodejs.org/", "JavaScript/TypeScript"):
            logger.error("#"*80)
            logger.error("# ESLint requires 'npx' which was not found.")
            logger.error("# Please install Node.js and npm to enable ESLint scanning.")
            logger.error("#"*80 + "\n")
            results["eslint"] = {"error": "Tool 'npx' not found.", "stdout": None, "stderr": None, "returncode": -1, "project_path": project_path}
        else:
            tools_found = True
            # Find JS/TS files
            js_ts_files = find_files_by_extension(project_path, [".js", ".jsx", ".ts", ".tsx"])
            
            if js_ts_files:
                # Run ESLint
                results["eslint"] = run_eslint(project_path, js_ts_files)
                results["eslint"]["project_path"] = project_path
                
                # Run TypeScript compiler check if TS files exist
                ts_files = [f for f in js_ts_files if f.endswith((".ts", ".tsx"))]
                if ts_files and os.path.exists(os.path.join(project_path, "tsconfig.json")):
                    results["typescript"] = run_typescript_check(project_path)
                    results["typescript"]["project_path"] = project_path
            else:
                results["eslint"] = {"error": "No JavaScript/TypeScript files found.", "stdout": None, "stderr": None, "returncode": 0, "project_path": project_path}
        
        # Check for RetireJS (JavaScript dependency vulnerabilities)
        if not check_prerequisite("retire", "Install RetireJS: npm install -g retire", "JavaScript/TypeScript"):
            logger.error("#"*80)
            logger.error("# RetireJS requires 'retire' which was not found.")
            logger.error("# Please install RetireJS to enable JavaScript dependency scanning.")
            logger.error("#"*80 + "\n")
            results["retirejs"] = {"error": "Tool 'retire' not found.", "stdout": None, "stderr": None, "returncode": -1, "project_path": project_path}
        else:
            tools_found = True
            try:
                # RetireJS: 0 = no vulnerabilities, 13 = vulnerabilities found
                results["retirejs"] = run_retirejs(project_path)
                results["retirejs"]["project_path"] = project_path
                # RetireJS returns 13 when it finds vulnerabilities, which is expected and should be treated as success
                if results["retirejs"]["returncode"] == 13:
                    results["retirejs"]["returncode"] = 0
            except Exception as e:
                logger.error(f"Error running RetireJS: {e}")
                results["retirejs"] = {"error": f"Error: {e}", "stdout": None, "stderr": str(e), "returncode": -1, "project_path": project_path}
        
        # Node.js specific checks
        print_section("Running Node.js Specific Checks")
        
        # Check for proper Node.js configuration
        nodejs_issues = []
        
        # Check for package.json
        if not os.path.exists(os.path.join(project_path, "package.json")):
            nodejs_issues.append({
                "file": "N/A",
                "line": 0,
                "column": 0,
                "code": "node-missing-package-json",
                "message": "Missing package.json file",
                "severity": "high",
                "tool": "vibe-nodejs"
            })
        else:
            # Check for proper package.json configuration
            try:
                with open(os.path.join(project_path, "package.json"), "r") as f:
                    package_data = json.load(f)
                    
                    # Check for main entry point
                    if "main" not in package_data:
                        nodejs_issues.append({
                            "file": "package.json",
                            "line": 0,
                            "column": 0,
                            "code": "node-missing-main",
                            "message": "Missing 'main' entry in package.json",
                            "severity": "medium",
                            "tool": "vibe-nodejs"
                        })
                    
                    # Check for scripts
                    if "scripts" not in package_data or not package_data["scripts"]:
                        nodejs_issues.append({
                            "file": "package.json",
                            "line": 0,
                            "column": 0,
                            "code": "node-missing-scripts",
                            "message": "Missing 'scripts' in package.json",
                            "severity": "low",
                            "tool": "vibe-nodejs"
                        })
                    elif "start" not in package_data.get("scripts", {}):
                        nodejs_issues.append({
                            "file": "package.json",
                            "line": 0,
                            "column": 0,
                            "code": "node-missing-start-script",
                            "message": "Missing 'start' script in package.json",
                            "severity": "low",
                            "tool": "vibe-nodejs"
                        })
                    
                    # Check for dependencies
                    if "dependencies" not in package_data and "devDependencies" not in package_data:
                        nodejs_issues.append({
                            "file": "N/A",
                            "line": 0,
                            "column": 0,
                            "code": "node-missing-dependencies",
                            "message": "No dependencies defined in package.json",
                            "severity": "medium",
                            "tool": "vibe-nodejs"
                        })
                    
                    # If Supabase is detected, check for proper Supabase configuration
                    if os.environ.get("VIBE_DETECTED_SUPABASE") == "true":
                        dependencies = {**package_data.get("dependencies", {}), **package_data.get("devDependencies", {})}
                        if "@supabase/supabase-js" not in dependencies:
                            nodejs_issues.append({
                                "file": "package.json",
                                "line": 0,
                                "column": 0,
                                "code": "node-missing-supabase",
                                "message": "Supabase integration detected but @supabase/supabase-js dependency is missing",
                                "severity": "medium",
                                "tool": "vibe-nodejs-supabase"
                            })
            except (json.JSONDecodeError, IOError) as e:
                nodejs_issues.append({
                    "file": "package.json",
                    "line": 0,
                    "column": 0,
                    "code": "node-invalid-package-json",
                    "message": f"Invalid package.json: {str(e)}",
                    "severity": "high",
                    "tool": "vibe-nodejs"
                })
        
        # Check for .env file if Supabase is detected
        if os.environ.get("VIBE_DETECTED_SUPABASE") == "true":
            env_files = [".env", ".env.local", ".env.development", ".env.production"]
            supabase_env_vars = False
            
            for env_file in env_files:
                env_path = os.path.join(project_path, env_file)
                if os.path.exists(env_path):
                    try:
                        with open(env_path, "r") as f:
                            content = f.read()
                            if "SUPABASE_URL" in content and "SUPABASE_KEY" in content:
                                supabase_env_vars = True
                                break
                    except IOError:
                        pass
            
            if not supabase_env_vars:
                nodejs_issues.append({
                    "file": "N/A",
                    "line": 0,
                    "column": 0,
                    "code": "node-supabase-env",
                    "message": "Supabase integration detected but missing required environment variables (SUPABASE_URL and SUPABASE_KEY)",
                    "severity": "medium",
                    "tool": "vibe-nodejs-supabase"
                })
        
        # Store Node.js specific issues
        results["nodejs"] = {
            "stdout": json.dumps(nodejs_issues),
            "stderr": None,
            "returncode": 0 if not nodejs_issues else 1,
            "project_path": project_path,
            "issues": nodejs_issues
        }
    
    # JavaScript scanning
    elif language == "javascript":
        print_section("Scanning JavaScript Project")
        
        # Check if ESLint is available
        if not check_prerequisite("npx", "Install Node.js and npm: https://nodejs.org/", "JavaScript"):
            logger.error("#"*80)
            logger.error("# ESLint requires 'npx' which was not found.")
            logger.error("# Please install Node.js and npm to enable ESLint scanning.")
            logger.error("#"*80 + "\n")
            results["eslint"] = {"error": "Tool 'npx' not found.", "stdout": None, "stderr": None, "returncode": -1, "project_path": project_path}
        else:
            tools_found = True
            # Find JS files
            js_files = find_files_by_extension(project_path, [".js", ".jsx"])
            
            if js_files:
                # Run ESLint
                results["eslint"] = run_eslint(project_path, js_files)
                results["eslint"]["project_path"] = project_path
            else:
                results["eslint"] = {"error": "No JavaScript files found.", "stdout": None, "stderr": None, "returncode": 0, "project_path": project_path}
        
        # Check for RetireJS (JavaScript dependency vulnerabilities)
        if not check_prerequisite("retire", "Install RetireJS: npm install -g retire", "JavaScript"):
            logger.error("#"*80)
            logger.error("# RetireJS requires 'retire' which was not found.")
            logger.error("# Please install RetireJS to enable JavaScript dependency scanning.")
            logger.error("#"*80 + "\n")
            results["retirejs"] = {"error": "Tool 'retire' not found.", "stdout": None, "stderr": None, "returncode": -1, "project_path": project_path}
        else:
            tools_found = True
            try:
                # RetireJS: 0 = no vulnerabilities, 13 = vulnerabilities found
                results["retirejs"] = run_retirejs(project_path)
                results["retirejs"]["project_path"] = project_path
                # RetireJS returns 13 when it finds vulnerabilities, which is expected and should be treated as success
                if results["retirejs"]["returncode"] == 13:
                    results["retirejs"]["returncode"] = 0
            except Exception as e:
                logger.error(f"Error running RetireJS: {e}")
                results["retirejs"] = {"error": f"Error: {e}", "stdout": None, "stderr": str(e), "returncode": -1, "project_path": project_path}
        
        # If Supabase is detected, check for proper Supabase configuration
        if os.environ.get("VIBE_DETECTED_SUPABASE") == "true":
            print_section("Checking Supabase Integration")
            
            supabase_issues = []
            
            # Check for Supabase client initialization
            js_files = find_files_by_extension(project_path, [".js", ".jsx"])
            supabase_client_found = False
            
            for js_file in js_files:
                try:
                    with open(js_file, "r", encoding="utf-8") as f:
                        content = f.read()
                        if "createClient" in content and "supabase" in content.lower():
                            supabase_client_found = True
                            break
                except IOError:
                    pass
            
            if not supabase_client_found:
                supabase_issues.append({
                    "file": "N/A",
                    "line": 0,
                    "column": 0,
                    "code": "js-supabase-client",
                    "message": "Supabase integration detected but no Supabase client initialization found",
                    "severity": "medium",
                    "tool": "vibe-js-supabase"
                })
            
            # Check for .env file with Supabase variables
            env_files = [".env", ".env.local", ".env.development", ".env.production"]
            supabase_env_vars = False
            
            for env_file in env_files:
                env_path = os.path.join(project_path, env_file)
                if os.path.exists(env_path):
                    try:
                        with open(env_path, "r") as f:
                            content = f.read()
                            if "SUPABASE_URL" in content and "SUPABASE_KEY" in content:
                                supabase_env_vars = True
                                break
                    except IOError:
                        pass
            
            if not supabase_env_vars:
                supabase_issues.append({
                    "file": "N/A",
                    "line": 0,
                    "column": 0,
                    "code": "js-supabase-env",
                    "message": "Supabase integration detected but missing required environment variables (SUPABASE_URL and SUPABASE_KEY)",
                    "severity": "medium",
                    "tool": "vibe-js-supabase"
                })
            
            # Store Supabase specific issues
            results["supabase"] = {
                "stdout": json.dumps(supabase_issues),
                "stderr": None,
                "returncode": 0 if not supabase_issues else 1,
                "project_path": project_path,
                "issues": supabase_issues
            }
    
    # TypeScript scanning
    elif language == "typescript":
        print_section("Scanning TypeScript Project")
        
        # Check if ESLint is available
        if not check_prerequisite("npx", "Install Node.js and npm: https://nodejs.org/", "TypeScript"):
            logger.error("#"*80)
            logger.error("# ESLint requires 'npx' which was not found.")
            logger.error("# Please install Node.js and npm to enable ESLint scanning.")
            logger.error("#"*80 + "\n")
            results["eslint"] = {"error": "Tool 'npx' not found.", "stdout": None, "stderr": None, "returncode": -1, "project_path": project_path}
        else:
            tools_found = True
            # Find TS files
            ts_files = find_files_by_extension(project_path, [".ts", ".tsx"])
            
            if ts_files:
                # Run ESLint
                results["eslint"] = run_eslint(project_path, ts_files)
                results["eslint"]["project_path"] = project_path
                
                # Run TypeScript compiler check
                results["typescript"] = run_typescript_check(project_path)
                results["typescript"]["project_path"] = project_path
            else:
                results["eslint"] = {"error": "No TypeScript files found.", "stdout": None, "stderr": None, "returncode": 0, "project_path": project_path}
        
        # Check for RetireJS (JavaScript dependency vulnerabilities)
        if not check_prerequisite("retire", "Install RetireJS: npm install -g retire", "TypeScript"):
            logger.error("#"*80)
            logger.error("# RetireJS requires 'retire' which was not found.")
            logger.error("# Please install RetireJS to enable JavaScript dependency scanning.")
            logger.error("#"*80 + "\n")
            results["retirejs"] = {"error": "Tool 'retire' not found.", "stdout": None, "stderr": None, "returncode": -1, "project_path": project_path}
        else:
            tools_found = True
            try:
                # RetireJS: 0 = no vulnerabilities, 13 = vulnerabilities found
                results["retirejs"] = run_retirejs(project_path)
                results["retirejs"]["project_path"] = project_path
                # RetireJS returns 13 when it finds vulnerabilities, which is expected and should be treated as success
                if results["retirejs"]["returncode"] == 13:
                    results["retirejs"]["returncode"] = 0
            except Exception as e:
                logger.error(f"Error running RetireJS: {e}")
                results["retirejs"] = {"error": f"Error: {e}", "stdout": None, "stderr": str(e), "returncode": -1, "project_path": project_path}
        
        # If Supabase is detected, check for proper Supabase configuration
        if os.environ.get("VIBE_DETECTED_SUPABASE") == "true":
            print_section("Checking Supabase Integration")
            
            supabase_issues = []
            
            # Check for Supabase client initialization
            ts_files = find_files_by_extension(project_path, [".ts", ".tsx"])
            supabase_client_found = False
            
            for ts_file in ts_files:
                try:
                    with open(ts_file, "r", encoding="utf-8") as f:
                        content = f.read()
                        if "createClient" in content and "supabase" in content.lower():
                            supabase_client_found = True
                            break
                except IOError:
                    pass
            
            if not supabase_client_found:
                supabase_issues.append({
                    "file": "N/A",
                    "line": 0,
                    "column": 0,
                    "code": "ts-supabase-client",
                    "message": "Supabase integration detected but no Supabase client initialization found",
                    "severity": "medium",
                    "tool": "vibe-ts-supabase"
                })
            
            # Check for proper type definitions
            supabase_types_found = False
            for ts_file in ts_files:
                try:
                    with open(ts_file, "r", encoding="utf-8") as f:
                        content = f.read()
                        if "Database" in content and "supabase" in content.lower() and "type" in content:
                            supabase_types_found = True
                            break
                except IOError:
                    pass
            
            if not supabase_types_found:
                supabase_issues.append({
                    "file": "N/A",
                    "line": 0,
                    "column": 0,
                    "code": "ts-supabase-types",
                    "message": "Supabase integration detected but no type definitions found. Consider adding proper TypeScript types for your database schema.",
                    "severity": "medium",
                    "tool": "vibe-ts-supabase"
                })
            
            # Check for .env file with Supabase variables
            env_files = [".env", ".env.local", ".env.development", ".env.production"]
            supabase_env_vars = False
            
            for env_file in env_files:
                env_path = os.path.join(project_path, env_file)
                if os.path.exists(env_path):
                    try:
                        with open(env_path, "r") as f:
                            content = f.read()
                            if "SUPABASE_URL" in content and "SUPABASE_KEY" in content:
                                supabase_env_vars = True
                                break
                    except IOError:
                        pass
            
            if not supabase_env_vars:
                supabase_issues.append({
                    "file": "N/A",
                    "line": 0,
                    "column": 0,
                    "code": "ts-supabase-env",
                    "message": "Supabase integration detected but missing required environment variables (SUPABASE_URL and SUPABASE_KEY)",
                    "severity": "medium",
                    "tool": "vibe-ts-supabase"
                })
            
            # Store Supabase specific issues
            results["supabase"] = {
                "stdout": json.dumps(supabase_issues),
                "stderr": None,
                "returncode": 0 if not supabase_issues else 1,
                "project_path": project_path,
                "issues": supabase_issues
            }
    
    # Python scanning
    elif language == "python":
        print_section("Scanning Python Project")
        
        # Check if Flake8 is available
        if not check_prerequisite("flake8", "Install Flake8: pip install flake8", "Python"):
            logger.error("#"*80)
            logger.error("# Flake8 was not found.")
            logger.error("# Please install Flake8 to enable Python code quality scanning.")
            logger.error("#"*80 + "\n")
            results["flake8"] = {"error": "Tool 'flake8' not found.", "stdout": None, "stderr": None, "returncode": -1, "project_path": project_path}
        else:
            tools_found = True
            # Run Flake8
            cmd = ["flake8", "."]
            results["flake8"] = _run_command_and_capture(cmd, cwd=project_path)
            results["flake8"]["project_path"] = project_path
        
        # Check if Bandit is available
        if not check_prerequisite("bandit", "Install Bandit: pip install bandit", "Python"):
            logger.error("#"*80)
            logger.error("# Bandit was not found.")
            logger.error("# Please install Bandit to enable Python security scanning.")
            logger.error("#"*80 + "\n")
            results["bandit"] = {"error": "Tool 'bandit' not found.", "stdout": None, "stderr": None, "returncode": -1, "project_path": project_path}
        else:
            tools_found = True
            # Run Bandit
            cmd = ["bandit", "-r", ".", "-f", "json"]
            results["bandit"] = _run_command_and_capture(cmd, cwd=project_path)
            results["bandit"]["project_path"] = project_path
        
        # If Supabase is detected, check for proper Supabase configuration
        if os.environ.get("VIBE_DETECTED_SUPABASE") == "true":
            print_section("Checking Supabase Integration")
            
            supabase_issues = []
            
            # Check for Supabase client initialization
            py_files = find_files_by_extension(project_path, [".py"])
            supabase_client_found = False
            
            for py_file in py_files:
                try:
                    with open(py_file, "r", encoding="utf-8") as f:
                        content = f.read()
                        if "supabase" in content.lower() and ("create_client" in content or "Client" in content):
                            supabase_client_found = True
                            break
                except IOError:
                    pass
            
            if not supabase_client_found:
                supabase_issues.append({
                    "file": "N/A",
                    "line": 0,
                    "column": 0,
                    "code": "py-supabase-client",
                    "message": "Supabase integration detected but no Supabase client initialization found",
                    "severity": "medium",
                    "tool": "vibe-py-supabase"
                })
            
            # Check for requirements.txt with supabase
            requirements_file = os.path.join(project_path, "requirements.txt")
            if os.path.exists(requirements_file):
                try:
                    with open(requirements_file, "r") as f:
                        content = f.read()
                        if "supabase" not in content:
                            supabase_issues.append({
                                "file": "requirements.txt",
                                "line": 0,
                                "column": 0,
                                "code": "py-supabase-requirements",
                                "message": "Supabase integration detected but supabase package not found in requirements.txt",
                                "severity": "medium",
                                "tool": "vibe-py-supabase"
                            })
                except IOError:
                    pass
            
            # Check for .env file with Supabase variables
            env_files = [".env", ".env.local", ".env.development", ".env.production"]
            supabase_env_vars = False
            
            for env_file in env_files:
                env_path = os.path.join(project_path, env_file)
                if os.path.exists(env_path):
                    try:
                        with open(env_path, "r") as f:
                            content = f.read()
                            if "SUPABASE_URL" in content and "SUPABASE_KEY" in content:
                                supabase_env_vars = True
                                break
                    except IOError:
                        pass
            
            if not supabase_env_vars:
                supabase_issues.append({
                    "file": "N/A",
                    "line": 0,
                    "column": 0,
                    "code": "py-supabase-env",
                    "message": "Supabase integration detected but missing required environment variables (SUPABASE_URL and SUPABASE_KEY)",
                    "severity": "medium",
                    "tool": "vibe-py-supabase"
                })
            
            # Store Supabase specific issues
            results["supabase"] = {
                "stdout": json.dumps(supabase_issues),
                "stderr": None,
                "returncode": 0 if not supabase_issues else 1,
                "project_path": project_path,
                "issues": supabase_issues
            }
    
    # Go scanning
    elif language == "go":
        print_section("Scanning Go Project")
        
        # Check if golangci-lint is available
        if not check_prerequisite("golangci-lint", "Install golangci-lint: https://golangci-lint.run/usage/install/", "Go"):
            logger.error("#"*80)
            logger.error("# golangci-lint was not found.")
            logger.error("# Please install golangci-lint to enable Go code quality scanning.")
            logger.error("#"*80 + "\n")
            results["golangci-lint"] = {"error": "Tool 'golangci-lint' not found.", "stdout": None, "stderr": None, "returncode": -1, "project_path": project_path}
        else:
            tools_found = True
            # Run golangci-lint
            cmd = ["golangci-lint", "run", "./...", "--out-format", "json", "--issues-exit-code", "1"]
            results["golangci-lint"] = _run_command_and_capture(cmd, cwd=project_path)
            results["golangci-lint"]["project_path"] = project_path
        
        # Check if gosec is available
        if not check_prerequisite("gosec", "Install gosec: go install github.com/securego/gosec/v2/cmd/gosec@latest", "Go"):
            logger.error("#"*80)
            logger.error("# gosec was not found.")
            logger.error("# Please install gosec to enable Go security scanning.")
            logger.error("#"*80 + "\n")
            results["gosec"] = {"error": "Tool 'gosec' not found.", "stdout": None, "stderr": None, "returncode": -1, "project_path": project_path}
        else:
            tools_found = True
            # Run gosec
            cmd = ["gosec", "-fmt=json", "./..."]
            results["gosec"] = _run_command_and_capture(cmd, cwd=project_path)
            results["gosec"]["project_path"] = project_path
    
    # Return to original working directory
    os.chdir(original_cwd)
    
    # Write results to JSON file
    with open(JSON_REPORT_FILENAME, "w") as f:
        json.dump(results, f, indent=4)
    
    # Print summary
    print_section("Scan Summary")
    print(f"Project path: {project_path}")
    print(f"Detected language: {language}")
    print(f"Tools found: {tools_found}")
    print(f"Results written to: {JSON_REPORT_FILENAME}")
    
    # Exit with return code 0 if no issues were found, 1 otherwise
    if any(issue["returncode"] != 0 for issue in results.values()):
        sys.exit(1)
    else:
        sys.exit(0)

def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description='Run static analysis tools on a project.')
    parser.add_argument('project_path', help='Path to the project directory')
    parser.add_argument('--language', help='Specify the project language (optional)')
    parser.add_argument('--github', help='GitHub repository URL to scan (e.g., https://github.com/username/repo)')
    parser.add_argument('--token', help='GitHub personal access token for private repositories')
    parser.add_argument('--branch', help='GitHub branch to scan (default: main or master)')
    args = parser.parse_args()
    
    # Set up logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Check if we're scanning a GitHub repository
    if args.github:
        print_section("GitHub Repository Scanning")
        print(f"Repository URL: {args.github}")
        
        # Create a temporary directory for the repository
        temp_dir = tempfile.mkdtemp()
        try:
            # Clone the repository
            clone_cmd = ["git", "clone"]
            
            # Add token if provided
            if args.token:
                # Parse the GitHub URL to add the token
                parsed_url = urlparse(args.github)
                auth_url = f"{parsed_url.scheme}://{args.token}@{parsed_url.netloc}{parsed_url.path}"
                clone_cmd.append(auth_url)
            else:
                clone_cmd.append(args.github)
            
            # Add branch if specified
            if args.branch:
                clone_cmd.extend(["--branch", args.branch])
            
            # Add destination directory
            clone_cmd.append(temp_dir)
            
            print(f"Cloning repository...")
            subprocess.run(clone_cmd, check=True)
            
            # Run the scan on the cloned repository
            project_path = temp_dir
            language = detect_language(project_path, args.language)
            
            # Check for Supabase integration
            if check_supabase_integration(project_path, language):
                print("Supabase integration confirmed.")
                os.environ["VIBE_DETECTED_SUPABASE"] = "true"
            
            # Run the tools
            run_tools(project_path, language)
            
            # Copy the results to the current directory
            if os.path.exists(os.path.join(temp_dir, JSON_REPORT_FILENAME)):
                shutil.copy(os.path.join(temp_dir, JSON_REPORT_FILENAME), os.getcwd())
                print(f"Scan results copied to {os.path.join(os.getcwd(), JSON_REPORT_FILENAME)}")
            
            # Copy the HTML report if it exists
            if os.path.exists(os.path.join(temp_dir, HTML_REPORT_FILENAME)):
                shutil.copy(os.path.join(temp_dir, HTML_REPORT_FILENAME), os.getcwd())
                print(f"HTML report copied to {os.path.join(os.getcwd(), HTML_REPORT_FILENAME)}")
            
        except subprocess.CalledProcessError as e:
            print(f"Error cloning repository: {e}")
            sys.exit(1)
        finally:
            # Clean up the temporary directory
            shutil.rmtree(temp_dir)
    else:
        # Validate project path
        project_path = os.path.abspath(args.project_path)
        if not os.path.isdir(project_path):
            print(f"Error: {project_path} is not a valid directory", file=sys.stderr)
            sys.exit(1)
        
        # Detect language and run tools
        language = detect_language(project_path, args.language)
        if not language:
            print("Error: Could not detect project language and none was specified", file=sys.stderr)
            sys.exit(1)
        
        # Check for Supabase integration
        if check_supabase_integration(project_path, language):
            print("Supabase integration confirmed.")
            os.environ["VIBE_DETECTED_SUPABASE"] = "true"
        
        # Run the tools
        run_tools(project_path, language)

if __name__ == "__main__":
    main()
