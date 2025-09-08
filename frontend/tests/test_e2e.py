import pytest
import asyncio
import sys
import os
from unittest.mock import Mock, patch, AsyncMock, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock the app module before importing
with patch('src.app.main.Config') as MockConfig:
    mock_config = Mock()
    mock_config.get = Mock(side_effect=lambda key, default=None: {
        "FABRIC_API_KEY": "test_key",
        "FABRIC_ORG_ID": "test_org",
        "FABRIC_PROJECT_ID": "test_project",
        "FABRIC_BASE_URL": "https://api.test.com/v1",
        "FABRIC_MODEL": "test-model",
        "AGTSDBX_BASE_URL": "http://localhost:8000",
        "AGTSDBX_TIMEOUT": 300,
        "FABRIC_TIMEOUT": 300,
    }.get(key, default))
    MockConfig.return_value = mock_config

# Now safe to import
from src.app.main import AgtsdbxApp


@pytest.fixture
async def mock_app():
    """Create a properly mocked app instance."""
    # Create app instance
    app = AgtsdbxApp()
    
    # Mock the config
    mock_config = Mock()
    mock_config.get = Mock(side_effect=lambda key, default=None: {
        "FABRIC_API_KEY": "test_key",
        "FABRIC_ORG_ID": "test_org",
        "FABRIC_PROJECT_ID": "test_project",
        "FABRIC_BASE_URL": "https://api.test.com/v1",
        "FABRIC_MODEL": "test-model",
        "AGTSDBX_BASE_URL": "http://localhost:8000",
        "AGTSDBX_TIMEOUT": 300,
        "FABRIC_TIMEOUT": 300,
    }.get(key, default))
    app.config = mock_config
    
    # Mock fabric client
    mock_fabric_client = AsyncMock()
    mock_fabric_client.health_check = AsyncMock(return_value={"status": "healthy"})
    mock_fabric_client.chat_completion = AsyncMock()
    app.fabric_client = mock_fabric_client
    
    # Mock agtsdbx client
    mock_agtsdbx_client = AsyncMock()
    mock_agtsdbx_client.health_check = AsyncMock(return_value={"status": "healthy"})
    mock_agtsdbx_client.__aenter__ = AsyncMock(return_value=mock_agtsdbx_client)
    mock_agtsdbx_client.__aexit__ = AsyncMock(return_value=None)
    app.agtsdbx_client = mock_agtsdbx_client
    
    # Mock tools
    app.tools = {
        "execution": Mock(),
        "file": Mock(),
        "system": Mock(),
        "docker": Mock(),
        "network": Mock(),
    }
    
    # Initialize messages
    app.messages = []
    
    return app  # Return, not yield, for a regular async fixture


class TestE2EWorkflows:
    @pytest.mark.asyncio
    async def test_complete_tool_execution_workflow(self, mock_app):
        """Test the complete workflow from user message to tool execution."""
        app = mock_app  # Get the app from fixture
        
        # Setup mock responses
        app.fabric_client.chat_completion.side_effect = [
            # First call returns tool request
            {
                "choices": [{
                    "message": {
                        "content": None,
                        "tool_calls": [{
                            "id": "call_123",
                            "type": "function",
                            "function": {
                                "name": "execute_shell_command",
                                "arguments": '{"command": "echo test"}'
                            }
                        }]
                    }
                }]
            },
            # Second call returns final response
            {
                "choices": [{
                    "message": {
                        "content": "I've executed the echo command for you."
                    }
                }]
            }
        ]
        
        # Mock tool execution
        with patch.object(app, '_execute_tool', new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = "Command executed successfully: test"
            
            response = await app.send_message("Run echo test")
            
            assert "executed the echo command" in response
            mock_execute.assert_called_once_with("execute_shell_command", {"command": "echo test"})
    
    @pytest.mark.asyncio
    async def test_multiple_tool_calls_in_sequence(self, mock_app):
        """Test handling multiple tool calls in a single request."""
        app = mock_app
        
        tool_calls = [
            {
                "id": "call_1",
                "function": {
                    "name": "write_file",
                    "arguments": '{"file_path": "/test.txt", "content": "test"}'
                }
            },
            {
                "id": "call_2",
                "function": {
                    "name": "read_file",
                    "arguments": '{"file_path": "/test.txt"}'
                }
            }
        ]
        
        with patch.object(app, '_execute_tool', new_callable=AsyncMock) as mock_execute:
            mock_execute.side_effect = [
                "File written successfully",
                "File content: test"
            ]
            
            responses = await app.handle_tool_calls(tool_calls)
            
            assert len(responses) == 2
            assert responses[0]["tool_call_id"] == "call_1"
            assert "File written successfully" in responses[0]["content"]
            assert responses[1]["tool_call_id"] == "call_2"
            assert "File content: test" in responses[1]["content"]
    
    @pytest.mark.asyncio
    async def test_tool_execution_error_handling(self, mock_app):
        """Test error handling when tool execution fails."""
        app = mock_app
        
        tool_calls = [
            {
                "id": "call_error",
                "function": {
                    "name": "nonexistent_tool",
                    "arguments": '{}'
                }
            }
        ]
        
        responses = await app.handle_tool_calls(tool_calls)
        
        assert len(responses) == 1
        assert "Tool execution failed" in responses[0]["content"]
        assert responses[0]["tool_call_id"] == "call_error"