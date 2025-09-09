import asyncio
import time
from typing import Optional

from nicegui import ui


class ChatComponent:
    def __init__(
        self, app_instance, container_classes: str = "w-full max-w-4xl mx-auto"
    ):
        self.app = app_instance
        self.container_classes = container_classes
        # CORRECTED: Added explicit Optional type hints. This tells mypy that we
        # know these variables can be None.
        self.chat_history: Optional[ui.column] = None
        self.input_field: Optional[ui.input] = None
        self.send_button: Optional[ui.button] = None
        self.is_processing = False

    async def render(self):
        """Render the chat component."""
        with ui.column().classes(self.container_classes):
            # Header
            with ui.row().classes("w-full justify-between items-center mb-4"):
                ui.label("Agtsdbx AI Assistant").classes("text-2xl font-bold")

                # Status indicators
                with ui.row().classes("gap-2"):
                    self.fabric_status = ui.badge("Fabric", color="green").classes(
                        "text-xs"
                    )
                    self.agtsdbx_status = ui.badge("Agtsdbx", color="green").classes(
                        "text-xs"
                    )

            # Chat history container
            with ui.scroll_area().classes("w-full h-96 border rounded-lg p-4"):
                self.chat_history = ui.column().classes("w-full gap-2")

            # Input area
            with ui.row().classes("w-full gap-2 mt-4"):
                self.input_field = ui.input(
                    placeholder="Ask me anything...I can execute commands, manage files, and more!",
                    validation={"min_length": 1},
                ).classes("flex-grow")

                self.send_button = ui.button(
                    "Send", on_click=self._handle_send, icon="send"
                ).classes("px-6")

            # Keyboard shortcut
            self.input_field.on("keydown.enter", self._handle_send)

            # Quick actions
            with ui.expansion("Quick Actions", icon="flash_on").classes("w-full mt-2"):
                with ui.grid(columns=3).classes("w-full gap-2"):
                    ui.button(
                        "System Info",
                        on_click=lambda: self._quick_action(
                            "Get system information and current status"
                        ),
                    ).classes("text-sm")
                    ui.button(
                        "List Files",
                        on_click=lambda: self._quick_action(
                            "List files in the current directory"
                        ),
                    ).classes("text-sm")
                    ui.button(
                        "Check Disk Space",
                        on_click=lambda: self._quick_action(
                            "Check available disk space"
                        ),
                    ).classes("text-sm")
                    ui.button(
                        "Network Test",
                        on_click=lambda: self._quick_action(
                            "Test network connectivity"
                        ),
                    ).classes("text-sm")
                    ui.button(
                        "Process List",
                        on_click=lambda: self._quick_action("Show running processes"),
                    ).classes("text-sm")
                    ui.button(
                        "Docker Status",
                        on_click=lambda: self._quick_action(
                            "Check Docker containers status"
                        ),
                    ).classes("text-sm")

        # Start status monitoring
        ui.timer(30.0, self._update_status)

    async def _handle_send(self):
        """Handle sending a message."""
        # CORRECTED: Added a "None check". This guarantees to mypy that if the code
        # proceeds, these variables are not None.
        if self.is_processing or self.input_field is None or self.send_button is None:
            return

        message = self.input_field.value.strip()
        if not message:
            return

        self.is_processing = True
        self.send_button.props("loading")
        self.input_field.value = ""

        try:
            # Add user message to chat
            await self._add_message(message, "user", "You")

            # Add thinking indicator
            thinking_msg = await self._add_message(
                "Thinking...", "assistant", "Assistant"
            )
            if thinking_msg:
                # Get AI response
                response = await self.app.send_message(message)
                # Remove thinking indicator and add real response
                thinking_msg.delete()
                await self._add_message(response, "assistant", "Assistant")

        except Exception as e:
            await self._add_message(
                f"Error: {str(e)}", "assistant", "System", "negative"
            )

        finally:
            self.is_processing = False
            self.send_button.props(remove="loading")

    async def _quick_action(self, action: str):
        """Execute a quick action."""
        if self.input_field is None:
            return
        self.input_field.value = action
        await self._handle_send()

    async def _add_message(
        self, content: str, role: str, name: str, color: Optional[str] = None
    ) -> Optional[ui.card]:
        """Add a message to the chat history."""
        # CORRECTED: Added a "None check" for chat_history. This protects both the
        # 'with' statement and the 'scroll_to' call later.
        if self.chat_history is None:
            return None

        message_card = None
        with self.chat_history:
            timestamp = time.strftime("%H:%M:%S")

            with ui.card().classes("w-full") as card:
                message_card = card
                with ui.row().classes("w-full justify-between items-start"):
                    with ui.column().classes("flex-grow"):
                        ui.label(f"{name} • {timestamp}").classes(
                            "text-sm text-gray-500 mb-1"
                        )

                        # Format content based on type
                        if content.startswith("```") and content.endswith("```"):
                            code = content[3:-3].strip()
                            ui.code(code).classes("w-full")
                        elif "\n" in content and any(
                            keyword in content.lower()
                            for keyword in ["stdout:", "stderr:", "exit code:"]
                        ):
                            ui.code(content).classes("w-full")
                        else:
                            ui.markdown(content).classes("w-full")

                    # Message actions
                    with ui.column().classes("gap-1"):
                        if role == "assistant":
                            ui.button(
                                icon="content_copy",
                                on_click=lambda c=content: ui.clipboard.write(c),
                            ).props("flat dense size=sm")

        # Auto-scroll to bottom
        await asyncio.sleep(0.1)
        self.chat_history.scroll_to(percent=1.0)
        return message_card

    async def _update_status(self):
        """Update service status indicators."""
        try:
            # Check Fabric status
            fabric_health = await self.app.fabric_client.health_check()
            if fabric_health["status"] == "healthy":
                self.fabric_status.props("color=green")
                self.fabric_status.text = "Fabric ✓"
            else:
                self.fabric_status.props("color=red")
                self.fabric_status.text = "Fabric ✗"

            # Check Agtsdbx status
            async with self.app.agtsdbx_client as client:
                agtsdbx_health = await client.health_check()
                if agtsdbx_health["status"] == "healthy":
                    self.agtsdbx_status.props("color=green")
                    self.agtsdbx_status.text = "Agtsdbx ✓"
                else:
                    self.agtsdbx_status.props("color=red")
                    self.agtsdbx_status.text = "Agtsdbx ✗"

        except Exception:
            self.fabric_status.props("color=orange")
            self.fabric_status.text = "Fabric ?"
            self.agtsdbx_status.props("color=orange")
            self.agtsdbx_status.text = "Agtsdbx ?"
