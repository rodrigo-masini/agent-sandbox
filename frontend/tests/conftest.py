import pytest
import sys
import os
from unittest.mock import MagicMock, Mock

# Add parent directory to path BEFORE any imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock NiceGUI before importing any app code
sys.modules['nicegui'] = MagicMock()
mock_ui = MagicMock()
mock_ui.run = Mock(return_value=None)  # Prevent ui.run() from blocking
mock_ui.page = Mock(return_value=lambda f: f)
mock_ui.label = Mock()
mock_ui.button = Mock()
mock_ui.input = Mock()
mock_ui.column = Mock()
mock_ui.row = Mock()
mock_ui.card = Mock()
mock_ui.notify = Mock()
sys.modules['nicegui'].ui = mock_ui
sys.modules['nicegui'].run = Mock(return_value=None)

# Now safe to import app modules
import asyncio

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()

@pytest.fixture
def mock_config():
    """Mock configuration."""
    from unittest.mock import Mock
    config = Mock()
    config.get = Mock(side_effect=lambda key, default=None: {
        "FABRIC_API_KEY": "test_key",
        "FABRIC_ORG_ID": "test_org",
        "FABRIC_PROJECT_ID": "test_project",
        "FABRIC_BASE_URL": "https://api.test.com/v1",
        "FABRIC_MODEL": "test-model",
        "AGTSDBX_BASE_URL": "http://localhost:8000",
        "ENABLE_STREAMING": True,
        "ENABLE_TOOL_CALLING": True,
    }.get(key, default))
    return config