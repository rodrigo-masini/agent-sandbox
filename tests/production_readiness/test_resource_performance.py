# tests/production_readiness/test_resource_performance.py
"""
Resource Limits and Performance Tests
Prevents: Out-of-memory kills, CPU throttling, disk space exhaustion
Saves: Money from oversized instances and debugging resource exhaustion
"""

import asyncio
import os
import tempfile
import time
import tracemalloc
from concurrent.futures import ThreadPoolExecutor

import httpx
import psutil
import pytest


class TestResourceLimits:
    """
    Test that the application respects resource constraints.
    These tests prevent your application from being killed by the cloud provider.
    """

    def test_memory_usage_under_limits(self):
        """
        Test that memory usage stays within configured limits.
        This prevents OOM kills which cause mysterious restarts in production.
        """
        # Start memory tracking
        tracemalloc.start()
        initial_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB

        # Simulate typical workload
        self._simulate_workload()

        # Check memory after workload
        peak_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        memory_increase = peak_memory - initial_memory

        # Get configured limit (default 512MB)
        memory_limit = int(os.getenv("CONTAINER_MEMORY_LIMIT", "512"))

        assert peak_memory < memory_limit * 0.8, (
            f"Memory usage ({peak_memory}MB) exceeds 80% of limit ({memory_limit}MB)\n"
            f"Production impact: Container will be killed by orchestrator\n"
            f"Solution: Either optimize memory usage or increase memory limits"
        )

        # Check for memory leaks
        assert memory_increase < 100, (
            f"Memory increased by {memory_increase}MB during workload\n"
            f"Production impact: Memory leak will cause crashes after hours/days\n"
            f"Solution: Fix memory leak in application"
        )

        tracemalloc.stop()

    def _simulate_workload(self):
        """Simulate a typical production workload."""
        # Create some temporary files
        for _ in range(10):
            with tempfile.NamedTemporaryFile(mode="w", delete=True) as f:
                f.write("x" * 1024 * 1024)  # 1MB files

        # Simulate concurrent operations
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = []
            for i in range(20):
                futures.append(executor.submit(self._dummy_operation, i))

            for future in futures:
                future.result()

    def _dummy_operation(self, index):
        """Simulate an operation."""
        time.sleep(0.1)
        return f"Operation {index} complete"

    @pytest.mark.asyncio
    async def test_concurrent_request_handling(self):
        """
        Test that the application handles concurrent requests without degradation.
        This prevents the "works fine with one user, crashes with ten" problem.
        """
        backend_url = os.getenv("AGTSDBX_BASE_URL", "http://localhost:8000")
        concurrent_users = 10  # Reduced for CI environment
        requests_per_user = 5

        async def user_session(user_id: int):
            """Simulate a user session with multiple requests."""
            async with httpx.AsyncClient(timeout=30) as client:
                response_times = []
                errors = []

                for i in range(requests_per_user):
                    try:
                        start = time.time()
                        response = await client.get(f"{backend_url}/health")
                        response_time = time.time() - start
                        response_times.append(response_time)

                        if response.status_code != 200:
                            errors.append(
                                f"User {user_id} request {i}: Status {response.status_code}"
                            )
                    except Exception as e:
                        errors.append(f"User {user_id} request {i}: {str(e)}")

                return response_times, errors

        # Run concurrent user sessions
        tasks = [user_session(i) for i in range(concurrent_users)]
        results = await asyncio.gather(*tasks)

        all_response_times = []
        all_errors = []

        for response_times, errors in results:
            all_response_times.extend(response_times)
            all_errors.extend(errors)

        # Validate results
        if all_errors:
            error_summary = "\n".join(all_errors[:10])
            if len(all_errors) > 10:
                error_summary += f"\n... and {len(all_errors)-10} more"
            assert not all_errors, f"Errors under concurrent load:\n{error_summary}"

        if all_response_times:
            avg_response_time = sum(all_response_times) / len(all_response_times)
            max_response_time = max(all_response_times)

            assert avg_response_time < 2.0, (
                f"Average response time {avg_response_time:.2f}s exceeds 2 seconds\n"
                f"Production impact: Poor user experience, potential timeouts"
            )

            assert max_response_time < 10.0, (
                f"Maximum response time {max_response_time:.2f}s exceeds 10 seconds\n"
                f"Production impact: Request timeouts, user frustration"
            )

    def test_disk_usage_limits(self):
        """
        Test that disk usage stays within reasonable bounds.
        This prevents disk space exhaustion which causes total system failure.
        """
        work_dir = os.getenv("WORKDIR", "backend/WORKDIR")

        # Ensure directory exists
        os.makedirs(work_dir, exist_ok=True)

        # Check available space
        stat = os.statvfs(work_dir)
        available_gb = (stat.f_bavail * stat.f_frsize) / (1024**3)

        # In CI, just warn if space is low
        if available_gb < 1.0:
            pytest.skip(f"Less than 1GB of disk space available ({available_gb:.2f}GB)")

        # Test file creation with size limits
        test_file = os.path.join(work_dir, "test_large_file.dat")
        max_file_size = int(os.getenv("MAX_FILE_SIZE", 10485760))  # 10MB default

        try:
            # Try to create a file at the limit
            with open(test_file, "wb") as f:
                f.write(b"x" * max_file_size)

            # Verify it was created
            assert os.path.getsize(test_file) == max_file_size

            # Clean up
            os.remove(test_file)

        except OSError as e:
            pytest.fail(
                f"Cannot create {max_file_size} byte file: {e}\n"
                f"Production impact: File uploads will fail mysteriously"
            )
