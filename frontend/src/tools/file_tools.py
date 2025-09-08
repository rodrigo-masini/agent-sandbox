# ==============================================
# FILE TOOLS IMPLEMENTATION
# ==============================================

from typing import Dict, List, Optional
import json
from .base_tool import BaseTool

class FileTools(BaseTool):
    """File operation tools for Agtsdbx."""
    
    def get_tool_definitions(self) -> List[Dict]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "write_file",
                    "description": "Write content to a file, creating it if it doesn't exist.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "file_path": {
                                "type": "string",
                                "description": "Path to the file to write"
                            },
                            "content": {
                                "type": "string",
                                "description": "Content to write to the file"
                            },
                            "append": {
                                "type": "boolean",
                                "description": "Whether to append to existing file",
                                "default": False
                            }
                        },
                        "required": ["file_path", "content"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "read_file",
                    "description": "Read the contents of a file.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "file_path": {
                                "type": "string",
                                "description": "Path to the file to read"
                            },
                            "encoding": {
                                "type": "string",
                                "description": "File encoding",
                                "default": "utf-8"
                            }
                        },
                        "required": ["file_path"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "list_files",
                    "description": "List files and directories in a given path.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "Directory path to list",
                                "default": "."
                            },
                            "recursive": {
                                "type": "boolean",
                                "description": "Whether to list recursively",
                                "default": False
                            },
                            "pattern": {
                                "type": "string",
                                "description": "Filter pattern (glob style)",
                                "default": "*"
                            }
                        },
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "delete_file",
                    "description": "Delete a file or empty directory.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "file_path": {
                                "type": "string",
                                "description": "Path to the file or directory to delete"
                            }
                        },
                        "required": ["file_path"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "create_directory",
                    "description": "Create a new directory.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "Path of the directory to create"
                            },
                            "parents": {
                                "type": "boolean",
                                "description": "Create parent directories if needed",
                                "default": True
                            }
                        },
                        "required": ["path"]
                    }
                }
            }
        ]
    
    async def write_file(self, **kwargs) -> str:
        """Write content to a file."""
        try:
            file_path = kwargs.get("file_path")
            content = kwargs.get("content")
            append = kwargs.get("append", False)
            
            options = {"append": append}
            
            async with self.agtsdbx_client as client:
                result = await client.write_file(file_path, content, options)
                
                if result.get("success"):
                    return f"Successfully wrote to file: {file_path}"
                else:
                    return f"Failed to write file: {result.get('error', 'Unknown error')}"
                
        except Exception as e:
            return f"Error writing file: {str(e)}"
    
    async def read_file(self, **kwargs) -> str:
        """Read file contents."""
        try:
            file_path = kwargs.get("file_path")
            encoding = kwargs.get("encoding", "utf-8")
            
            options = {"encoding": encoding}
            
            async with self.agtsdbx_client as client:
                result = await client.read_file(file_path, options)
                
                if result.get("success"):
                    return f"File contents of {file_path}:\n\n{result.get('content', '')}"
                else:
                    return f"Failed to read file: {result.get('error', 'Unknown error')}"
                
        except Exception as e:
            return f"Error reading file: {str(e)}"
    
    async def list_files(self, **kwargs) -> str:
        """List files in directory."""
        try:
            path = kwargs.get("path", ".")
            recursive = kwargs.get("recursive", False)
            pattern = kwargs.get("pattern", "*")
            
            options = {
                "recursive": recursive,
                "pattern": pattern
            }
            
            async with self.agtsdbx_client as client:
                result = await client.list_files(path, options)
                
                if result.get("success"):
                    files = result.get("files", [])
                    if files:
                        file_list = "\n".join([f"- {f}" for f in files])
                        return f"Files in {path}:\n{file_list}"
                    else:
                        return f"No files found in {path}"
                else:
                    return f"Failed to list files: {result.get('error', 'Unknown error')}"
                
        except Exception as e:
            return f"Error listing files: {str(e)}"
    
    async def delete_file(self, **kwargs) -> str:
        """Delete a file."""
        try:
            file_path = kwargs.get("file_path")
            
            async with self.agtsdbx_client as client:
                result = await client.delete_file(file_path)
                
                if result.get("success"):
                    return f"Successfully deleted: {file_path}"
                else:
                    return f"Failed to delete file: {result.get('error', 'Unknown error')}"
                
        except Exception as e:
            return f"Error deleting file: {str(e)}"
    
    async def create_directory(self, **kwargs) -> str:
        """Create a directory."""
        try:
            path = kwargs.get("path")
            parents = kwargs.get("parents", True)
            
            command = f"mkdir {'-p ' if parents else ''}{path}"
            
            async with self.agtsdbx_client as client:
                result = await client.execute_command(command)
                
                if result.get("exit_code", 0) == 0:
                    return f"Successfully created directory: {path}"
                else:
                    return f"Failed to create directory: {result.get('stderr', 'Unknown error')}"
                
        except Exception as e:
            return f"Error creating directory: {str(e)}"
