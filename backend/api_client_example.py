"""
API Client Utilities for Testing the Backend

Usage:
    python api_client.py
"""

import requests
import base64
import json
from typing import Optional, Dict, Any, List

BASE_URL = "http://localhost:8000/api"


class AgentAPIClient:
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
    
    # Session Management
    def create_session(self, title: str = "New Chat", system_prompt: Optional[str] = None) -> Dict[str, Any]:
        """Create a new session"""
        response = requests.post(
            f"{self.base_url}/sessions",
            json={
                "title": title,
                "system_prompt": system_prompt
            }
        )
        return response.json()
    
    def list_sessions(self) -> List[Dict[str, Any]]:
        """List all sessions"""
        response = requests.get(f"{self.base_url}/sessions")
        return response.json()
    
    def get_session(self, session_id: str) -> Dict[str, Any]:
        """Get session details"""
        response = requests.get(f"{self.base_url}/sessions/{session_id}")
        return response.json()
    
    def delete_session(self, session_id: str) -> Dict[str, Any]:
        """Delete a session"""
        response = requests.delete(f"{self.base_url}/sessions/{session_id}")
        return response.json()
    
    # Chat
    def send_message(
        self,
        session_id: str,
        message: str,
        images: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Send a message to the agent"""
        payload = {
            "session_id": session_id,
            "message": message
        }
        if images:
            payload["images"] = images
        
        response = requests.post(
            f"{self.base_url}/chat",
            json=payload
        )
        return response.json()
    
    # Tools
    def get_tools(self) -> Dict[str, Any]:
        """Get available tools"""
        response = requests.get(f"{self.base_url}/tools")
        return response.json()
    
    def execute_tool(self, tool_name: str, **parameters) -> Dict[str, Any]:
        """Execute a tool directly"""
        response = requests.post(
            f"{self.base_url}/tools/execute",
            json={
                "tool_name": tool_name,
                "parameters": parameters
            }
        )
        return response.json()
    
    # System
    def update_system_prompt(self, session_id: str, system_prompt: str) -> Dict[str, Any]:
        """Update session system prompt"""
        response = requests.post(
            f"{self.base_url}/sessions/{session_id}/system-prompt",
            json={"system_prompt": system_prompt}
        )
        return response.json()
    
    def upload_image(self, image_path: str) -> Dict[str, Any]:
        """Upload an image"""
        with open(image_path, 'rb') as f:
            files = {'file': f}
            response = requests.post(
                f"{self.base_url}/upload-image",
                files=files
            )
        return response.json()
    
    def health_check(self) -> Dict[str, Any]:
        """Check if backend is running"""
        response = requests.get(f"{self.base_url}/health")
        return response.json()


def load_image_as_base64(image_path: str) -> str:
    """Load image and convert to base64"""
    with open(image_path, 'rb') as f:
        return base64.standard_b64encode(f.read()).decode('utf-8')


if __name__ == "__main__":
    # Example usage
    client = AgentAPIClient()
    
    # Test connection
    print("Checking health...")
    print(client.health_check())
    
    # List available tools
    print("\nAvailable tools:")
    tools = client.get_tools()
    for tool in tools.get('tools', []):
        print(f"  - {tool['function']['name']}: {tool['function']['description']}")
    
    # Create session
    print("\nCreating session...")
    session = client.create_session("Python Code Review")
    print(f"Session created: {session['id']}")
    
    # Send message
    print("\nSending message...")
    response = client.send_message(
        session['id'],
        "List the files in the current directory"
    )
    print(f"Response: {response['message']['content'][:100]}...")
    
    # Update system prompt
    print("\nUpdating system prompt...")
    client.update_system_prompt(
        session['id'],
        "You are a helpful Python expert who explains code clearly."
    )
    
    print("\nDone!")
