# ==============================================
# TERMINAL COMPONENT
# ==============================================

import asyncio
from typing import Any, List, Optional

from nicegui import ui


class TerminalComponent:
    """Terminal emulator component."""

    # CORRECTED: Added full type hints to the __init__ method and instance variables.
    # This resolves the mypy note and makes the entire class type-safe.
    def __init__(self, app_instance: Any) -> None:
        self.app = app_instance
        self.command_history: List[str] = []
        self.history_index = -1
        self.output_area: Optional[ui.column] = None
        self.input_field: Optional[ui.input] = None

    async def render(self):
        """Render the terminal component."""
        with ui.column().classes("w-full h-full bg-black"):
            # Header
            with ui.row().classes("w-full bg-gray-800 p-2"):
                ui.label("Terminal").classes("text-white font-mono")
                ui.space()
                ui.button(icon="clear_all", on_click=self.clear_terminal).props(
                    "flat color=white dense"
                )

            # Output area
            with ui.scroll_area().classes("w-full flex-grow bg-black p-2"):
                self.output_area = ui.column().classes(
                    "w-full font-mono text-green-400"
                )
                self.add_output("Agtsdbx Terminal v1.0.0")
                self.add_output('Type "help" for available commands')
                self.add_output("-" * 40)

            # Input area
            with ui.row().classes("w-full bg-gray-900 p-2"):
                ui.label("$").classes("text-green-400 font-mono")
                self.input_field = (
                    ui.input(
                        placeholder="Enter command...", on_change=self.handle_enter
                    )
                    .classes("flex-grow bg-black text-green-400 font-mono")
                    .props("outlined dense dark")
                )

                # Handle command history with arrow keys
                if self.input_field:
                    self.input_field.on("keydown.up", self.history_up)
                    self.input_field.on("keydown.down", self.history_down)

    def add_output(self, text: str, color: str = "text-green-400"):
        """Add text to terminal output."""
        # CORRECTED: Added a safety check for the optional variable.
        if self.output_area is None:
            return

        with self.output_area:
            ui.label(text).classes(f"font-mono {color} whitespace-pre-wrap break-all")

        # Auto-scroll to bottom
        asyncio.create_task(self.scroll_to_bottom())

    async def scroll_to_bottom(self):
        """Scroll output area to bottom."""
        await asyncio.sleep(0.1)
        if self.output_area:
            self.output_area.scroll_to(percent=1.0)

    async def handle_enter(self):
        """Handle Enter key press."""
        # CORRECTED: Added a safety check for the optional variable.
        if self.input_field is None:
            return

        command = self.input_field.value.strip()
        if not command:
            return

        # Add to history
        self.command_history.append(command)
        self.history_index = len(self.command_history)

        # Display command
        self.add_output(f"$ {command}", "text-blue-400")

        # Clear input
        self.input_field.value = ""

        # Handle special commands
        if command.lower() == "help":
            self.show_help()
        elif command.lower() == "clear":
            self.clear_terminal()
        elif command.lower() == "exit":
            ui.notify("Use the navigation menu to leave terminal", type="info")
        else:
            # Execute command
            await self.execute_command(command)

    async def execute_command(self, command: str):
        """Execute a command through Agtsdbx."""
        try:
            from ...tools.execution_tools import ExecutionTools

            exec_tools = ExecutionTools(self.app.agtsdbx_client)

            # Show loading indicator
            self.add_output("Executing...", "text-yellow-400")

            # Execute command
            result = await exec_tools.execute_shell_command(command=command)

            # Parse and display result
            lines = result.split("\n")
            for line in lines:
                if line.startswith("STDOUT:"):
                    continue
                elif line.startswith("STDERR:"):
                    continue
                elif line.startswith("EXIT CODE:"):
                    if "EXIT CODE: 0" in line:
                        color = "text-gray-500"
                    else:
                        color = "text-red-400"
                    self.add_output(line, color)
                elif line.startswith("Error:"):
                    self.add_output(line, "text-red-400")
                else:
                    self.add_output(line)

        except Exception as e:
            self.add_output(f"Error: {str(e)}", "text-red-400")

    def show_help(self):
        """Show help information."""
        help_text = """
Available Commands:
  help     - Show this help message
  clear    - Clear the terminal
  exit     - Exit terminal (use navigation menu).
  You can run any shell command available in the Agtsdbx environment.
Examples:
  ls       - List files
  pwd      - Show current directory
  cat file - Display file contents
  python   - Start Python interpreter
  docker   - Docker commands (if enabled)
        """
        self.add_output(help_text, "text-cyan-400")

    def clear_terminal(self):
        """Clear terminal output."""
        if self.output_area:
            self.output_area.clear()
            self.add_output("Terminal cleared")

    def history_up(self):
        """Navigate up in command history."""
        # CORRECTED: Added a safety check for the optional variable.
        if self.input_field is None:
            return

        if self.command_history and self.history_index > 0:
            self.history_index -= 1
            self.input_field.value = self.command_history[self.history_index]

    def history_down(self):
        """Navigate down in command history."""
        # CORRECTED: Added a safety check for the optional variable.
        if self.input_field is None:
            return

        if self.command_history and self.history_index < len(self.command_history) - 1:
            self.history_index += 1
            self.input_field.value = self.command_history[self.history_index]
        elif self.history_index == len(self.command_history) - 1:
            self.history_index = len(self.command_history)
            self.input_field.value = ""
