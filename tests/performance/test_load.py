import asyncio
import os
import sys
import time

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))


class TestPerformance:
    """Performance and load testing."""

    @pytest.mark.asyncio
    async def test_concurrent_command_execution(self):
        """Test system handles concurrent command execution properly."""
        from unittest.mock import AsyncMock

        from src.tools.execution_tools import ExecutionTools

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()

        exec_tools = ExecutionTools(mock_client)

        # Simulate delay in execution
        async def delayed_execute(*args, **kwargs):
            await asyncio.sleep(0.1)
            return {"stdout": "output", "exit_code": 0}

        mock_client.execute_command = delayed_execute

        # Execute 20 commands concurrently
        start_time = time.time()

        tasks = [
            exec_tools.execute_parallel_commands(
                commands=[f"echo {i}" for i in range(10)], max_concurrent=5
            )
            for _ in range(2)
        ]

        results = await asyncio.gather(*tasks)

        elapsed = time.time() - start_time

        # Should complete faster than sequential (20 * 0.1 = 2 seconds)
        assert elapsed < 1.0, f"Concurrent execution took too long: {elapsed}s"
        assert all("output" in str(r) for r in results)

    @pytest.mark.asyncio
    async def test_file_operation_performance(self):
        """Test file operations handle large files efficiently."""
        from unittest.mock import AsyncMock

        from src.tools.file_tools import FileTools

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()

        file_tools = FileTools(mock_client)

        # Create a large content (5MB)
        large_content = "x" * (5 * 1024 * 1024)

        mock_client.write_file = AsyncMock(return_value={"success": True})

        start_time = time.time()
        result = await file_tools.write_file(
            file_path="/tmp/large_file.txt", content=large_content
        )
        elapsed = time.time() - start_time

        # Should handle large file in reasonable time
        assert elapsed < 2.0, f"Large file write took too long: {elapsed}s"
        assert "Successfully" in result

    @pytest.mark.asyncio
    async def test_memory_usage_with_multiple_operations(self):
        """Test that memory usage stays reasonable with many operations."""
        import tracemalloc

        tracemalloc.start()

        from unittest.mock import AsyncMock

        from src.tools.execution_tools import ExecutionTools

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        mock_client.execute_command = AsyncMock(
            return_value={"stdout": "ok", "exit_code": 0}
        )

        exec_tools = ExecutionTools(mock_client)

        # Get initial memory
        snapshot1 = tracemalloc.take_snapshot()

        # Execute many operations
        for _ in range(100):
            await exec_tools.execute_shell_command(command="echo test")

        # Get final memory
        snapshot2 = tracemalloc.take_snapshot()

        top_stats = snapshot2.compare_to(snapshot1, "lineno")
        total_memory_increase = sum(stat.size_diff for stat in top_stats)

        # Memory increase should be reasonable (< 10MB)
        assert (
            total_memory_increase < 10 * 1024 * 1024
        ), f"Memory usage increased too much: {total_memory_increase / 1024 / 1024:.2f}MB"

        tracemalloc.stop()
