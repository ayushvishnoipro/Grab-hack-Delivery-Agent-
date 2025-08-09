"""
Configuration settings for Project Synapse.

This module manages all configuration settings including API keys, 
agent parameters, and operational settings.
"""

import os
from typing import Optional
from dataclasses import dataclass
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


@dataclass
class SynapseSettings:
    """Configuration settings for the Synapse agent."""
    
    # API Configuration
    google_api_key: str
    
    # Agent Configuration
    agent_name: str = "Synapse"
    agent_version: str = "1.0.0"
    
    # Tool Configuration
    tool_timeout_seconds: int = 30
    max_reasoning_steps: int = 10
    confidence_threshold: float = 0.7
    
    # CLI Configuration
    verbose_mode: bool = False
    interactive_mode: bool = False
    
    # Simulation Configuration
    enable_realistic_delays: bool = True
    traffic_api_simulation: bool = True
    merchant_status_simulation: bool = True
    
    # Performance Configuration
    max_concurrent_tools: int = 3
    response_timeout_seconds: int = 30
    retry_attempts: int = 3
    
    # Logging Configuration
    log_level: str = "INFO"
    log_reasoning_steps: bool = True
    export_reasoning_logs: bool = True


def get_settings() -> SynapseSettings:
    """Get application settings from environment variables."""
    
    google_api_key = os.getenv("GOOGLE_API_KEY")
    if not google_api_key:
        # For demo purposes, provide a placeholder
        google_api_key = "your_google_api_key_here"
        print("⚠️  Warning: GOOGLE_API_KEY not found in environment. Using placeholder.")
        print("   Please set your Google API key in .env file for full functionality.")
    
    return SynapseSettings(
        # API Configuration
        google_api_key=google_api_key,
        
        # Agent Configuration
        agent_name=os.getenv("AGENT_NAME", "Synapse"),
        agent_version=os.getenv("AGENT_VERSION", "1.0.0"),
        
        # Tool Configuration
        tool_timeout_seconds=int(os.getenv("TOOL_TIMEOUT_SECONDS", "30")),
        max_reasoning_steps=int(os.getenv("MAX_REASONING_STEPS", "10")),
        confidence_threshold=float(os.getenv("CONFIDENCE_THRESHOLD", "0.7")),
        
        # CLI Configuration
        verbose_mode=os.getenv("VERBOSE_MODE", "false").lower() == "true",
        interactive_mode=os.getenv("INTERACTIVE_MODE", "false").lower() == "true",
        
        # Simulation Configuration
        enable_realistic_delays=os.getenv("ENABLE_REALISTIC_DELAYS", "true").lower() == "true",
        traffic_api_simulation=os.getenv("TRAFFIC_API_SIMULATION", "true").lower() == "true",
        merchant_status_simulation=os.getenv("MERCHANT_STATUS_SIMULATION", "true").lower() == "true",
        
        # Performance Configuration
        max_concurrent_tools=int(os.getenv("MAX_CONCURRENT_TOOLS", "3")),
        response_timeout_seconds=int(os.getenv("RESPONSE_TIMEOUT_SECONDS", "30")),
        retry_attempts=int(os.getenv("RETRY_ATTEMPTS", "3")),
        
        # Logging Configuration
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        log_reasoning_steps=os.getenv("LOG_REASONING_STEPS", "true").lower() == "true",
        export_reasoning_logs=os.getenv("EXPORT_REASONING_LOGS", "true").lower() == "true"
    )


# Global settings instance
_settings: Optional[SynapseSettings] = None


def get_global_settings() -> SynapseSettings:
    """Get the global settings instance."""
    global _settings
    if _settings is None:
        _settings = get_settings()
    return _settings


def update_setting(key: str, value) -> None:
    """Update a specific setting value."""
    global _settings
    if _settings is None:
        _settings = get_settings()
    
    if hasattr(_settings, key):
        setattr(_settings, key, value)
    else:
        raise ValueError(f"Unknown setting: {key}")


def reset_settings() -> None:
    """Reset settings to reload from environment."""
    global _settings
    _settings = None
