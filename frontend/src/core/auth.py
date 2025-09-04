# ==============================================
# AUTHENTICATION MANAGER
# ==============================================

import jwt
import time
import hashlib
import secrets
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import logging

class AuthManager:
    """Authentication and authorization manager."""
    
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.jwt_secret = config.get("JWT_SECRET") or config.get("SECRET_KEY")
        self.jwt_expiry = config.get("JWT_EXPIRY", 3600)
        self._sessions = {}  # In-memory session store (use Redis in production)
    
    def generate_token(self, user_data: Dict[str, Any]) -> str:
        """Generate JWT token for user."""
        payload = {
            "user_id": user_data.get("id"),
            "username": user_data.get("username"),
            "role": user_data.get("role", "user"),
            "exp": datetime.utcnow() + timedelta(seconds=self.jwt_expiry),
            "iat": datetime.utcnow(),
            "jti": secrets.token_hex(16)  # JWT ID for revocation
        }
        
        token = jwt.encode(payload, self.jwt_secret, algorithm="HS256")
        
        # Store session
        self._sessions[payload["jti"]] = {
            "user_id": payload["user_id"],
            "created_at": time.time(),
            "last_activity": time.time()
        }
        
        return token
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify JWT token and return payload."""
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=["HS256"])
            
            # Check if session exists and is not revoked
            jti = payload.get("jti")
            if jti and jti not in self._sessions:
                self.logger.warning("Token session not found or revoked")
                return None
            
            # Update last activity
            if jti in self._sessions:
                self._sessions[jti]["last_activity"] = time.time()
            
            return payload
            
        except jwt.ExpiredSignatureError:
            self.logger.warning("Token has expired")
            return None
        except jwt.InvalidTokenError as e:
            self.logger.warning(f"Invalid token: {e}")
            return None
    
    def revoke_token(self, token: str) -> bool:
        """Revoke a JWT token."""
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=["HS256"], options={"verify_exp": False})
            jti = payload.get("jti")
            
            if jti and jti in self._sessions:
                del self._sessions[jti]
                self.logger.info(f"Token revoked: {jti}")
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to revoke token: {e}")
            
        return False
    
    def hash_password(self, password: str) -> str:
        """Hash password using PBKDF2."""
        salt = secrets.token_bytes(32)
        key = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
        return f"{salt.hex()}:{key.hex()}"
    
    def verify_password(self, password: str, hashed: str) -> bool:
        """Verify password against hash."""
        try:
            salt_hex, key_hex = hashed.split(':')
            salt = bytes.fromhex(salt_hex)
            stored_key = bytes.fromhex(key_hex)
            
            new_key = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
            
            return secrets.compare_digest(stored_key, new_key)
            
        except Exception as e:
            self.logger.error(f"Password verification failed: {e}")
            return False
    
    def is_admin(self, user_data: Optional[Dict[str, Any]] = None) -> bool:
        """Check if user has admin role."""
        if not user_data:
            return False
        return user_data.get("role") == "admin"
    
    def has_permission(self, user_data: Optional[Dict[str, Any]], permission: str) -> bool:
        """Check if user has specific permission."""
        if not user_data:
            return False
            
        role = user_data.get("role", "user")
        
        # Define role-based permissions
        permissions = {
            "admin": ["*"],  # All permissions
            "power_user": [
                "execute_commands",
                "manage_files",
                "view_system",
                "use_docker",
                "make_network_requests"
            ],
            "user": [
                "execute_commands",
                "manage_files",
                "view_system"
            ],
            "viewer": [
                "view_system"
            ]
        }
        
        role_permissions = permissions.get(role, [])
        
        # Check for wildcard or specific permission
        return "*" in role_permissions or permission in role_permissions
    
    def cleanup_sessions(self, max_idle_time: int = 3600):
        """Clean up idle sessions."""
        current_time = time.time()
        expired_sessions = []
        
        for jti, session in self._sessions.items():
            if current_time - session["last_activity"] > max_idle_time:
                expired_sessions.append(jti)
        
        for jti in expired_sessions:
            del self._sessions[jti]
            
        if expired_sessions:
            self.logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")
