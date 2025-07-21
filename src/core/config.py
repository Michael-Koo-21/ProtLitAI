"""Configuration management for ProtLitAI."""

import os
import json
from pathlib import Path
from typing import Optional, Dict, Any
from pydantic import Field
from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class AppSettings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Application
    app_name: str = "ProtLitAI"
    version: str = "1.0.0"
    debug: bool = Field(default=False, validation_alias="DEBUG")
    
    # Database
    db_path: str = Field(default="data/literature.db", validation_alias="DB_PATH")
    analytics_db_path: str = Field(default="data/analytics.db", validation_alias="ANALYTICS_DB_PATH")
    
    # API Keys
    pubmed_api_key: Optional[str] = Field(default=None, validation_alias="PUBMED_API_KEY")
    openai_api_key: Optional[str] = Field(default=None, validation_alias="OPENAI_API_KEY")
    
    # API Rate Limits (requests per second)
    pubmed_rate_limit: float = Field(default=10.0, validation_alias="PUBMED_RATE_LIMIT")
    arxiv_rate_limit: float = Field(default=1.0, validation_alias="ARXIV_RATE_LIMIT")
    scholar_rate_limit: float = Field(default=0.5, validation_alias="SCHOLAR_RATE_LIMIT")
    
    # ML Model Settings
    embedding_model: str = Field(default="all-MiniLM-L6-v2", validation_alias="EMBEDDING_MODEL")
    spacy_model: str = Field(default="en_core_web_sm", validation_alias="SPACY_MODEL")
    device: str = Field(default="mps", validation_alias="DEVICE")  # M2 optimization
    batch_size: int = Field(default=32, validation_alias="BATCH_SIZE")
    max_memory_gb: float = Field(default=6.0, validation_alias="MAX_MEMORY_GB")
    
    # Storage
    pdf_storage_path: str = Field(default="cache/pdfs", validation_alias="PDF_STORAGE_PATH")
    embedding_cache_path: str = Field(default="cache/embeddings", validation_alias="EMBEDDING_CACHE_PATH")
    model_cache_path: str = Field(default="models", validation_alias="MODEL_CACHE_PATH")
    
    # Logging
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")
    log_file: str = Field(default="logs/protlitai.log", validation_alias="LOG_FILE")
    log_rotation_mb: int = Field(default=100, validation_alias="LOG_ROTATION_MB")
    
    # Collection Settings
    collection_schedule: str = Field(default="0 6 * * *", validation_alias="COLLECTION_SCHEDULE")  # Daily at 6 AM
    max_papers_per_day: int = Field(default=1000, validation_alias="MAX_PAPERS_PER_DAY")
    retry_attempts: int = Field(default=3, validation_alias="RETRY_ATTEMPTS")
    request_timeout: int = Field(default=30, validation_alias="REQUEST_TIMEOUT")
    
    model_config = ConfigDict(
        env_file=".env",
        case_sensitive=False,
        env_prefix=""
    )


class ConfigManager:
    """Manages application configuration."""
    
    def __init__(self, config_dir: str = "data/configs"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.settings = AppSettings()
        self._user_config = {}
        self._load_user_config()
    
    def _load_user_config(self) -> None:
        """Load user-specific configuration."""
        config_file = self.config_dir / "user_config.json"
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    self._user_config = json.load(f)
            except Exception as e:
                print(f"Warning: Could not load user config: {e}")
    
    def save_user_config(self) -> None:
        """Save user-specific configuration."""
        config_file = self.config_dir / "user_config.json"
        try:
            with open(config_file, 'w') as f:
                json.dump(self._user_config, f, indent=2)
        except Exception as e:
            print(f"Error saving user config: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        # Check user config first
        if key in self._user_config:
            return self._user_config[key]
        
        # Check settings
        if hasattr(self.settings, key):
            return getattr(self.settings, key)
        
        return default
    
    def set(self, key: str, value: Any) -> None:
        """Set user configuration value."""
        self._user_config[key] = value
        self.save_user_config()
    
    def get_db_paths(self) -> Dict[str, str]:
        """Get database file paths."""
        return {
            "literature": self.settings.db_path,
            "analytics": self.settings.analytics_db_path
        }
    
    def get_cache_paths(self) -> Dict[str, str]:
        """Get cache directory paths."""
        return {
            "pdfs": self.settings.pdf_storage_path,
            "embeddings": self.settings.embedding_cache_path,
            "models": self.settings.model_cache_path
        }
    
    def ensure_directories(self) -> None:
        """Ensure all required directories exist."""
        directories = [
            Path(self.settings.db_path).parent,
            Path(self.settings.pdf_storage_path),
            Path(self.settings.embedding_cache_path),
            Path(self.settings.model_cache_path),
            Path(self.settings.log_file).parent,
            self.config_dir
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
    
    def get_api_config(self) -> Dict[str, Any]:
        """Get API configuration."""
        return {
            "pubmed": {
                "api_key": self.settings.pubmed_api_key,
                "rate_limit": self.settings.pubmed_rate_limit
            },
            "openai": {
                "api_key": self.settings.openai_api_key
            },
            "arxiv": {
                "rate_limit": self.settings.arxiv_rate_limit
            },
            "scholar": {
                "rate_limit": self.settings.scholar_rate_limit
            }
        }
    
    def get_ml_config(self) -> Dict[str, Any]:
        """Get machine learning configuration."""
        return {
            "embedding_model": self.settings.embedding_model,
            "spacy_model": self.settings.spacy_model,
            "device": self.settings.device,
            "batch_size": self.settings.batch_size,
            "max_memory_gb": self.settings.max_memory_gb,
            "model_cache_path": self.settings.model_cache_path
        }


# Global configuration instance
config = ConfigManager()

# Ensure directories exist on import
config.ensure_directories()