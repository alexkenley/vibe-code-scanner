import requests
import json
import os
import time
from typing import Dict, List, Optional, Any, Union
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("vibe_mcp_client")

class VibeCodeScannerClient:
    """Client for interacting with the Vibe Code Scanner MCP Server"""
    
    def __init__(self, base_url: str = "http://127.0.0.1:8000"):
        """
        Initialize the client with the server URL
        
        Args:
            base_url: Base URL of the Vibe Code Scanner MCP Server
        """
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
    
    def check_server_health(self) -> Dict[str, Any]:
        """
        Check if the server is running and healthy
        
        Returns:
            Dict containing server health information
        
        Raises:
            ConnectionError: If the server is not reachable
        """
        try:
            response = self.session.get(f"{self.base_url}/health")
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Failed to connect to server: {e}")
            raise ConnectionError(f"Failed to connect to Vibe Code Scanner server: {e}")
    
    def get_capabilities(self) -> Dict[str, Any]:
        """
        Get the capabilities of the server
        
        Returns:
            Dict containing server capabilities
        """
        response = self.session.get(f"{self.base_url}/capabilities")
        response.raise_for_status()
        return response.json()
    
    def scan_project(self, project_path: str, language: Optional[str] = None, scan_id: Optional[str] = None) -> str:
        """
        Start a scan of a project directory
        
        Args:
            project_path: Path to the project directory
            language: Optional language specification
            scan_id: Optional client-provided scan ID
        
        Returns:
            Scan ID that can be used to check status and get results
        """
        payload = {
            "project_path": os.path.abspath(project_path),
            "language": language,
            "scan_id": scan_id
        }
        
        response = self.session.post(f"{self.base_url}/scan/project", json=payload)
        response.raise_for_status()
        result = response.json()
        return result["scan_id"]
    
    def scan_file(self, file_path: str, language: str, file_content: Optional[str] = None) -> Dict[str, Any]:
        """
        Scan a single file
        
        Args:
            file_path: Path to the file
            language: Language of the file
            file_content: Optional file content (if not provided, will read from file_path)
        
        Returns:
            Dict containing scan results
        """
        # Read file content if not provided
        if file_content is None:
            with open(file_path, 'r', encoding='utf-8') as f:
                file_content = f.read()
        
        payload = {
            "file_content": {
                "path": os.path.basename(file_path),
                "content": file_content
            },
            "language": language
        }
        
        response = self.session.post(f"{self.base_url}/scan/file", json=payload)
        response.raise_for_status()
        return response.json()
    
    def get_scan_status(self, scan_id: str) -> Dict[str, Any]:
        """
        Get the status of a scan
        
        Args:
            scan_id: ID of the scan
        
        Returns:
            Dict containing scan status
        """
        response = self.session.get(f"{self.base_url}/scan/{scan_id}/status")
        response.raise_for_status()
        return response.json()
    
    def get_scan_result(self, scan_id: str) -> Dict[str, Any]:
        """
        Get the results of a completed scan
        
        Args:
            scan_id: ID of the scan
        
        Returns:
            Dict containing scan results
        
        Raises:
            requests.HTTPError: If scan is still in progress or not found
        """
        response = self.session.get(f"{self.base_url}/scan/{scan_id}/result")
        response.raise_for_status()
        return response.json()
    
    def wait_for_scan_completion(self, scan_id: str, timeout: int = 300, poll_interval: int = 2) -> Dict[str, Any]:
        """
        Wait for a scan to complete and return the results
        
        Args:
            scan_id: ID of the scan
            timeout: Maximum time to wait in seconds
            poll_interval: Time between status checks in seconds
        
        Returns:
            Dict containing scan results
        
        Raises:
            TimeoutError: If the scan does not complete within the timeout
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                status = self.get_scan_status(scan_id)
                
                if status["status"] == "completed":
                    return self.get_scan_result(scan_id)
                
                if status["status"] == "failed":
                    result = self.get_scan_result(scan_id)
                    logger.error(f"Scan failed: {result.get('error', 'Unknown error')}")
                    return result
                
                # Still running, wait and try again
                time.sleep(poll_interval)
                
            except requests.HTTPError as e:
                if e.response.status_code == 202:
                    # Still running, wait and try again
                    time.sleep(poll_interval)
                else:
                    raise
        
        raise TimeoutError(f"Scan did not complete within {timeout} seconds")
    
    def cancel_scan(self, scan_id: str) -> Dict[str, Any]:
        """
        Cancel a running scan
        
        Args:
            scan_id: ID of the scan
        
        Returns:
            Dict containing cancellation status
        """
        response = self.session.delete(f"{self.base_url}/scan/{scan_id}")
        response.raise_for_status()
        return response.json()


# Example usage
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Vibe Code Scanner MCP Client")
    parser.add_argument("--server", default="http://127.0.0.1:8000", help="MCP Server URL")
    parser.add_argument("--project", help="Path to project to scan")
    parser.add_argument("--file", help="Path to file to scan")
    parser.add_argument("--language", help="Language to use for scanning")
    
    args = parser.parse_args()
    
    client = VibeCodeScannerClient(args.server)
    
    # Check server health
    try:
        health = client.check_server_health()
        print(f"Server is {health['status']}")
        print(f"Available tools: {', '.join(tool for tool, available in health['tools'].items() if available)}")
    except ConnectionError as e:
        print(f"Error: {e}")
        exit(1)
    
    # Scan project or file
    if args.project:
        print(f"Scanning project: {args.project}")
        scan_id = client.scan_project(args.project, args.language)
        print(f"Scan started with ID: {scan_id}")
        
        print("Waiting for scan to complete...")
        result = client.wait_for_scan_completion(scan_id)
        
        print(f"Scan completed with status: {result['status']}")
        if result['status'] == "completed":
            summary = result.get('summary', {})
            print(f"Language: {summary.get('language', 'unknown')}")
            print(f"Tools run: {', '.join(summary.get('tools_run', []))}")
            print(f"Issues found: {summary.get('issues_found', 0)}")
    
    elif args.file:
        if not args.language:
            print("Error: --language is required when scanning a file")
            exit(1)
        
        print(f"Scanning file: {args.file}")
        result = client.scan_file(args.file, args.language)
        
        print(f"Scan completed with status: {result['status']}")
        if result['status'] == "completed":
            summary = result.get('summary', {})
            print(f"Language: {summary.get('language', 'unknown')}")
            print(f"Tools run: {', '.join(summary.get('tools_run', []))}")
            print(f"Issues found: {summary.get('issues_found', 0)}")
    
    else:
        capabilities = client.get_capabilities()
        print("Server capabilities:")
        print(f"Supported languages: {', '.join(capabilities['languages'])}")
        print("Supported tools:")
        for lang, tools in capabilities['tools'].items():
            print(f"  {lang}: {', '.join(tools)}")
