import os
import sys
import time
from unittest.mock import MagicMock, Mock

import jwt
import pytest
from src.core.auth import AuthManager

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


class TestAuthManager:
    @pytest.fixture
    def config(self):
        mock_config = Mock()
        mock_config.get = MagicMock(
            side_effect=lambda key, default=None: {
                "JWT_SECRET": "test_secret_key",
                "SECRET_KEY": "test_secret_key",
                "JWT_EXPIRY": 3600,
            }.get(key, default)
        )
        return mock_config

    @pytest.fixture
    def auth_manager(self, config):
        return AuthManager(config)

    def test_generate_and_verify_token(self, auth_manager):
        user_data = {"id": 1, "username": "testuser", "role": "admin"}

        token = auth_manager.generate_token(user_data)
        assert token is not None

        payload = auth_manager.verify_token(token)
        assert payload is not None
        assert payload["user_id"] == 1
        assert payload["username"] == "testuser"
        assert payload["role"] == "admin"

    def test_verify_expired_token(self, auth_manager):
        # Create an expired token
        expired_payload = {
            "user_id": 1,
            "exp": time.time() - 3600,  # Expired 1 hour ago
        }
        expired_token = jwt.encode(
            expired_payload, "test_secret_key", algorithm="HS256"
        )

        result = auth_manager.verify_token(expired_token)
        assert result is None

    def test_verify_invalid_token(self, auth_manager):
        invalid_token = "invalid.token.here"
        result = auth_manager.verify_token(invalid_token)
        assert result is None

    def test_revoke_token(self, auth_manager):
        user_data = {"id": 1, "username": "testuser"}
        token = auth_manager.generate_token(user_data)

        # Token should be valid initially
        assert auth_manager.verify_token(token) is not None

        # Revoke the token
        success = auth_manager.revoke_token(token)
        assert success is True

        # Token should now be invalid
        assert auth_manager.verify_token(token) is None

    def test_password_hashing(self, auth_manager):
        password = "MySecurePassword123!"

        hashed = auth_manager.hash_password(password)
        assert hashed != password
        assert ":" in hashed  # Should contain salt:hash format

        # Verify correct password
        assert auth_manager.verify_password(password, hashed) is True

        # Verify incorrect password
        assert auth_manager.verify_password("WrongPassword", hashed) is False

    def test_has_permission(self, auth_manager):
        admin_user = {"role": "admin"}
        power_user = {"role": "power_user"}
        regular_user = {"role": "user"}
        viewer = {"role": "viewer"}

        # Admin has all permissions
        assert auth_manager.has_permission(admin_user, "execute_commands") is True
        assert auth_manager.has_permission(admin_user, "use_docker") is True
        assert auth_manager.has_permission(admin_user, "anything") is True

        # Power user has specific permissions
        assert auth_manager.has_permission(power_user, "execute_commands") is True
        assert auth_manager.has_permission(power_user, "use_docker") is True

        # Regular user has limited permissions
        assert auth_manager.has_permission(regular_user, "execute_commands") is True
        assert auth_manager.has_permission(regular_user, "use_docker") is False

        # Viewer has minimal permissions
        assert auth_manager.has_permission(viewer, "view_system") is True
        assert auth_manager.has_permission(viewer, "execute_commands") is False

    def test_cleanup_sessions(self, auth_manager):
        # Create some sessions
        user_data = {"id": 1, "username": "user1"}
        token1 = auth_manager.generate_token(user_data)

        # Manually expire a session
        jti = jwt.decode(
            token1,
            "test_secret_key",
            algorithms=["HS256"],
            options={"verify_exp": False},
        )["jti"]
        auth_manager._sessions[jti]["last_activity"] = time.time() - 7200  # 2 hours ago

        # Create a recent session
        token2 = auth_manager.generate_token({"id": 2, "username": "user2"})

        # Clean up with 1 hour max idle time
        auth_manager.cleanup_sessions(max_idle_time=3600)

        # Old session should be gone
        assert auth_manager.verify_token(token1) is None

        # Recent session should still be valid
        assert auth_manager.verify_token(token2) is not None
