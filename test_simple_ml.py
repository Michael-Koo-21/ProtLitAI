#!/usr/bin/env python3
"""
Simple test for basic ML pipeline structure

This test checks if the code loads properly without requiring model downloads.
"""

import sys
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_imports():
    """Test that all modules can be imported"""
    logger.info("Testing module imports...")
    
    try:
        # Test core imports
        from core.config import AppSettings
        from core.database import db_manager
        from core.models import Paper, Entity, ProcessingStatus
        from core.repository import PaperRepository, EmbeddingRepository, EntityRepository
        logger.info("✅ Core modules imported successfully")
        
        # Test processing imports (structure only)
        from processing.ml_models import ModelConfig
        from processing.embedding_generator import EmbeddingConfig  
        from processing.entity_extractor import EntityExtractionConfig, EntityType
        from processing.nlp_pipeline import PipelineConfig
        logger.info("✅ Processing modules imported successfully")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Import failed: {e}")
        return False

def test_torch_mps():
    """Test PyTorch MPS availability"""
    logger.info("Testing PyTorch MPS support...")
    
    try:
        import torch
        
        logger.info(f"PyTorch version: {torch.__version__}")
        
        # Check MPS availability
        if torch.backends.mps.is_available():
            logger.info("✅ MPS (Metal Performance Shaders) is available")
            
            # Test MPS device creation
            device = torch.device("mps")
            logger.info(f"✅ MPS device created: {device}")
            
            # Test simple tensor operation on MPS
            x = torch.rand(10, 10).to(device)
            y = torch.rand(10, 10).to(device)
            z = torch.matmul(x, y)
            
            logger.info(f"✅ MPS computation test passed: result shape {z.shape}")
            return True
        else:
            logger.warning("⚠️ MPS is not available on this system")
            return False
            
    except Exception as e:
        logger.error(f"❌ PyTorch MPS test failed: {e}")
        return False

def test_database_connection():
    """Test database connection"""
    logger.info("Testing database connection...")
    
    try:
        from core.database import db_manager
        
        # Initialize database
        db_manager.initialize()
        logger.info("✅ Database initialized successfully")
        
        # Test SQLite connection
        with db_manager.get_sqlite_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            if result[0] == 1:
                logger.info("✅ SQLite connection test passed")
            
        # Test DuckDB connection
        with db_manager.get_duckdb_connection() as conn:
            result = conn.execute("SELECT 1").fetchone()
            if result[0] == 1:
                logger.info("✅ DuckDB connection test passed")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Database test failed: {e}")
        return False

def test_model_classes():
    """Test model class instantiation"""
    logger.info("Testing model classes...")
    
    try:
        from core.models import Paper, Entity
        from processing.ml_models import ModelConfig
        from processing.embedding_generator import EmbeddingConfig
        from processing.entity_extractor import EntityExtractionConfig, EntityType
        
        # Test Paper model
        paper = Paper(
            id="test_001",
            title="Test Paper",
            abstract="Test abstract",
            authors=["Test Author"],
            journal="Test Journal",
            publication_date="2024-01-01",
            doi="10.1234/test",
            paper_type="journal",
            source="pubmed",
            processing_status=ProcessingStatus.PENDING
        )
        logger.info(f"✅ Paper model created: {paper.title}")
        
        # Test Entity model
        entity = Entity(
            paper_id="test_001",
            entity_text="protein",
            entity_type="protein",
            confidence=0.95,
            start_position=0,
            end_position=7,
            context="This protein is important"
        )
        logger.info(f"✅ Entity model created: {entity.entity_text}")
        
        # Test config classes
        model_config = ModelConfig()
        logger.info(f"✅ ModelConfig created: {model_config.embedding_model_name}")
        
        embedding_config = EmbeddingConfig()
        logger.info(f"✅ EmbeddingConfig created: batch_size={embedding_config.batch_size}")
        
        entity_config = EntityExtractionConfig()
        logger.info(f"✅ EntityExtractionConfig created: threshold={entity_config.confidence_threshold}")
        
        # Test EntityType enum
        protein_type = EntityType.PROTEIN
        logger.info(f"✅ EntityType enum: {protein_type.value}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Model class test failed: {e}")
        return False

def main():
    """Run all simple tests"""
    logger.info("🧪 Starting Simple ML Pipeline Tests")
    logger.info("=" * 50)
    
    test_results = []
    
    # Test 1: Module imports
    test_results.append(("Module Imports", test_imports()))
    
    # Test 2: PyTorch MPS
    test_results.append(("PyTorch MPS", test_torch_mps()))
    
    # Test 3: Database connection
    test_results.append(("Database Connection", test_database_connection()))
    
    # Test 4: Model classes
    test_results.append(("Model Classes", test_model_classes()))
    
    # Print results
    logger.info("=" * 50)
    logger.info("🧪 Simple Test Results")
    logger.info("=" * 50)
    
    all_passed = True
    for test_name, passed in test_results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        logger.info(f"{test_name:20} {status}")
        if not passed:
            all_passed = False
    
    logger.info("=" * 50)
    
    if all_passed:
        logger.info("🎉 All basic tests passed! ML Pipeline structure is correct.")
        logger.info("ℹ️ To test full functionality, install required models:")
        logger.info("   python -m spacy download en_core_sci_lg")
        logger.info("   (sentence-transformers models will download automatically)")
        return 0
    else:
        logger.error("❌ Some tests failed. Please check the logs above.")
        return 1

if __name__ == "__main__":
    exit(main())