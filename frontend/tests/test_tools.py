import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.tools.execution_tools import ExecutionTools
from src.tools.file_tools import FileTools
from src.tools.docker_tools import DockerTools
from src.tools.network_tools import NetworkTools
from src.tools.system_tools import SystemTools

class TestExecutionTools:
    @pytest.fixture
    def mock_client(self):
        client = AsyncMock()
        return client
    
    @pytest.fixture
    def exec_tools(self, mock_client):
        return ExecutionTools(mock_client)
    
    @pytest.mark.asyncio
    async def test_execute_shell_command_success(self, exec_tools, mock_client):
        mock_client.execute_command = AsyncMock(return_value={
            "stdout": "test output",
            "stderr": "",
            "exit_code": 0,
            "success": True,
            "metadata": {"duration": 0.5}
        })
        
        # Need to use async context manager
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        
        result = await exec_tools.execute_shell_command(command="echo test")
        
        assert "STDOUT:\ntest output" in result
        assert "EXIT CODE: 0" in result
        mock_client.execute_command.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_script_builds_correct_command(self, exec_tools, mock_client):
        mock_client.execute_command = AsyncMock(return_value={
            "stdout": "script output",
            "exit_code": 0
        })
        
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        
        result = await exec_tools.execute_script(
            script_path="/path/script.py",
            interpreter="python3",
            arguments=["--arg1", "value1"]
        )
        
        # Check that the command was built correctly
        expected_command = "python3 /path/script.py --arg1 value1"
        mock_client.execute_command.assert_called_with(
            expected_command,
            {"timeout": 300}
        )
    
    @pytest.mark.asyncio
    async def test_execute_parallel_commands(self, exec_tools, mock_client):
        commands = ["echo 1", "echo 2", "echo 3"]
        
        async def mock_execute(cmd, options):
            return {"stdout": f"output for {cmd}", "exit_code": 0}
        
        mock_client.execute_command = mock_execute
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        
        result = await exec_tools.execute_parallel_commands(
            commands=commands,
            max_concurrent=2
        )
        
        for i, cmd in enumerate(commands, 1):
            assert f"Command {i}: {cmd}" in result
            assert f"output for {cmd}" in result

class TestFileTools:
    @pytest.fixture
    def file_tools(self):
        mock_client = AsyncMock()
        return FileTools(mock_client)
    
    @pytest.mark.asyncio
    async def test_write_file_success(self, file_tools):
        mock_client = file_tools.agtsdbx_client
        mock_client.write_file = AsyncMock(return_value={"success": True})
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        
        result = await file_tools.write_file(
            file_path="/test/file.txt",
            content="test content",
            append=False
        )
        
        assert "Successfully wrote to file" in result
        mock_client.write_file.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_read_file_formats_output(self, file_tools):
        mock_client = file_tools.agtsdbx_client
        mock_client.read_file = AsyncMock(return_value={
            "success": True,
            "content": "file contents here"
        })
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        
        result = await file_tools.read_file(file_path="/test/file.txt")
        
        assert "File contents of /test/file.txt:" in result
        assert "file contents here" in result
    
    # Find and replace the test_delete_file_handles_errors method
    @pytest.mark.asyncio
    async def test_delete_file_handles_errors(self, file_tools):
        mock_client = file_tools.agtsdbx_client
        mock_client.delete_file = AsyncMock(side_effect=Exception("Permission denied"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        # FIX: Explicitly return None or False to not suppress exceptions
        mock_client.__aexit__ = AsyncMock(return_value=None)
        
        result = await file_tools.delete_file(file_path="/protected/file.txt")
        
        assert "Error deleting file" in result
        assert "Permission denied" in result

class TestDockerTools:
    @pytest.fixture
    def docker_tools(self):
        mock_client = AsyncMock()
        return DockerTools(mock_client)
    
    @pytest.mark.asyncio
    async def test_docker_run_with_options(self, docker_tools):
        mock_client = docker_tools.agtsdbx_client
        mock_client.docker_run = AsyncMock(return_value={
            "success": True,
            "container_id": "abc123"
        })
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        
        result = await docker_tools.docker_run(
            image="python:3.11-slim",
            command="python --version",
            name="test-container",
            detached=True,
            environment={"ENV_VAR": "value"},
            ports={"8080": "80"}
        )
        
        assert "Successfully started container: abc123" in result
        assert "Image: python:3.11-slim" in result
        
        # Verify options were passed correctly
        mock_client.docker_run.assert_called_with(
            "python:3.11-slim",
            "python --version",
            {
                "command": "python --version",
                "name": "test-container",
                "detached": True,
                "environment": {"ENV_VAR": "value"},
                "ports": {"8080": "80"},
                "volumes": {}
            }
        )
    
    @pytest.mark.asyncio
    async def test_docker_list_formats_output(self, docker_tools):
        mock_client = docker_tools.agtsdbx_client
        mock_client.docker_list = AsyncMock(return_value={
            "success": True,
            "containers": [
                {"id": "abc123", "image": "nginx", "status": "running", "name": "web"},
                {"id": "def456", "image": "redis", "status": "stopped", "name": "cache"}
            ]
        })
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        
        result = await docker_tools.docker_list(all=True, format="table")
        
        assert "CONTAINER ID" in result
        assert "abc123" in result
        assert "nginx" in result
        assert "web" in result

class TestNetworkTools:
    @pytest.fixture
    def network_tools(self):
        mock_client = AsyncMock()
        return NetworkTools(mock_client)
    
    @pytest.mark.asyncio
    async def test_http_request_formats_response(self, network_tools):
        mock_client = network_tools.agtsdbx_client
        mock_client.network_request = AsyncMock(return_value={
            "success": True,
            "data": {
                "status_code": 200,
                "body": "Response body content"
            }
        })
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        
        result = await network_tools.http_request(
            url="https://api.example.com",
            method="GET",
            headers={"Accept": "application/json"}
        )
        
        assert "HTTP GET https://api.example.com" in result
        assert "Status: 200" in result
        assert "Response body content" in result
    
    @pytest.mark.asyncio
    async def test_check_port_open(self, network_tools):
        mock_client = network_tools.agtsdbx_client
        mock_client.execute_command = AsyncMock(return_value={"exit_code": 0})
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        
        result = await network_tools.check_port(host="example.com", port=80)
        
        assert "Port 80 on example.com is OPEN" in result
    
    @pytest.mark.asyncio
    async def test_dns_lookup_handles_no_records(self, network_tools):
        mock_client = network_tools.agtsdbx_client
        mock_client.execute_command = AsyncMock(return_value={
            "exit_code": 0,
            "stdout": ""
        })
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        
        result = await network_tools.dns_lookup(domain="nonexistent.example", record_type="A")
        
        assert "No A records found for nonexistent.example" in result

class TestSystemTools:
    @pytest.fixture
    def system_tools(self):
        mock_client = AsyncMock()
        return SystemTools(mock_client)
    
    @pytest.mark.asyncio
    async def test_get_system_info_formats_correctly(self, system_tools):
        mock_client = system_tools.agtsdbx_client
        mock_client.get_system_info = AsyncMock(return_value={
            "success": True,
            "data": {
                "os": {"type": "Linux", "version": "5.15"},
                "memory": {"total": 16000000000, "free": 8000000000},
                "cpu": {"cores": 8, "model": "Intel i7"}
            }
        })
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        
        result = await system_tools.get_system_info()
        
        assert "System Information:" in result
        assert "OS:" in result
        assert "type: Linux" in result
        assert "MEMORY:" in result
    
    @pytest.mark.asyncio
    async def test_check_network_connectivity(self, system_tools):
        mock_client = system_tools.agtsdbx_client
        
        # Mock responses for different hosts
        def execute_side_effect(command):
            if "8.8.8.8" in command:
                return {"exit_code": 0}
            elif "1.1.1.1" in command:
                return {"exit_code": 0}
            else:
                return {"exit_code": 1}
        
        mock_client.execute_command = AsyncMock(side_effect=execute_side_effect)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        
        result = await system_tools.check_network_connectivity(
            hosts=["8.8.8.8", "1.1.1.1", "unreachable.local"]
        )
        
        assert "✓ 8.8.8.8: Reachable" in result
        assert "✓ 1.1.1.1: Reachable" in result
        assert "✗ unreachable.local: Unreachable" in result