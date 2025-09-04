from nicegui import ui
from typing import Callable, Optional
import asyncio
import time

class ChatComponent:
    def __init__(self, app_instance, container_classes: str = "w-full max-w-4xl mx-auto"):
        self.app = app_instance
        self.container_classes = container_classes
        self.chat_history = None
        self.input_field = None
        self.send_button = None
        self.is_processing = False
        
    async def render(self):
        """Render the chat component."""
        with ui.column().classes(self.container_classes):
            # Header
            with ui.row().classes('w-full justify-between items-center mb-4'):
                ui.label('Pandora AI Assistant').classes('text-2xl font-bold')
                
                # Status indicators
                with ui.row().classes('gap-2'):
                    self.tela_status = ui.badge('Tela', color='green').classes('text-xs')
                    self.pandora_status = ui.badge('Pandora', color='green').classes('text-xs')
                    
            # Chat history container
            with ui.scroll_area().classes('w-full h-96 border rounded-lg p-4'):
                self.chat_history = ui.column().classes('w-full gap-2')
                
            # Input area
            with ui.row().classes('w-full gap-2 mt-4'):
                self.input_field = ui.input(
                    placeholder='Ask me anything... I can execute commands, manage files, and more!',
                    validation={'min_length': 1}
                ).classes('flex-grow')
                
                self.send_button = ui.button(
                    'Send',
                    on_click=self._handle_send,
                    icon='send'
                ).classes('px-6')
                
            # Keyboard shortcut
            self.input_field.on('keydown.enter', self._handle_send)
            
            # Quick actions
            with ui.expansion('Quick Actions', icon='flash_on').classes('w-full mt-2'):
                with ui.grid(columns=3).classes('w-full gap-2'):
                    ui.button('System Info', on_click=lambda: self._quick_action('Get system information and current status')).classes('text-sm')
                    ui.button('List Files', on_click=lambda: self._quick_action('List files in the current directory')).classes('text-sm')
                    ui.button('Check Disk Space', on_click=lambda: self._quick_action('Check available disk space')).classes('text-sm')
                    ui.button('Network Test', on_click=lambda: self._quick_action('Test network connectivity')).classes('text-sm')
                    ui.button('Process List', on_click=lambda: self._quick_action('Show running processes')).classes('text-sm')
                    ui.button('Docker Status', on_click=lambda: self._quick_action('Check Docker containers status')).classes('text-sm')
                    
        # Start status monitoring
        ui.timer(30.0, self._update_status)
        
    async def _handle_send(self):
        """Handle sending a message."""
        if self.is_processing:
            return
            
        message = self.input_field.value.strip()
        if not message:
            return
            
        self.is_processing = True
        self.send_button.props('loading')
        self.input_field.value = ''
        
        try:
            # Add user message to chat
            await self._add_message(message, 'user', 'You')
            
            # Add thinking indicator
            thinking_msg = await self._add_message('Thinking...', 'assistant', 'Assistant')
            
            # Get AI response
            response = await self.app.send_message(message)
            
            # Remove thinking indicator and add real response
            thinking_msg.delete()
            await self._add_message(response, 'assistant', 'Assistant')
            
        except Exception as e:
            await self._add_message(f'Error: {str(e)}', 'assistant', 'System', 'negative')
            
        finally:
            self.is_processing = False
            self.send_button.props(remove='loading')
            
    async def _quick_action(self, action: str):
        """Execute a quick action."""
        self.input_field.value = action
        await self._handle_send()
        
    async def _add_message(self, content: str, role: str, name: str, color: Optional[str] = None):
        """Add a message to the chat history."""
        with self.chat_history:
            timestamp = time.strftime('%H:%M:%S')
            
            with ui.card().classes('w-full'):
                with ui.row().classes('w-full justify-between items-start'):
                    with ui.column().classes('flex-grow'):
                        ui.label(f'{name} • {timestamp}').classes('text-sm text-gray-500 mb-1')
                        
                        # Format content based on type
                        if content.startswith('```') and content.endswith('```'):
                            # Code block
                            code = content[3:-3].strip()
                            ui.code(code).classes('w-full')
                        elif '\n' in content and any(keyword in content.lower() for keyword in ['stdout:', 'stderr:', 'exit code:']):
                            # Command output
                            ui.code(content).classes('w-full')
                        else:
                            # Regular text
                            ui.markdown(content).classes('w-full')
                            
                    # Message actions
                    with ui.column().classes('gap-1'):
                        if role == 'assistant':
                            ui.button(icon='content_copy', on_click=lambda c=content: ui.clipboard.write(c)).props('flat dense size=sm')
                            
        # Auto-scroll to bottom
        await asyncio.sleep(0.1)
        self.chat_history.scroll_to(percent=1.0)
        
    async def _update_status(self):
        """Update service status indicators."""
        try:
            # Check Tela status
            tela_health = await self.app.tela_client.health_check()
            if tela_health["status"] == "healthy":
                self.tela_status.props('color=green')
                self.tela_status.text = 'Tela ✓'
            else:
                self.tela_status.props('color=red')
                self.tela_status.text = 'Tela ✗'
                
            # Check Pandora status
            async with self.app.pandora_client as client:
                pandora_health = await client.health_check()
                if pandora_health["status"] == "healthy":
                    self.pandora_status.props('color=green')
                    self.pandora_status.text = 'Pandora ✓'
                else:
                    self.pandora_status.props('color=red')
                    self.pandora_status.text = 'Pandora ✗'
                    
        except Exception as e:
            self.tela_status.props('color=orange')
            self.tela_status.text = 'Tela ?'
            self.pandora_status.props('color=orange')
            self.pandora_status.text = 'Pandora ?'
