import os
import asyncio
import json
from typing import Dict, List, Optional
from nicegui import ui, app, run
from contextlib import asynccontextmanager

from ..core.config import Config
from ..core.auth import AuthManager
from ..clients.tela_client import TelaClient, TelaConfig
from ..clients.pandora_client import PandoraClient
from ..tools.execution_tools import ExecutionTools
from ..tools.file_tools import FileTools
from ..tools.system_tools import SystemTools
from ..tools.docker_tools import DockerTools
from ..tools.network_tools import NetworkTools
from ..ui.components.chat import ChatComponent
from ..ui.components.file_browser import FileBrowserComponent
from ..ui.components.terminal import TerminalComponent
from ..ui.components.system_monitor import SystemMonitorComponent
from ..ui.layouts.main_layout import MainLayout

class PandoraApp:
    def __init__(self):
        self.config = Config()
        self.auth_manager = AuthManager(self.config)
        self.tela_client = None
        self.pandora_client = None
        self.tools = {}
        self.messages = []
        self.components = {}
        
    async def initialize(self):
        """Initialize the application components."""
        # Initialize clients
        tela_config = TelaConfig(
            api_key=self.config.get("TELAOS_API_KEY"),
            org_id=self.config.get("TELAOS_ORG_ID"),
            project_id=self.config.get("TELAOS_PROJECT_ID"),
            base_url=self.config.get("TELAOS_BASE_URL", "https://api.telaos.com/v1"),
            model=self.config.get("TELAOS_MODEL", "wizard"),
            timeout=self.config.get("TELAOS_TIMEOUT", 300),
        )
        
        self.tela_client = TelaClient(tela_config)
        self.pandora_client = PandoraClient(
            base_url=self.config.get("PANDORA_BASE_URL", "http://localhost:8000"),
            timeout=self.config.get("PANDORA_TIMEOUT", 300)
        )
        
        # Initialize tools
        self.tools = {
            "execution": ExecutionTools(self.pandora_client),
            "file": FileTools(self.pandora_client),
            "system": SystemTools(self.pandora_client),
            "docker": DockerTools(self.pandora_client),
            "network": NetworkTools(self.pandora_client),
        }
        
        # Health checks
        await self._perform_health_checks()

    async def _perform_health_checks(self):
        """Perform health checks on all services."""
        try:
            tela_health = await self.tela_client.health_check()
            async with self.pandora_client as client:
                pandora_health = await client.health_check()
                
            if tela_health["status"] != "healthy":
                ui.notify(f"Tela/Fabric service unhealthy: {tela_health.get('error', 'Unknown error')}", type="negative")
                
            if pandora_health["status"] != "healthy":
                ui.notify(f"Pandora service unhealthy: {pandora_health.get('error', 'Unknown error')}", type="negative")
                
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
            response = await self.tela_client.chat_completion(
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
                final_response = await self.tela_client.chat_completion(
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
            response = await self.tela_client.chat_completion(
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
            async for chunk in self.tela_client.chat_completion(
                messages=self.messages,
                stream=True
            ):
                if chunk.get("content"):
                    yield chunk["content"]
                    
        except Exception as e:
            yield f"Error: {str(e)}"

# Global app instance
pandora_app = PandoraApp()

@ui.page('/')
async def main_page():
    """Main application page."""
    if not pandora_app.tela_client:
        await pandora_app.initialize()
    
    # Create main layout
    layout = MainLayout(pandora_app)
    await layout.render()

@ui.page('/admin')
async def admin_page():
    """Admin interface page."""
    if not pandora_app.auth_manager.is_admin():
        ui.navigate.to('/')
        return
        
    # Admin interface implementation
    ui.label('Admin Interface').classes('text-2xl font-bold mb-4')
    # Add admin functionality here

@ui.page('/api/health')
async def health_endpoint():
    """Health check endpoint."""
    try:
        if pandora_app.tela_client and pandora_app.pandora_client:
            tela_health = await pandora_app.tela_client.health_check()
            async with pandora_app.pandora_client as client:
                pandora_health = await client.health_check()
                
            return {
                "status": "healthy",
                "services": {
                    "tela": tela_health,
                    "pandora": pandora_health
                }
            }
        else:
            return {"status": "initializing"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}

def run_app():
    """Run the application."""
    ui.run(
        title="Pandora Enterprise - AI-Powered System Interface",
        port=int(os.getenv("PORT", 8080)),
        host=os.getenv("HOST", "0.0.0.0"),
        reload=os.getenv("DEBUG", "false").lower() == "true",
        show=False,
        favicon="🔧"
    )

if __name__ == "__main__":
    run_app()
