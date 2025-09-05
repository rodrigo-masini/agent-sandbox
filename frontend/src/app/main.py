import os
import sys
import asyncio
import json
from typing import Dict, List, Optional
from nicegui import ui, app, run
from contextlib import asynccontextmanager

# Add parent directory to path to fix imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import Config
from core.auth import AuthManager
from clients.fabric_client import FabricClient, FabricConfig
from clients.agtsdbx_client import AgtsdbxClient
from tools.execution_tools import ExecutionTools
from tools.file_tools import FileTools
from tools.system_tools import SystemTools
from tools.docker_tools import DockerTools
from tools.network_tools import NetworkTools
from ui.components.chat import ChatComponent
from ui.components.file_browser import FileBrowserComponent
from ui.components.terminal import TerminalComponent
from ui.components.system_monitor import SystemMonitorComponent
from ui.layouts.main_layout import MainLayout

class AgtsdbxApp:
    def __init__(self):
        self.config = Config()
        self.auth_manager = AuthManager(self.config)
        self.fabric_client = None
        self.agtsdbx_client = None
        self.tools = {}
        self.messages = []
        self.components = {}
        
    async def initialize(self):
        """Initialize the application components."""
        # Initialize clients
        fabric_config = FabricConfig(
            api_key=self.config.get("FABRIC_API_KEY"),
            org_id=self.config.get("FABRIC_ORG_ID"),
            project_id=self.config.get("FABRIC_PROJECT_ID"),
            base_url=self.config.get("FABRIC_BASE_URL", "https://api.telaos.com/v1"),
            model=self.config.get("FABRIC_MODEL", "wizard"),
            timeout=self.config.get("FABRIC_TIMEOUT", 300),
        )
        
        self.fabric_client = FabricClient(fabric_config)
        self.agtsdbx_client = AgtsdbxClient(
            base_url=self.config.get("AGTSDBX_BASE_URL", "http://localhost:8000"),
            timeout=self.config.get("AGTSDBX_TIMEOUT", 300)
        )
        
        # Initialize tools
        self.tools = {
            "execution": ExecutionTools(self.agtsdbx_client),
            "file": FileTools(self.agtsdbx_client),
            "system": SystemTools(self.agtsdbx_client),
            "docker": DockerTools(self.agtsdbx_client),
            "network": NetworkTools(self.agtsdbx_client),
        }
        
        # Health checks
        await self._perform_health_checks()

    async def _perform_health_checks(self):
        """Perform health checks on all services."""
        try:
            fabric_health = await self.fabric_client.health_check()
            async with self.agtsdbx_client as client:
                agtsdbx_health = await client.health_check()
                
            if fabric_health["status"] != "healthy":
                ui.notify(f"Fabric service unhealthy: {fabric_health.get('error', 'Unknown error')}", type="negative")
                
            if agtsdbx_health["status"] != "healthy":
                ui.notify(f"Agtsdbx service unhealthy: {agtsdbx_health.get('error', 'Unknown error')}", type="negative")
                
        except Exception as e:
            ui.notify(f"Health check failed: {str(e)}", type="negative")

    def get_all_tool_definitions(self) -> List[Dict]:
        """Get all tool definitions from registered tools."""
        all_tools = []
        for tool in self.tools.values():
            all_tools.extend(tool.get_tool_definitions())
        return all_tools

    async def handle_tool_calls(self, tool_calls: List[Dict]) -> List[Dict]:
        """Handle tool calls from the AI model."""
        tool_responses = []
        
        for tool_call in tool_calls:
            function_name = tool_call["function"]["name"]
            arguments = json.loads(tool_call["function"]["arguments"])
            
            try:
                # Find the appropriate tool
                tool_result = await self._execute_tool(function_name, arguments)
                
                tool_responses.append({
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "name": function_name,
                    "content": tool_result
                })
                
            except Exception as e:
                error_message = f"Tool execution failed: {str(e)}"
                tool_responses.append({
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "name": function_name,
                    "content": error_message
                })
                
        return tool_responses

    async def _execute_tool(self, function_name: str, arguments: Dict) -> str:
        """Execute a specific tool function."""
        for tool in self.tools.values():
            if hasattr(tool, function_name):
                method = getattr(tool, function_name)
                return await method(**arguments)
                
        raise ValueError(f"Tool function '{function_name}' not found")

    async def send_message(self, user_message: str) -> str:
        """Send a message and get AI response with tool execution."""
        self.messages.append({"role": "user", "content": user_message})
        
        try:
            # Get initial response from AI
            response = await self.fabric_client.chat_completion(
                messages=self.messages,
                tools=self.get_all_tool_definitions(),
                tool_choice="auto"
            )
            
            choice = response["choices"][0]
            message = choice["message"]
            
            # Handle tool calls if present
            if message.get("tool_calls"):
                tool_responses = await self.handle_tool_calls(message["tool_calls"])
                self.messages.extend(tool_responses)
                
                # Get final response after tool execution
                final_response = await self.fabric_client.chat_completion(
                    messages=self.messages
                )
                
                assistant_message = final_response["choices"][0]["message"]["content"]
            else:
                assistant_message = message["content"]
            
            self.messages.append({"role": "assistant", "content": assistant_message})
            return assistant_message
            
        except Exception as e:
            error_message = f"Error processing message: {str(e)}"
            self.messages.append({"role": "assistant", "content": error_message})
            return error_message

    async def stream_message(self, user_message: str):
        """Send a message and stream the AI response."""
        self.messages.append({"role": "user", "content": user_message})
        
        try:
            # Handle tool calls first (non-streaming)
            response = await self.fabric_client.chat_completion(
                messages=self.messages,
                tools=self.get_all_tool_definitions(),
                tool_choice="auto"
            )
            
            choice = response["choices"][0]
            message = choice["message"]
            
            if message.get("tool_calls"):
                tool_responses = await self.handle_tool_calls(message["tool_calls"])
                self.messages.extend(tool_responses)
            
            # Stream final response
            async for chunk in self.fabric_client.chat_completion(
                messages=self.messages,
                stream=True
            ):
                if chunk.get("content"):
                    yield chunk["content"]
                    
        except Exception as e:
            yield f"Error: {str(e)}"

# Global app instance
agtsdbx_app = AgtsdbxApp()

@ui.page('/')
async def main_page():
    """Main application page."""
    if not agtsdbx_app.fabric_client:
        await agtsdbx_app.initialize()
    
    # Create main layout
    layout = MainLayout(agtsdbx_app)
    await layout.render()

@ui.page('/admin')
async def admin_page():
    """Admin interface page."""
    if not agtsdbx_app.auth_manager.is_admin():
        ui.navigate.to('/')
        return
        
    # Admin interface implementation
    ui.label('Admin Interface').classes('text-2xl font-bold mb-4')
    # Add admin functionality here

@ui.page('/api/health')
async def health_endpoint():
    """Health check endpoint."""
    try:
        if agtsdbx_app.fabric_client and agtsdbx_app.agtsdbx_client:
            fabric_health = await agtsdbx_app.fabric_client.health_check()
            async with agtsdbx_app.agtsdbx_client as client:
                agtsdbx_health = await client.health_check()
                
            return {
                "status": "healthy",
                "services": {
                    "fabric": fabric_health,
                    "agtsdbx": agtsdbx_health
                }
            }
        else:
            return {"status": "initializing"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}

def run_app():
    """Run the application."""
    # This configuration is the correct, documented method for the updated NiceGUI version.
    socket_io_config = {
        "ping_interval": agtsdbx_app.config.get("RECONNECT_TIMEOUT", 5),
        "ping_timeout": agtsdbx_app.config.get("RECONNECT_TIMEOUT", 5) * 2
    }

    ui.run(
        title="Agent Sandbox - AI-Powered System Interface",
        port=agtsdbx_app.config.get("PORT"),
        host=agtsdbx_app.config.get("HOST"),
        reload=agtsdbx_app.config.get("DEBUG"),
        socket_io_server_kwargs=socket_io_config,
        show=False,
        favicon="🔧"
    )

if __name__ == "__main__":
    run_app()