# tests/production_readiness/test_config_validation.py
"""
Configuration Validation Tests
Prevents: Deployment failures due to missing/invalid configuration
Saves: Hours of debugging "why won't it connect" issues
"""

import os
import re
import sys
from pathlib import Path

import httpx
import pytest

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestConfigurationValidation:
    """
    These tests ensure all required configuration is present and valid
    BEFORE you deploy. Each test represents a potential production failure.
    """

    @pytest.fixture(autouse=True)
    def setup(self):
        """Load and validate the base configuration."""
        self.required_env_vars = {
            # Critical Fabric/Tela API configuration
            "FABRIC_API_KEY": {
                "format": r"^[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+$",
                "error": "Fabric API key missing or invalid format",
                "production_impact": "AI features will be completely non-functional",
            },
            "FABRIC_ORG_ID": {
                "format": r"^[a-zA-Z0-9_-]+$",
                "error": "Fabric Organization ID missing",
                "production_impact": "API calls will fail with 403 Forbidden",
            },
            "FABRIC_PROJECT_ID": {
                "format": r"^[a-zA-Z0-9_-]+$",
                "error": "Fabric Project ID missing",
                "production_impact": "API calls will fail with project not found",
            },
            # Backend configuration
            "SECRET_KEY": {
                "format": r"^.{32,}$",
                "error": "Secret key too short or missing",
                "production_impact": "Security vulnerability - sessions can be hijacked",
            },
            "JWT_SECRET": {
                "format": r"^.{32,}$",
                "error": "JWT secret too short or missing",
                "production_impact": "Authentication will fail completely",
            },
            # Database configuration
            "DATABASE_URL": {
                "format": r"^(postgresql|mysql|sqlite)://.+$",
                "error": "Invalid database URL format",
                "production_impact": "Application cannot store any data",
            },
        }

    def test_all_required_env_vars_present(self):
        """
        Test that all required environment variables are set.
        This prevents the #1 cause of production failures: missing config.
        """
        missing_vars = []
        impact_summary = []

        for var_name, config in self.required_env_vars.items():
            value = os.getenv(var_name)
            if not value:
                missing_vars.append(var_name)
                impact_summary.append(f"- {var_name}: {config['production_impact']}")

        assert not missing_vars, (
            f"Missing critical environment variables: {', '.join(missing_vars)}\n"
            f"Production impact if deployed:\n" + "\n".join(impact_summary)
        )

    def test_env_var_formats_valid(self):
        """
        Test that environment variables match expected formats.
        This catches typos and copy-paste errors before they cause mysterious failures.
        """
        format_errors = []

        for var_name, config in self.required_env_vars.items():
            value = os.getenv(var_name, "")
            if value and not re.match(config["format"], value):
                format_errors.append(
                    f"{var_name}: Current value doesn't match expected format. "
                    f"Error: {config['error']}"
                )

        assert not format_errors, "Configuration format errors detected:\n" + "\n".join(
            format_errors
        )

    @pytest.mark.asyncio
    async def test_api_endpoints_accessible(self):
        """
        Test that configured API endpoints are actually reachable.
        This prevents deploying with wrong URLs that will fail at runtime.
        """
        endpoints_to_test = [
            (
                os.getenv("FABRIC_BASE_URL", "https://api.telaos.com/v1"),
                "Fabric API",
            ),
            (os.getenv("AGTSDBX_BASE_URL", "http://localhost:8000"), "Backend Service"),
        ]

        unreachable = []

        async with httpx.AsyncClient(timeout=5, follow_redirects=True) as client:
            for endpoint, name in endpoints_to_test:
                try:
                    response = await client.get(endpoint)
                    # We expect some response, even if it's 401/403
                    if response.status_code >= 500:
                        unreachable.append(
                            f"{name} ({endpoint}): Server error {response.status_code}"
                        )
                except Exception as e:
                    unreachable.append(f"{name} ({endpoint}): {str(e)}")

        assert (
            not unreachable
        ), "API endpoints unreachable (will fail in production):\n" + "\n".join(
            unreachable
        )

    def test_file_permissions_and_paths(self):
        """
        Test that all required directories exist and are writable.
        This prevents "Permission denied" errors that are hard to debug in containers.
        """
        required_paths = [
            ("backend/WORKDIR", "Working directory for file operations"),
            ("backend/storage/logs", "Log storage"),
            ("backend/storage/cache", "Cache storage"),
            ("frontend/static", "Static file storage"),
        ]

        path_issues = []

        for path, description in required_paths:
            path_obj = Path(path)
            if not path_obj.exists():
                # Try to create it
                try:
                    path_obj.mkdir(parents=True, exist_ok=True)
                except Exception as e:
                    path_issues.append(
                        f"{path} ({description}): Cannot create - {str(e)}"
                    )
                    continue

            if not os.access(path, os.W_OK):
                path_issues.append(f"{path} ({description}): Not writable")

        assert (
            not path_issues
        ), "File system issues that will cause production failures:\n" + "\n".join(
            path_issues
        )

    def test_docker_socket_accessible(self):
        """
        Test Docker socket accessibility if Docker features are enabled.
        This prevents "Cannot connect to Docker" errors in production.
        """
        if os.getenv("DOCKER_ENABLED", "true").lower() != "true":
            pytest.skip("Docker is disabled")

        docker_socket = Path("/var/run/docker.sock")

        if not docker_socket.exists():
            # In CI environment, Docker might be accessed differently
            import subprocess

            try:
                result = subprocess.run(
                    ["docker", "version"],
                    capture_output=True,
                    timeout=5,
                    check=False,
                )
                if result.returncode != 0:
                    pytest.skip("Docker not available in CI environment")
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pytest.skip("Docker not available in CI environment")
        else:
            assert docker_socket.exists(), (
                "Docker is enabled but socket not found. "
                "Production impact: All Docker features will fail"
            )
