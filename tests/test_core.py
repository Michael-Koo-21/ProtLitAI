"""Tests for core application components."""

import pytest
from pathlib import Path
import tempfile
import shutil

from src.core.config import ConfigManager, AppSettings
from src.core.database import DatabaseManager
from src.core.models import Paper, PaperType, SourceType


class TestConfiguration:
    """Test configuration management."""
    
    def test_app_settings_defaults(self):
        """Test default application settings."""
        settings = AppSettings()
        assert settings.app_name == "ProtLitAI"
        assert settings.version == "1.0.0"
        assert settings.debug is False
        assert settings.device == "mps"
    
    def test_config_manager_initialization(self):
        """Test configuration manager initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = ConfigManager(config_dir=tmpdir)
            assert config.config_dir.exists()
            
    def test_config_get_set(self):
        """Test configuration get/set operations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = ConfigManager(config_dir=tmpdir)
            
            # Test default value
            assert config.get("nonexistent_key", "default") == "default"
            
            # Test set and get
            config.set("test_key", "test_value")
            assert config.get("test_key") == "test_value"


class TestDatabaseManager:
    """Test database management."""
    
    def test_database_initialization(self):
        """Test database manager initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Use temporary directory for test databases
            db_manager = DatabaseManager()
            # Override paths for testing
            db_manager.logger.info("Testing database initialization")
            # Would need actual database setup for full testing


class TestModels:
    """Test data models."""
    
    def test_paper_model_creation(self):
        """Test Paper model creation and validation."""
        paper = Paper(
            id="test-001",
            title="Test Paper",
            source=SourceType.PUBMED,
            paper_type=PaperType.JOURNAL,
            authors=["Author One", "Author Two"],
            relevance_score=0.85
        )
        
        assert paper.id == "test-001"
        assert paper.title == "Test Paper"
        assert paper.source == SourceType.PUBMED
        assert paper.relevance_score == 0.85
        assert len(paper.authors) == 2
    
    def test_paper_model_validation(self):
        """Test Paper model validation."""
        # Test invalid relevance score
        with pytest.raises(ValueError):
            Paper(
                id="test-002",
                title="Test Paper",
                source=SourceType.ARXIV,
                relevance_score=1.5  # Invalid score > 1
            )
    
    def test_author_cleanup(self):
        """Test author name cleanup."""
        paper = Paper(
            id="test-003",
            title="Test Paper",
            source=SourceType.BIORXIV,
            authors=["  Author One  ", "", "Author Two"]
        )
        
        # Should clean up whitespace and remove empty strings
        assert paper.authors == ["Author One", "Author Two"]


if __name__ == "__main__":
    pytest.main([__file__])