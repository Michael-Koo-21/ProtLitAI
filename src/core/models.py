"""Data models for ProtLitAI."""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, field_validator, ConfigDict
from enum import Enum


class PaperType(str, Enum):
    """Types of academic papers."""
    JOURNAL = "journal"
    PREPRINT = "preprint"
    PATENT = "patent"
    CONFERENCE = "conference"


class SourceType(str, Enum):
    """Sources for literature collection."""
    PUBMED = "pubmed"
    ARXIV = "arxiv"
    BIORXIV = "biorxiv"
    MEDRXIV = "medrxiv"
    SCHOLAR = "scholar"


class EntityType(str, Enum):
    """Types of extracted entities."""
    PROTEIN = "protein"
    GENE = "gene"
    METHOD = "method"
    COMPANY = "company"
    INSTITUTION = "institution"
    CHEMICAL = "chemical"


class ProcessingStatus(str, Enum):
    """Status of paper processing."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class Paper(BaseModel):
    """Paper data model."""
    
    id: str = Field(..., description="Unique paper identifier")
    title: str = Field(..., description="Paper title")
    abstract: Optional[str] = Field(None, description="Paper abstract")
    authors: List[str] = Field(default_factory=list, description="List of authors")
    journal: Optional[str] = Field(None, description="Journal name")
    publication_date: Optional[datetime] = Field(None, description="Publication date")
    doi: Optional[str] = Field(None, description="Digital Object Identifier")
    arxiv_id: Optional[str] = Field(None, description="arXiv identifier")
    pubmed_id: Optional[int] = Field(None, description="PubMed ID")
    pdf_url: Optional[str] = Field(None, description="PDF download URL")
    local_pdf_path: Optional[str] = Field(None, description="Local PDF file path")
    full_text: Optional[str] = Field(None, description="Extracted full text")
    paper_type: PaperType = Field(default=PaperType.JOURNAL, description="Type of paper")
    source: SourceType = Field(..., description="Source of the paper")
    relevance_score: Optional[float] = Field(None, description="Relevance score (0-1)")
    processing_status: ProcessingStatus = Field(
        default=ProcessingStatus.PENDING, 
        description="Processing status"
    )
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    
    @field_validator('relevance_score')
    @classmethod
    def validate_relevance_score(cls, v):
        if v is not None and (v < 0 or v > 1):
            raise ValueError('Relevance score must be between 0 and 1')
        return v
    
    @field_validator('authors')
    @classmethod
    def validate_authors(cls, v):
        return [author.strip() for author in v if author.strip()]
    
    model_config = ConfigDict(use_enum_values=True)


class Author(BaseModel):
    """Author data model."""
    
    id: Optional[int] = Field(None, description="Unique author ID")
    name: str = Field(..., description="Author name")
    normalized_name: Optional[str] = Field(None, description="Normalized author name")
    orcid: Optional[str] = Field(None, description="ORCID identifier")
    h_index: Optional[int] = Field(None, description="H-index")
    affiliations: List[str] = Field(default_factory=list, description="Institutional affiliations")
    research_areas: List[str] = Field(default_factory=list, description="Research areas")
    first_seen: Optional[datetime] = Field(None, description="First appearance date")
    last_seen: Optional[datetime] = Field(None, description="Last appearance date")
    
    model_config = ConfigDict(use_enum_values=True)


class Entity(BaseModel):
    """Extracted entity data model."""
    
    id: Optional[int] = Field(None, description="Unique entity ID")
    paper_id: str = Field(..., description="Associated paper ID")
    entity_text: str = Field(..., description="Extracted entity text")
    entity_type: EntityType = Field(..., description="Type of entity")
    confidence: float = Field(..., description="Extraction confidence (0-1)")
    start_position: Optional[int] = Field(None, description="Start position in text")
    end_position: Optional[int] = Field(None, description="End position in text")
    context: Optional[str] = Field(None, description="Surrounding context")
    
    @field_validator('confidence')
    @classmethod
    def validate_confidence(cls, v):
        if v < 0 or v > 1:
            raise ValueError('Confidence must be between 0 and 1')
        return v
    
    model_config = ConfigDict(use_enum_values=True)


class Embedding(BaseModel):
    """Paper embedding data model."""
    
    paper_id: str = Field(..., description="Associated paper ID")
    embedding: List[float] = Field(..., description="Embedding vector")
    model_version: str = Field(..., description="Model version used")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    
    @field_validator('embedding')
    @classmethod
    def validate_embedding(cls, v):
        if not v:
            raise ValueError('Embedding cannot be empty')
        return v


class Trend(BaseModel):
    """Research trend data model."""
    
    id: Optional[int] = Field(None, description="Unique trend ID")
    topic_name: str = Field(..., description="Topic name")
    keywords: List[str] = Field(default_factory=list, description="Associated keywords")
    paper_count: int = Field(..., description="Number of papers in this trend")
    time_period_start: datetime = Field(..., description="Trend period start")
    time_period_end: datetime = Field(..., description="Trend period end")
    growth_rate: Optional[float] = Field(None, description="Growth rate (papers/month)")
    significance_score: Optional[float] = Field(None, description="Statistical significance")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    
    @field_validator('paper_count')
    @classmethod
    def validate_paper_count(cls, v):
        if v < 0:
            raise ValueError('Paper count cannot be negative')
        return v


class Alert(BaseModel):
    """User alert data model."""
    
    id: Optional[int] = Field(None, description="Unique alert ID")
    name: str = Field(..., description="Alert name")
    query: str = Field(..., description="Search query")
    keywords: List[str] = Field(default_factory=list, description="Keywords to monitor")
    entities: List[str] = Field(default_factory=list, description="Entities to monitor")
    frequency: str = Field(default="daily", description="Alert frequency")
    last_triggered: Optional[datetime] = Field(None, description="Last trigger time")
    is_active: bool = Field(default=True, description="Whether alert is active")
    
    @field_validator('frequency')
    @classmethod
    def validate_frequency(cls, v):
        valid_frequencies = ['daily', 'weekly', 'monthly']
        if v not in valid_frequencies:
            raise ValueError(f'Frequency must be one of {valid_frequencies}')
        return v


class UserSetting(BaseModel):
    """User setting data model."""
    
    key: str = Field(..., description="Setting key")
    value: str = Field(..., description="Setting value")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update time")


class SearchQuery(BaseModel):
    """Search query data model."""
    
    query: str = Field(..., description="Search query text")
    filters: Dict[str, Any] = Field(default_factory=dict, description="Search filters")
    limit: int = Field(default=50, description="Result limit")
    offset: int = Field(default=0, description="Result offset")
    sort_by: str = Field(default="relevance", description="Sort field")
    sort_order: str = Field(default="desc", description="Sort order")
    
    @field_validator('limit')
    @classmethod
    def validate_limit(cls, v):
        if v <= 0 or v > 1000:
            raise ValueError('Limit must be between 1 and 1000')
        return v
    
    @field_validator('sort_order')
    @classmethod
    def validate_sort_order(cls, v):
        if v not in ['asc', 'desc']:
            raise ValueError('Sort order must be "asc" or "desc"')
        return v


class SearchResult(BaseModel):
    """Search result data model."""
    
    papers: List[Paper] = Field(default_factory=list, description="Found papers")
    total_count: int = Field(..., description="Total number of matching papers")
    query_time: float = Field(..., description="Query execution time in seconds")
    facets: Dict[str, Any] = Field(default_factory=dict, description="Search facets")


class SystemHealth(BaseModel):
    """System health data model."""
    
    status: str = Field(..., description="Overall system status")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Health check time")
    components: Dict[str, Any] = Field(default_factory=dict, description="Component health")
    metrics: Dict[str, Any] = Field(default_factory=dict, description="System metrics")