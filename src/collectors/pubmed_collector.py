"""PubMed literature collector using E-utilities API."""

import asyncio
import aiohttp
import xml.etree.ElementTree as ET
from typing import List, Dict, Any, Optional, AsyncIterator
from datetime import datetime
from urllib.parse import urlencode
import hashlib

from .base_collector import BaseCollector
from core.models import Paper, SourceType, PaperType
from core.config import config


class PubMedCollector(BaseCollector):
    """Collector for PubMed literature using E-utilities API."""
    
    BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    
    def __init__(self):
        rate_limit = config.get("pubmed_rate_limit", 10.0)
        super().__init__(SourceType.PUBMED, rate_limit)
        self.api_key = config.get("pubmed_api_key")
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.request_timeout)
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
        """Search for papers using PubMed E-utilities."""
        if not self.session:
            raise RuntimeError("PubMedCollector must be used as async context manager")
        
        # Step 1: Search for PMIDs
        pmids = await self._search_pmids(query, max_results, date_from, date_to)
        self.logger.info(f"Found {len(pmids)} PMIDs for query")
        
        # Step 2: Fetch details in batches
        batch_size = 100  # PubMed API limitation
        for i in range(0, len(pmids), batch_size):
            batch_pmids = pmids[i:i + batch_size]
            papers = await self._fetch_paper_details(batch_pmids)
            
            for paper in papers:
                yield paper
    
    async def get_paper_details(self, paper_id: str) -> Optional[Paper]:
        """Get detailed information for a specific PMID."""
        if not self.session:
            raise RuntimeError("PubMedCollector must be used as async context manager")
        
        try:
            pmid = int(paper_id)
            papers = await self._fetch_paper_details([pmid])
            return papers[0] if papers else None
        except ValueError:
            self.logger.error(f"Invalid PMID: {paper_id}")
            return None
    
    async def _search_pmids(
        self,
        query: str,
        max_results: int,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> List[int]:
        """Search for PMIDs using esearch."""
        params = {
            "db": "pubmed",
            "term": query,
            "retmax": min(max_results, 10000),  # API limit
            "retmode": "xml",
            "sort": "pub date",
            "tool": "ProtLitAI",
            "email": "research@example.com"
        }
        
        if self.api_key:
            params["api_key"] = self.api_key
        
        # Add date range if specified
        if date_from or date_to:
            date_filter = self._build_date_filter(date_from, date_to)
            params["term"] += f" AND {date_filter}"
        
        url = f"{self.BASE_URL}/esearch.fcgi"
        
        async def make_search_request():
            async with self.session.get(url, params=params) as response:
                response.raise_for_status()
                return await response.text()
        
        xml_text = await self._make_request_with_retry(make_search_request)
        return self._parse_search_results(xml_text)
    
    async def _fetch_paper_details(self, pmids: List[int]) -> List[Paper]:
        """Fetch paper details using efetch."""
        if not pmids:
            return []
        
        params = {
            "db": "pubmed",
            "id": ",".join(map(str, pmids)),
            "retmode": "xml",
            "rettype": "abstract",
            "tool": "ProtLitAI",
            "email": "research@example.com"
        }
        
        if self.api_key:
            params["api_key"] = self.api_key
        
        url = f"{self.BASE_URL}/efetch.fcgi"
        
        async def make_fetch_request():
            async with self.session.get(url, params=params) as response:
                response.raise_for_status()
                return await response.text()
        
        xml_text = await self._make_request_with_retry(make_fetch_request)
        return self._parse_paper_details(xml_text)
    
    def _build_date_filter(
        self,
        date_from: Optional[datetime],
        date_to: Optional[datetime]
    ) -> str:
        """Build PubMed date filter."""
        if not date_from and not date_to:
            return ""
        
        date_from_str = date_from.strftime("%Y/%m/%d") if date_from else ""
        date_to_str = date_to.strftime("%Y/%m/%d") if date_to else ""
        
        if date_from_str and date_to_str:
            return f'("{date_from_str}"[Date - Publication] : "{date_to_str}"[Date - Publication])'
        elif date_from_str:
            return f'"{date_from_str}"[Date - Publication] : 3000[Date - Publication]'
        else:
            return f'1900[Date - Publication] : "{date_to_str}"[Date - Publication]'
    
    def _parse_search_results(self, xml_text: str) -> List[int]:
        """Parse search results XML to extract PMIDs."""
        try:
            root = ET.fromstring(xml_text)
            pmids = []
            
            # Check for errors
            error_list = root.find("ErrorList")
            if error_list is not None:
                errors = [error.text for error in error_list.findall("PhraseNotFound")]
                if errors:
                    self.logger.warning(f"PubMed search warnings: {errors}")
            
            # Extract PMIDs
            id_list = root.find("IdList")
            if id_list is not None:
                for id_elem in id_list.findall("Id"):
                    try:
                        pmids.append(int(id_elem.text))
                    except (ValueError, TypeError):
                        continue
            
            return pmids
            
        except ET.ParseError as e:
            self.logger.error(f"Failed to parse search results XML: {e}")
            return []
    
    def _parse_paper_details(self, xml_text: str) -> List[Paper]:
        """Parse paper details XML to extract Paper objects."""
        try:
            root = ET.fromstring(xml_text)
            papers = []
            
            for article in root.findall(".//PubmedArticle"):
                paper = self._extract_paper_from_article(article)
                if paper:
                    papers.append(paper)
            
            return papers
            
        except ET.ParseError as e:
            self.logger.error(f"Failed to parse paper details XML: {e}")
            return []
    
    def _extract_paper_from_article(self, article: ET.Element) -> Optional[Paper]:
        """Extract Paper object from PubmedArticle XML element."""
        try:
            # Get PMID
            pmid_elem = article.find(".//PMID")
            if pmid_elem is None:
                return None
            
            pmid = int(pmid_elem.text)
            
            # Get basic article info
            medline_citation = article.find("MedlineCitation")
            if medline_citation is None:
                return None
            
            article_elem = medline_citation.find("Article")
            if article_elem is None:
                return None
            
            # Extract title
            title_elem = article_elem.find("ArticleTitle")
            title = title_elem.text if title_elem is not None else ""
            
            # Extract abstract
            abstract_text = ""
            abstract = article_elem.find("Abstract")
            if abstract is not None:
                abstract_parts = []
                for abstract_text_elem in abstract.findall("AbstractText"):
                    text = abstract_text_elem.text or ""
                    label = abstract_text_elem.get("Label", "")
                    if label:
                        text = f"{label}: {text}"
                    abstract_parts.append(text)
                abstract_text = " ".join(abstract_parts)
            
            # Extract authors
            authors = []
            author_list = article_elem.find("AuthorList")
            if author_list is not None:
                for author in author_list.findall("Author"):
                    last_name = author.find("LastName")
                    fore_name = author.find("ForeName")
                    if last_name is not None:
                        name_parts = [last_name.text]
                        if fore_name is not None:
                            name_parts.append(fore_name.text)
                        authors.append(" ".join(name_parts))
            
            # Extract journal
            journal_elem = article_elem.find(".//Title")
            journal = journal_elem.text if journal_elem is not None else ""
            
            # Extract publication date
            pub_date = self._extract_publication_date(article_elem)
            
            # Extract DOI
            doi = None
            for article_id in article_elem.findall(".//ArticleId"):
                if article_id.get("IdType") == "doi":
                    doi = article_id.text
                    break
            
            # Generate unique ID
            paper_id = self._generate_paper_id(pmid, title)
            
            return Paper(
                id=paper_id,
                title=title,
                abstract=abstract_text,
                authors=authors,
                journal=journal,
                publication_date=pub_date,
                doi=doi,
                pubmed_id=pmid,
                paper_type=PaperType.JOURNAL,
                source=SourceType.PUBMED,
                processing_status="pending"
            )
            
        except Exception as e:
            self.logger.error(f"Failed to extract paper from article: {e}")
            return None
    
    def _extract_publication_date(self, article: ET.Element) -> Optional[datetime]:
        """Extract publication date from article XML."""
        # Try different date elements
        date_elements = [
            "Journal/JournalIssue/PubDate",
            "ArticleDate",
            "Journal/JournalIssue/PubDate"
        ]
        
        for date_path in date_elements:
            date_elem = article.find(date_path)
            if date_elem is not None:
                year_elem = date_elem.find("Year")
                month_elem = date_elem.find("Month")
                day_elem = date_elem.find("Day")
                
                try:
                    year = int(year_elem.text) if year_elem is not None else None
                    month = self._parse_month(month_elem.text) if month_elem is not None else 1
                    day = int(day_elem.text) if day_elem is not None else 1
                    
                    if year:
                        return datetime(year, month, day)
                except (ValueError, TypeError):
                    continue
        
        return None
    
    def _parse_month(self, month_str: str) -> int:
        """Parse month string to integer."""
        month_map = {
            "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
            "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
            "January": 1, "February": 2, "March": 3, "April": 4,
            "June": 6, "July": 7, "August": 8, "September": 9,
            "October": 10, "November": 11, "December": 12
        }
        
        if month_str.isdigit():
            return min(max(int(month_str), 1), 12)
        
        return month_map.get(month_str, 1)
    
    def _generate_paper_id(self, pmid: int, title: str) -> str:
        """Generate unique paper ID."""
        content = f"pubmed_{pmid}_{title}"
        return hashlib.md5(content.encode()).hexdigest()


# Convenience function for easy usage
async def collect_pubmed_papers(
    query: Optional[str] = None,
    days_back: int = 1,
    max_papers: int = 100
) -> List[Paper]:
    """Collect papers from PubMed."""
    async with PubMedCollector() as collector:
        return await collector.collect_recent_papers(
            days_back=days_back,
            max_papers=max_papers,
            query_filter=query
        )