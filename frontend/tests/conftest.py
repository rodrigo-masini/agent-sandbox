import asyncio
import os
import sys
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Mock NiceGUI before importing any app code
sys.modules["nicegui"] = MagicMock()
mock_ui = MagicMock()
mock_ui.run = Mock(return_value=None)
mock_ui.page = Mock(return_value=lambda f: f)
mock_ui.label = Mock()
mock_ui.button = Mock()
mock_ui.input = Mock()
mock_ui.column = Mock()
mock_ui.row = Mock()
mock_ui.card = Mock()
mock_ui.notify = Mock()
mock_ui.dark_mode = Mock(return_value=Mock(enable=Mock()))
mock_ui.header = Mock()
mock_ui.footer = Mock()
mock_ui.splitter = Mock()
mock_ui.space = Mock()
mock_ui.badge = Mock()
mock_ui.menu = Mock()
mock_ui.menu_item = Mock()
mock_ui.separator = Mock()
mock_ui.switch = Mock()
mock_ui.scroll_area = Mock()
mock_ui.dialog = Mock()
mock_ui.tabs = Mock()
mock_ui.tab = Mock()
mock_ui.tab_panels = Mock()
mock_ui.tab_panel = Mock()
mock_ui.timer = Mock()
mock_ui.navigate = Mock(to=Mock())

# CORRECTED: Added '# type: ignore' to tell mypy that we are intentionally
# modifying the mock module, which is a dynamic operation it can't understand.
sys.modules["nicegui"].ui = mock_ui  # type: ignore[attr-defined]
sys.modules["nicegui"].run = Mock(return_value=None)  # type: ignore[attr-defined]
sys.modules["nicegui"].app = Mock()  # type: ignore[attr-defined]


# Configure pytest-asyncio
pytest_plugins = ("pytest_asyncio",)


@pytest.fixture(scope="function")
def event_loop():
    """Create an instance of the default event loop for each test."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    # Clean up
    try:
        loop.run_until_complete(loop.shutdown_asyncgens())
    finally:
        loop.close()


@pytest.fixture
def mock_config():
    """Mock configuration."""
    config = Mock()
    config.get = Mock(
        side_effect=lambda key, default=None: {
            "FABRIC_API_KEY": "test_key",
            "FABRIC_ORG_ID": "test_org",
            "FABRIC_PROJECT_ID": "test_project",
            "FABRIC_BASE_URL": "https://api.test.com/v1",
            "FABRIC_MODEL": "test-model",
            "AGTSDBX_BASE_URL": "http://localhost:8000",
            "AGTSDBX_TIMEOUT": 300,
            "FABRIC_TIMEOUT": 300,
            "ENABLE_STREAMING": True,
            "ENABLE_TOOL_CALLING": True,
            "JWT_SECRET": "test_secret",
            "SECRET_KEY": "test_secret",
        }.get(key, default)
    )
    return config


@pytest.fixture
async def mock_agtsdbx_client():
    """Properly configured mock Agtsdbx client."""
    client = AsyncMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    client.execute_command = AsyncMock(
        return_value={"success": True, "stdout": "test", "exit_code": 0}
    )
    client.write_file = AsyncMock(return_value={"success": True})
    client.read_file = AsyncMock(
        return_value={"success": True, "content": "test content"}
    )
    client.list_files = AsyncMock(return_value={"success": True, "files": []})
    client.delete_file = AsyncMock(return_value={"success": True})
    client.get_system_info = AsyncMock(return_value={"success": True, "data": {}})
    client.get_metrics = AsyncMock(return_value={"success": True, "data": {}})
    client.docker_run = AsyncMock(return_value={"success": True})
    client.docker_list = AsyncMock(return_value={"success": True, "containers": []})
    client.network_request = AsyncMock(return_value={"success": True, "data": {}})
    client.health_check = AsyncMock(return_value={"status": "healthy"})
    return client
