"""Base collector class for literature sources."""

import asyncio
import time
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, AsyncIterator
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass

from core.models import Paper, SourceType
from core.config import config


@dataclass
class CollectionStats:
    """Collection statistics."""
    source: str
    papers_collected: int
    papers_skipped: int
    errors: int
    start_time: datetime
    end_time: Optional[datetime] = None
    
    @property
    def duration(self) -> timedelta:
        """Get collection duration."""
        end = self.end_time or datetime.utcnow()
        return end - self.start_time
    
    @property
    def papers_per_minute(self) -> float:
        """Get papers collected per minute."""
        duration_minutes = self.duration.total_seconds() / 60
        if duration_minutes == 0:
            return 0
        return self.papers_collected / duration_minutes


class RateLimiter:
    """Simple rate limiter using token bucket algorithm."""
    
    def __init__(self, requests_per_second: float):
        self.requests_per_second = requests_per_second
        self.bucket_size = max(1, int(requests_per_second))
        self.tokens = self.bucket_size
        self.last_update = time.time()
    
    async def acquire(self) -> None:
        """Acquire a token, waiting if necessary."""
        now = time.time()
        elapsed = now - self.last_update
        self.last_update = now
        
        # Add tokens based on elapsed time
        self.tokens = min(
            self.bucket_size,
            self.tokens + elapsed * self.requests_per_second
        )
        
        if self.tokens >= 1:
            self.tokens -= 1
        else:
            # Wait until we can get a token
            wait_time = (1 - self.tokens) / self.requests_per_second
            await asyncio.sleep(wait_time)
            self.tokens = 0


class BaseCollector(ABC):
    """Base class for literature collectors."""
    
    def __init__(self, source_type: SourceType, rate_limit: float = 1.0):
        self.source_type = source_type
        self.logger = logging.getLogger(f"collectors.{source_type.value}")
        self.rate_limiter = RateLimiter(rate_limit)
        self.stats = CollectionStats(
            source=source_type.value,
            papers_collected=0,
            papers_skipped=0,
            errors=0,
            start_time=datetime.utcnow()
        )
        self.retry_attempts = config.get("retry_attempts", 3)
        self.request_timeout = config.get("request_timeout", 30)
        
    @abstractmethod
    async def search_papers(
        self, 
        query: str, 
        max_results: int = 100,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> AsyncIterator[Paper]:
        """Search for papers matching the query."""
        pass
    
    @abstractmethod
    async def get_paper_details(self, paper_id: str) -> Optional[Paper]:
        """Get detailed information for a specific paper."""
        pass
    
    async def collect_recent_papers(
        self,
        days_back: int = 1,
        max_papers: int = 1000,
        query_filter: Optional[str] = None
    ) -> List[Paper]:
        """Collect recent papers from the source."""
        self.logger.info(
            f"Starting collection from {self.source_type.value}: "
            f"{days_back} days back, max {max_papers} papers"
        )
        
        date_from = datetime.utcnow() - timedelta(days=days_back)
        query = self._build_query(query_filter)
        
        papers = []
        async for paper in self.search_papers(
            query=query,
            max_results=max_papers,
            date_from=date_from
        ):
            papers.append(paper)
            self.stats.papers_collected += 1
            
            if len(papers) >= max_papers:
                break
        
        self.stats.end_time = datetime.utcnow()
        self.logger.info(
            f"Collection completed: {self.stats.papers_collected} papers "
            f"in {self.stats.duration.total_seconds():.1f}s "
            f"({self.stats.papers_per_minute:.1f} papers/min)"
        )
        
        return papers
    
    def _build_query(self, user_filter: Optional[str] = None) -> str:
        """Build search query for protein design papers."""
        base_terms = [
            "protein design",
            "protein engineering",
            "computational protein design",
            "protein structure prediction",
            "de novo protein design",
            "protein folding",
            "machine learning protein",
            "AI protein design",
            "protein sequence design",
            "directed evolution"
        ]
        
        query_parts = []
        
        # Add base protein design terms
        if self.source_type == SourceType.PUBMED:
            # PubMed-specific query syntax
            protein_query = " OR ".join([f'"{term}"[Title/Abstract]' for term in base_terms])
            query_parts.append(f"({protein_query})")
        else:
            # General query syntax
            protein_query = " OR ".join([f'"{term}"' for term in base_terms])
            query_parts.append(f"({protein_query})")
        
        # Add user filter if provided
        if user_filter:
            query_parts.append(user_filter)
        
        return " AND ".join(query_parts)
    
    async def _make_request_with_retry(
        self,
        request_func,
        *args,
        **kwargs
    ) -> Any:
        """Make request with retry logic and rate limiting."""
        await self.rate_limiter.acquire()
        
        for attempt in range(self.retry_attempts):
            try:
                return await request_func(*args, **kwargs)
            except Exception as e:
                self.stats.errors += 1
                
                if attempt == self.retry_attempts - 1:
                    self.logger.error(
                        f"Request failed after {self.retry_attempts} attempts: {e}"
                    )
                    raise
                
                # Exponential backoff
                wait_time = 2 ** attempt
                self.logger.warning(
                    f"Request failed (attempt {attempt + 1}/{self.retry_attempts}): {e}. "
                    f"Retrying in {wait_time}s..."
                )
                await asyncio.sleep(wait_time)
    
    def get_stats(self) -> CollectionStats:
        """Get collection statistics."""
        return self.stats
    
    def reset_stats(self) -> None:
        """Reset collection statistics."""
        self.stats = CollectionStats(
            source=self.source_type.value,
            papers_collected=0,
            papers_skipped=0,
            errors=0,
            start_time=datetime.utcnow()
        )