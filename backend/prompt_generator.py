"""System Prompt Generator for Agent"""

from datetime import datetime
from zoneinfo import ZoneInfo
from typing import List, Dict, Any
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from executor import tool_executor


# Initialize Jinja2 Environment
TEMPLATE_DIR = Path(__file__).parent / "templates"
jinja_env = Environment(
    loader=FileSystemLoader(str(TEMPLATE_DIR)),
    trim_blocks=True,
    lstrip_blocks=True,
    autoescape=False
)


def get_current_datetime_info() -> Dict[str, str]:
    """
    Get current date, time and timezone information
    
    Returns:
        Dictionary containing formatted date/time/timezone
    """
    # Get current UTC time
    utc_now = datetime.now(ZoneInfo("UTC"))
    
    # Also get local timezone (system timezone)
    local_tz = datetime.now().astimezone().tzinfo
    local_now = datetime.now(local_tz)
    
    return {
        "current_utc": utc_now.strftime("%Y-%m-%d %H:%M:%S UTC"),
        "current_local": local_now.strftime("%Y-%m-%d %H:%M:%S %Z"),
        "timezone": str(local_tz),
    }


def get_available_tools_description() -> str:
    """
    Get descriptions of all available tools for the prompt
    
    Returns:
        Formatted string describing all available tools
    """
    tools = tool_executor.get_all_tools()
    
    if not tools:
        return "No tools are currently available."
    
    tools_description = "## Available Tools\n\n"
    
    for tool in tools:
        # Extract tool info from OpenAI function format
        func = tool.get('function', {})
        tool_name = func.get('name', 'Unknown')
        tool_desc = func.get('description', 'No description available')
        params = func.get('parameters', {})
        
        tools_description += f"### {tool_name}\n"
        tools_description += f"Description: {tool_desc}\n"
        
        if 'properties' in params:
            tools_description += "Parameters:\n"
            for param_name, param_info in params['properties'].items():
                param_type = param_info.get('type', 'unknown')
                param_desc = param_info.get('description', 'No description')
                required = param_name in params.get('required', [])
                req_mark = " (required)" if required else " (optional)"
                tools_description += f"  - `{param_name}` ({param_type}){req_mark}: {param_desc}\n"
        
        tools_description += "\n"
    
    return tools_description


def generate_system_prompt(custom_instructions: str = "") -> str:
    """
    Generate a system prompt for the Agent using Jinja2 template
    
    Args:
        custom_instructions: Optional custom instructions to append to the prompt
    
    Returns:
        Complete system prompt string
    """
    datetime_info = get_current_datetime_info()
    tools_desc = get_available_tools_description()
    
    # Load and render template
    template = jinja_env.get_template("system_prompt.j2")
    
    prompt = template.render(
        current_utc=datetime_info['current_utc'],
        current_local=datetime_info['current_local'],
        timezone=datetime_info['timezone'],
        tools_description=tools_desc,
        custom_instructions=custom_instructions
    )
    
    return prompt
