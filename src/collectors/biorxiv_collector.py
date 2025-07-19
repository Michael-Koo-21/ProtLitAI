"""bioRxiv and medRxiv literature collector using web scraping."""

import asyncio
import aiohttp
from bs4 import BeautifulSoup
import re
import json
from typing import List, Dict, Any, Optional, AsyncIterator
from datetime import datetime, timedelta
from urllib.parse import urljoin, quote
import hashlib

from collectors.base_collector import BaseCollector
from core.models import Paper, SourceType, PaperType
from core.config import config


class BiorxivCollector(BaseCollector):
    """Collector for bioRxiv and medRxiv preprints using web scraping."""
    
    BIORXIV_BASE_URL = "https://www.biorxiv.org"
    MEDRXIV_BASE_URL = "https://www.medrxiv.org"
    
    def __init__(self, include_medrxiv: bool = True):
        rate_limit = config.get("biorxiv_rate_limit", 0.5)  # Be respectful
        super().__init__(SourceType.BIORXIV, rate_limit)
        self.include_medrxiv = include_medrxiv
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.request_timeout),
            headers={
                "User-Agent": "ProtLitAI/1.0 (research@example.com; respectful scraping)",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
            }
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
        """Search for papers using bioRxiv search."""
        if not self.session:
            raise RuntimeError("BiorxivCollector must be used as async context manager")
        
        # Search both bioRxiv and medRxiv
        sources = [("bioRxiv", self.BIORXIV_BASE_URL)]
        if self.include_medrxiv:
            sources.append(("medRxiv", self.MEDRXIV_BASE_URL))
        
        papers_yielded = 0
        for source_name, base_url in sources:
            if papers_yielded >= max_results:
                break
                
            self.logger.info(f"Searching {source_name} for: {query}")
            
            async for paper in self._search_source(
                base_url, query, max_results - papers_yielded, date_from, date_to
            ):
                yield paper
                papers_yielded += 1
                
                if papers_yielded >= max_results:
                    break
    
    async def get_paper_details(self, paper_id: str) -> Optional[Paper]:
        """Get detailed information for a specific DOI or bioRxiv ID."""
        if not self.session:
            raise RuntimeError("BiorxivCollector must be used as async context manager")
        
        # Try to construct bioRxiv URL from paper_id
        if paper_id.startswith("10.1101/"):
            # This is a bioRxiv DOI
            biorxiv_id = paper_id.replace("10.1101/", "")
            url = f"{self.BIORXIV_BASE_URL}/content/10.1101/{biorxiv_id}v1"
        else:
            # Assume it's a direct bioRxiv URL or ID
            url = paper_id if paper_id.startswith("http") else f"{self.BIORXIV_BASE_URL}/content/{paper_id}"
        
        return await self._fetch_paper_details(url)
    
    async def collect_recent_papers(
        self,
        days_back: int = 1,
        max_papers: int = 1000,
        query_filter: Optional[str] = None
    ) -> List[Paper]:
        """Collect recent papers from bioRxiv/medRxiv."""
        self.logger.info(
            f"Starting collection from bioRxiv/medRxiv: "
            f"{days_back} days back, max {max_papers} papers"
        )
        
        papers = []
        
        # Use recent papers endpoints
        sources = [("bioRxiv", self.BIORXIV_BASE_URL)]
        if self.include_medrxiv:
            sources.append(("medRxiv", self.MEDRXIV_BASE_URL))
        
        for source_name, base_url in sources:
            self.logger.info(f"Collecting from {source_name}")
            
            source_papers = await self._collect_recent_from_source(
                base_url, days_back, max_papers // len(sources)
            )
            
            # Filter for relevance if needed
            for paper in source_papers:
                if self._is_relevant_paper(paper):
                    papers.append(paper)
                    
            if len(papers) >= max_papers:
                break
        
        # Sort by publication date
        papers.sort(key=lambda p: p.publication_date or datetime.min, reverse=True)
        
        self.stats.papers_collected = len(papers)
        self.stats.end_time = datetime.utcnow()
        
        self.logger.info(
            f"Collection completed: {len(papers)} papers "
            f"in {self.stats.duration.total_seconds():.1f}s"
        )
        
        return papers[:max_papers]
    
    async def _search_source(
        self,
        base_url: str,
        query: str,
        max_results: int,
        date_from: Optional[datetime],
        date_to: Optional[datetime]
    ) -> AsyncIterator[Paper]:
        """Search a specific source (bioRxiv or medRxiv)."""
        # Build search URL
        search_url = f"{base_url}/search/{quote(query)}"
        
        page = 0
        papers_found = 0
        
        while papers_found < max_results:
            # Add pagination parameter
            page_url = f"{search_url}?page={page}"
            
            try:
                papers = await self._fetch_search_results(page_url, base_url)
                
                if not papers:
                    break
                
                for paper in papers:
                    # Apply date filter
                    if date_from and paper.publication_date and paper.publication_date < date_from:
                        continue
                    if date_to and paper.publication_date and paper.publication_date > date_to:
                        continue
                    
                    if self._is_relevant_paper(paper):
                        yield paper
                        papers_found += 1
                        
                        if papers_found >= max_results:
                            break
                
                page += 1
                
                # Avoid infinite loops
                if page > 10:  # Reasonable limit
                    break
                    
            except Exception as e:
                self.logger.error(f"Error fetching search results from {base_url}: {e}")
                break
    
    async def _collect_recent_from_source(
        self,
        base_url: str,
        days_back: int,
        max_papers: int
    ) -> List[Paper]:
        """Collect recent papers from a specific source."""
        # Use the "new results" or recent papers page
        recent_url = f"{base_url}/content/about-biorxiv"  # This might need adjustment
        
        # Alternative: use search with date filter
        date_from = datetime.utcnow() - timedelta(days=days_back)
        search_query = "protein OR design OR structure OR folding"
        
        papers = []
        async for paper in self._search_source(
            base_url, search_query, max_papers, date_from, None
        ):
            papers.append(paper)
            
        return papers
    
    async def _fetch_search_results(self, url: str, base_url: str) -> List[Paper]:
        """Fetch and parse search results page."""
        async def fetch_page():
            async with self.session.get(url) as response:
                response.raise_for_status()
                return await response.text()
        
        html_content = await self._make_request_with_retry(fetch_page)
        return self._parse_search_results(html_content, base_url)
    
    async def _fetch_paper_details(self, url: str) -> Optional[Paper]:
        """Fetch detailed information for a specific paper."""
        async def fetch_page():
            async with self.session.get(url) as response:
                response.raise_for_status()
                return await response.text()
        
        try:
            html_content = await self._make_request_with_retry(fetch_page)
            return self._parse_paper_page(html_content, url)
        except Exception as e:
            self.logger.error(f"Error fetching paper details from {url}: {e}")
            return None
    
    def _parse_search_results(self, html_content: str, base_url: str) -> List[Paper]:
        """Parse search results HTML page."""
        soup = BeautifulSoup(html_content, 'html.parser')
        papers = []
        
        # Find paper entries (this might need adjustment based on site structure)
        paper_elements = soup.find_all(['div', 'article'], class_=re.compile(r'.*result.*|.*paper.*|.*article.*'))
        
        for element in paper_elements:
            try:
                paper = self._extract_paper_from_search_element(element, base_url)
                if paper:
                    papers.append(paper)
            except Exception as e:
                self.logger.debug(f"Error parsing search result element: {e}")
                continue
        
        return papers
    
    def _parse_paper_page(self, html_content: str, url: str) -> Optional[Paper]:
        """Parse detailed paper page."""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        try:
            # Extract title
            title_elem = soup.find('h1', {'id': 'page-title'}) or soup.find('h1')
            title = title_elem.get_text(strip=True) if title_elem else ""
            
            # Extract abstract
            abstract_elem = soup.find('div', {'id': 'abstract'}) or soup.find('div', class_='abstract')
            abstract = ""
            if abstract_elem:
                # Remove the "Abstract" label if present
                abstract_text = abstract_elem.get_text(separator=' ', strip=True)
                abstract = re.sub(r'^Abstract\s*', '', abstract_text, flags=re.IGNORECASE)
            
            # Extract authors
            authors = []
            author_elements = soup.find_all('span', class_='author') or soup.find_all('a', class_='author-name')
            for author_elem in author_elements:
                author_name = author_elem.get_text(strip=True)
                if author_name:
                    authors.append(author_name)
            
            # Extract DOI
            doi = None
            doi_elem = soup.find('span', class_='doi') or soup.find(text=re.compile(r'doi:'))
            if doi_elem:
                if isinstance(doi_elem, str):
                    doi_match = re.search(r'doi:\s*(.+)', doi_elem)
                    if doi_match:
                        doi = doi_match.group(1).strip()
                else:
                    doi = doi_elem.get_text(strip=True).replace('doi:', '').strip()
            
            # Extract publication date
            publication_date = None
            date_elem = soup.find('span', class_='published') or soup.find('time')
            if date_elem:
                date_text = date_elem.get_text(strip=True)
                publication_date = self._parse_date(date_text)
            
            # Extract PDF URL
            pdf_url = None
            pdf_link = soup.find('a', href=re.compile(r'\.pdf$')) or soup.find('a', text=re.compile(r'PDF'))
            if pdf_link:
                pdf_href = pdf_link.get('href')
                if pdf_href:
                    pdf_url = urljoin(url, pdf_href)
            
            # Determine source type
            source_type = SourceType.BIORXIV if 'biorxiv' in url.lower() else SourceType.BIORXIV
            
            # Generate unique ID
            paper_id = self._generate_paper_id(doi or url, title)
            
            return Paper(
                id=paper_id,
                title=title,
                abstract=abstract,
                authors=authors,
                journal="bioRxiv" if 'biorxiv' in url.lower() else "medRxiv",
                publication_date=publication_date,
                doi=doi,
                pdf_url=pdf_url,
                paper_type=PaperType.PREPRINT,
                source=source_type,
                processing_status="pending"
            )
            
        except Exception as e:
            self.logger.error(f"Error parsing paper page: {e}")
            return None
    
    def _extract_paper_from_search_element(self, element, base_url: str) -> Optional[Paper]:
        """Extract paper information from search result element."""
        try:
            # Extract title and link
            title_link = element.find('a', href=re.compile(r'/content/'))
            if not title_link:
                return None
            
            title = title_link.get_text(strip=True)
            paper_url = urljoin(base_url, title_link.get('href'))
            
            # Extract authors (simplified)
            authors = []
            author_text = element.find(text=re.compile(r'Authors?:'))
            if author_text:
                # Extract author names following "Authors:"
                author_parent = author_text.parent
                if author_parent:
                    author_content = author_parent.get_text()
                    # Simple parsing - this might need refinement
                    author_match = re.search(r'Authors?:\s*(.+)', author_content)
                    if author_match:
                        authors = [name.strip() for name in author_match.group(1).split(',')]
            
            # Extract date
            publication_date = None
            date_elem = element.find('span', class_='date') or element.find(text=re.compile(r'\d{4}-\d{2}-\d{2}'))
            if date_elem:
                date_text = date_elem if isinstance(date_elem, str) else date_elem.get_text()
                publication_date = self._parse_date(date_text)
            
            # Extract abstract preview
            abstract = ""
            abstract_elem = element.find('div', class_='abstract') or element.find('p')
            if abstract_elem:
                abstract = abstract_elem.get_text(strip=True)[:500]  # Preview only
            
            # Generate unique ID
            paper_id = self._generate_paper_id(paper_url, title)
            
            return Paper(
                id=paper_id,
                title=title,
                abstract=abstract,
                authors=authors,
                journal="bioRxiv" if 'biorxiv' in base_url.lower() else "medRxiv",
                publication_date=publication_date,
                pdf_url=f"{paper_url}.pdf",  # Common pattern
                paper_type=PaperType.PREPRINT,
                source=SourceType.BIORXIV,
                processing_status="pending"
            )
            
        except Exception as e:
            self.logger.debug(f"Error extracting paper from search element: {e}")
            return None
    
    def _parse_date(self, date_text: str) -> Optional[datetime]:
        """Parse various date formats."""
        date_text = date_text.strip()
        
        # Common patterns
        patterns = [
            r'(\d{4})-(\d{2})-(\d{2})',  # 2023-01-15
            r'(\d{2})/(\d{2})/(\d{4})',  # 01/15/2023
            r'(\d{1,2})\s+(\w+)\s+(\d{4})',  # 15 January 2023
        ]
        
        for pattern in patterns:
            match = re.search(pattern, date_text)
            if match:
                try:
                    if '-' in pattern:
                        year, month, day = match.groups()
                        return datetime(int(year), int(month), int(day))
                    elif '/' in pattern:
                        month, day, year = match.groups()
                        return datetime(int(year), int(month), int(day))
                    else:
                        day, month_name, year = match.groups()
                        month_map = {
                            'January': 1, 'February': 2, 'March': 3, 'April': 4,
                            'May': 5, 'June': 6, 'July': 7, 'August': 8,
                            'September': 9, 'October': 10, 'November': 11, 'December': 12,
                            'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
                            'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12
                        }
                        month = month_map.get(month_name, 1)
                        return datetime(int(year), month, int(day))
                except ValueError:
                    continue
        
        return None
    
    def _is_relevant_paper(self, paper: Paper) -> bool:
        """Check if paper is relevant to protein design."""
        if not paper.title and not paper.abstract:
            return False
        
        content = f"{paper.title} {paper.abstract}".lower()
        
        # Key terms for bioRxiv/medRxiv relevance
        relevant_terms = [
            "protein", "peptide", "amino acid", "structure", "folding",
            "design", "engineering", "computational", "molecular dynamics",
            "binding", "enzyme", "antibody", "drug", "therapeutic",
            "bioinformatics", "structural biology", "biochemistry"
        ]
        
        return any(term in content for term in relevant_terms)
    
    def _generate_paper_id(self, identifier: str, title: str) -> str:
        """Generate unique paper ID."""
        content = f"biorxiv_{identifier}_{title}"
        return hashlib.md5(content.encode()).hexdigest()


# Convenience function for easy usage
async def collect_biorxiv_papers(
    query: Optional[str] = None,
    days_back: int = 1,
    max_papers: int = 100,
    include_medrxiv: bool = True
) -> List[Paper]:
    """Collect papers from bioRxiv and optionally medRxiv."""
    async with BiorxivCollector(include_medrxiv=include_medrxiv) as collector:
        return await collector.collect_recent_papers(
            days_back=days_back,
            max_papers=max_papers,
            query_filter=query
        )