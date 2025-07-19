"""
Named Entity Recognition and Extraction Module

This module handles the extraction of biomedical entities from literature papers
using spaCy biomedical models optimized for protein design research.
"""

import logging
import time
from typing import List, Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass
from enum import Enum
import re

from ..core.models import Paper, Entity
from ..core.repository import EntityRepository
from .ml_models import get_model_manager

logger = logging.getLogger(__name__)

class EntityType(Enum):
    """Supported entity types for biomedical literature"""
    PROTEIN = "protein"
    GENE = "gene"
    DISEASE = "disease"
    CHEMICAL = "chemical"
    ORGANISM = "organism"
    TISSUE = "tissue"
    CELL_TYPE = "cell_type"
    COMPANY = "company"
    INSTITUTION = "institution"
    METHOD = "method"
    TECHNOLOGY = "technology"
    
    @classmethod
    def get_protein_design_entities(cls):
        """Get entity types most relevant to protein design"""
        return [cls.PROTEIN, cls.GENE, cls.CHEMICAL, cls.METHOD, cls.TECHNOLOGY, cls.COMPANY]

@dataclass
class EntityExtractionConfig:
    """Configuration for entity extraction"""
    confidence_threshold: float = 0.5
    min_entity_length: int = 2
    max_entity_length: int = 100
    batch_size: int = 16  # Smaller batches for NER
    include_context: bool = True
    context_window: int = 50  # Characters before/after entity
    filter_common_words: bool = True
    deduplicate_entities: bool = True
    protein_design_focus: bool = True  # Focus on protein design relevant entities


class EntityNormalizer:
    """
    Normalizes and validates extracted entities
    """
    
    def __init__(self):
        # Common words to filter out (domain-specific stop words)
        self.common_words = {
            'and', 'or', 'the', 'a', 'an', 'in', 'on', 'at', 'to', 'for', 'of', 'with',
            'by', 'from', 'as', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'should',
            'could', 'can', 'may', 'might', 'must', 'shall', 'this', 'that', 'these',
            'those', 'we', 'us', 'our', 'ours', 'you', 'your', 'yours', 'he', 'him',
            'his', 'she', 'her', 'hers', 'it', 'its', 'they', 'them', 'their', 'theirs'
        }
        
        # Protein name patterns (basic patterns for validation)
        self.protein_patterns = [
            r'^[A-Z][a-z]+\d*$',  # Standard protein names like Gfp1, His3
            r'^[A-Z]{2,}$',       # All caps abbreviations like GFP, ATP
            r'^p\d+$',            # p53-style names
            r'^\w+[A-Z]\d+[A-Z]$' # Mutation style like V600E
        ]
        
        # Company/institution indicators
        self.institution_indicators = {
            'university', 'college', 'institute', 'laboratory', 'lab', 'research',
            'center', 'centre', 'hospital', 'clinic', 'foundation', 'school',
            'company', 'corporation', 'corp', 'inc', 'ltd', 'llc', 'pharma',
            'pharmaceutical', 'biotech', 'biotechnology'
        }
    
    def normalize_entity_text(self, text: str) -> str:
        """Normalize entity text"""
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text.strip())
        
        # Remove special characters at start/end
        text = re.sub(r'^[^\w]+|[^\w]+$', '', text)
        
        return text
    
    def is_valid_entity(self, text: str, entity_type: str, config: EntityExtractionConfig) -> bool:
        """Validate if an entity should be kept"""
        
        # Basic length checks
        if len(text) < config.min_entity_length or len(text) > config.max_entity_length:
            return False
        
        # Filter common words
        if config.filter_common_words and text.lower() in self.common_words:
            return False
        
        # Filter purely numeric entities (unless specific types)
        if text.isdigit() and entity_type not in ['CARDINAL', 'QUANTITY']:
            return False
        
        # Filter single characters
        if len(text) == 1:
            return False
        
        # Validate protein names with basic patterns
        if entity_type.lower() in ['protein', 'gene'] and config.protein_design_focus:
            if any(re.match(pattern, text) for pattern in self.protein_patterns):
                return True
            # Also allow longer descriptive names
            if len(text) > 3 and not text.islower():
                return True
            return False
        
        return True
    
    def classify_entity_type(self, text: str, spacy_label: str) -> EntityType:
        """Map spaCy labels to our entity types"""
        
        # Direct mapping from spaCy biomedical labels
        label_mapping = {
            'PROTEIN': EntityType.PROTEIN,
            'GENE_OR_GENE_PRODUCT': EntityType.PROTEIN,
            'GENE': EntityType.GENE,
            'DISEASE': EntityType.DISEASE,
            'CHEMICAL': EntityType.CHEMICAL,
            'ORGANISM': EntityType.ORGANISM,
            'TISSUE': EntityType.TISSUE,
            'CELL_TYPE': EntityType.CELL_TYPE,
            'CELL_LINE': EntityType.CELL_TYPE,
            'ORG': EntityType.INSTITUTION,  # spaCy organization
            'PERSON': EntityType.INSTITUTION,  # Sometimes institutions are tagged as PERSON
        }
        
        if spacy_label in label_mapping:
            return label_mapping[spacy_label]
        
        # Heuristic classification based on text content
        text_lower = text.lower()
        
        # Check for institution indicators
        if any(indicator in text_lower for indicator in self.institution_indicators):
            return EntityType.INSTITUTION
        
        # Check for method/technology keywords
        method_keywords = {'method', 'technique', 'assay', 'protocol', 'procedure', 'approach'}
        if any(keyword in text_lower for keyword in method_keywords):
            return EntityType.METHOD
        
        # Default to chemical for unknown entities in biomedical context
        return EntityType.CHEMICAL


class EntityExtractor:
    """
    Extracts and processes biomedical entities from literature papers.
    
    Features:
    - spaCy biomedical NER with custom validation
    - Entity normalization and deduplication
    - Context extraction for better understanding
    - Batch processing with M2 optimization
    - Protein design domain focus
    """
    
    def __init__(self, 
                 entity_repo: EntityRepository,
                 config: Optional[EntityExtractionConfig] = None):
        self.entity_repo = entity_repo
        self.config = config or EntityExtractionConfig()
        self.model_manager = get_model_manager()
        self.normalizer = EntityNormalizer()
        
        # Performance tracking
        self.stats = {
            "papers_processed": 0,
            "entities_extracted": 0,
            "entities_filtered": 0,
            "total_processing_time": 0.0,
            "entities_by_type": {}
        }
        
        logger.info("EntityExtractor initialized")
    
    def _extract_context(self, text: str, start: int, end: int) -> str:
        """Extract context around an entity"""
        if not self.config.include_context:
            return ""
        
        context_start = max(0, start - self.config.context_window)
        context_end = min(len(text), end + self.config.context_window)
        
        context = text[context_start:context_end]
        
        # Clean up context
        context = re.sub(r'\s+', ' ', context.strip())
        
        return context
    
    def _process_spacy_entities(self, text: str, spacy_entities: List[Dict]) -> List[Dict[str, Any]]:
        """Process entities extracted by spaCy"""
        
        processed_entities = []
        seen_entities = set()  # For deduplication
        
        for ent_data in spacy_entities:
            entity_text = self.normalizer.normalize_entity_text(ent_data['text'])
            
            # Skip if empty after normalization
            if not entity_text:
                continue
            
            # Validate entity
            if not self.normalizer.is_valid_entity(
                entity_text, 
                ent_data['label'], 
                self.config
            ):
                self.stats["entities_filtered"] += 1
                continue
            
            # Classify entity type
            entity_type = self.normalizer.classify_entity_type(
                entity_text, 
                ent_data['label']
            )
            
            # Focus on protein design relevant entities if configured
            if (self.config.protein_design_focus and 
                entity_type not in EntityType.get_protein_design_entities()):
                continue
            
            # Deduplication
            if self.config.deduplicate_entities:
                entity_key = (entity_text.lower(), entity_type.value)
                if entity_key in seen_entities:
                    continue
                seen_entities.add(entity_key)
            
            # Extract context
            context = self._extract_context(text, ent_data['start'], ent_data['end'])
            
            processed_entity = {
                'text': entity_text,
                'type': entity_type.value,
                'start_position': ent_data['start'],
                'end_position': ent_data['end'],
                'confidence': ent_data.get('confidence', 1.0),
                'context': context,
                'original_label': ent_data['label']
            }
            
            processed_entities.append(processed_entity)
            self.stats["entities_extracted"] += 1
            
            # Track by type
            if entity_type.value not in self.stats["entities_by_type"]:
                self.stats["entities_by_type"][entity_type.value] = 0
            self.stats["entities_by_type"][entity_type.value] += 1
        
        return processed_entities
    
    def extract_paper_entities(self, paper: Paper) -> List[Entity]:
        """
        Extract entities from a single paper
        """
        start_time = time.time()
        
        try:
            # Check if entities already exist
            existing_entities = self.entity_repo.get_by_paper_id(paper.id)
            if existing_entities:
                logger.debug(f"Using cached entities for paper {paper.id}")
                return existing_entities
            
            # Prepare text for entity extraction
            texts_to_process = []
            text_sources = []
            
            if paper.title:
                texts_to_process.append(paper.title)
                text_sources.append("title")
            
            if paper.abstract:
                texts_to_process.append(paper.abstract)
                text_sources.append("abstract")
            
            if paper.full_text:
                # For full text, we might want to process in chunks
                # For now, process the full text as one unit
                texts_to_process.append(paper.full_text[:10000])  # Limit to first 10k chars
                text_sources.append("full_text")
            
            if not texts_to_process:
                logger.warning(f"No text content found for paper {paper.id}")
                return []
            
            # Extract entities using spaCy
            logger.debug(f"Extracting entities from {len(texts_to_process)} text sections")
            
            all_spacy_entities = self.model_manager.extract_entities(
                texts_to_process,
                batch_size=self.config.batch_size
            )
            
            # Process and combine entities from all sections
            all_entities = []
            char_offset = 0
            
            for text, source, spacy_entities in zip(texts_to_process, text_sources, all_spacy_entities):
                processed_entities = self._process_spacy_entities(text, spacy_entities)
                
                # Adjust positions for combined text and add source info
                for entity_data in processed_entities:
                    entity_data['start_position'] += char_offset
                    entity_data['end_position'] += char_offset
                    entity_data['source_section'] = source
                    
                    # Create Entity object
                    entity = Entity(
                        paper_id=paper.id,
                        entity_text=entity_data['text'],
                        entity_type=entity_data['type'],
                        confidence=entity_data['confidence'],
                        start_position=entity_data['start_position'],
                        end_position=entity_data['end_position'],
                        context=entity_data['context']
                    )
                    
                    all_entities.append(entity)
                
                char_offset += len(text) + 1  # +1 for separator
            
            # Store entities in database
            if all_entities:
                for entity in all_entities:
                    self.entity_repo.create(entity)
                
                logger.info(f"Extracted {len(all_entities)} entities from paper {paper.id}")
            
            processing_time = time.time() - start_time
            self.stats["papers_processed"] += 1
            self.stats["total_processing_time"] += processing_time
            
            logger.debug(f"Entity extraction completed for paper {paper.id} in {processing_time:.2f}s")
            
            return all_entities
            
        except Exception as e:
            logger.error(f"Failed to extract entities from paper {paper.id}: {e}")
            raise
    
    def extract_batch_entities(self, papers: List[Paper]) -> Dict[str, List[Entity]]:
        """
        Extract entities from multiple papers
        """
        if not papers:
            return {}
        
        start_time = time.time()
        logger.info(f"Extracting entities from {len(papers)} papers")
        
        results = {}
        
        for i, paper in enumerate(papers):
            try:
                entities = self.extract_paper_entities(paper)
                results[paper.id] = entities
                
                # Log progress for large batches
                if (i + 1) % 10 == 0:
                    elapsed = time.time() - start_time
                    remaining = len(papers) - (i + 1)
                    eta = (elapsed / (i + 1)) * remaining
                    logger.info(f"Processed {i + 1}/{len(papers)} papers "
                               f"(ETA: {eta:.1f}s)")
                
            except Exception as e:
                logger.error(f"Failed to process paper {paper.id}: {e}")
                results[paper.id] = []
                continue
        
        total_time = time.time() - start_time
        total_entities = sum(len(entities) for entities in results.values())
        
        logger.info(f"Batch entity extraction completed: {total_entities} entities "
                   f"from {len(papers)} papers in {total_time:.2f}s")
        
        return results
    
    def get_entities_by_type(self, paper_id: str, entity_type: EntityType) -> List[Entity]:
        """Get entities of a specific type for a paper"""
        return self.entity_repo.get_by_paper_and_type(paper_id, entity_type.value)
    
    def get_entity_statistics(self, paper_id: Optional[str] = None) -> Dict[str, Any]:
        """Get entity statistics for a paper or all papers"""
        if paper_id:
            entities = self.entity_repo.get_by_paper_id(paper_id)
        else:
            entities = self.entity_repo.get_all()
        
        stats = {
            "total_entities": len(entities),
            "entities_by_type": {},
            "avg_confidence": 0.0,
            "unique_entities": set()
        }
        
        if entities:
            confidences = []
            for entity in entities:
                entity_type = entity.entity_type
                if entity_type not in stats["entities_by_type"]:
                    stats["entities_by_type"][entity_type] = 0
                stats["entities_by_type"][entity_type] += 1
                
                confidences.append(entity.confidence)
                stats["unique_entities"].add(entity.entity_text.lower())
            
            stats["avg_confidence"] = sum(confidences) / len(confidences)
            stats["unique_entity_count"] = len(stats["unique_entities"])
            del stats["unique_entities"]  # Remove set for JSON serialization
        
        return stats
    
    def get_processing_statistics(self) -> Dict[str, Any]:
        """Get processing statistics"""
        stats = self.stats.copy()
        
        if stats["papers_processed"] > 0:
            stats["avg_processing_time"] = stats["total_processing_time"] / stats["papers_processed"]
            stats["avg_entities_per_paper"] = stats["entities_extracted"] / stats["papers_processed"]
        
        # Add model manager stats
        stats["model_performance"] = self.model_manager.get_performance_stats()
        
        return stats


# Convenience functions
def extract_paper_entities(paper: Paper, 
                         entity_repo: EntityRepository,
                         config: Optional[EntityExtractionConfig] = None) -> List[Entity]:
    """Convenience function to extract entities from a single paper"""
    extractor = EntityExtractor(entity_repo, config)
    return extractor.extract_paper_entities(paper)

def extract_batch_entities(papers: List[Paper],
                         entity_repo: EntityRepository,
                         config: Optional[EntityExtractionConfig] = None) -> Dict[str, List[Entity]]:
    """Convenience function to extract entities from multiple papers"""
    extractor = EntityExtractor(entity_repo, config)
    return extractor.extract_batch_entities(papers)