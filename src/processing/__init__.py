"""Text processing and NLP modules."""

from .pdf_processor import PDFProcessor, ProcessingResult, process_papers_batch, process_single_paper
from .ml_models import M2ModelManager, ModelConfig, get_model_manager, generate_embeddings, extract_entities, cleanup_models
from .embedding_generator import EmbeddingGenerator, EmbeddingConfig, generate_paper_embeddings, generate_batch_embeddings
from .entity_extractor import EntityExtractor, EntityExtractionConfig, EntityType, extract_paper_entities, extract_batch_entities
from .nlp_pipeline import NLPPipeline, PipelineConfig, process_papers_pipeline, process_new_papers_pipeline

__all__ = [
    # PDF Processing
    "PDFProcessor",
    "ProcessingResult", 
    "process_papers_batch",
    "process_single_paper",
    
    # ML Models
    "M2ModelManager",
    "ModelConfig", 
    "get_model_manager",
    "generate_embeddings",
    "extract_entities",
    "cleanup_models",
    
    # Embedding Generation
    "EmbeddingGenerator",
    "EmbeddingConfig",
    "generate_paper_embeddings", 
    "generate_batch_embeddings",
    
    # Entity Extraction
    "EntityExtractor",
    "EntityExtractionConfig",
    "EntityType",
    "extract_paper_entities",
    "extract_batch_entities",
    
    # NLP Pipeline
    "NLPPipeline",
    "PipelineConfig",
    "process_papers_pipeline",
    "process_new_papers_pipeline"
]