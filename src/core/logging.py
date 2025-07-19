"""Structured logging configuration for ProtLitAI."""

import sys
import logging
import logging.handlers
from pathlib import Path
from typing import Any, Dict, Optional
import structlog
from rich.logging import RichHandler
from rich.console import Console

from .config import config


class ProtLitAILogger:
    """Custom logger for ProtLitAI with structured logging."""
    
    def __init__(self):
        self.console = Console()
        self._setup_logging()
    
    def _setup_logging(self) -> None:
        """Configure structured logging with both file and console output."""
        
        # Configure structlog
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                structlog.processors.JSONRenderer()
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )
        
        # Get root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, config.get("log_level", "INFO")))
        
        # Clear any existing handlers
        root_logger.handlers.clear()
        
        # Console handler with Rich formatting
        console_handler = RichHandler(
            console=self.console,
            rich_tracebacks=True,
            markup=True,
            show_path=False,
            show_time=True
        )
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            "%(message)s",
            datefmt="[%X]"
        )
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)
        
        # File handler with rotation
        log_file = Path(config.get("log_file", "logs/protlitai.log"))
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=config.get("log_rotation_mb", 100) * 1024 * 1024,
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
    
    def get_logger(self, name: str) -> structlog.BoundLogger:
        """Get a structured logger for a specific component."""
        return structlog.get_logger(name)


class ComponentLogger:
    """Base class for component-specific logging."""
    
    def __init__(self, component_name: str):
        self.logger = structlog.get_logger(component_name)
        self.component = component_name
    
    def debug(self, message: str, **kwargs) -> None:
        """Log debug message."""
        self.logger.debug(message, component=self.component, **kwargs)
    
    def info(self, message: str, **kwargs) -> None:
        """Log info message."""
        self.logger.info(message, component=self.component, **kwargs)
    
    def warning(self, message: str, **kwargs) -> None:
        """Log warning message."""
        self.logger.warning(message, component=self.component, **kwargs)
    
    def error(self, message: str, **kwargs) -> None:
        """Log error message."""
        self.logger.error(message, component=self.component, **kwargs)
    
    def critical(self, message: str, **kwargs) -> None:
        """Log critical message."""
        self.logger.critical(message, component=self.component, **kwargs)
    
    def log_performance(self, operation: str, duration: float, **kwargs) -> None:
        """Log performance metrics."""
        self.logger.info(
            "Performance metric",
            component=self.component,
            operation=operation,
            duration_seconds=round(duration, 3),
            **kwargs
        )
    
    def log_api_call(self, api: str, endpoint: str, status_code: int, 
                     duration: float, **kwargs) -> None:
        """Log API call details."""
        self.logger.info(
            "API call",
            component=self.component,
            api=api,
            endpoint=endpoint,
            status_code=status_code,
            duration_seconds=round(duration, 3),
            **kwargs
        )
    
    def log_ml_operation(self, operation: str, model: str, batch_size: int,
                        duration: float, **kwargs) -> None:
        """Log machine learning operations."""
        self.logger.info(
            "ML operation",
            component=self.component,
            operation=operation,
            model=model,
            batch_size=batch_size,
            duration_seconds=round(duration, 3),
            **kwargs
        )
    
    def log_database_operation(self, operation: str, table: str, 
                              records_affected: int, duration: float,
                              **kwargs) -> None:
        """Log database operations."""
        self.logger.info(
            "Database operation",
            component=self.component,
            operation=operation,
            table=table,
            records_affected=records_affected,
            duration_seconds=round(duration, 3),
            **kwargs
        )


class PerformanceLogger:
    """Context manager for performance logging."""
    
    def __init__(self, logger: ComponentLogger, operation: str, **kwargs):
        self.logger = logger
        self.operation = operation
        self.kwargs = kwargs
        self.start_time = None
    
    def __enter__(self):
        import time
        self.start_time = time.time()
        self.logger.debug(f"Starting {self.operation}", **self.kwargs)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        import time
        duration = time.time() - self.start_time
        
        if exc_type is None:
            self.logger.log_performance(self.operation, duration, **self.kwargs)
        else:
            self.logger.error(
                f"Error in {self.operation}",
                duration_seconds=round(duration, 3),
                error_type=exc_type.__name__,
                error_message=str(exc_val),
                **self.kwargs
            )


# Global logger instance
logger_manager = ProtLitAILogger()

# Convenience function for getting loggers
def get_logger(component_name: str) -> ComponentLogger:
    """Get a component logger."""
    return ComponentLogger(component_name)

def setup_logging() -> None:
    """Setup logging system - convenience function."""
    # The logger manager is already initialized on import
    pass