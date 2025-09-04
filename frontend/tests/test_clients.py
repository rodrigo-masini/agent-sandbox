import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.clients.fabric_client import FabricClient, FabricConfig
from src.clients.agtsdbx_client import AgtsdbxClient

class TestFabricClient:
    @pytest.fixture
    def fabric_config(self):
        return FabricConfig(
            api_key="test_key",
            org_id="test_org",
            project_id="test_project",
            base_url="https://api.test.com/v1",
            model="test-model",
            timeout=30
        )
    
    @pytest.fixture
    def fabric_client(self, fabric_config):
        return FabricClient(fabric_config)
    
    @pytest.mark.asyncio
    async def test_health_check_healthy(self, fabric_client):
        with patch.object(fabric_client, 'chat_completion', new_callable=AsyncMock) as mock_chat:
            mock_chat.return_value = {
                "choices": [{"message": {"content": "Hello"}}],
                "metadata": {"duration": 0.5}
            }
            
            result = await fabric_client.health_check()
            
            assert result["status"] == "healthy"
            assert "response_time" in result
            mock_chat.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_health_check_unhealthy(self, fabric_client):
        with patch.object(fabric_client, 'chat_completion', new_callable=AsyncMock) as mock_chat:
            mock_chat.side_effect = Exception("Connection error")
            
            result = await fabric_client.health_check()
            
            assert result["status"] == "unhealthy"
            assert "error" in result
            assert "Connection error" in result["error"]
    
    @pytest.mark.asyncio
    async def test_format_response(self, fabric_client):
        mock_response = Mock()
        mock_response.choices = [
            Mock(
                message=Mock(
                    role="assistant",
                    content="Test response",
                    tool_calls=None
                ),
                finish_reason="stop"
            )
        ]
        mock_response.usage = Mock(
            prompt_tokens=10,
            completion_tokens=5,
            total_tokens=15
        )
        mock_response.model = "test-model"
        mock_response.id = "test-id"
        mock_response.created = 1234567890
        
        result = fabric_client._format_response(mock_response, 1.5)
        
        assert len(result["choices"]) == 1
        assert result["choices"][0]["message"]["content"] == "Test response"
        assert result["usage"]["total_tokens"] == 15
        assert result["metadata"]["duration"] == 1.5

class TestAgtsdbxClient:
    @pytest.fixture
    def agtsdbx_client(self):
        return AgtsdbxClient(base_url="http://localhost:8000", timeout=30)
    
    @pytest.mark.asyncio
    async def test_execute_command(self, agtsdbx_client):
        with patch.object(agtsdbx_client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {
                "stdout": "command output",
                "stderr": "",
                "exit_code": 0,
                "success": True
            }
            
            async with agtsdbx_client:
                result = await agtsdbx_client.execute_command("echo test")
            
            assert result["stdout"] == "command output"
            assert result["success"] is True
            assert "metadata" in result
            mock_request.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_write_file(self, agtsdbx_client):
        with patch.object(agtsdbx_client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {"success": True}
            
            async with agtsdbx_client:
                result = await agtsdbx_client.write_file("/test/file.txt", "content")
            
            assert result["success"] is True
            mock_request.assert_called_once_with(
                "POST",
                "/api/v1/file/write",
                json={
                    "filePath": "/test/file.txt",
                    "content": "content",
                    "options": {}
                }
            )
    
    @pytest.mark.asyncio
    async def test_health_check(self, agtsdbx_client):
        with patch.object(agtsdbx_client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {"status": "healthy"}
            
            async with agtsdbx_client:
                result = await agtsdbx_client.health_check()
            
            assert result["status"] == "healthy"
            mock_request.assert_called_once_with("GET", "/health", timeout=10)
    
    @pytest.mark.asyncio
    async def test_retry_logic(self, agtsdbx_client):
        with patch('httpx.AsyncClient.request', new_callable=AsyncMock) as mock_request:
            mock_response = Mock()
            mock_response.raise_for_status = Mock()
            mock_response.headers = {"content-type": "application/json"}
            mock_response.json = Mock(return_value={"success": True})
            
            # Fail twice, then succeed
            mock_request.side_effect = [
                Exception("Network error"),
                Exception("Network error"),
                mock_response
            ]
            
            async with agtsdbx_client:
                agtsdbx_client.session = AsyncMock()
                agtsdbx_client.session.request = mock_request
                
                with patch('asyncio.sleep', new_callable=AsyncMock):
                    result = await agtsdbx_client._make_request("GET", "/test")
            
            assert result["success"] is True
            assert mock_request.call_count == 3