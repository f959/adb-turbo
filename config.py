"""
Configuration Management for ADB Performance Optimizer
Supports environment variables with sensible defaults
"""

import os
import logging
from dataclasses import dataclass
from typing import Optional


@dataclass
class Config:
    """Application configuration with environment variable support"""
    
    # Server Configuration
    HOST: str = os.getenv('ADB_HOST', '0.0.0.0')
    PORT: int = int(os.getenv('ADB_PORT', '8765'))
    DEBUG: bool = os.getenv('DEBUG', 'False').lower() == 'true'
    
    # Logging Configuration
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE: Optional[str] = os.getenv('LOG_FILE', None)
    
    # ADB Configuration
    ADB_TIMEOUT: int = int(os.getenv('ADB_TIMEOUT', '30'))
    
    # CORS Configuration
    CORS_ORIGINS: str = os.getenv('CORS_ORIGINS', '*')
    
    def __post_init__(self):
        """Validate configuration after initialization"""
        if self.PORT < 1 or self.PORT > 65535:
            raise ValueError(f"Invalid port number: {self.PORT}")
        
        if self.ADB_TIMEOUT < 1:
            raise ValueError(f"Invalid timeout: {self.ADB_TIMEOUT}")
        
        valid_log_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if self.LOG_LEVEL.upper() not in valid_log_levels:
            raise ValueError(f"Invalid log level: {self.LOG_LEVEL}")
    
    @property
    def url(self) -> str:
        """Get the server URL"""
        host = 'localhost' if self.HOST == '0.0.0.0' else self.HOST
        return f"http://{host}:{self.PORT}"


def setup_logging(config: Config) -> None:
    """
    Configure application-wide logging
    
    Args:
        config: Configuration object with logging settings
    """
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    handlers = []
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(log_format))
    handlers.append(console_handler)
    
    # File handler (optional)
    if config.LOG_FILE:
        file_handler = logging.FileHandler(config.LOG_FILE)
        file_handler.setFormatter(logging.Formatter(log_format))
        handlers.append(file_handler)
    
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL.upper()),
        format=log_format,
        handlers=handlers
    )
    
    # Set Flask logger level
    logging.getLogger('werkzeug').setLevel(logging.WARNING)


# Create global config instance
config = Config()

