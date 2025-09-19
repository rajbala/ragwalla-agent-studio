#!/usr/bin/env python3

import os
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class AppConfig:
    """Application configuration from environment variables"""
    
    def __init__(self):
        # Server Configuration
        self.host = os.getenv("HOST", "0.0.0.0")
        self.port = int(os.getenv("PORT", "8000"))
        self.debug = os.getenv("DEBUG", "false").lower() == "true"
        
        # Database Configuration
        self.database_url = os.getenv("DATABASE_URL", "sqlite:///./ragwalla_agent_studio.db")
        
        # Ragwalla Agent Configuration (required)
        self.agent_base_url = os.getenv("AGENT_BASE_URL")
        self.ragwalla_api_key = os.getenv("RAGWALLA_API_KEY")
        
        # Optional Default Agent Configuration
        self.default_agent_id = os.getenv("DEFAULT_AGENT_ID")
        self.default_agent_name = os.getenv("DEFAULT_AGENT_NAME", "AI Assistant")
        self.default_agent_description = os.getenv("DEFAULT_AGENT_DESCRIPTION", "AI Assistant for chat support")
        
        # Generate organization_id if not provided
        self.organization_name = os.getenv("ORGANIZATION_NAME", "Default Organization")
        self.organization_id = os.getenv("ORGANIZATION_ID")
        if not self.organization_id:
            import uuid
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y%m%d")
            self.organization_id = f"org-{timestamp}-" + str(uuid.uuid4())
        
        # Default User Configuration
        self.default_user_id = os.getenv("DEFAULT_USER_ID", "default-user")
        self.default_user_email = os.getenv("DEFAULT_USER_EMAIL", "admin@example.com")
        self.default_user_first_name = os.getenv("DEFAULT_USER_FIRST_NAME", "Admin")
        self.default_user_last_name = os.getenv("DEFAULT_USER_LAST_NAME", "User")
        
        # Chat Configuration
        self.max_message_length = int(os.getenv("MAX_MESSAGE_LENGTH", "4000"))
        # Timeout configurations removed - no timeouts enforced
        self.websocket_max_reconnect_attempts = int(os.getenv("WEBSOCKET_MAX_RECONNECT_ATTEMPTS", "5"))
        self.websocket_reconnect_delay = int(os.getenv("WEBSOCKET_RECONNECT_DELAY", "1000"))  # milliseconds
        
        # CORS Configuration
        cors_origins_str = os.getenv("CORS_ORIGINS", "*")
        self.cors_origins = [origin.strip() for origin in cors_origins_str.split(",")]

# Global configuration instance
config = AppConfig()

def get_config() -> AppConfig:
    """Get the application configuration"""
    return config

def validate_required_config():
    """Validate that all required configuration is present"""
    required_fields = ["agent_base_url", "ragwalla_api_key"]
    missing_fields = []
    
    for field in required_fields:
        if not getattr(config, field, None):
            missing_fields.append(field.upper())
    
    if missing_fields:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_fields)}")
    
    return True

def get_agent_config() -> Dict[str, Any]:
    """Get agent-specific configuration"""
    return {
        "base_url": config.agent_base_url,
        "api_key": config.ragwalla_api_key,
        "default_agent_id": config.default_agent_id,
        "default_agent_name": config.default_agent_name,
        "default_agent_description": config.default_agent_description
    }

def get_database_config() -> Dict[str, Any]:
    """Get database configuration"""
    return {
        "url": config.database_url,
        "organization_name": config.organization_name,
        "organization_id": config.organization_id
    }
