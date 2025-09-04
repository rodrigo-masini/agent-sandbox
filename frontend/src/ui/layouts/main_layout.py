# ==============================================
# MAIN LAYOUT IMPLEMENTATION
# ==============================================

from nicegui import ui
from typing import Optional
import asyncio

class MainLayout:
    """Main application layout."""
    
    def __init__(self, app_instance):
        self.app = app_instance
        self.current_view = "chat"
        self.sidebar_expanded = True
        
    async def render(self):
        """Render the main layout."""
        # Apply dark theme by default
        ui.dark_mode().enable()
        
        with ui.header(elevated=True).classes('items-center justify-between'):
            with ui.row().classes('items-center gap-4'):
                ui.button(icon='menu', on_click=self.toggle_sidebar).props('flat color=white')
                ui.label('Agent Sandbox').classes('text-xl font-bold')
                
            with ui.row().classes('items-center gap-2'):
                # Status indicators
                ui.badge('AI Connected', color='green').classes('text-xs')
                ui.badge('System Ready', color='green').classes('text-xs')
                
                # User menu
                with ui.button(icon='account_circle').props('flat color=white'):
                    with ui.menu() as menu:
                        ui.menu_item('Profile', on_click=lambda: ui.notify('Profile'))
                        ui.menu_item('Settings', on_click=lambda: self.show_settings())
                        ui.separator()
                        ui.menu_item('Logout', on_click=lambda: ui.navigate.to('/'))
        
        with ui.splitter(value=20).classes('w-full') as splitter:
            # Sidebar
            with splitter.before:
                await self.render_sidebar()
            
            # Main content
            with splitter.after:
                self.content_container = ui.column().classes('w-full h-full p-4')
                await self.render_content()
        
        # Footer
        with ui.footer().classes('bg-gray-900 text-gray-400 text-xs'):
            ui.label('© 2025 Agents Sandbox - AI-Powered System Interface')
    
    async def render_sidebar(self):
        """Render the sidebar navigation."""
        with ui.column().classes('h-full bg-gray-900 p-2'):
            ui.label('Navigation').classes('text-sm text-gray-400 mb-2')
            
            # Navigation items
            nav_items = [
                ('chat', 'chat', 'AI Assistant'),
                ('folder', 'files', 'File Browser'),
                ('terminal', 'terminal', 'Terminal'),
                ('monitoring', 'monitor', 'System Monitor'),
                ('memory', 'docker', 'Docker'),
                ('network_check', 'network', 'Network'),
                ('storage', 'database', 'Database'),
            ]
            
            for icon, view, label in nav_items:
                is_active = self.current_view == view
                button = ui.button(
                    label if self.sidebar_expanded else '',
                    on_click=lambda v=view: self.switch_view(v)
                ).props(f"{'color=primary' if is_active else 'flat'}")
                
                if not self.sidebar_expanded:
                    button.props('icon=' + icon)
                else:
                    with button:
                        with ui.row().classes('items-center gap-2'):
                            ui.icon(icon)
                            ui.label(label)
            
            # Spacer
            ui.space()
            
            # Settings at bottom
            ui.button(
                'Settings' if self.sidebar_expanded else '',
                icon='settings',
                on_click=self.show_settings
            ).props('flat')
    
    async def render_content(self):
        """Render the main content area based on current view."""
        with self.content_container:
            self.content_container.clear()
            
            if self.current_view == 'chat':
                from ..components.chat import ChatComponent
                chat = ChatComponent(self.app)
                await chat.render()
                
            elif self.current_view == 'files':
                from ..components.file_browser import FileBrowserComponent
                browser = FileBrowserComponent(self.app)
                await browser.render()
                
            elif self.current_view == 'terminal':
                from ..components.terminal import TerminalComponent
                terminal = TerminalComponent(self.app)
                await terminal.render()
                
            elif self.current_view == 'monitor':
                from ..components.system_monitor import SystemMonitorComponent
                monitor = SystemMonitorComponent(self.app)
                await monitor.render()
                
            elif self.current_view == 'docker':
                await self.render_docker_view()
                
            elif self.current_view == 'network':
                await self.render_network_view()
                
            elif self.current_view == 'database':
                await self.render_database_view()
                
            else:
                ui.label(f'View not implemented: {self.current_view}')
    
    async def switch_view(self, view: str):
        """Switch to a different view."""
        self.current_view = view
        await self.render_content()
    
    def toggle_sidebar(self):
        """Toggle sidebar expanded/collapsed state."""
        self.sidebar_expanded = not self.sidebar_expanded
        ui.notify(f"Sidebar {'expanded' if self.sidebar_expanded else 'collapsed'}", position='bottom')
    
    def show_settings(self):
        """Show settings dialog."""
        with ui.dialog() as dialog, ui.card():
            ui.label('Settings').classes('text-xl mb-4')
            
            with ui.tabs().classes('w-full') as tabs:
                general_tab = ui.tab('General')
                api_tab = ui.tab('API')
                security_tab = ui.tab('Security')
                
            with ui.tab_panels(tabs, value=general_tab).classes('w-full'):
                with ui.tab_panel(general_tab):
                    ui.label('Theme')
                    ui.switch('Dark Mode', value=True)
                    
                    ui.label('Chat Settings')
                    ui.slider(min=0, max=2, value=0.7, step=0.1, label='Temperature')
                    ui.number('Max Tokens', value=2000, min=100, max=4000)
                    
                with ui.tab_panel(api_tab):
                    ui.label('Fabric API')
                    ui.input('API Key', password=True, value='****')
                    ui.input('Organization ID', value=self.app.config.get('FABRIC_ORG_ID'))
                    ui.input('Project ID', value=self.app.config.get('FABRIC_PROJECT_ID'))
                    
                with ui.tab_panel(security_tab):
                    ui.label('Security Settings')
                    ui.switch('Enable Command Whitelist', value=False)
                    ui.switch('Enable Rate Limiting', value=True)
                    ui.number('Rate Limit (requests/min)', value=60)
            
            with ui.row():
                ui.button('Save', on_click=lambda: self.save_settings(dialog))
                ui.button('Cancel', on_click=dialog.close)
        
        dialog.open()
    
    def save_settings(self, dialog):
        """Save settings."""
        ui.notify('Settings saved', type='positive')
        dialog.close()
    
    async def render_docker_view(self):
        """Render Docker management view."""
        ui.label('Docker Management').classes('text-2xl mb-4')
        
        with ui.row().classes('gap-2 mb-4'):
            ui.button('List Containers', icon='list', on_click=self.list_docker_containers)
            ui.button('Pull Image', icon='download', on_click=self.pull_docker_image)
            ui.button('Run Container', icon='play_arrow', on_click=self.run_docker_container)
        
        # Container list
        self.docker_container = ui.column().classes('w-full')
        await self.list_docker_containers()
    
    async def render_network_view(self):
        """Render Network tools view."""
        ui.label('Network Tools').classes('text-2xl mb-4')
        
        with ui.row().classes('gap-2 mb-4'):
            ui.button('HTTP Request', icon='http', on_click=self.show_http_dialog)
            ui.button('Port Scanner', icon='security', on_click=self.show_port_scanner)
            ui.button('DNS Lookup', icon='dns', on_click=self.show_dns_lookup)
        
        self.network_results = ui.column().classes('w-full')
    
    async def render_database_view(self):
        """Render Database management view."""
        ui.label('Database Tools').classes('text-2xl mb-4')
        
        with ui.row().classes('gap-2 mb-4'):
            ui.button('Execute Query', icon='code', on_click=self.show_query_dialog)
            ui.button('Backup Database', icon='backup', on_click=self.show_backup_dialog)
        
        self.db_results = ui.column().classes('w-full')
    
    async def list_docker_containers(self):
        """List Docker containers."""
        self.docker_container.clear()
        with self.docker_container:
            ui.label('Loading containers...').classes('text-gray-500')
            
        try:
            from ...tools.docker_tools import DockerTools
            docker = DockerTools(self.app.pandora_client)
            result = await docker.docker_list(all=True, format="table")
            
            self.docker_container.clear()
            with self.docker_container:
                ui.code(result).classes('w-full')
                
        except Exception as e:
            self.docker_container.clear()
            with self.docker_container:
                ui.label(f'Error: {str(e)}').classes('text-red-500')
    
    def pull_docker_image(self):
        """Show dialog to pull Docker image."""
        with ui.dialog() as dialog, ui.card():
            ui.label('Pull Docker Image').classes('text-xl mb-4')
            image_input = ui.input('Image Name', placeholder='e.g., ubuntu:22.04')
            
            async def pull():
                if image_input.value:
                    ui.notify(f'Pulling {image_input.value}...', type='ongoing')
                    # Implementation would go here
                    dialog.close()
            
            with ui.row():
                ui.button('Pull', on_click=pull)
                ui.button('Cancel', on_click=dialog.close)
        
        dialog.open()
    
    def run_docker_container(self):
        """Show dialog to run Docker container."""
        with ui.dialog() as dialog, ui.card():
            ui.label('Run Docker Container').classes('text-xl mb-4')
            
            image_input = ui.input('Image', placeholder='ubuntu:22.04')
            name_input = ui.input('Container Name', placeholder='my-container')
            command_input = ui.input('Command', placeholder='bash')
            
            with ui.row():
                ui.button('Run', on_click=lambda: ui.notify('Running container...'))
                ui.button('Cancel', on_click=dialog.close)
        
        dialog.open()
    
    def show_http_dialog(self):
        """Show HTTP request dialog."""
        with ui.dialog() as dialog, ui.card().classes('w-96'):
            ui.label('HTTP Request').classes('text-xl mb-4')
            
            url_input = ui.input('URL', placeholder='https://api.example.com')
            method_select = ui.select(['GET', 'POST', 'PUT', 'DELETE'], value='GET', label='Method')
            headers_input = ui.textarea('Headers (JSON)', placeholder='{"Content-Type": "application/json"}')
            body_input = ui.textarea('Body', placeholder='Request body...')
            
            async def send_request():
                ui.notify('Sending request...', type='ongoing')
                # Implementation would go here
                dialog.close()
            
            with ui.row():
                ui.button('Send', on_click=send_request)
                ui.button('Cancel', on_click=dialog.close)
        
        dialog.open()
    
    def show_port_scanner(self):
        """Show port scanner dialog."""
        with ui.dialog() as dialog, ui.card():
            ui.label('Port Scanner').classes('text-xl mb-4')
            
            host_input = ui.input('Host', placeholder='example.com')
            port_input = ui.input('Port', placeholder='80')
            
            with ui.row():
                ui.button('Scan', on_click=lambda: ui.notify('Scanning...'))
                ui.button('Cancel', on_click=dialog.close)
        
        dialog.open()
    
    def show_dns_lookup(self):
        """Show DNS lookup dialog."""
        with ui.dialog() as dialog, ui.card():
            ui.label('DNS Lookup').classes('text-xl mb-4')
            
            domain_input = ui.input('Domain', placeholder='example.com')
            type_select = ui.select(['A', 'AAAA', 'MX', 'TXT', 'NS', 'CNAME'], value='A', label='Record Type')
            
            with ui.row():
                ui.button('Lookup', on_click=lambda: ui.notify('Looking up...'))
                ui.button('Cancel', on_click=dialog.close)
        
        dialog.open()
    
    def show_query_dialog(self):
        """Show database query dialog."""
        with ui.dialog() as dialog, ui.card().classes('w-96'):
            ui.label('Execute SQL Query').classes('text-xl mb-4')
            
            db_select = ui.select(['sqlite', 'postgresql', 'mysql'], value='sqlite', label='Database Type')
            conn_input = ui.input('Connection String', placeholder='database.db')
            query_input = ui.textarea('SQL Query', placeholder='SELECT * FROM table')
            
            with ui.row():
                ui.button('Execute', on_click=lambda: ui.notify('Executing...'))
                ui.button('Cancel', on_click=dialog.close)
        
        dialog.open()
    
    def show_backup_dialog(self):
        """Show database backup dialog."""
        with ui.dialog() as dialog, ui.card():
            ui.label('Backup Database').classes('text-xl mb-4')
            
            db_select = ui.select(['sqlite', 'postgresql', 'mysql'], value='sqlite', label='Database Type')
            source_input = ui.input('Source Database', placeholder='database.db')
            output_input = ui.input('Backup Path', placeholder='backup.sql')
            
            with ui.row():
                ui.button('Backup', on_click=lambda: ui.notify('Creating backup...'))
                ui.button('Cancel', on_click=dialog.close)
        
        dialog.open()
