"""
Semantic Embedding Generation Module

This module handles the generation and management of semantic embeddings for papers
using sentence transformers optimized for M2 hardware.
"""

import logging
import time
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
from dataclasses import dataclass
from pathlib import Path
import json
import hashlib

from ..core.models import Paper
from ..core.repository import EmbeddingRepository
from .ml_models import get_model_manager, M2ModelManager

logger = logging.getLogger(__name__)

@dataclass
class EmbeddingConfig:
    """Configuration for embedding generation"""
    model_version: str = "all-MiniLM-L6-v2"
    chunk_size: int = 512  # Maximum text length per embedding
    overlap_size: int = 50  # Overlap between chunks
    min_text_length: int = 10  # Minimum text length to process
    batch_size: int = 32
    cache_embeddings: bool = True
    include_sections: List[str] = None  # Which sections to embed separately
    
    def __post_init__(self):
        if self.include_sections is None:
            self.include_sections = ["title", "abstract", "full_text"]


class EmbeddingGenerator:
    """
    Generates and manages semantic embeddings for literature papers.
    
    Features:
    - Document-level and section-level embeddings
    - Text chunking for long documents
    - Batch processing with M2 optimization
    - Embedding caching and versioning
    - Quality validation
    """
    
    def __init__(self, 
                 embedding_repo: EmbeddingRepository,
                 config: Optional[EmbeddingConfig] = None):
        self.embedding_repo = embedding_repo
        self.config = config or EmbeddingConfig()
        self.model_manager = get_model_manager()
        
        # Performance tracking
        self.stats = {
            "embeddings_generated": 0,
            "total_processing_time": 0.0,
            "cache_hits": 0,
            "cache_misses": 0
        }
        
        logger.info(f"EmbeddingGenerator initialized with model: {self.config.model_version}")
    
    def _create_text_chunks(self, text: str) -> List[str]:
        """
        Split long text into overlapping chunks for embedding generation
        """
        if len(text) <= self.config.chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + self.config.chunk_size
            
            # If we're not at the end, try to break at word boundary
            if end < len(text):
                # Look for space within the last 50 characters
                last_space = text.rfind(' ', end - 50, end)
                if last_space > start:
                    end = last_space
            
            chunk = text[start:end].strip()
            if len(chunk) >= self.config.min_text_length:
                chunks.append(chunk)
            
            # Move start position with overlap
            start = end - self.config.overlap_size
            
            # Prevent infinite loop
            if start >= len(text):
                break
        
        return chunks
    
    def _prepare_texts_for_embedding(self, paper: Paper) -> Dict[str, List[str]]:
        """
        Prepare different text sections for embedding generation
        """
        texts = {}
        
        if "title" in self.config.include_sections and paper.title:
            texts["title"] = [paper.title]
        
        if "abstract" in self.config.include_sections and paper.abstract:
            texts["abstract"] = [paper.abstract]
        
        if "full_text" in self.config.include_sections and paper.full_text:
            # Split full text into chunks
            texts["full_text"] = self._create_text_chunks(paper.full_text)
        
        # Combined text for document-level embedding
        combined_parts = []
        if paper.title:
            combined_parts.append(paper.title)
        if paper.abstract:
            combined_parts.append(paper.abstract)
        
        if combined_parts:
            combined_text = " ".join(combined_parts)
            texts["document"] = [combined_text]
        
        return texts
    
    def _calculate_text_hash(self, text: str) -> str:
        """Calculate hash for text to enable caching"""
        return hashlib.md5(text.encode('utf-8')).hexdigest()
    
    def _validate_embedding(self, embedding: np.ndarray) -> bool:
        """
        Validate embedding quality
        """
        if embedding is None or len(embedding) == 0:
            return False
        
        # Check for NaN or infinite values
        if np.any(np.isnan(embedding)) or np.any(np.isinf(embedding)):
            return False
        
        # Check if embedding is all zeros
        if np.allclose(embedding, 0):
            return False
        
        # Check embedding dimension (typically 384 for all-MiniLM-L6-v2)
        if len(embedding) < 100:  # Reasonable minimum dimension
            return False
        
        return True
    
    def generate_paper_embeddings(self, paper: Paper) -> Dict[str, Any]:
        """
        Generate embeddings for a single paper
        """
        start_time = time.time()
        
        try:
            # Check if embeddings already exist
            existing_embedding = self.embedding_repo.get_by_paper_id(paper.id)
            if existing_embedding and existing_embedding.model_version == self.config.model_version:
                logger.debug(f"Using cached embeddings for paper {paper.id}")
                self.stats["cache_hits"] += 1
                return existing_embedding.to_dict()
            
            self.stats["cache_misses"] += 1
            
            # Prepare texts for embedding
            section_texts = self._prepare_texts_for_embedding(paper)
            
            if not section_texts:
                logger.warning(f"No text content found for paper {paper.id}")
                return None
            
            # Generate embeddings for each section
            section_embeddings = {}
            all_texts = []
            text_to_section = {}
            
            # Collect all texts for batch processing
            for section, texts in section_texts.items():
                for i, text in enumerate(texts):
                    all_texts.append(text)
                    text_to_section[len(all_texts) - 1] = (section, i)
            
            if not all_texts:
                logger.warning(f"No valid texts to embed for paper {paper.id}")
                return None
            
            # Generate embeddings in batch
            logger.debug(f"Generating embeddings for {len(all_texts)} text segments")
            embeddings = self.model_manager.generate_embeddings(
                all_texts, 
                batch_size=self.config.batch_size
            )
            
            # Organize embeddings by section
            for idx, embedding in enumerate(embeddings):
                if not self._validate_embedding(embedding):
                    logger.warning(f"Invalid embedding generated for text {idx}")
                    continue
                
                section, text_idx = text_to_section[idx]
                
                if section not in section_embeddings:
                    section_embeddings[section] = []
                
                section_embeddings[section].append(embedding.tolist())
            
            # Create document-level embedding (average of all embeddings)
            if section_embeddings:
                all_embeddings = []
                for section_embs in section_embeddings.values():
                    all_embeddings.extend(section_embs)
                
                if all_embeddings:
                    document_embedding = np.mean(all_embeddings, axis=0)
                    
                    if self._validate_embedding(document_embedding):
                        section_embeddings["document_average"] = document_embedding.tolist()
            
            # Store embeddings in database
            embedding_data = {
                "paper_id": paper.id,
                "sections": section_embeddings,
                "model_version": self.config.model_version,
                "generation_time": time.time() - start_time,
                "text_count": len(all_texts)
            }
            
            # Save to database
            self.embedding_repo.create_or_update(
                paper_id=paper.id,
                embedding_data=section_embeddings,
                model_version=self.config.model_version
            )
            
            processing_time = time.time() - start_time
            self.stats["embeddings_generated"] += 1
            self.stats["total_processing_time"] += processing_time
            
            logger.info(f"Generated embeddings for paper {paper.id} in {processing_time:.2f}s "
                       f"({len(all_texts)} segments)")
            
            return embedding_data
            
        except Exception as e:
            logger.error(f"Failed to generate embeddings for paper {paper.id}: {e}")
            raise
    
    def generate_batch_embeddings(self, papers: List[Paper]) -> List[Dict[str, Any]]:
        """
        Generate embeddings for multiple papers with optimized batch processing
        """
        if not papers:
            return []
        
        start_time = time.time()
        logger.info(f"Generating embeddings for {len(papers)} papers")
        
        results = []
        
        # Process papers individually but with optimized batching within each paper
        for i, paper in enumerate(papers):
            try:
                result = self.generate_paper_embeddings(paper)
                if result:
                    results.append(result)
                
                # Log progress for large batches
                if (i + 1) % 10 == 0:
                    elapsed = time.time() - start_time
                    remaining = len(papers) - (i + 1)
                    eta = (elapsed / (i + 1)) * remaining
                    logger.info(f"Processed {i + 1}/{len(papers)} papers "
                               f"(ETA: {eta:.1f}s)")
                
            except Exception as e:
                logger.error(f"Failed to process paper {paper.id}: {e}")
                continue
        
        total_time = time.time() - start_time
        logger.info(f"Batch embedding generation completed: {len(results)} papers in {total_time:.2f}s "
                   f"({len(results)/total_time:.1f} papers/sec)")
        
        return results
    
    def find_similar_papers(self, 
                           query_embedding: np.ndarray, 
                           top_k: int = 10,
                           threshold: float = 0.7) -> List[Tuple[str, float]]:
        """
        Find papers similar to the query embedding using cosine similarity
        """
        try:
            # Get all embeddings from database
            all_embeddings = self.embedding_repo.get_all_embeddings()
            
            if not all_embeddings:
                logger.warning("No embeddings found in database")
                return []
            
            similarities = []
            
            for embedding_record in all_embeddings:
                # Use document-level embedding if available, otherwise use average
                paper_embedding = None
                
                if "document_average" in embedding_record.embedding_data:
                    paper_embedding = np.array(embedding_record.embedding_data["document_average"])
                elif "document" in embedding_record.embedding_data:
                    paper_embedding = np.array(embedding_record.embedding_data["document"][0])
                
                if paper_embedding is not None and self._validate_embedding(paper_embedding):
                    # Calculate cosine similarity
                    similarity = np.dot(query_embedding, paper_embedding) / (
                        np.linalg.norm(query_embedding) * np.linalg.norm(paper_embedding)
                    )
                    
                    if similarity >= threshold:
                        similarities.append((embedding_record.paper_id, float(similarity)))
            
            # Sort by similarity and return top k
            similarities.sort(key=lambda x: x[1], reverse=True)
            return similarities[:top_k]
            
        except Exception as e:
            logger.error(f"Failed to find similar papers: {e}")
            return []
    
    def get_paper_embedding(self, paper_id: str, section: str = "document_average") -> Optional[np.ndarray]:
        """
        Get embedding for a specific paper and section
        """
        try:
            embedding_record = self.embedding_repo.get_by_paper_id(paper_id)
            
            if not embedding_record:
                return None
            
            if section in embedding_record.embedding_data:
                embedding = embedding_record.embedding_data[section]
                
                # Handle list of embeddings (return first one)
                if isinstance(embedding, list) and len(embedding) > 0:
                    if isinstance(embedding[0], list):
                        embedding = embedding[0]
                
                return np.array(embedding)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get embedding for paper {paper_id}: {e}")
            return None
    
    def update_embeddings_for_new_model(self, new_model_version: str) -> int:
        """
        Update all embeddings when a new model version is used
        """
        logger.info(f"Updating embeddings for new model version: {new_model_version}")
        
        # Update config
        old_version = self.config.model_version
        self.config.model_version = new_model_version
        
        # Get all papers that need embedding updates
        outdated_count = self.embedding_repo.count_outdated_embeddings(new_model_version)
        
        logger.info(f"Found {outdated_count} papers with outdated embeddings "
                   f"(model version: {old_version} -> {new_model_version})")
        
        return outdated_count
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get embedding generation statistics"""
        stats = self.stats.copy()
        
        if stats["embeddings_generated"] > 0:
            stats["avg_processing_time"] = stats["total_processing_time"] / stats["embeddings_generated"]
        
        stats["cache_hit_rate"] = (
            stats["cache_hits"] / (stats["cache_hits"] + stats["cache_misses"])
            if (stats["cache_hits"] + stats["cache_misses"]) > 0 else 0
        )
        
        # Add model manager stats
        stats["model_performance"] = self.model_manager.get_performance_stats()
        
        return stats


# Convenience functions
def generate_paper_embeddings(paper: Paper, 
                            embedding_repo: EmbeddingRepository,
                            config: Optional[EmbeddingConfig] = None) -> Dict[str, Any]:
    """Convenience function to generate embeddings for a single paper"""
    generator = EmbeddingGenerator(embedding_repo, config)
    return generator.generate_paper_embeddings(paper)

def generate_batch_embeddings(papers: List[Paper],
                            embedding_repo: EmbeddingRepository, 
                            config: Optional[EmbeddingConfig] = None) -> List[Dict[str, Any]]:
    """Convenience function to generate embeddings for multiple papers"""
    generator = EmbeddingGenerator(embedding_repo, config)
    return generator.generate_batch_embeddings(papers)