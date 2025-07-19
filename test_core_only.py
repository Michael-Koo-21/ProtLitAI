#!/usr/bin/env python3
"""
Core-only test for basic functionality

This test checks the core functionality without ML dependencies.
"""

import sys
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_core_imports():
    """Test core module imports"""
    logger.info("Testing core module imports...")
    
    try:
        from core.config import AppSettings
        from core.database import db_manager
        from core.models import Paper, Entity, ProcessingStatus
        from core.repository import PaperRepository, EmbeddingRepository, EntityRepository
        logger.info("✅ All core modules imported successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Core import failed: {e}")
        return False

def test_pytorch_mps():
    """Test PyTorch MPS availability"""
    logger.info("Testing PyTorch MPS support...")
    
    try:
        import torch
        
        logger.info(f"PyTorch version: {torch.__version__}")
        
        if torch.backends.mps.is_available():
            logger.info("✅ MPS (Metal Performance Shaders) is available")
            
            device = torch.device("mps")
            logger.info(f"✅ MPS device created: {device}")
            
            # Test simple computation
            x = torch.rand(5, 5).to(device)
            y = torch.rand(5, 5).to(device)
            z = torch.matmul(x, y)
            
            logger.info(f"✅ MPS computation test passed: {z.shape}")
            return True
        else:
            logger.warning("⚠️ MPS is not available")
            return False
            
    except Exception as e:
        logger.error(f"❌ PyTorch MPS test failed: {e}")
        return False

def test_database():
    """Test database functionality"""
    logger.info("Testing database functionality...")
    
    try:
        from core.database import db_manager
        from core.repository import PaperRepository
        from core.models import Paper, ProcessingStatus
        
        # Initialize database
        db_manager.initialize()
        logger.info("✅ Database initialized successfully")
        
        # Test repository
        paper_repo = PaperRepository()
        
        # Create test paper
        test_paper = Paper(
            id="test_core_001",
            title="Core Test Paper",
            abstract="This is a test paper for core functionality",
            authors=["Test Author"],
            journal="Test Journal",
            publication_date="2024-01-01",
            doi="10.1234/test.core.001",
            paper_type="journal",
            source="pubmed",
            processing_status=ProcessingStatus.PENDING
        )
        
        # Try to create paper
        try:
            created_paper = paper_repo.create(test_paper)
            logger.info(f"✅ Paper created successfully: {created_paper.title}")
        except Exception as e:
            if "UNIQUE constraint failed" in str(e):
                logger.info("✅ Paper already exists (expected)")
            else:
                raise
        
        # Test retrieval
        retrieved_paper = paper_repo.get_by_id("test_core_001")
        if retrieved_paper:
            logger.info(f"✅ Paper retrieved successfully: {retrieved_paper.title}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Database test failed: {e}")
        return False

def test_config_classes():
    """Test configuration classes (without ML dependencies)"""
    logger.info("Testing configuration classes...")
    
    try:
        # Test core configs that don't require ML imports
        from core.models import Paper, Entity, ProcessingStatus
        
        # Test Paper model
        paper = Paper(
            id="config_test_001",
            title="Config Test Paper",
            abstract="Testing configuration",
            authors=["Config Author"],
            journal="Config Journal", 
            publication_date="2024-01-01",
            doi="10.1234/config.001",
            paper_type="journal",
            source="pubmed",
            processing_status=ProcessingStatus.PENDING
        )
        logger.info(f"✅ Paper model works: {paper.title}")
        
        # Test Entity model
        entity = Entity(
            paper_id="config_test_001",
            entity_text="test_protein",
            entity_type="protein", 
            confidence=0.95,
            start_position=0,
            end_position=12,
            context="This test_protein is used for testing"
        )
        logger.info(f"✅ Entity model works: {entity.entity_text}")
        
        # Test ProcessingStatus enum
        status = ProcessingStatus.PROCESSING
        logger.info(f"✅ ProcessingStatus enum works: {status.value}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Config class test failed: {e}")
        return False

def test_ml_pipeline_structure():
    """Test ML pipeline file structure without imports"""
    logger.info("Testing ML pipeline file structure...")
    
    try:
        # Check if files exist
        src_dir = Path(__file__).parent / "src"
        processing_dir = src_dir / "processing"
        
        required_files = [
            "ml_models.py",
            "embedding_generator.py", 
            "entity_extractor.py",
            "nlp_pipeline.py"
        ]
        
        for file_name in required_files:
            file_path = processing_dir / file_name
            if file_path.exists():
                logger.info(f"✅ {file_name} exists")
            else:
                logger.error(f"❌ {file_name} missing")
                return False
                
        logger.info("✅ All ML pipeline files are present")
        return True
        
    except Exception as e:
        logger.error(f"❌ File structure test failed: {e}")
        return False

def main():
    """Run core-only tests"""
    logger.info("🧪 Starting Core-Only Tests")
    logger.info("=" * 50)
    
    test_results = []
    
    # Test 1: Core imports
    test_results.append(("Core Imports", test_core_imports()))
    
    # Test 2: PyTorch MPS  
    test_results.append(("PyTorch MPS", test_pytorch_mps()))
    
    # Test 3: Database
    test_results.append(("Database", test_database()))
    
    # Test 4: Config classes
    test_results.append(("Config Classes", test_config_classes()))
    
    # Test 5: ML pipeline structure
    test_results.append(("ML Pipeline Structure", test_ml_pipeline_structure()))
    
    # Print results
    logger.info("=" * 50)
    logger.info("🧪 Core Test Results") 
    logger.info("=" * 50)
    
    all_passed = True
    for test_name, passed in test_results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        logger.info(f"{test_name:25} {status}")
        if not passed:
            all_passed = False
    
    logger.info("=" * 50)
    
    if all_passed:
        logger.info("🎉 All core tests passed! Foundation is solid.")
        logger.info("ℹ️ ML functionality requires model downloads:")
        logger.info("   pip install huggingface_hub==0.17.3")  
        logger.info("   python -m spacy download en_core_sci_lg")
        return 0
    else:
        logger.error("❌ Some core tests failed.")
        return 1

if __name__ == "__main__":
    exit(main())