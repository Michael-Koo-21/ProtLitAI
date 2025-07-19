"""arXiv literature collector using arXiv API."""

import asyncio
import aiohttp
import xml.etree.ElementTree as ET
import feedparser
from typing import List, Dict, Any, Optional, AsyncIterator
from datetime import datetime, timedelta
from urllib.parse import urlencode, quote
import hashlib
import re

from collectors.base_collector import BaseCollector
from core.models import Paper, SourceType, PaperType
from core.config import config


class ArxivCollector(BaseCollector):
    """Collector for arXiv preprints using arXiv API."""
    
    API_BASE_URL = "http://export.arxiv.org/api/query"
    RSS_BASE_URL = "http://rss.arxiv.org/rss"
    
    # Relevant categories for protein design
    RELEVANT_CATEGORIES = [
        "cs.LG",      # Machine Learning
        "q-bio.BM",   # Biomolecules
        "physics.bio-ph",  # Biological Physics
        "stat.ML",    # Machine Learning (Statistics)
        "cs.AI",      # Artificial Intelligence
        "q-bio.QM",   # Quantitative Methods
    ]
    
    def __init__(self):
        rate_limit = config.get("arxiv_rate_limit", 1.0)
        super().__init__(SourceType.ARXIV, rate_limit)
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.request_timeout),
            headers={"User-Agent": "ProtLitAI/1.0 (research@example.com)"}
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def search_papers(
        self, 
        query: str, 
        max_results: int = 100,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> AsyncIterator[Paper]:
        """Search for papers using arXiv API."""
        if not self.session:
            raise RuntimeError("ArxivCollector must be used as async context manager")
        
        # Build search query with categories
        search_query = self._build_arxiv_query(query, date_from, date_to)
        
        # Fetch papers in batches (arXiv API has rate limits)
        batch_size = 50
        start = 0
        
        while start < max_results:
            current_batch_size = min(batch_size, max_results - start)
            papers = await self._fetch_papers_batch(
                search_query, start, current_batch_size
            )
            
            if not papers:
                break
            
            for paper in papers:
                yield paper
            
            start += len(papers)
            
            # If we got fewer papers than requested, we've reached the end
            if len(papers) < current_batch_size:
                break
    
    async def get_paper_details(self, paper_id: str) -> Optional[Paper]:
        """Get detailed information for a specific arXiv ID."""
        if not self.session:
            raise RuntimeError("ArxivCollector must be used as async context manager")
        
        # Clean arXiv ID (remove version if present)
        arxiv_id = self._clean_arxiv_id(paper_id)
        
        params = {
            "id_list": arxiv_id,
            "max_results": 1
        }
        
        papers = await self._fetch_papers_batch("", 0, 1, params)
        return papers[0] if papers else None
    
    async def collect_recent_from_rss(
        self,
        category: str = "cs.LG",
        max_papers: int = 50
    ) -> List[Paper]:
        """Collect recent papers from arXiv RSS feeds."""
        self.logger.info(f"Collecting recent papers from arXiv RSS: {category}")
        
        url = f"{self.RSS_BASE_URL}/{category}"
        
        async def fetch_rss():
            async with self.session.get(url) as response:
                response.raise_for_status()
                return await response.text()
        
        rss_content = await self._make_request_with_retry(fetch_rss)
        
        # Parse RSS feed
        feed = feedparser.parse(rss_content)
        papers = []
        
        for entry in feed.entries[:max_papers]:
            paper = self._parse_rss_entry(entry)
            if paper and self._is_relevant_paper(paper):
                papers.append(paper)
        
        self.logger.info(f"Collected {len(papers)} relevant papers from RSS")
        return papers
    
    async def _fetch_papers_batch(
        self,
        query: str,
        start: int,
        max_results: int,
        custom_params: Optional[Dict] = None
    ) -> List[Paper]:
        """Fetch a batch of papers from arXiv API."""
        params = custom_params or {
            "search_query": query,
            "start": start,
            "max_results": max_results,
            "sortBy": "submittedDate",
            "sortOrder": "descending"
        }
        
        url = f"{self.API_BASE_URL}?{urlencode(params)}"
        
        async def make_api_request():
            async with self.session.get(url) as response:
                response.raise_for_status()
                return await response.text()
        
        xml_content = await self._make_request_with_retry(make_api_request)
        return self._parse_arxiv_response(xml_content)
    
    def _build_arxiv_query(
        self,
        base_query: str,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> str:
        """Build arXiv API search query."""
        # Convert protein design terms to arXiv-appropriate query
        protein_terms = [
            "protein design",
            "protein engineering", 
            "computational protein",
            "protein structure prediction",
            "de novo protein",
            "protein folding",
            "machine learning protein",
            "AI protein",
            "protein sequence"
        ]
        
        # Combine terms with OR
        query_parts = []
        
        # Add protein-related terms
        term_query = " OR ".join([f'"{term}"' for term in protein_terms])
        query_parts.append(f"({term_query})")
        
        # Add category restrictions
        cat_query = " OR ".join([f"cat:{cat}" for cat in self.RELEVANT_CATEGORIES])
        query_parts.append(f"({cat_query})")
        
        # Add user query if provided
        if base_query and base_query.strip():
            query_parts.append(base_query)
        
        final_query = " AND ".join(query_parts)
        
        # Add date filter if specified
        if date_from:
            date_str = date_from.strftime("%Y%m%d")
            final_query += f" AND submittedDate:[{date_str}* TO *]"
        
        return final_query
    
    def _parse_arxiv_response(self, xml_content: str) -> List[Paper]:
        """Parse arXiv API XML response."""
        try:
            # Parse XML with namespace handling
            root = ET.fromstring(xml_content)
            namespace = {"atom": "http://www.w3.org/2005/Atom"}
            
            papers = []
            entries = root.findall("atom:entry", namespace)
            
            for entry in entries:
                paper = self._parse_arxiv_entry(entry, namespace)
                if paper and self._is_relevant_paper(paper):
                    papers.append(paper)
            
            return papers
            
        except ET.ParseError as e:
            self.logger.error(f"Failed to parse arXiv response: {e}")
            return []
    
    def _parse_arxiv_entry(self, entry: ET.Element, namespace: Dict) -> Optional[Paper]:
        """Parse individual arXiv entry."""
        try:
            # Extract arXiv ID
            id_elem = entry.find("atom:id", namespace)
            if id_elem is None:
                return None
            
            arxiv_url = id_elem.text
            arxiv_id = self._extract_arxiv_id(arxiv_url)
            
            # Extract title
            title_elem = entry.find("atom:title", namespace)
            title = title_elem.text.strip() if title_elem is not None else ""
            
            # Extract abstract
            summary_elem = entry.find("atom:summary", namespace)
            abstract = summary_elem.text.strip() if summary_elem is not None else ""
            
            # Extract authors
            authors = []
            for author in entry.findall("atom:author", namespace):
                name_elem = author.find("atom:name", namespace)
                if name_elem is not None:
                    authors.append(name_elem.text.strip())
            
            # Extract published date
            published_elem = entry.find("atom:published", namespace)
            publication_date = None
            if published_elem is not None:
                publication_date = self._parse_arxiv_date(published_elem.text)
            
            # Extract categories
            categories = []
            for category in entry.findall("atom:category", namespace):
                term = category.get("term")
                if term:
                    categories.append(term)
            
            # Extract PDF URL
            pdf_url = None
            for link in entry.findall("atom:link", namespace):
                if link.get("type") == "application/pdf":
                    pdf_url = link.get("href")
                    break
            
            # Generate unique ID
            paper_id = self._generate_paper_id(arxiv_id, title)
            
            return Paper(
                id=paper_id,
                title=title,
                abstract=abstract,
                authors=authors,
                journal="arXiv",  # arXiv is the journal/venue
                publication_date=publication_date,
                arxiv_id=arxiv_id,
                pdf_url=pdf_url,
                paper_type=PaperType.PREPRINT,
                source=SourceType.ARXIV,
                processing_status="pending"
            )
            
        except Exception as e:
            self.logger.error(f"Failed to parse arXiv entry: {e}")
            return None
    
    def _parse_rss_entry(self, entry) -> Optional[Paper]:
        """Parse RSS feed entry."""
        try:
            # Extract title
            title = entry.title if hasattr(entry, 'title') else ""
            
            # Extract abstract from description
            abstract = ""
            if hasattr(entry, 'summary'):
                # Remove HTML tags and clean up
                abstract = re.sub(r'<[^>]+>', '', entry.summary)
                abstract = abstract.strip()
            
            # Extract arXiv ID from link
            arxiv_id = None
            if hasattr(entry, 'link'):
                arxiv_id = self._extract_arxiv_id(entry.link)
            
            # Extract publication date
            publication_date = None
            if hasattr(entry, 'published_parsed'):
                publication_date = datetime(*entry.published_parsed[:6])
            
            # Extract authors from title (arXiv RSS format)
            authors = []
            if hasattr(entry, 'author'):
                # RSS author format is different from API
                authors = [entry.author.strip()]
            
            if not arxiv_id:
                return None
            
            # Generate unique ID
            paper_id = self._generate_paper_id(arxiv_id, title)
            
            return Paper(
                id=paper_id,
                title=title,
                abstract=abstract,
                authors=authors,
                journal="arXiv",
                publication_date=publication_date,
                arxiv_id=arxiv_id,
                pdf_url=f"https://arxiv.org/pdf/{arxiv_id}.pdf",
                paper_type=PaperType.PREPRINT,
                source=SourceType.ARXIV,
                processing_status="pending"
            )
            
        except Exception as e:
            self.logger.error(f"Failed to parse RSS entry: {e}")
            return None
    
    def _extract_arxiv_id(self, url_or_id: str) -> str:
        """Extract arXiv ID from URL or clean existing ID."""
        # Handle various formats:
        # http://arxiv.org/abs/2301.12345v1
        # https://arxiv.org/abs/2301.12345
        # 2301.12345v1
        # 2301.12345
        
        if "arxiv.org" in url_or_id:
            match = re.search(r'arxiv\.org/abs/([0-9]{4}\.[0-9]{4,5}(?:v[0-9]+)?)', url_or_id)
            if match:
                return match.group(1)
        
        # Direct arXiv ID
        match = re.match(r'^([0-9]{4}\.[0-9]{4,5}(?:v[0-9]+)?)$', url_or_id)
        if match:
            return match.group(1)
        
        return url_or_id
    
    def _clean_arxiv_id(self, arxiv_id: str) -> str:
        """Remove version suffix from arXiv ID if present."""
        return re.sub(r'v[0-9]+$', '', arxiv_id)
    
    def _parse_arxiv_date(self, date_str: str) -> Optional[datetime]:
        """Parse arXiv date string."""
        try:
            # arXiv uses ISO format: 2023-01-15T10:30:00Z
            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except Exception:
            try:
                # Fallback format
                return datetime.strptime(date_str[:10], '%Y-%m-%d')
            except Exception:
                return None
    
    def _is_relevant_paper(self, paper: Paper) -> bool:
        """Check if paper is relevant to protein design."""
        if not paper.title and not paper.abstract:
            return False
        
        # Combine title and abstract for relevance checking
        content = f"{paper.title} {paper.abstract}".lower()
        
        # Key terms that indicate protein design relevance
        relevant_terms = [
            "protein", "peptide", "amino acid", "structure prediction",
            "molecular dynamics", "folding", "design", "engineering",
            "alphafold", "binding", "enzyme", "antibody", "therapeutic",
            "drug discovery", "computational biology", "bioinformatics"
        ]
        
        # Check if any relevant terms are present
        return any(term in content for term in relevant_terms)
    
    def _generate_paper_id(self, arxiv_id: str, title: str) -> str:
        """Generate unique paper ID."""
        content = f"arxiv_{arxiv_id}_{title}"
        return hashlib.md5(content.encode()).hexdigest()


# Convenience function for easy usage
async def collect_arxiv_papers(
    query: Optional[str] = None,
    days_back: int = 1,
    max_papers: int = 100,
    use_rss: bool = False
) -> List[Paper]:
    """Collect papers from arXiv."""
    async with ArxivCollector() as collector:
        if use_rss:
            # Collect from multiple relevant categories
            all_papers = []
            for category in ArxivCollector.RELEVANT_CATEGORIES[:3]:  # Limit to avoid rate limits
                papers = await collector.collect_recent_from_rss(
                    category=category,
                    max_papers=max_papers // 3
                )
                all_papers.extend(papers)
            return all_papers[:max_papers]
        else:
            return await collector.collect_recent_papers(
                days_back=days_back,
                max_papers=max_papers,
                query_filter=query
            )