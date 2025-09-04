# ==============================================
# DOCKER TOOLS IMPLEMENTATION
# ==============================================

from typing import Dict, List
import json
from .base_tool import BaseTool

class DockerTools(BaseTool):
    """Docker container management tools."""
    
    def get_tool_definitions(self) -> List[Dict]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "docker_run",
                    "description": "Run a Docker container with specified image and options.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "image": {
                                "type": "string",
                                "description": "Docker image to run (e.g., 'ubuntu:22.04', 'python:3.11-slim')"
                            },
                            "command": {
                                "type": "string",
                                "description": "Command to execute in container"
                            },
                            "name": {
                                "type": "string",
                                "description": "Container name"
                            },
                            "detached": {
                                "type": "boolean",
                                "description": "Run container in background",
                                "default": False
                            },
                            "environment": {
                                "type": "object",
                                "description": "Environment variables",
                                "default": {}
                            },
                            "ports": {
                                "type": "object",
                                "description": "Port mappings (host:container)",
                                "default": {}
                            },
                            "volumes": {
                                "type": "object",
                                "description": "Volume mappings",
                                "default": {}
                            }
                        },
                        "required": ["image"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "docker_list",
                    "description": "List Docker containers.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "all": {
                                "type": "boolean",
                                "description": "Show all containers (including stopped)",
                                "default": False
                            },
                            "format": {
                                "type": "string",
                                "description": "Output format",
                                "enum": ["table", "json", "names"],
                                "default": "table"
                            }
                        },
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "docker_stop",
                    "description": "Stop a running Docker container.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "container": {
                                "type": "string",
                                "description": "Container name or ID"
                            },
                            "timeout": {
                                "type": "integer",
                                "description": "Seconds to wait before killing",
                                "default": 10
                            }
                        },
                        "required": ["container"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "docker_remove",
                    "description": "Remove a Docker container.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "container": {
                                "type": "string",
                                "description": "Container name or ID"
                            },
                            "force": {
                                "type": "boolean",
                                "description": "Force removal even if running",
                                "default": False
                            }
                        },
                        "required": ["container"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "docker_logs",
                    "description": "Get logs from a Docker container.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "container": {
                                "type": "string",
                                "description": "Container name or ID"
                            },
                            "lines": {
                                "type": "integer",
                                "description": "Number of lines to show",
                                "default": 50
                            },
                            "follow": {
                                "type": "boolean",
                                "description": "Follow log output",
                                "default": False
                            }
                        },
                        "required": ["container"]
                    }
                }
            }
        ]
    
    async def docker_run(self, **kwargs) -> str:
        """Run a Docker container."""
        try:
            image = kwargs.get("image")
            command = kwargs.get("command", "")
            name = kwargs.get("name", "")
            detached = kwargs.get("detached", False)
            environment = kwargs.get("environment", {})
            ports = kwargs.get("ports", {})
            volumes = kwargs.get("volumes", {})
            
            options = {
                "command": command,
                "name": name,
                "detached": detached,
                "environment": environment,
                "ports": ports,
                "volumes": volumes
            }
            
            async with self.agtsdbx_client as client:
                result = await client.docker_run(image, command, options)
                
            if result.get("success"):
                container_id = result.get("container_id", "unknown")
                return f"Successfully started container: {container_id}\nImage: {image}"
            else:
                return f"Failed to run container: {result.get('error', 'Unknown error')}"
                
        except Exception as e:
            return f"Error running Docker container: {str(e)}"
    
    async def docker_list(self, **kwargs) -> str:
        """List Docker containers."""
        try:
            show_all = kwargs.get("all", False)
            format_type = kwargs.get("format", "table")
            
            async with self.agtsdbx_client as client:
                result = await client.docker_list()
                
            if result.get("success"):
                containers = result.get("containers", [])
                if not containers:
                    return "No containers found"
                    
                if format_type == "json":
                    return json.dumps(containers, indent=2)
                elif format_type == "names":
                    names = [c.get("name", c.get("id", "unknown")) for c in containers]
                    return "Container names:\n" + "\n".join(f"- {name}" for name in names)
                else:
                    # Table format
                    lines = ["CONTAINER ID    IMAGE           STATUS          NAMES"]
                    for c in containers:
                        line = f"{c.get('id', '')[:12]}    {c.get('image', '')[:15]}    {c.get('status', '')[:15]}    {c.get('name', '')}"
                        lines.append(line)
                    return "\n".join(lines)
            else:
                return f"Failed to list containers: {result.get('error', 'Unknown error')}"
                
        except Exception as e:
            return f"Error listing containers: {str(e)}"
    
    async def docker_stop(self, **kwargs) -> str:
        """Stop a Docker container."""
        try:
            container = kwargs.get("container")
            timeout = kwargs.get("timeout", 10)
            
            command = f"docker stop -t {timeout} {container}"
            
            async with self.agtsdbx_client as client:
                result = await client.execute_command(command)
                
            if result.get("exit_code", 0) == 0:
                return f"Successfully stopped container: {container}"
            else:
                return f"Failed to stop container: {result.get('stderr', 'Unknown error')}"
                
        except Exception as e:
            return f"Error stopping container: {str(e)}"
    
    async def docker_remove(self, **kwargs) -> str:
        """Remove a Docker container."""
        try:
            container = kwargs.get("container")
            force = kwargs.get("force", False)
            
            command = f"docker rm {'-f ' if force else ''}{container}"
            
            async with self.agtsdbx_client as client:
                result = await client.execute_command(command)
                
            if result.get("exit_code", 0) == 0:
                return f"Successfully removed container: {container}"
            else:
                return f"Failed to remove container: {result.get('stderr', 'Unknown error')}"
                
        except Exception as e:
            return f"Error removing container: {str(e)}"
    
    async def docker_logs(self, **kwargs) -> str:
        """Get Docker container logs."""
        try:
            container = kwargs.get("container")
            lines = kwargs.get("lines", 50)
            follow = kwargs.get("follow", False)
            
            command = f"docker logs {'--follow ' if follow else ''}-n {lines} {container}"
            
            async with self.agtsdbx_client as client:
                result = await client.execute_command(command, {"timeout": 30 if not follow else 300})
                
            if result.get("exit_code", 0) == 0:
                logs = result.get("stdout", "No logs available")
                return f"Logs for container {container}:\n\n{logs}"
            else:
                return f"Failed to get logs: {result.get('stderr', 'Unknown error')}"
                
        except Exception as e:
            return f"Error getting logs: {str(e)}"
