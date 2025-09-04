# ==============================================
# BASE TOOL IMPLEMENTATION
# ==============================================

from typing import Dict, List, Any
from abc import ABC, abstractmethod

class BaseTool(ABC):
    """Base class for all tool implementations."""
    
    def __init__(self, agtsdbx_client):
        self.agtsdbx_client = agtsdbx_client
        
    @abstractmethod
    def get_tool_definitions(self) -> List[Dict]:
        """Return OpenAI-style tool definitions."""
        pass
        
    async def execute(self, function_name: str, **kwargs) -> str:
        """Execute a tool function by name."""
        if hasattr(self, function_name):
            method = getattr(self, function_name)
            return await method(**kwargs)
        raise ValueError(f"Function '{function_name}' not found in {self.__class__.__name__}")
