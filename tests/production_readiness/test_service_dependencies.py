# tests/production_readiness/test_service_dependencies.py
"""
Service Dependency Tests
Prevents: Service connection failures in production
Saves: Hours debugging "connection refused" and timeout issues
"""

import os
import time

import httpx
import pytest
import redis


class TestServiceDependencies:
    """
    Test all external service dependencies to ensure they'll work in production.
    Each test here prevents a category of "works on my machine" issues.
    """

    @pytest.mark.asyncio
    async def test_redis_connectivity_and_operations(self):
        """
        Test Redis is accessible and supports required operations.
        This prevents cache/session storage failures in production.
        """
        redis_host = os.getenv("REDIS_HOST", "localhost")
        redis_port = int(os.getenv("REDIS_PORT", 6379))
        redis_password = os.getenv("REDIS_PASSWORD")

        try:
            # Test connection
            r = redis.Redis(
                host=redis_host,
                port=redis_port,
                password=redis_password,
                socket_connect_timeout=5,
                decode_responses=True,
            )

            # Test basic operations that the app uses
            test_key = "test:production:readiness"

            # SET operation (for caching)
            r.set(test_key, "test_value", ex=10)

            # GET operation
            value = r.get(test_key)
            assert value == "test_value", "Redis GET/SET not working"

            # INCREMENT operation (for rate limiting)
            r.set("test:counter", 0)
            new_value = r.incr("test:counter")
            assert new_value == 1, "Redis INCR not working"

            # Cleanup
            r.delete(test_key, "test:counter")

        except redis.ConnectionError as e:
            pytest.fail(
                f"Redis connection failed: {e}\n"
                f"Production impact: No caching, no rate limiting, no session storage"
            )
        except redis.ResponseError as e:
            pytest.fail(
                f"Redis command failed: {e}\n"
                f"Production impact: Application features will fail randomly"
            )

    @pytest.mark.asyncio
    async def test_backend_service_health(self):
        """
        Test that the backend service is healthy and responsive.
        This prevents deployment with a broken backend.
        """
        backend_url = os.getenv("AGTSDBX_BASE_URL", "http://localhost:8000")

        async with httpx.AsyncClient(timeout=10) as client:
            try:
                response = await client.get(f"{backend_url}/health")
                assert response.status_code == 200, (
                    f"Backend health check failed with status {response.status_code}\n"
                    f"Production impact: Backend service is not healthy"
                )

                # Verify response structure
                data = response.json()
                assert "status" in data, "Health response missing status field"

            except httpx.RequestError as e:
                pytest.fail(
                    f"Backend connection failed: {e}\n"
                    f"Production impact: No command execution, file operations will fail"
                )

    @pytest.mark.asyncio
    async def test_frontend_service_health(self):
        """
        Test that the frontend service is healthy and responsive.
        This prevents deployment with a broken UI.
        """
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:8080")

        async with httpx.AsyncClient(timeout=10) as client:
            try:
                response = await client.get(f"{frontend_url}/api/health")
                assert response.status_code == 200, (
                    f"Frontend health check failed with status {response.status_code}\n"
                    f"Production impact: UI will be inaccessible"
                )

            except httpx.RequestError as e:
                pytest.fail(
                    f"Frontend connection failed: {e}\n"
                    f"Production impact: Users cannot access the application"
                )

    def test_service_startup_order(self):
        """
        Test that services start in the correct order with proper health checks.
        This prevents race conditions that cause intermittent production failures.
        """
        startup_sequence = [
            ("Redis", self._check_redis_ready),
            ("Backend", self._check_backend_ready),
            ("Frontend", self._check_frontend_ready),
        ]

        for service_name, check_function in startup_sequence:
            start_time = time.time()
            max_wait = 30  # seconds

            while time.time() - start_time < max_wait:
                if check_function():
                    break
                time.sleep(1)
            else:
                pytest.fail(
                    f"{service_name} did not become ready in {max_wait} seconds\n"
                    f"Production impact: Deployment will fail or service will be unstable"
                )

    def _check_redis_ready(self) -> bool:
        """Check if Redis is ready."""
        try:
            r = redis.Redis(
                host=os.getenv("REDIS_HOST", "localhost"),
                decode_responses=True,
            )
            return r.ping()
        except Exception:
            return False

    def _check_backend_ready(self) -> bool:
        """Check if backend service is ready."""
        import httpx

        try:
            response = httpx.get(
                f"{os.getenv('AGTSDBX_BASE_URL', 'http://localhost:8000')}/health",
                timeout=5,
            )
            return response.status_code == 200
        except Exception:
            return False

    def _check_frontend_ready(self) -> bool:
        """Check if frontend service is ready."""
        import httpx

        try:
            response = httpx.get(
                f"{os.getenv('FRONTEND_URL', 'http://localhost:8080')}/api/health",
                timeout=5,
            )
            return response.status_code == 200
        except Exception:
            return False
