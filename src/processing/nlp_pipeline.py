"""
Comprehensive NLP Pipeline for Literature Processing

This module coordinates the complete NLP processing pipeline, integrating
embedding generation, entity extraction, and other text processing tasks.
"""

import logging
import time
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
import json

from ..core.models import Paper, Entity
from ..core.repository import PaperRepository, EmbeddingRepository, EntityRepository
from .ml_models import get_model_manager, cleanup_models
from .embedding_generator import EmbeddingGenerator, EmbeddingConfig
from .entity_extractor import EntityExtractor, EntityExtractionConfig
from .pdf_processor import PDFProcessor

logger = logging.getLogger(__name__)

@dataclass
class PipelineConfig:
    """Configuration for the complete NLP pipeline"""
    # Processing stages to run
    extract_text: bool = True
    generate_embeddings: bool = True
    extract_entities: bool = True
    calculate_relevance: bool = True
    
    # Batch processing settings
    batch_size: int = 10
    max_workers: int = 4
    parallel_processing: bool = True
    
    # Model configurations
    embedding_config: Optional[EmbeddingConfig] = None
    entity_config: Optional[EntityExtractionConfig] = None
    
    # Performance settings
    enable_warmup: bool = True
    cleanup_on_complete: bool = True
    monitor_performance: bool = True
    
    def __post_init__(self):
        if self.embedding_config is None:
            self.embedding_config = EmbeddingConfig()
        if self.entity_config is None:
            self.entity_config = EntityExtractionConfig()


class PipelineStats:
    """Statistics tracking for pipeline performance"""
    
    def __init__(self):
        self.reset()
    
    def reset(self):
        self.papers_processed = 0
        self.papers_failed = 0
        self.total_processing_time = 0.0
        self.stage_times = {
            "text_extraction": 0.0,
            "embedding_generation": 0.0,
            "entity_extraction": 0.0,
            "relevance_calculation": 0.0
        }
        self.entities_extracted = 0
        self.embeddings_generated = 0
        self.start_time = None
        self.end_time = None
    
    def start_processing(self):
        self.start_time = time.time()
    
    def end_processing(self):
        self.end_time = time.time()
        if self.start_time:
            self.total_processing_time = self.end_time - self.start_time
    
    def add_stage_time(self, stage: str, duration: float):
        if stage in self.stage_times:
            self.stage_times[stage] += duration
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "papers_processed": self.papers_processed,
            "papers_failed": self.papers_failed,
            "success_rate": self.papers_processed / (self.papers_processed + self.papers_failed) 
                          if (self.papers_processed + self.papers_failed) > 0 else 0,
            "total_processing_time": self.total_processing_time,
            "avg_time_per_paper": self.total_processing_time / self.papers_processed 
                                 if self.papers_processed > 0 else 0,
            "stage_times": self.stage_times,
            "entities_extracted": self.entities_extracted,
            "embeddings_generated": self.embeddings_generated,
            "throughput": self.papers_processed / self.total_processing_time 
                         if self.total_processing_time > 0 else 0
        }


class NLPPipeline:
    """
    Comprehensive NLP processing pipeline for literature analysis.
    
    Features:
    - Coordinated text processing workflow
    - Parallel processing with configurable workers
    - Comprehensive error handling and recovery
    - Performance monitoring and optimization
    - M2 hardware optimization
    """
    
    def __init__(self, 
                 paper_repo: PaperRepository,
                 embedding_repo: EmbeddingRepository,
                 entity_repo: EntityRepository,
                 config: Optional[PipelineConfig] = None):
        
        self.paper_repo = paper_repo
        self.embedding_repo = embedding_repo
        self.entity_repo = entity_repo
        self.config = config or PipelineConfig()
        
        # Initialize components
        self.pdf_processor = PDFProcessor()
        self.embedding_generator = EmbeddingGenerator(embedding_repo, self.config.embedding_config)
        self.entity_extractor = EntityExtractor(entity_repo, self.config.entity_config)
        self.model_manager = get_model_manager()
        
        # Statistics tracking
        self.stats = PipelineStats()
        
        logger.info("NLP Pipeline initialized")
    
    def _calculate_relevance_score(self, paper: Paper) -> float:
        """
        Calculate relevance score for protein design research
        """
        try:
            score = 0.0
            
            # Keyword-based scoring for protein design relevance
            protein_keywords = [
                'protein', 'peptide', 'enzyme', 'antibody', 'antigen',
                'folding', 'structure', 'design', 'engineering', 'modeling',
                'binding', 'interaction', 'crystal', 'nmr', 'cryo-em',
                'mutation', 'variant', 'evolution', 'directed evolution'
            ]
            
            # Score based on title
            if paper.title:
                title_lower = paper.title.lower()
                title_matches = sum(1 for keyword in protein_keywords if keyword in title_lower)
                score += title_matches * 0.3
            
            # Score based on abstract
            if paper.abstract:
                abstract_lower = paper.abstract.lower()
                abstract_matches = sum(1 for keyword in protein_keywords if keyword in abstract_lower)
                score += abstract_matches * 0.2
            
            # Journal-based scoring
            high_impact_journals = [
                'nature', 'science', 'cell', 'pnas', 'nature biotechnology',
                'nature structural', 'protein science', 'journal of molecular biology'
            ]
            
            if paper.journal:
                journal_lower = paper.journal.lower()
                if any(journal in journal_lower for journal in high_impact_journals):
                    score += 1.0
            
            # Normalize score to 0-1 range
            max_possible_score = len(protein_keywords) * 0.5 + 1.0
            normalized_score = min(score / max_possible_score, 1.0)
            
            return normalized_score
            
        except Exception as e:
            logger.warning(f"Failed to calculate relevance score for paper {paper.id}: {e}")
            return 0.5  # Default score
    
    def _process_single_paper(self, paper: Paper) -> Dict[str, Any]:
        """
        Process a single paper through the complete pipeline
        """
        start_time = time.time()
        result = {
            "paper_id": paper.id,
            "success": False,
            "stages_completed": [],
            "errors": [],
            "processing_time": 0.0,
            "entities_count": 0,
            "embedding_generated": False,
            "relevance_score": 0.0
        }
        
        try:
            logger.debug(f"Processing paper {paper.id}")
            
            # Stage 1: Text extraction (if needed)
            if self.config.extract_text and not paper.full_text:
                stage_start = time.time()
                try:
                    if paper.local_pdf_path:
                        processing_result = self.pdf_processor.process_pdf(paper.local_pdf_path)
                        if processing_result and processing_result.full_text:
                            paper.full_text = processing_result.full_text
                            # Update paper in database
                            self.paper_repo.update(paper.id, {"full_text": paper.full_text})
                            logger.debug(f"Extracted text for paper {paper.id}")
                    
                    result["stages_completed"].append("text_extraction")
                    self.stats.add_stage_time("text_extraction", time.time() - stage_start)
                    
                except Exception as e:
                    logger.warning(f"Text extraction failed for paper {paper.id}: {e}")
                    result["errors"].append(f"text_extraction: {str(e)}")
            
            # Stage 2: Embedding generation
            if self.config.generate_embeddings:
                stage_start = time.time()
                try:
                    embedding_result = self.embedding_generator.generate_paper_embeddings(paper)
                    if embedding_result:
                        result["embedding_generated"] = True
                        result["stages_completed"].append("embedding_generation")
                        self.stats.embeddings_generated += 1
                    
                    self.stats.add_stage_time("embedding_generation", time.time() - stage_start)
                    
                except Exception as e:
                    logger.error(f"Embedding generation failed for paper {paper.id}: {e}")
                    result["errors"].append(f"embedding_generation: {str(e)}")
            
            # Stage 3: Entity extraction
            if self.config.extract_entities:
                stage_start = time.time()
                try:
                    entities = self.entity_extractor.extract_paper_entities(paper)
                    result["entities_count"] = len(entities)
                    result["stages_completed"].append("entity_extraction")
                    self.stats.entities_extracted += len(entities)
                    
                    self.stats.add_stage_time("entity_extraction", time.time() - stage_start)
                    
                except Exception as e:
                    logger.error(f"Entity extraction failed for paper {paper.id}: {e}")
                    result["errors"].append(f"entity_extraction: {str(e)}")
            
            # Stage 4: Relevance calculation
            if self.config.calculate_relevance:
                stage_start = time.time()
                try:
                    relevance_score = self._calculate_relevance_score(paper)
                    result["relevance_score"] = relevance_score
                    
                    # Update paper with relevance score
                    self.paper_repo.update(paper.id, {"relevance_score": relevance_score})
                    result["stages_completed"].append("relevance_calculation")
                    
                    self.stats.add_stage_time("relevance_calculation", time.time() - stage_start)
                    
                except Exception as e:
                    logger.warning(f"Relevance calculation failed for paper {paper.id}: {e}")
                    result["errors"].append(f"relevance_calculation: {str(e)}")
            
            # Mark as successful if at least one stage completed
            if result["stages_completed"]:
                result["success"] = True
                self.stats.papers_processed += 1
            else:
                self.stats.papers_failed += 1
            
        except Exception as e:
            logger.error(f"Unexpected error processing paper {paper.id}: {e}")
            result["errors"].append(f"unexpected_error: {str(e)}")
            self.stats.papers_failed += 1
        
        result["processing_time"] = time.time() - start_time
        return result
    
    def process_papers(self, papers: List[Paper]) -> Dict[str, Any]:
        """
        Process multiple papers through the pipeline
        """
        if not papers:
            logger.warning("No papers provided for processing")
            return {"results": [], "stats": self.stats.to_dict()}
        
        logger.info(f"Starting NLP pipeline for {len(papers)} papers")
        self.stats.reset()
        self.stats.start_processing()
        
        # Warm up models if configured
        if self.config.enable_warmup:
            logger.info("Warming up ML models...")
            self.model_manager.warmup_models()
        
        results = []
        
        if self.config.parallel_processing and len(papers) > 1:
            # Parallel processing
            results = self._process_papers_parallel(papers)
        else:
            # Sequential processing
            results = self._process_papers_sequential(papers)
        
        self.stats.end_processing()
        
        # Cleanup if configured
        if self.config.cleanup_on_complete:
            logger.info("Cleaning up models...")
            cleanup_models()
        
        final_stats = self.stats.to_dict()
        logger.info(f"Pipeline completed: {final_stats['papers_processed']} papers processed, "
                   f"{final_stats['papers_failed']} failed, "
                   f"{final_stats['total_processing_time']:.2f}s total time")
        
        return {
            "results": results,
            "stats": final_stats,
            "config": {
                "batch_size": self.config.batch_size,
                "parallel_processing": self.config.parallel_processing,
                "stages_enabled": {
                    "extract_text": self.config.extract_text,
                    "generate_embeddings": self.config.generate_embeddings,
                    "extract_entities": self.config.extract_entities,
                    "calculate_relevance": self.config.calculate_relevance
                }
            }
        }
    
    def _process_papers_sequential(self, papers: List[Paper]) -> List[Dict[str, Any]]:
        """Process papers sequentially"""
        results = []
        
        for i, paper in enumerate(papers):
            result = self._process_single_paper(paper)
            results.append(result)
            
            # Log progress
            if (i + 1) % 10 == 0 or (i + 1) == len(papers):
                logger.info(f"Processed {i + 1}/{len(papers)} papers")
        
        return results
    
    def _process_papers_parallel(self, papers: List[Paper]) -> List[Dict[str, Any]]:
        """Process papers in parallel using ThreadPoolExecutor"""
        results = []
        completed_count = 0
        
        with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
            # Submit all papers for processing
            future_to_paper = {
                executor.submit(self._process_single_paper, paper): paper 
                for paper in papers
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_paper):
                paper = future_to_paper[future]
                try:
                    result = future.result()
                    results.append(result)
                    completed_count += 1
                    
                    # Log progress
                    if completed_count % 10 == 0 or completed_count == len(papers):
                        logger.info(f"Completed {completed_count}/{len(papers)} papers")
                        
                except Exception as e:
                    logger.error(f"Failed to process paper {paper.id}: {e}")
                    results.append({
                        "paper_id": paper.id,
                        "success": False,
                        "errors": [f"execution_error: {str(e)}"]
                    })
                    self.stats.papers_failed += 1
        
        # Sort results by paper order
        paper_order = {paper.id: i for i, paper in enumerate(papers)}
        results.sort(key=lambda x: paper_order.get(x["paper_id"], len(papers)))
        
        return results
    
    def process_new_papers(self, limit: Optional[int] = None) -> Dict[str, Any]:
        """
        Process all papers that haven't been processed yet
        """
        # Get papers that need processing (no embeddings or entities)
        unprocessed_papers = []
        
        # Check for papers without embeddings
        if self.config.generate_embeddings:
            papers_without_embeddings = self.paper_repo.get_papers_without_embeddings(limit)
            unprocessed_papers.extend(papers_without_embeddings)
        
        # Check for papers without entities
        if self.config.extract_entities:
            papers_without_entities = self.paper_repo.get_papers_without_entities(limit)
            # Add papers that aren't already in the list
            existing_ids = {p.id for p in unprocessed_papers}
            for paper in papers_without_entities:
                if paper.id not in existing_ids:
                    unprocessed_papers.append(paper)
        
        if not unprocessed_papers:
            logger.info("No unprocessed papers found")
            return {"results": [], "stats": self.stats.to_dict()}
        
        # Limit if specified
        if limit and len(unprocessed_papers) > limit:
            unprocessed_papers = unprocessed_papers[:limit]
        
        logger.info(f"Found {len(unprocessed_papers)} papers that need processing")
        return self.process_papers(unprocessed_papers)
    
    def get_pipeline_status(self) -> Dict[str, Any]:
        """Get current pipeline status and statistics"""
        return {
            "stats": self.stats.to_dict(),
            "config": {
                "batch_size": self.config.batch_size,
                "max_workers": self.config.max_workers,
                "parallel_processing": self.config.parallel_processing
            },
            "component_stats": {
                "embedding_generator": self.embedding_generator.get_statistics(),
                "entity_extractor": self.entity_extractor.get_processing_statistics(),
                "model_manager": self.model_manager.get_performance_stats()
            }
        }


# Convenience functions
def process_papers_pipeline(papers: List[Paper],
                          paper_repo: PaperRepository,
                          embedding_repo: EmbeddingRepository,
                          entity_repo: EntityRepository,
                          config: Optional[PipelineConfig] = None) -> Dict[str, Any]:
    """Convenience function to process papers through the complete pipeline"""
    pipeline = NLPPipeline(paper_repo, embedding_repo, entity_repo, config)
    return pipeline.process_papers(papers)

def process_new_papers_pipeline(paper_repo: PaperRepository,
                              embedding_repo: EmbeddingRepository,
                              entity_repo: EntityRepository,
                              limit: Optional[int] = None,
                              config: Optional[PipelineConfig] = None) -> Dict[str, Any]:
    """Convenience function to process all new papers"""
    pipeline = NLPPipeline(paper_repo, embedding_repo, entity_repo, config)
    return pipeline.process_new_papers(limit)