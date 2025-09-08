import pytest
import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()

@pytest.fixture
async def mock_agtsdbx_client():
    """Properly configured mock client."""
    from unittest.mock import AsyncMock
    
    client = AsyncMock()
    # Properly configure async context manager
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    
    # Configure methods
    client.execute_command = AsyncMock(return_value={"success": True})
    client.write_file = AsyncMock(return_value={"success": True})
    client.read_file = AsyncMock(return_value={"success": True, "content": ""})
    
    yield client
    
    # Cleanup
    await asyncio.sleep(0)  # Allow pending tasks to complete