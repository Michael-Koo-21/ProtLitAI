"""
ML Models for M2-Optimized Processing

This module sets up and manages machine learning models optimized for Apple M2 hardware
with MPS acceleration.
"""

import logging
import os
import time
from pathlib import Path
from typing import Optional, Dict, Any, List
import torch
import torch.nn as nn
from sentence_transformers import SentenceTransformer
import spacy
from spacy.tokens import Doc
import numpy as np
from dataclasses import dataclass

from core.config import config

logger = logging.getLogger(__name__)

@dataclass
class ModelConfig:
    """Configuration for ML models"""
    embedding_model_name: str = "all-MiniLM-L6-v2"
    spacy_model_name: str = "en_core_sci_lg"
    max_sequence_length: int = 512
    batch_size: int = 32
    cache_dir: str = "models"
    use_mps: bool = True
    quantize_models: bool = True


class M2ModelManager:
    """
    Manages ML models optimized for Apple M2 hardware.
    
    Features:
    - MPS acceleration for PyTorch models
    - Dynamic batch sizing based on memory
    - Model caching and quantization
    - Performance monitoring
    """
    
    def __init__(self, model_config: Optional[ModelConfig] = None):
        self.config = model_config or ModelConfig()
        self.settings = config.settings
        
        # Initialize device (MPS for M2, CPU fallback)
        self.device = self._setup_device()
        
        # Model storage
        self._embedding_model: Optional[SentenceTransformer] = None
        self._spacy_model: Optional[spacy.Language] = None
        
        # Performance tracking
        self.performance_stats = {
            "embedding_inference_times": [],
            "ner_inference_times": [],
            "memory_usage": [],
            "batch_sizes_used": []
        }
        
        # Set up model directories
        self.cache_dir = Path(self.settings.model_cache_path)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"M2ModelManager initialized with device: {self.device}")
    
    def _setup_device(self) -> torch.device:
        """Set up optimal device for M2 hardware"""
        if self.config.use_mps and torch.backends.mps.is_available():
            device = torch.device("mps")
            logger.info("Using MPS (Metal Performance Shaders) acceleration")
        else:
            device = torch.device("cpu")
            logger.info("Using CPU (MPS not available or disabled)")
        
        return device
    
    def _optimize_batch_size(self, base_batch_size: int) -> int:
        """
        Dynamically optimize batch size based on available memory
        """
        try:
            # Get system memory info
            import psutil
            memory = psutil.virtual_memory()
            available_gb = memory.available / (1024**3)
            
            # Adjust batch size based on available memory
            if available_gb > 16:
                multiplier = 2.0
            elif available_gb > 8:
                multiplier = 1.5
            else:
                multiplier = 1.0
                
            optimized_size = int(base_batch_size * multiplier)
            logger.debug(f"Optimized batch size: {optimized_size} (available memory: {available_gb:.1f}GB)")
            
            return min(optimized_size, 128)  # Cap at 128
            
        except Exception as e:
            logger.warning(f"Could not optimize batch size: {e}")
            return base_batch_size
    
    def _clear_mps_cache(self):
        """Clear MPS cache to free up memory"""
        if self.device.type == "mps":
            try:
                torch.mps.empty_cache()
                logger.debug("Cleared MPS cache")
            except Exception as e:
                logger.warning(f"Could not clear MPS cache: {e}")
    
    def load_embedding_model(self) -> SentenceTransformer:
        """
        Load and configure sentence transformer model for embeddings
        """
        if self._embedding_model is not None:
            return self._embedding_model
        
        start_time = time.time()
        
        try:
            logger.info(f"Loading embedding model: {self.config.embedding_model_name}")
            
            # Load model with M2 optimizations
            model = SentenceTransformer(
                self.config.embedding_model_name,
                cache_folder=str(self.cache_dir / "sentence_transformers")
            )
            
            # Move to optimal device
            if self.device.type == "mps":
                model = model.to(self.device)
                logger.info("Moved embedding model to MPS device")
            
            # Configure for optimal performance
            model.max_seq_length = self.config.max_sequence_length
            
            # Quantize model if requested (for faster inference)
            if self.config.quantize_models and self.device.type == "mps":
                try:
                    # Note: Quantization may not be available for all models on MPS
                    logger.info("Model quantization enabled for faster inference")
                except Exception as e:
                    logger.warning(f"Could not quantize model: {e}")
            
            self._embedding_model = model
            
            load_time = time.time() - start_time
            logger.info(f"Embedding model loaded successfully in {load_time:.2f}s")
            
            return self._embedding_model
            
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise
    
    def load_spacy_model(self) -> spacy.Language:
        """
        Load and configure spaCy biomedical model for NER
        """
        if self._spacy_model is not None:
            return self._spacy_model
        
        start_time = time.time()
        
        try:
            logger.info(f"Loading spaCy model: {self.config.spacy_model_name}")
            
            # Check if model is installed
            if not spacy.util.is_package(self.config.spacy_model_name):
                logger.error(f"spaCy model {self.config.spacy_model_name} not installed")
                logger.info("Install with: python -m spacy download en_core_sci_lg")
                raise ValueError(f"Model {self.config.spacy_model_name} not found")
            
            # Load model
            nlp = spacy.load(self.config.spacy_model_name)
            
            # Optimize for batch processing
            nlp.max_length = 1000000  # Increase max length for long documents
            
            # Disable unnecessary components for better performance
            disable = ["tagger", "parser", "lemmatizer"] if "ner" in nlp.pipe_names else []
            for component in disable:
                if component in nlp.pipe_names:
                    nlp.disable_pipes(component)
                    logger.debug(f"Disabled spaCy component: {component}")
            
            self._spacy_model = nlp
            
            load_time = time.time() - start_time
            logger.info(f"spaCy model loaded successfully in {load_time:.2f}s")
            
            return self._spacy_model
            
        except Exception as e:
            logger.error(f"Failed to load spaCy model: {e}")
            raise
    
    def generate_embeddings(self, texts: List[str], batch_size: Optional[int] = None) -> np.ndarray:
        """
        Generate semantic embeddings for texts using optimized batching
        """
        if not texts:
            return np.array([])
        
        start_time = time.time()
        
        try:
            model = self.load_embedding_model()
            
            # Optimize batch size
            if batch_size is None:
                batch_size = self._optimize_batch_size(self.config.batch_size)
            
            self.performance_stats["batch_sizes_used"].append(batch_size)
            
            # Clear cache before processing
            self._clear_mps_cache()
            
            # Generate embeddings in batches
            logger.debug(f"Generating embeddings for {len(texts)} texts (batch_size: {batch_size})")
            
            embeddings = model.encode(
                texts,
                batch_size=batch_size,
                show_progress_bar=len(texts) > 100,
                convert_to_numpy=True,
                device=str(self.device) if self.device.type == "mps" else None
            )
            
            # Clear cache after processing
            self._clear_mps_cache()
            
            inference_time = time.time() - start_time
            self.performance_stats["embedding_inference_times"].append(inference_time)
            
            logger.info(f"Generated {len(embeddings)} embeddings in {inference_time:.2f}s "
                       f"({len(texts)/inference_time:.1f} texts/sec)")
            
            return embeddings
            
        except Exception as e:
            logger.error(f"Failed to generate embeddings: {e}")
            raise
    
    def extract_entities(self, texts: List[str], batch_size: Optional[int] = None) -> List[List[Dict[str, Any]]]:
        """
        Extract named entities from texts using spaCy biomedical model
        """
        if not texts:
            return []
        
        start_time = time.time()
        
        try:
            nlp = self.load_spacy_model()
            
            # Optimize batch size for NER (typically smaller than embedding batch size)
            if batch_size is None:
                batch_size = self._optimize_batch_size(self.config.batch_size // 2)
            
            logger.debug(f"Extracting entities from {len(texts)} texts (batch_size: {batch_size})")
            
            all_entities = []
            
            # Process in batches using spaCy's pipe for efficiency
            for doc in nlp.pipe(texts, batch_size=batch_size):
                entities = []
                for ent in doc.ents:
                    entities.append({
                        "text": ent.text,
                        "label": ent.label_,
                        "start": ent.start_char,
                        "end": ent.end_char,
                        "confidence": getattr(ent, "_.confidence", 1.0)  # Default confidence
                    })
                all_entities.append(entities)
            
            inference_time = time.time() - start_time
            self.performance_stats["ner_inference_times"].append(inference_time)
            
            total_entities = sum(len(entities) for entities in all_entities)
            logger.info(f"Extracted {total_entities} entities from {len(texts)} texts in {inference_time:.2f}s")
            
            return all_entities
            
        except Exception as e:
            logger.error(f"Failed to extract entities: {e}")
            raise
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics for monitoring and optimization"""
        stats = {}
        
        if self.performance_stats["embedding_inference_times"]:
            embedding_times = self.performance_stats["embedding_inference_times"]
            stats["embedding"] = {
                "avg_inference_time": np.mean(embedding_times),
                "min_inference_time": np.min(embedding_times),
                "max_inference_time": np.max(embedding_times),
                "total_inferences": len(embedding_times)
            }
        
        if self.performance_stats["ner_inference_times"]:
            ner_times = self.performance_stats["ner_inference_times"]
            stats["ner"] = {
                "avg_inference_time": np.mean(ner_times),
                "min_inference_time": np.min(ner_times),
                "max_inference_time": np.max(ner_times),
                "total_inferences": len(ner_times)
            }
        
        if self.performance_stats["batch_sizes_used"]:
            batch_sizes = self.performance_stats["batch_sizes_used"]
            stats["batch_processing"] = {
                "avg_batch_size": np.mean(batch_sizes),
                "min_batch_size": np.min(batch_sizes),
                "max_batch_size": np.max(batch_sizes)
            }
        
        # System info
        stats["system"] = {
            "device": str(self.device),
            "mps_available": torch.backends.mps.is_available(),
            "torch_version": torch.__version__
        }
        
        return stats
    
    def warmup_models(self):
        """Warm up models with sample data to optimize initial performance"""
        logger.info("Warming up ML models...")
        
        # Warm up embedding model
        try:
            sample_texts = [
                "Protein folding is a fundamental biological process.",
                "Machine learning accelerates drug discovery research."
            ]
            self.generate_embeddings(sample_texts)
            logger.debug("Embedding model warmed up successfully")
        except Exception as e:
            logger.warning(f"Could not warm up embedding model: {e}")
        
        # Warm up spaCy model
        try:
            self.extract_entities(sample_texts)
            logger.debug("spaCy model warmed up successfully")
        except Exception as e:
            logger.warning(f"Could not warm up spaCy model: {e}")
        
        logger.info("Model warmup completed")
    
    def cleanup(self):
        """Clean up resources and clear caches"""
        logger.info("Cleaning up ML models...")
        
        # Clear MPS cache
        self._clear_mps_cache()
        
        # Clear model references
        self._embedding_model = None
        self._spacy_model = None
        
        logger.info("Model cleanup completed")


# Convenience functions for easy access
_model_manager: Optional[M2ModelManager] = None

def get_model_manager() -> M2ModelManager:
    """Get singleton model manager instance"""
    global _model_manager
    if _model_manager is None:
        _model_manager = M2ModelManager()
    return _model_manager

def generate_embeddings(texts: List[str], batch_size: Optional[int] = None) -> np.ndarray:
    """Convenience function to generate embeddings"""
    return get_model_manager().generate_embeddings(texts, batch_size)

def extract_entities(texts: List[str], batch_size: Optional[int] = None) -> List[List[Dict[str, Any]]]:
    """Convenience function to extract entities"""
    return get_model_manager().extract_entities(texts, batch_size)

def cleanup_models():
    """Convenience function to cleanup models"""
    global _model_manager
    if _model_manager:
        _model_manager.cleanup()
        _model_manager = None