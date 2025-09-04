# ==============================================
# SYSTEM TOOLS IMPLEMENTATION
# ==============================================

from typing import Dict, List
from .base_tool import BaseTool

class SystemTools(BaseTool):
    """System information and management tools."""
    
    def get_tool_definitions(self) -> List[Dict]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "get_system_info",
                    "description": "Get comprehensive system information including OS, CPU, memory, and disk.",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_process_list",
                    "description": "Get list of running processes with details.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "sort_by": {
                                "type": "string",
                                "enum": ["cpu", "memory", "pid", "name"],
                                "description": "Sort processes by",
                                "default": "cpu"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Number of processes to return",
                                "default": 20
                            }
                        },
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "check_disk_usage",
                    "description": "Check disk usage for all mounted filesystems.",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "check_network_connectivity",
                    "description": "Test network connectivity to common services.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "hosts": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of hosts to ping",
                                "default": ["8.8.8.8", "1.1.1.1", "google.com"]
                            }
                        },
                        "required": []
                    }
                }
            }
        ]
    
    async def get_system_info(self, **kwargs) -> str:
        """Get system information."""
        try:
            async with self.pandora_client as client:
                result = await client.get_system_info()
                
            if result.get("success"):
                info = result.get("data", {})
                return self._format_system_info(info)
            else:
                return f"Failed to get system info: {result.get('error', 'Unknown error')}"
                
        except Exception as e:
            return f"Error getting system info: {str(e)}"
    
    async def get_process_list(self, **kwargs) -> str:
        """Get list of running processes."""
        try:
            sort_by = kwargs.get("sort_by", "cpu")
            limit = kwargs.get("limit", 20)
            
            sort_flag = {
                "cpu": "--sort=-%cpu",
                "memory": "--sort=-%mem",
                "pid": "--sort=pid",
                "name": "--sort=comm"
            }.get(sort_by, "--sort=-%cpu")
            
            command = f"ps aux {sort_flag} | head -n {limit + 1}"
            
            async with self.pandora_client as client:
                result = await client.execute_command(command)
                
            if result.get("exit_code", 0) == 0:
                return f"Top {limit} processes by {sort_by}:\n\n{result.get('stdout', 'No output')}"
            else:
                return f"Failed to get process list: {result.get('stderr', 'Unknown error')}"
                
        except Exception as e:
            return f"Error getting process list: {str(e)}"
    
    async def check_disk_usage(self, **kwargs) -> str:
        """Check disk usage."""
        try:
            command = "df -h"
            
            async with self.pandora_client as client:
                result = await client.execute_command(command)
                
            if result.get("exit_code", 0) == 0:
                return f"Disk Usage:\n\n{result.get('stdout', 'No output')}"
            else:
                return f"Failed to check disk usage: {result.get('stderr', 'Unknown error')}"
                
        except Exception as e:
            return f"Error checking disk usage: {str(e)}"
    
    async def check_network_connectivity(self, **kwargs) -> str:
        """Test network connectivity."""
        try:
            hosts = kwargs.get("hosts", ["8.8.8.8", "1.1.1.1", "google.com"])
            results = []
            
            async with self.pandora_client as client:
                for host in hosts:
                    command = f"ping -c 1 -W 2 {host}"
                    result = await client.execute_command(command)
                    
                    if result.get("exit_code", 0) == 0:
                        results.append(f"✓ {host}: Reachable")
                    else:
                        results.append(f"✗ {host}: Unreachable")
            
            return "Network Connectivity Test:\n" + "\n".join(results)
            
        except Exception as e:
            return f"Error checking network: {str(e)}"
    
    def _format_system_info(self, info: Dict) -> str:
        """Format system information for display."""
        lines = ["System Information:"]
        lines.append("-" * 40)
        
        for key, value in info.items():
            if isinstance(value, dict):
                lines.append(f"\n{key.upper()}:")
                for sub_key, sub_value in value.items():
                    lines.append(f"  {sub_key}: {sub_value}")
            else:
                lines.append(f"{key}: {value}")
        
        return "\n".join(lines)
