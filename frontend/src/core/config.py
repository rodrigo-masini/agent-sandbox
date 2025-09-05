# ==============================================
# CONFIGURATION MANAGEMENT
# ==============================================

import os
import json
from typing import Any, Optional
from pathlib import Path
import logging

class Config:
    """Configuration management for the application."""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or os.getenv("CONFIG_PATH", "config.json")
        self.config = {}
        self.env_vars = {}
        self.logger = logging.getLogger(__name__)
        self._load_config()
        self._load_env_vars()
    
    def _load_config(self):
        """Load configuration from file if it exists."""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    self.config = json.load(f)
                self.logger.info(f"Loaded configuration from {self.config_path}")
            except Exception as e:
                self.logger.error(f"Failed to load config: {e}")
                self.config = {}
        else:
            self.config = self._get_default_config()
    
    def _load_env_vars(self):
        """Load configuration from environment variables."""
        self.env_vars = {
            # Tela/Fabric API Configuration
            "FABRIC_API_KEY": os.getenv("FABRIC_API_KEY", ""),
            "FABRIC_ORG_ID": os.getenv("FABRIC_ORG_ID", ""),
            "FABRIC_PROJECT_ID": os.getenv("FABRIC_PROJECT_ID", ""),
            "FABRIC_BASE_URL": os.getenv("FABRIC_BASE_URL", "https://api.telaos.com/v1"),
            "FABRIC_MODEL": os.getenv("FABRIC_MODEL", "wizard"),
            "FABRIC_TIMEOUT": int(os.getenv("FABRIC_TIMEOUT", "300")),
            
            # Agent Sandbox Configuration
            "AGTSDBX_BASE_URL": os.getenv("AGTSDBX_BASE_URL", "http://localhost:8000"),
            "AGTSDBX_TIMEOUT": int(os.getenv("AGTSDBX_TIMEOUT", "300")),
            "AGTSDBX_API_KEY": os.getenv("AGTSDBX_API_KEY", ""),
            
            # Application Configuration
            "APP_ENV": os.getenv("APP_ENV", "development"),
            "LOG_LEVEL": os.getenv("LOG_LEVEL", "INFO"),
            "DEBUG": os.getenv("DEBUG", "false").lower() == "true",
            "HOST": os.getenv("HOST", "0.0.0.0"),
            "PORT": int(os.getenv("PORT", "8080")),
            
            # Security Configuration
            "SECRET_KEY": os.getenv("SECRET_KEY", self._generate_secret_key()),
            "JWT_SECRET": os.getenv("JWT_SECRET", ""),
            "JWT_EXPIRY": int(os.getenv("JWT_EXPIRY", "3600")),
            
            # Redis Configuration
            "REDIS_HOST": os.getenv("REDIS_HOST", "localhost"),
            "REDIS_PORT": int(os.getenv("REDIS_PORT", "6379")),
            "REDIS_PASSWORD": os.getenv("REDIS_PASSWORD", ""),
            "REDIS_DB": int(os.getenv("REDIS_DB", "0")),
            
            # Database Configuration
            "DATABASE_URL": os.getenv("DATABASE_URL", "sqlite:///agtsdbx.db"),
            
            # Feature Flags
            "ENABLE_STREAMING": os.getenv("ENABLE_STREAMING", "true").lower() == "true",
            "ENABLE_TOOL_CALLING": os.getenv("ENABLE_TOOL_CALLING", "true").lower() == "true",
            "ENABLE_DOCKER": os.getenv("ENABLE_DOCKER", "true").lower() == "true",
            "ENABLE_NETWORK": os.getenv("ENABLE_NETWORK", "true").lower() == "true",
            "ENABLE_DATABASE": os.getenv("ENABLE_DATABASE", "true").lower() == "true",

            # WebSocket Configuration (add this)
            "RECONNECT_TIMEOUT": int(os.getenv("RECONNECT_TIMEOUT", "5")),
            
            # Rate Limiting
            "RATE_LIMIT_ENABLED": os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true",
            "RATE_LIMIT_RPM": int(os.getenv("RATE_LIMIT_RPM", "60")),
            "RATE_LIMIT_WINDOW": int(os.getenv("RATE_LIMIT_WINDOW", "60")),
        }
    
    def _get_default_config(self) -> dict:
        """Get default configuration."""
        return {
            "app": {
                "name": "Magic Agent Sandbox",
                "version": "1.0.0",
                "description": "AI-Powered System Interface"
            },
            "ui": {
                "theme": "dark",
                "max_message_length": 10000,
                "auto_scroll": True,
                "show_timestamps": True,
                "enable_markdown": True,
                "enable_syntax_highlighting": True
            },
            "chat": {
                "max_history": 100,
                "context_window": 100000,
                "default_temperature": 0.1,
                "default_max_tokens": 100000
            },
            "security": {
                "allowed_commands": [
                    "ls", "cat", "echo", "pwd", "whoami", "date", "uptime",
                    "ps", "top", "df", "du", "free", "uname",
                    "python", "python3", "node", "npm", "git"
                ],
                "forbidden_paths": [
                    "/etc", "/usr", "/var", "/bin", "/sbin",
                    "/boot", "/dev", "/proc", "/sys", "/root"
                ]
            }
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key."""
        # First check environment variables
        if key in self.env_vars:
            return self.env_vars[key]
        
        # Then check config file (supports nested keys with dot notation)
        keys = key.split('.')
        value = self.config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value
    
    def set(self, key: str, value: Any):
        """Set configuration value."""
        keys = key.split('.')
        config = self.config
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        config[keys[-1]] = value
    
    def save(self):
        """Save configuration to file."""
        try:
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=2)
            self.logger.info(f"Saved configuration to {self.config_path}")
        except Exception as e:
            self.logger.error(f"Failed to save config: {e}")
    
    def _generate_secret_key(self) -> str:
        """Generate a random secret key."""
        import secrets
        return secrets.token_hex(32)
    
    def validate(self) -> tuple[bool, list[str]]:
        """Validate configuration and return status and errors."""
        errors = []
        
        # Check required Tela/Fabric configuration
        if not self.get("FABRIC_API_KEY"):
            errors.append("FABRIC_API_KEY is required")
        if not self.get("FABRIC_ORG_ID"):
            errors.append("FABRIC_ORG_ID is required")
        if not self.get("FABRIC_PROJECT_ID"):
            errors.append("FABRIC_PROJECT_ID is required")
        
        # Check Pandora URL format
        pandora_url = self.get("AGTSDBX_BASE_URL")
        if not pandora_url or not (pandora_url.startswith("http://") or pandora_url.startswith("https://")):
            errors.append("AGTSDBX_BASE_URL must be a valid HTTP(S) URL")
        
        return len(errors) == 0, errors
