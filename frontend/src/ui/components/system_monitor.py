# ==============================================
# SYSTEM MONITOR COMPONENT
# ==============================================

from nicegui import ui
import asyncio
from typing import Dict, List

class SystemMonitorComponent:
    """System monitoring dashboard component."""
    
    def __init__(self, app_instance):
        self.app = app_instance
        self.refresh_interval = 5  # seconds
        self.monitoring = False
        self.charts = {}
        
    async def render(self):
        """Render the system monitor component."""
        with ui.column().classes('w-full h-full'):
            # Header
            with ui.row().classes('w-full justify-between items-center mb-4'):
                ui.label('System Monitor').classes('text-2xl font-bold')
                
                with ui.row().classes('gap-2'):
                    self.auto_refresh_switch = ui.switch('Auto Refresh', value=True)
                    ui.button('Refresh Now', icon='refresh', on_click=self.refresh_data)
            
            # Stats grid
            with ui.grid(columns=4).classes('w-full gap-4 mb-4'):
                self.cpu_card = self.create_stat_card('CPU Usage', '0%', 'memory')
                self.memory_card = self.create_stat_card('Memory Usage', '0%', 'storage')
                self.disk_card = self.create_stat_card('Disk Usage', '0%', 'folder')
                self.network_card = self.create_stat_card('Network', 'Connected', 'wifi')
            
            # Tabs for different views
            with ui.tabs().classes('w-full') as tabs:
                overview_tab = ui.tab('Overview')
                processes_tab = ui.tab('Processes')
                network_tab = ui.tab('Network')
                docker_tab = ui.tab('Docker')
            
            with ui.tab_panels(tabs, value=overview_tab).classes('w-full'):
                with ui.tab_panel(overview_tab):
                    await self.render_overview()
                    
                with ui.tab_panel(processes_tab):
                    await self.render_processes()
                    
                with ui.tab_panel(network_tab):
                    await self.render_network()
                    
                with ui.tab_panel(docker_tab):
                    await self.render_docker()
            
            # Start monitoring
            await self.start_monitoring()
    
    def create_stat_card(self, title: str, value: str, icon: str) -> Dict:
        """Create a statistics card."""
        with ui.card().classes('p-4'):
            with ui.row().classes('items-center gap-4'):
                ui.icon(icon, size='lg').classes('text-primary')
                with ui.column():
                    ui.label(title).classes('text-sm text-gray-600')
                    label = ui.label(value).classes('text-2xl font-bold')
        
        return {'card': label, 'title': title}
    
    async def render_overview(self):
        """Render system overview."""
        with ui.column().classes('w-full gap-4'):
            # System info
            self.system_info = ui.card().classes('w-full p-4')
            with self.system_info:
                ui.label('System Information').classes('text-lg font-bold mb-2')
                self.info_content = ui.column()
            
            # Resource usage charts would go here
            ui.label('Resource usage charts would be displayed here').classes('text-gray-500')
    
    async def render_processes(self):
        """Render process list."""
        with ui.column().classes('w-full'):
            # Controls
            with ui.row().classes('gap-2 mb-4'):
                ui.select(['cpu', 'memory', 'pid', 'name'], value='cpu', label='Sort by')
                ui.number('Show top', value=20, min=5, max=100)
                ui.button('Kill Process', icon='stop', color='red')
            
            # Process table
            self.process_table = ui.column().classes('w-full')
            await self.load_processes()
    
    async def render_network(self):
        """Render network information."""
        with ui.column().classes('w-full gap-4'):
            # Network status
            ui.card().classes('w-full p-4')
            ui.label('Network Status').classes('text-lg font-bold mb-2')
            
            # Connection test
            with ui.row().classes('gap-2'):
                ui.button('Test Connectivity', icon='network_check', on_click=self.test_connectivity)
                ui.button('DNS Test', icon='dns', on_click=self.test_dns)
            
            self.network_results = ui.column().classes('w-full mt-4')
    
    async def render_docker(self):
        """Render Docker container status."""
        with ui.column().classes('w-full'):
            ui.label('Docker Containers').classes('text-lg font-bold mb-2')
            self.docker_list = ui.column().classes('w-full')
            
            if self.app.config.get('ENABLE_DOCKER'):
                await self.load_docker_status()
            else:
                ui.label('Docker is disabled').classes('text-gray-500')
    
    async def start_monitoring(self):
        """Start auto-refresh monitoring."""
        self.monitoring = True
        while self.monitoring:
            if self.auto_refresh_switch and self.auto_refresh_switch.value:
                await self.refresh_data()
            await asyncio.sleep(self.refresh_interval)
    
    async def refresh_data(self):
        """Refresh all monitoring data."""
        try:
            from ...tools.system_tools import SystemTools
            system_tools = SystemTools(self.app.agtsdbx_client)
            
            # Get system info
            info = await system_tools.get_system_info()
            
            # Update stat cards
            # This would parse the actual system info
            self.cpu_card['card'].text = '25%'
            self.memory_card['card'].text = '4.2 GB / 16 GB'
            self.disk_card['card'].text = '120 GB / 500 GB'
            self.network_card['card'].text = 'Connected'
            
            # Update system info display
            if self.info_content:
                self.info_content.clear()
                with self.info_content:
                    ui.code(info).classes('w-full')
                    
        except Exception as e:
            ui.notify(f'Error refreshing data: {str(e)}', type='negative')
    
    async def load_processes(self):
        """Load process list."""
        try:
            from ...tools.system_tools import SystemTools
            system_tools = SystemTools(self.app.agtsdbx_client)
            
            result = await system_tools.get_process_list(sort_by='cpu', limit=20)
            
            if self.process_table:
                self.process_table.clear()
                with self.process_table:
                    ui.code(result).classes('w-full')
                    
        except Exception as e:
            ui.notify(f'Error loading processes: {str(e)}', type='negative')
    
    async def test_connectivity(self):
        """Test network connectivity."""
        try:
            from ...tools.system_tools import SystemTools
            system_tools = SystemTools(self.app.agtsdbx_client)
            
            result = await system_tools.check_network_connectivity()
            
            if self.network_results:
                self.network_results.clear()
                with self.network_results:
                    ui.code(result).classes('w-full')
                    
        except Exception as e:
            ui.notify(f'Error testing connectivity: {str(e)}', type='negative')
    
    async def test_dns(self):
        """Test DNS resolution."""
        try:
            from ...tools.network_tools import NetworkTools
            network_tools = NetworkTools(self.app.agtsdbx_client)
            
            result = await network_tools.dns_lookup(domain='google.com')
            
            if self.network_results:
                self.network_results.clear()
                with self.network_results:
                    ui.code(result).classes('w-full')
                    
        except Exception as e:
            ui.notify(f'Error testing DNS: {str(e)}', type='negative')
    
    async def load_docker_status(self):
        """Load Docker container status."""
        try:
            from ...tools.docker_tools import DockerTools
            docker_tools = DockerTools(self.app.agtsdbx_client)
            
            result = await docker_tools.docker_list(all=True, format='table')
            
            if self.docker_list:
                self.docker_list.clear()
                with self.docker_list:
                    ui.code(result).classes('w-full')
                    
        except Exception as e:
            if self.docker_list:
                self.docker_list.clear()
                with self.docker_list:
                    ui.label(f'Error loading Docker status: {str(e)}').classes('text-red-500')
