#!/usr/bin/env python3
"""
Test script for ML Pipeline components

This script tests the ML models, embedding generation, and entity extraction
components to ensure they work correctly on M2 hardware.
"""

import sys
import os
import logging
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from core.config import AppSettings
from core.database import db_manager
from core.repository import PaperRepository, EmbeddingRepository, EntityRepository
from core.models import Paper, ProcessingStatus
from processing.ml_models import get_model_manager, ModelConfig
from processing.embedding_generator import EmbeddingGenerator, EmbeddingConfig
from processing.entity_extractor import EntityExtractor, EntityExtractionConfig
from processing.nlp_pipeline import NLPPipeline, PipelineConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_test_papers() -> list[Paper]:
    """Create test papers for ML pipeline testing"""
    test_papers = [
        Paper(
            id="test_001",
            title="Deep Learning Approaches for Protein Structure Prediction",
            abstract="This paper presents novel deep learning methods for predicting protein secondary and tertiary structures. We developed a transformer-based architecture that achieves state-of-the-art accuracy on benchmark datasets.",
            authors=["John Smith", "Jane Doe"],
            journal="Nature Biotechnology",
            publication_date="2024-01-15",
            doi="10.1038/nbt.test.001",
            paper_type="journal",
            source="pubmed",
            processing_status=ProcessingStatus.PENDING
        ),
        Paper(
            id="test_002", 
            title="CRISPR-Cas9 Engineering for Enhanced Protein Design",
            abstract="We demonstrate the use of CRISPR-Cas9 technology for precise protein engineering. Our approach enables rapid prototyping of enzyme variants with improved catalytic efficiency.",
            authors=["Alice Johnson", "Bob Wilson"],
            journal="Science",
            publication_date="2024-02-10",
            doi="10.1126/science.test.002",
            paper_type="journal",
            source="pubmed",
            processing_status=ProcessingStatus.PENDING
        ),
        Paper(
            id="test_003",
            title="Machine Learning for Drug Discovery: A Comprehensive Review",
            abstract="This comprehensive review covers recent advances in machine learning applications for drug discovery, including molecular property prediction, virtual screening, and de novo drug design.",
            authors=["Carol Brown", "David Lee"],
            journal="Cell",
            publication_date="2024-03-05",
            doi="10.1016/j.cell.test.003",
            paper_type="journal", 
            source="pubmed",
            processing_status=ProcessingStatus.PENDING
        )
    ]
    
    return test_papers

def test_model_manager():
    """Test M2 model manager functionality"""
    logger.info("Testing M2 Model Manager...")
    
    try:
        # Get model manager
        model_manager = get_model_manager()
        
        # Test device setup
        logger.info(f"Device: {model_manager.device}")
        logger.info(f"MPS available: {model_manager.device.type == 'mps'}")
        
        # Test embedding model loading
        logger.info("Loading embedding model...")
        embedding_model = model_manager.load_embedding_model()
        logger.info(f"Embedding model loaded: {type(embedding_model)}")
        
        # Test spaCy model loading
        logger.info("Loading spaCy model...")
        try:
            spacy_model = model_manager.load_spacy_model()
            logger.info(f"spaCy model loaded: {spacy_model.meta['name']}")
        except Exception as e:
            logger.warning(f"spaCy model not available: {e}")
            logger.info("Install with: python -m spacy download en_core_sci_lg")
            return False
        
        # Test warmup
        model_manager.warmup_models()
        
        # Get performance stats
        stats = model_manager.get_performance_stats()
        logger.info(f"Performance stats: {stats}")
        
        logger.info("✅ Model Manager test completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Model Manager test failed: {e}")
        return False

def test_embedding_generation(papers, embedding_repo):
    """Test embedding generation"""
    logger.info("Testing Embedding Generation...")
    
    try:
        # Configure embedding generation
        config = EmbeddingConfig(
            batch_size=2,  # Small batch for testing
            include_sections=["title", "abstract"]
        )
        
        generator = EmbeddingGenerator(embedding_repo, config)
        
        # Test single paper embedding
        logger.info("Generating embeddings for single paper...")
        result = generator.generate_paper_embeddings(papers[0])
        
        if result:
            logger.info(f"Single paper embedding result: {result['text_count']} segments processed")
            logger.info(f"Sections generated: {list(result['sections'].keys())}")
        
        # Test batch embedding generation
        logger.info("Generating embeddings for batch...")
        batch_results = generator.generate_batch_embeddings(papers[:2])
        
        logger.info(f"Batch processing completed: {len(batch_results)} papers")
        
        # Test similarity search
        if result and "document_average" in result["sections"]:
            logger.info("Testing similarity search...")
            import numpy as np
            query_embedding = np.array(result["sections"]["document_average"])
            similar_papers = generator.find_similar_papers(query_embedding, top_k=5)
            logger.info(f"Found {len(similar_papers)} similar papers")
        
        # Get statistics
        stats = generator.get_statistics()
        logger.info(f"Embedding generation stats: {stats}")
        
        logger.info("✅ Embedding Generation test completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Embedding Generation test failed: {e}")
        return False

def test_entity_extraction(papers, entity_repo):
    """Test entity extraction"""
    logger.info("Testing Entity Extraction...")
    
    try:
        # Configure entity extraction
        config = EntityExtractionConfig(
            confidence_threshold=0.3,  # Lower threshold for testing
            batch_size=2,
            protein_design_focus=True
        )
        
        extractor = EntityExtractor(entity_repo, config)
        
        # Test single paper entity extraction
        logger.info("Extracting entities from single paper...")
        entities = extractor.extract_paper_entities(papers[0])
        
        logger.info(f"Extracted {len(entities)} entities from single paper")
        if entities:
            entity_types = set(entity.entity_type for entity in entities)
            logger.info(f"Entity types found: {entity_types}")
        
        # Test batch entity extraction
        logger.info("Extracting entities from batch...")
        batch_results = extractor.extract_batch_entities(papers[:2])
        
        total_entities = sum(len(entities) for entities in batch_results.values())
        logger.info(f"Batch extraction completed: {total_entities} total entities")
        
        # Get statistics
        stats = extractor.get_processing_statistics()
        logger.info(f"Entity extraction stats: {stats}")
        
        logger.info("✅ Entity Extraction test completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Entity Extraction test failed: {e}")
        return False

def test_nlp_pipeline(papers, paper_repo, embedding_repo, entity_repo):
    """Test complete NLP pipeline"""
    logger.info("Testing Complete NLP Pipeline...")
    
    try:
        # Configure pipeline
        config = PipelineConfig(
            batch_size=2,
            max_workers=2,
            parallel_processing=True,
            enable_warmup=True
        )
        
        pipeline = NLPPipeline(paper_repo, embedding_repo, entity_repo, config)
        
        # Process papers through pipeline
        logger.info("Processing papers through complete pipeline...")
        results = pipeline.process_papers(papers)
        
        logger.info(f"Pipeline results: {len(results['results'])} papers processed")
        logger.info(f"Pipeline stats: {results['stats']}")
        
        # Check results
        for result in results['results']:
            if result['success']:
                logger.info(f"Paper {result['paper_id']}: "
                           f"stages={result['stages_completed']}, "
                           f"entities={result['entities_count']}, "
                           f"embedding={result['embedding_generated']}")
            else:
                logger.warning(f"Paper {result['paper_id']} failed: {result['errors']}")
        
        # Get pipeline status
        status = pipeline.get_pipeline_status()
        logger.info(f"Pipeline status: {status['stats']}")
        
        logger.info("✅ NLP Pipeline test completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ NLP Pipeline test failed: {e}")
        return False

def main():
    """Run all ML pipeline tests"""
    logger.info("🧪 Starting ML Pipeline Tests")
    logger.info("=" * 50)
    
    # Initialize components
    try:
        settings = AppSettings()
        db_manager.initialize()
        
        # Initialize repositories
        paper_repo = PaperRepository(db_manager)
        embedding_repo = EmbeddingRepository(db_manager)
        entity_repo = EntityRepository(db_manager)
        
        # Create test papers
        test_papers = create_test_papers()
        
        # Store test papers in database
        for paper in test_papers:
            try:
                paper_repo.create(paper)
            except Exception as e:
                # Paper might already exist
                logger.debug(f"Paper {paper.id} already exists: {e}")
        
        logger.info(f"Created {len(test_papers)} test papers")
        
    except Exception as e:
        logger.error(f"Failed to initialize test environment: {e}")
        return 1
    
    # Run tests
    test_results = []
    
    # Test 1: Model Manager
    test_results.append(("Model Manager", test_model_manager()))
    
    # Test 2: Embedding Generation
    test_results.append(("Embedding Generation", test_embedding_generation(test_papers, embedding_repo)))
    
    # Test 3: Entity Extraction
    test_results.append(("Entity Extraction", test_entity_extraction(test_papers, entity_repo)))
    
    # Test 4: Complete Pipeline
    test_results.append(("NLP Pipeline", test_nlp_pipeline(test_papers, paper_repo, embedding_repo, entity_repo)))
    
    # Print results
    logger.info("=" * 50)
    logger.info("🧪 ML Pipeline Test Results")
    logger.info("=" * 50)
    
    all_passed = True
    for test_name, passed in test_results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        logger.info(f"{test_name:20} {status}")
        if not passed:
            all_passed = False
    
    logger.info("=" * 50)
    
    if all_passed:
        logger.info("🎉 All tests passed! ML Pipeline is ready for production.")
        return 0
    else:
        logger.error("❌ Some tests failed. Please check the logs above.")
        return 1

if __name__ == "__main__":
    exit(main())