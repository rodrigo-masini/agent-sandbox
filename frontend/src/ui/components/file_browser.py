# ==============================================
# FILE BROWSER COMPONENT
# ==============================================

from nicegui import ui
from typing import Optional, List
import asyncio
import os

class FileBrowserComponent:
    """File browser component for navigating and managing files."""
    
    def __init__(self, app_instance, initial_path: str = "."):
        self.app = app_instance
        self.current_path = initial_path
        self.selected_file = None
        self.file_list = None
        
    async def render(self):
        """Render the file browser component."""
        with ui.column().classes('w-full h-full'):
            # Header
            ui.label('File Browser').classes('text-2xl font-bold mb-4')
            
            # Path navigation
            with ui.row().classes('w-full gap-2 mb-4'):
                self.path_input = ui.input(
                    'Path',
                    value=self.current_path,
                    on_change=self.navigate_to_path
                ).classes('flex-grow')
                
                ui.button(icon='refresh', on_click=self.refresh_files)
                ui.button(icon='folder_open', on_click=self.navigate_up)
                ui.button(icon='create_new_folder', on_click=self.create_folder)
                ui.button(icon='upload_file', on_click=self.upload_file)
            
            # File list
            with ui.scroll_area().classes('w-full flex-grow border rounded'):
                self.file_list = ui.column().classes('w-full')
                await self.load_files()
            
            # Actions bar
            with ui.row().classes('w-full gap-2 mt-4'):
                ui.button('New File', icon='add', on_click=self.create_file)
                ui.button('Delete', icon='delete', on_click=self.delete_selected)
                ui.button('Rename', icon='edit', on_click=self.rename_selected)
                ui.button('Download', icon='download', on_click=self.download_selected)
    
    async def load_files(self):
        """Load files for current path."""
        if not self.file_list:
            return
            
        self.file_list.clear()
        
        try:
            from ...tools.file_tools import FileTools
            file_tools = FileTools(self.app.pandora_client)
            
            result = await file_tools.list_files(path=self.current_path)
            
            # Parse the result to get file list
            if "Files in" in result:
                lines = result.split('\n')[1:]  # Skip header
                files = [line.strip('- ') for line in lines if line.startswith('- ')]
                
                with self.file_list:
                    for file in files:
                        self.render_file_item(file)
            else:
                with self.file_list:
                    ui.label('No files found').classes('text-gray-500')
                    
        except Exception as e:
            with self.file_list:
                ui.label(f'Error loading files: {str(e)}').classes('text-red-500')
    
    def render_file_item(self, filename: str):
        """Render a single file item."""
        is_dir = filename.endswith('/')
        icon = 'folder' if is_dir else 'description'
        
        with ui.card().classes('w-full cursor-pointer hover:bg-gray-100'):
            with ui.row().classes('items-center gap-2'):
                ui.icon(icon).classes('text-gray-600')
                ui.label(filename).classes('flex-grow')
                
                if not is_dir:
                    ui.button(
                        icon='visibility',
                        on_click=lambda f=filename: self.view_file(f)
                    ).props('flat dense')
                    ui.button(
                        icon='edit',
                        on_click=lambda f=filename: self.edit_file(f)
                    ).props('flat dense')
    
    async def navigate_to_path(self):
        """Navigate to the path in the input field."""
        self.current_path = self.path_input.value
        await self.load_files()
    
    async def navigate_up(self):
        """Navigate to parent directory."""
        self.current_path = os.path.dirname(self.current_path) or '.'
        self.path_input.value = self.current_path
        await self.load_files()
    
    async def refresh_files(self):
        """Refresh the file list."""
        await self.load_files()
        ui.notify('Files refreshed', position='bottom')
    
    def create_file(self):
        """Create a new file."""
        with ui.dialog() as dialog, ui.card():
            ui.label('Create New File').classes('text-xl mb-4')
            
            name_input = ui.input('File Name', placeholder='example.txt')
            content_input = ui.textarea('Content', placeholder='File content...')
            
            async def create():
                if name_input.value:
                    file_path = os.path.join(self.current_path, name_input.value)
                    from ...tools.file_tools import FileTools
                    file_tools = FileTools(self.app.pandora_client)
                    result = await file_tools.write_file(
                        file_path=file_path,
                        content=content_input.value
                    )
                    ui.notify(result, type='positive' if 'Successfully' in result else 'negative')
                    await self.load_files()
                    dialog.close()
            
            with ui.row():
                ui.button('Create', on_click=create)
                ui.button('Cancel', on_click=dialog.close)
        
        dialog.open()
    
    def create_folder(self):
        """Create a new folder."""
        with ui.dialog() as dialog, ui.card():
            ui.label('Create New Folder').classes('text-xl mb-4')
            
            name_input = ui.input('Folder Name', placeholder='new-folder')
            
            async def create():
                if name_input.value:
                    folder_path = os.path.join(self.current_path, name_input.value)
                    from ...tools.file_tools import FileTools
                    file_tools = FileTools(self.app.pandora_client)
                    result = await file_tools.create_directory(path=folder_path)
                    ui.notify(result, type='positive' if 'Successfully' in result else 'negative')
                    await self.load_files()
                    dialog.close()
            
            with ui.row():
                ui.button('Create', on_click=create)
                ui.button('Cancel', on_click=dialog.close)
        
        dialog.open()
    
    def upload_file(self):
        """Upload a file."""
        ui.notify('File upload not yet implemented', type='warning')
    
    def delete_selected(self):
        """Delete selected file."""
        if self.selected_file:
            ui.notify(f'Deleting {self.selected_file}...', type='warning')
    
    def rename_selected(self):
        """Rename selected file."""
        if self.selected_file:
            ui.notify(f'Renaming {self.selected_file}...', type='info')
    
    def download_selected(self):
        """Download selected file."""
        if self.selected_file:
            ui.notify(f'Downloading {self.selected_file}...', type='info')
    
    async def view_file(self, filename: str):
        """View file contents."""
        file_path = os.path.join(self.current_path, filename)
        
        try:
            from ...tools.file_tools import FileTools
            file_tools = FileTools(self.app.pandora_client)
            result = await file_tools.read_file(file_path=file_path)
            
            with ui.dialog() as dialog, ui.card().classes('w-96'):
                ui.label(f'File: {filename}').classes('text-xl mb-4')
                ui.code(result).classes('w-full max-h-96 overflow-auto')
                ui.button('Close', on_click=dialog.close)
            
            dialog.open()
            
        except Exception as e:
            ui.notify(f'Error viewing file: {str(e)}', type='negative')
    
    async def edit_file(self, filename: str):
        """Edit file contents."""
        file_path = os.path.join(self.current_path, filename)
        
        try:
            from ...tools.file_tools import FileTools
            file_tools = FileTools(self.app.pandora_client)
            result = await file_tools.read_file(file_path=file_path)
            
            # Extract content from result
            content = result.split('\n\n', 1)[1] if '\n\n' in result else result
            
            with ui.dialog() as dialog, ui.card().classes('w-96'):
                ui.label(f'Edit: {filename}').classes('text-xl mb-4')
                editor = ui.textarea('Content', value=content).classes('w-full')
                
                async def save():
                    result = await file_tools.write_file(
                        file_path=file_path,
                        content=editor.value
                    )
                    ui.notify(result, type='positive' if 'Successfully' in result else 'negative')
                    dialog.close()
                
                with ui.row():
                    ui.button('Save', on_click=save)
                    ui.button('Cancel', on_click=dialog.close)
            
            dialog.open()
            
        except Exception as e:
            ui.notify(f'Error editing file: {str(e)}', type='negative')
