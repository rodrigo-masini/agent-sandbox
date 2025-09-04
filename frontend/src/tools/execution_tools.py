from typing import Dict, List, Optional, Any
import json
import asyncio
from .base_tool import BaseTool

class ExecutionTools(BaseTool):
    """Enhanced execution tools with advanced capabilities."""

    def get_tool_definitions(self) -> List[Dict]:
        """Return tool definitions for the OpenAI API."""
        return [
            {
                "type": "function",
                "function": {
                    "name": "execute_shell_command",
                    "description": "Execute a shell command with advanced options and safety checks.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "command": {
                                "type": "string",
                                "description": "The shell command to execute"
                            },
                            "timeout": {
                                "type": "integer",
                                "description": "Command timeout in seconds (default: 300)",
                                "default": 300
                            },
                            "working_directory": {
                                "type": "string",
                                "description": "Working directory for command execution",
                                "default": "."
                            },
                            "environment": {
                                "type": "object",
                                "description": "Environment variables to set",
                                "default": {}
                            },
                            "capture_output": {
                                "type": "boolean",
                                "description": "Whether to capture stdout/stderr",
                                "default": True
                            }
                        },
                        "required": ["command"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "execute_script",
                    "description": "Execute a script file with specified interpreter.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "script_path": {
                                "type": "string",
                                "description": "Path to the script file"
                            },
                            "interpreter": {
                                "type": "string",
                                "description": "Script interpreter (python, bash, node, etc.)",
                                "enum": ["python", "python3", "bash", "sh", "node", "ruby", "perl"]
                            },
                            "arguments": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Command line arguments for the script"
                            },
                            "timeout": {
                                "type": "integer",
                                "description": "Script timeout in seconds",
                                "default": 300
                            }
                        },
                        "required": ["script_path", "interpreter"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "execute_parallel_commands",
                    "description": "Execute multiple commands in parallel.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "commands": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of commands to execute in parallel"
                            },
                            "max_concurrent": {
                                "type": "integer",
                                "description": "Maximum number of concurrent executions",
                                "default": 5
                            },
                            "timeout": {
                                "type": "integer",
                                "description": "Timeout for each command",
                                "default": 300
                            }
                        },
                        "required": ["commands"]
                    }
                }
            }
        ]

    async def execute_shell_command(self, **kwargs) -> str:
        """Execute a shell command with enhanced options."""
        command = kwargs.get("command")
        options = {
            "timeout": kwargs.get("timeout", 300),
            "working_directory": kwargs.get("working_directory", "."),
            "environment": kwargs.get("environment", {}),
            "capture_output": kwargs.get("capture_output", True)
        }

        try:
            async with self.pandora_client as client:
                result = await client.execute_command(command, options)
                
                return self._format_execution_result(result)
                
        except Exception as e:
            return f"Execution failed: {str(e)}"

    async def execute_script(self, **kwargs) -> str:
        """Execute a script file with specified interpreter."""
        script_path = kwargs.get("script_path")
        interpreter = kwargs.get("interpreter")
        arguments = kwargs.get("arguments", [])
        timeout = kwargs.get("timeout", 300)

        # Build command
        command_parts = [interpreter, script_path] + arguments
        command = " ".join(command_parts)

        options = {"timeout": timeout}

        try:
            async with self.pandora_client as client:
                result = await client.execute_command(command, options)
                return self._format_execution_result(result)
                
        except Exception as e:
            return f"Script execution failed: {str(e)}"

    async def execute_parallel_commands(self, **kwargs) -> str:
        """Execute multiple commands in parallel."""
        commands = kwargs.get("commands", [])
        max_concurrent = kwargs.get("max_concurrent", 5)
        timeout = kwargs.get("timeout", 300)

        if not commands:
            return "No commands provided"

        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def execute_single(cmd):
            async with semaphore:
                try:
                    async with self.pandora_client as client:
                        return await client.execute_command(cmd, {"timeout": timeout})
                except Exception as e:
                    return {"error": str(e), "command": cmd}

        try:
            results = await asyncio.gather(*[execute_single(cmd) for cmd in commands])
            
            formatted_results = []
            for i, result in enumerate(results):
                formatted_results.append(f"Command {i+1}: {commands[i]}")
                formatted_results.append(self._format_execution_result(result))
                formatted_results.append("-" * 50)
            
            return "\n".join(formatted_results)
            
        except Exception as e:
            return f"Parallel execution failed: {str(e)}"

    def _format_execution_result(self, result: Dict) -> str:
        """Format execution result for display."""
        if "error" in result:
            return f"Error: {result['error']}"
            
        parts = []
        
        if result.get("stdout"):
            parts.append(f"STDOUT:\n{result['stdout']}")
            
        if result.get("stderr"):
            parts.append(f"STDERR:\n{result['stderr']}")
            
        exit_code = result.get("exit_code", result.get("return_value", 0))
        parts.append(f"EXIT CODE: {exit_code}")
        
        if "metadata" in result:
            duration = result["metadata"].get("duration", 0)
            parts.append(f"DURATION: {duration:.2f}s")
        
        return "\n\n".join(parts)
