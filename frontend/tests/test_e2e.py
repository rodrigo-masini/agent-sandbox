import pytest
import asyncio
import sys
import os
from unittest.mock import Mock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.app.main import AgtsdbxApp
from src.clients.fabric_client import FabricConfig

@pytest.mark.asyncio
class TestE2EWorkflows:
    @pytest.fixture
    async def app(self):
        # Mock config
        with patch('src.app.main.Config') as MockConfig:
            mock_config = Mock()
            mock_config.get = Mock(side_effect=lambda key, default=None: {
                "FABRIC_API_KEY": "test_key",
                "FABRIC_ORG_ID": "test_org",
                "FABRIC_PROJECT_ID": "test_project",
                "FABRIC_BASE_URL": "https://api.test.com/v1",
                "FABRIC_MODEL": "test-model",
                "AGTSDBX_BASE_URL": "http://localhost:8000"
            }.get(key, default))
            
            MockConfig.return_value = mock_config
            
            app = AgtsdbxApp()
            await app.initialize()
            return app
    
    async def test_complete_tool_execution_workflow(self, app):
        """Test the complete workflow from user message to tool execution."""
        # Mock the Fabric client response with tool calls
        with patch.object(app.fabric_client, 'chat_completion') as mock_chat:
            # First call returns tool request
            mock_chat.return_value = asyncio.coroutine(lambda: {
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
            })()
            
            # Mock tool execution
            with patch.object(app, '_execute_tool') as mock_execute:
                mock_execute.return_value = asyncio.coroutine(
                    lambda: "Command executed successfully: test"
                )()
                
                # Second call returns final response
                mock_chat.side_effect = [
                    mock_chat.return_value,
                    asyncio.coroutine(lambda: {
                        "choices": [{
                            "message": {
                                "content": "I've executed the echo command for you."
                            }
                        }]
                    })()
                ]
                
                response = await app.send_message("Run echo test")
                
                assert "executed the echo command" in response
                mock_execute.assert_called_once_with("execute_shell_command", {"command": "echo test"})
    
    async def test_multiple_tool_calls_in_sequence(self, app):
        """Test handling multiple tool calls in a single request."""
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
        
        with patch.object(app, '_execute_tool') as mock_execute:
            mock_execute.side_effect = [
                asyncio.coroutine(lambda: "File written successfully")(),
                asyncio.coroutine(lambda: "File content: test")()
            ]
            
            responses = await app.handle_tool_calls(tool_calls)
            
            assert len(responses) == 2
            assert responses[0]["tool_call_id"] == "call_1"
            assert "File written successfully" in responses[0]["content"]
            assert responses[1]["tool_call_id"] == "call_2"
            assert "File content: test" in responses[1]["content"]
    
    async def test_tool_execution_error_handling(self, app):
        """Test error handling when tool execution fails."""
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