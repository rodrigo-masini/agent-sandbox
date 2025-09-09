# ==============================================
# MAIN LAYOUT IMPLEMENTATION
# ==============================================

from nicegui import ui


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

        with ui.header(elevated=True).classes("items-center justify-between"):
            with ui.row().classes("items-center gap-4"):
                ui.button(icon="menu", on_click=self.toggle_sidebar).props(
                    "flat color=white"
                )
                ui.label("Agent Sandbox").classes("text-xl font-bold")

            with ui.row().classes("items-center gap-2"):
                # Status indicators
                ui.badge("AI Connected", color="green").classes("text-xs")
                ui.badge("System Ready", color="green").classes("text-xs")

                # User menu
                with ui.button(icon="account_circle").props("flat color=white"):
                    with ui.menu() as _:
                        ui.menu_item("Profile", on_click=lambda: ui.notify("Profile"))
                        ui.menu_item("Settings", on_click=lambda: self.show_settings())
                        ui.separator()
                        ui.menu_item("Logout", on_click=lambda: ui.navigate.to("/"))

        with ui.splitter(value=20).classes("w-full") as splitter:
            # Sidebar
            with splitter.before:
                await self.render_sidebar()

            # Main content
            with splitter.after:
                self.content_container = ui.column().classes("w-full h-full p-4")
                await self.render_content()

        # Footer
        with ui.footer().classes("bg-gray-900 text-gray-400 text-xs"):
            ui.label("© 2025 Agents Sandbox - AI-Powered System Interface")

    async def render_sidebar(self):
        """Render the sidebar navigation."""
        with ui.column().classes("h-full bg-gray-900 p-2"):
            ui.label("Navigation").classes("text-sm text-gray-400 mb-2")

            nav_items = [
                ("chat", "chat", "AI Assistant"),
                ("folder", "files", "File Browser"),
                ("terminal", "terminal", "Terminal"),
                ("monitoring", "monitor", "System Monitor"),
                ("memory", "docker", "Docker"),
                ("network_check", "network", "Network"),
                ("storage", "database", "Database"),
            ]

            for icon, view, label in nav_items:
                is_active = self.current_view == view
                button = ui.button(
                    label if self.sidebar_expanded else "",
                    on_click=lambda v=view: self.switch_view(v),
                ).props(f"{'color=primary' if is_active else 'flat'}")

                if not self.sidebar_expanded:
                    button.props("icon=" + icon)
                else:
                    with button:
                        with ui.row().classes("items-center gap-2"):
                            ui.icon(icon)
                            ui.label(label)

            ui.space()
            ui.button(
                "Settings" if self.sidebar_expanded else "",
                icon="settings",
                on_click=self.show_settings,
            ).props("flat")

    async def render_content(self):
        """Render the main content area based on current view."""
        with self.content_container:
            self.content_container.clear()

            if self.current_view == "chat":
                from ..components.chat import ChatComponent

                chat = ChatComponent(self.app)
                await chat.render()
            elif self.current_view == "files":
                from ..components.file_browser import FileBrowserComponent

                browser = FileBrowserComponent(self.app)
                await browser.render()
            elif self.current_view == "terminal":
                from ..components.terminal import TerminalComponent

                terminal = TerminalComponent(self.app)
                await terminal.render()
            elif self.current_view == "monitor":
                from ..components.system_monitor import SystemMonitorComponent

                monitor = SystemMonitorComponent(self.app)
                await monitor.render()
            elif self.current_view == "docker":
                await self.render_docker_view()
            elif self.current_view == "network":
                await self.render_network_view()
            elif self.current_view == "database":
                await self.render_database_view()
            else:
                ui.label(f"View not implemented: {self.current_view}")

    async def switch_view(self, view: str):
        self.current_view = view
        await self.render_content()

    def toggle_sidebar(self):
        self.sidebar_expanded = not self.sidebar_expanded
        ui.notify(
            f"Sidebar {'expanded' if self.sidebar_expanded else 'collapsed'}",
            position="bottom",
        )

    def show_settings(self):
        with ui.dialog() as dialog, ui.card():
            ui.label("Settings").classes("text-xl mb-4")
            with ui.tabs().classes("w-full") as tabs:
                general_tab, api_tab, security_tab = "General", "API", "Security"
            with ui.tab_panels(tabs, value=general_tab).classes("w-full"):
                with ui.tab_panel(general_tab):
                    ui.label("Theme")
                    ui.switch("Dark Mode", value=True)
                    ui.label("Chat Settings")
                    ui.slider(min=0, max=2, value=0.7, step=0.1, label="Temperature")
                    ui.number("Max Tokens", value=2000, min=100, max=4000)
                with ui.tab_panel(api_tab):
                    ui.label("Fabric API")
                    ui.input("API Key", password=True, value="****")
                    ui.input("Org ID", value=self.app.config.get("FABRIC_ORG_ID"))
                    ui.input(
                        "Project ID", value=self.app.config.get("FABRIC_PROJECT_ID")
                    )
                with ui.tab_panel(security_tab):
                    ui.label("Security Settings")
                    ui.switch("Enable Command Whitelist", value=False)
                    ui.switch("Enable Rate Limiting", value=True)
                    ui.number("Rate Limit (requests/min)", value=60)
            with ui.row():
                ui.button("Save", on_click=lambda: self.save_settings(dialog))
                ui.button("Cancel", on_click=dialog.close)
        dialog.open()

    def save_settings(self, dialog):
        ui.notify("Settings saved", type="positive")
        dialog.close()

    async def render_docker_view(self):
        ui.label("Docker Management").classes("text-2xl mb-4")
        with ui.row().classes("gap-2 mb-4"):
            ui.button("List", icon="list", on_click=self.list_docker_containers)
            ui.button("Pull Image", icon="download", on_click=self.pull_docker_image)
            ui.button("Run", icon="play_arrow", on_click=self.run_docker_container)
        self.docker_container = ui.column().classes("w-full")
        await self.list_docker_containers()

    async def render_network_view(self):
        ui.label("Network Tools").classes("text-2xl mb-4")
        with ui.row().classes("gap-2 mb-4"):
            ui.button("HTTP Request", icon="http", on_click=self.show_http_dialog)
            ui.button("Port Scan", icon="security", on_click=self.show_port_scanner)
            ui.button("DNS Lookup", icon="dns", on_click=self.show_dns_lookup)
        self.network_results = ui.column().classes("w-full")

    async def render_database_view(self):
        ui.label("Database Tools").classes("text-2xl mb-4")
        with ui.row().classes("gap-2 mb-4"):
            ui.button("Execute Query", icon="code", on_click=self.show_query_dialog)
            ui.button("Backup", icon="backup", on_click=self.show_backup_dialog)
        self.db_results = ui.column().classes("w-full")

    async def list_docker_containers(self):
        self.docker_container.clear()
        with self.docker_container:
            ui.label("Loading containers...").classes("text-gray-500")
        try:
            from ...tools.docker_tools import DockerTools

            docker = DockerTools(self.app.agtsdbx_client)
            result = await docker.docker_list(all=True, format="table")
            self.docker_container.clear()
            with self.docker_container:
                ui.code(result).classes("w-full")
        except Exception as e:
            self.docker_container.clear()
            with self.docker_container:
                ui.label(f"Error: {str(e)}").classes("text-red-500")

    def pull_docker_image(self):
        with ui.dialog() as dialog, ui.card():
            ui.label("Pull Docker Image").classes("text-xl mb-4")
            image_input = ui.input("Image Name", placeholder="e.g., ubuntu:22.04")

            async def do_pull():
                image_name = image_input.value
                if image_name:
                    ui.notify(f"Pulling {image_name}...", type="ongoing")
                    dialog.close()
                else:
                    ui.notify("Please enter an image name.", type="warning")

            with ui.row():
                ui.button("Pull", on_click=do_pull)
                ui.button("Cancel", on_click=dialog.close)
        dialog.open()

    def run_docker_container(self):
        with ui.dialog() as dialog, ui.card():
            ui.label("Run Docker Container").classes("text-xl mb-4")
            image_input = ui.input("Image", placeholder="ubuntu:22.04")
            name_input = ui.input("Container Name", placeholder="my-container")
            command_input = ui.input("Command", placeholder="bash")

            async def do_run():
                image = image_input.value
                name = name_input.value
                command = command_input.value  # CORRECTED: Now used in the notification
                if image:
                    msg = (
                        f"Running container '{name or image}' with command '{command}'"
                    )
                    ui.notify(msg, type="ongoing")
                    dialog.close()
                else:
                    ui.notify("Image name is required.", type="warning")

            with ui.row():
                ui.button("Run", on_click=do_run)
                ui.button("Cancel", on_click=dialog.close)
        dialog.open()

    def show_http_dialog(self):
        with ui.dialog() as dialog, ui.card().classes("w-96"):
            ui.label("HTTP Request").classes("text-xl mb-4")
            url_input = ui.input("URL", placeholder="https://api.example.com")
            method_select = ui.select(
                ["GET", "POST", "PUT", "DELETE"], value="GET", label="Method"
            )
            headers_input = ui.textarea(
                "Headers (JSON)", placeholder='{"Content-Type": "application/json"}'
            )
            body_input = ui.textarea("Body", placeholder="Request body...")

            async def do_send_request():
                url = url_input.value
                # CORRECTED: Read values from headers and body inputs
                headers = headers_input.value
                body = body_input.value
                if url:
                    msg = f"Sending {method_select.value} to {url}"
                    ui.notify(msg, type="ongoing")
                    # You can now use 'headers' and 'body' in your implementation
                    print(f"Headers: {headers}, Body: {body}")
                    dialog.close()
                else:
                    ui.notify("URL is required.", type="warning")

            with ui.row():
                ui.button("Send", on_click=do_send_request)
                ui.button("Cancel", on_click=dialog.close)
        dialog.open()

    def show_port_scanner(self):
        with ui.dialog() as dialog, ui.card():
            ui.label("Port Scanner").classes("text-xl mb-4")
            host_input = ui.input("Host", placeholder="example.com")
            port_input = ui.input("Port", placeholder="80")

            async def do_scan():
                host = host_input.value
                port = port_input.value
                if host and port:
                    ui.notify(f"Scanning port {port} on {host}...", type="ongoing")
                    dialog.close()
                else:
                    ui.notify("Host and Port are required.", type="warning")

            with ui.row():
                ui.button("Scan", on_click=do_scan)
                ui.button("Cancel", on_click=dialog.close)
        dialog.open()

    def show_dns_lookup(self):
        with ui.dialog() as dialog, ui.card():
            ui.label("DNS Lookup").classes("text-xl mb-4")
            domain_input = ui.input("Domain", placeholder="example.com")
            type_select = ui.select(
                ["A", "AAAA", "MX", "TXT", "NS", "CNAME"],
                value="A",
                label="Record Type",
            )

            async def do_lookup():
                domain = domain_input.value
                record_type = type_select.value
                if domain:
                    ui.notify(
                        f"Looking up {record_type} for {domain}...", type="ongoing"
                    )
                    dialog.close()
                else:
                    ui.notify("Domain is required.", type="warning")

            with ui.row():
                ui.button("Lookup", on_click=do_lookup)
                ui.button("Cancel", on_click=dialog.close)
        dialog.open()

    def show_query_dialog(self):
        with ui.dialog() as dialog, ui.card().classes("w-96"):
            ui.label("Execute SQL Query").classes("text-xl mb-4")
            db_select = ui.select(
                ["sqlite", "postgresql", "mysql"], value="sqlite", label="Database Type"
            )
            conn_input = ui.input("Connection String", placeholder="database.db")
            query_input = ui.textarea("SQL Query", placeholder="SELECT * FROM table")

            async def do_execute():
                conn = conn_input.value
                query = query_input.value
                if conn and query:
                    ui.notify(
                        f"Executing query on {db_select.value}...", type="ongoing"
                    )
                    dialog.close()
                else:
                    ui.notify("Connection and Query are required.", type="warning")

            with ui.row():
                ui.button("Execute", on_click=do_execute)
                ui.button("Cancel", on_click=dialog.close)
        dialog.open()

    def show_backup_dialog(self):
        with ui.dialog() as dialog, ui.card():
            ui.label("Backup Database").classes("text-xl mb-4")
            db_select = ui.select(
                ["sqlite", "postgresql", "mysql"], value="sqlite", label="Database Type"
            )
            source_input = ui.input("Source Database", placeholder="database.db")
            output_input = ui.input("Backup Path", placeholder="backup.sql")

            async def do_backup():
                source = source_input.value
                output = output_input.value
                db_type = db_select.value  # CORRECTED: Read the value from the select
                if source and output:
                    ui.notify(
                        f"Backing up {db_type} database {source}...", type="ongoing"
                    )
                    dialog.close()
                else:
                    ui.notify("Source and Output Path are required.", type="warning")

            with ui.row():
                ui.button("Backup", on_click=do_backup)
                ui.button("Cancel", on_click=dialog.close)
        dialog.open()
