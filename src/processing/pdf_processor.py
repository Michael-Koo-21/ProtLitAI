"""PDF processing pipeline for text extraction and content analysis."""

import asyncio
import aiohttp
import aiofiles
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
import hashlib
import tempfile
import logging
from dataclasses import dataclass
import re

# PDF processing libraries
try:
    import PyPDF2
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

from core.models import Paper
from core.config import config
from core.logging import get_logger


@dataclass
class ProcessingResult:
    """Result of PDF processing."""
    success: bool
    full_text: str = ""
    sections: Dict[str, str] = None
    figures_text: List[str] = None
    tables_text: List[str] = None
    metadata: Dict[str, Any] = None
    error_message: str = ""
    processing_time: float = 0.0
    
    def __post_init__(self):
        if self.sections is None:
            self.sections = {}
        if self.figures_text is None:
            self.figures_text = []
        if self.tables_text is None:
            self.tables_text = []
        if self.metadata is None:
            self.metadata = {}


class PDFProcessor:
    """Advanced PDF processing with multiple extraction methods."""
    
    def __init__(self):
        self.logger = get_logger("pdf_processor")
        self.storage_path = Path(config.get("pdf_storage_path", "cache/pdfs"))
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Check available libraries
        self.available_methods = []
        if PYPDF2_AVAILABLE:
            self.available_methods.append("pypdf2")
        if PDFPLUMBER_AVAILABLE:
            self.available_methods.append("pdfplumber")
        if PYMUPDF_AVAILABLE:
            self.available_methods.append("pymupdf")
        
        if not self.available_methods:
            self.logger.warning("No PDF processing libraries available!")
        else:
            self.logger.info(f"Available PDF methods: {self.available_methods}")
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=60),  # PDFs can be large
            headers={"User-Agent": "ProtLitAI/1.0 (research@example.com)"}
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def process_paper(self, paper: Paper) -> ProcessingResult:
        """Process a paper's PDF and extract text content."""
        import time
        start_time = time.time()
        
        try:
            # Download PDF if needed
            pdf_path = await self._get_pdf_path(paper)
            if not pdf_path:
                return ProcessingResult(
                    success=False,
                    error_message="Could not download or locate PDF",
                    processing_time=time.time() - start_time
                )
            
            # Extract text using best available method
            result = await self._extract_text_from_pdf(pdf_path)
            result.processing_time = time.time() - start_time
            
            self.logger.info(
                f"Processed PDF for paper {paper.id}: "
                f"{'success' if result.success else 'failed'} "
                f"in {result.processing_time:.2f}s"
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error processing PDF for paper {paper.id}: {e}")
            return ProcessingResult(
                success=False,
                error_message=str(e),
                processing_time=time.time() - start_time
            )
    
    async def _get_pdf_path(self, paper: Paper) -> Optional[Path]:
        """Get local path to PDF, downloading if necessary."""
        # Check if already downloaded
        if paper.local_pdf_path and Path(paper.local_pdf_path).exists():
            return Path(paper.local_pdf_path)
        
        # Generate local filename
        pdf_filename = self._generate_pdf_filename(paper)
        local_path = self.storage_path / pdf_filename
        
        if local_path.exists():
            return local_path
        
        # Download PDF
        if paper.pdf_url:
            success = await self._download_pdf(paper.pdf_url, local_path)
            if success:
                return local_path
        
        return None
    
    async def _download_pdf(self, url: str, local_path: Path) -> bool:
        """Download PDF from URL."""
        if not self.session:
            self.logger.error("PDFProcessor must be used as async context manager")
            return False
        
        try:
            self.logger.info(f"Downloading PDF from {url}")
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    async with aiofiles.open(local_path, 'wb') as f:
                        async for chunk in response.content.iter_chunked(8192):
                            await f.write(chunk)
                    
                    self.logger.info(f"Downloaded PDF to {local_path}")
                    return True
                else:
                    self.logger.error(f"Failed to download PDF: HTTP {response.status}")
                    return False
                    
        except Exception as e:
            self.logger.error(f"Error downloading PDF: {e}")
            return False
    
    async def _extract_text_from_pdf(self, pdf_path: Path) -> ProcessingResult:
        """Extract text from PDF using available methods."""
        # Try methods in order of preference
        methods = ["pdfplumber", "pymupdf", "pypdf2"]
        
        for method in methods:
            if method in self.available_methods:
                try:
                    result = await self._extract_with_method(pdf_path, method)
                    if result.success and result.full_text.strip():
                        return result
                except Exception as e:
                    self.logger.warning(f"Method {method} failed: {e}")
                    continue
        
        return ProcessingResult(
            success=False,
            error_message="All extraction methods failed"
        )
    
    async def _extract_with_method(self, pdf_path: Path, method: str) -> ProcessingResult:
        """Extract text using specific method."""
        self.logger.debug(f"Extracting text with {method}")
        
        if method == "pdfplumber":
            return await self._extract_with_pdfplumber(pdf_path)
        elif method == "pymupdf":
            return await self._extract_with_pymupdf(pdf_path)
        elif method == "pypdf2":
            return await self._extract_with_pypdf2(pdf_path)
        else:
            raise ValueError(f"Unknown extraction method: {method}")
    
    async def _extract_with_pdfplumber(self, pdf_path: Path) -> ProcessingResult:
        """Extract text using pdfplumber (best for text extraction)."""
        import pdfplumber
        
        try:
            full_text = ""
            tables_text = []
            
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    # Extract text
                    page_text = page.extract_text()
                    if page_text:
                        full_text += f"\n--- Page {page_num + 1} ---\n{page_text}\n"
                    
                    # Extract tables
                    tables = page.extract_tables()
                    for table in tables:
                        if table:
                            table_text = self._table_to_text(table)
                            tables_text.append(table_text)
            
            # Parse sections
            sections = self._parse_sections(full_text)
            
            return ProcessingResult(
                success=True,
                full_text=full_text.strip(),
                sections=sections,
                tables_text=tables_text,
                metadata={"method": "pdfplumber", "pages": len(pdf.pages)}
            )
            
        except Exception as e:
            return ProcessingResult(
                success=False,
                error_message=f"pdfplumber extraction failed: {e}"
            )
    
    async def _extract_with_pymupdf(self, pdf_path: Path) -> ProcessingResult:
        """Extract text using PyMuPDF (good for complex layouts)."""
        import fitz
        
        try:
            doc = fitz.open(pdf_path)
            full_text = ""
            figures_text = []
            
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                
                # Extract text
                page_text = page.get_text()
                if page_text:
                    full_text += f"\n--- Page {page_num + 1} ---\n{page_text}\n"
                
                # Extract text from figures/images (if available)
                try:
                    text_dict = page.get_text("dict")
                    for block in text_dict.get("blocks", []):
                        if "lines" in block:
                            for line in block["lines"]:
                                for span in line.get("spans", []):
                                    if span.get("flags", 0) & 2**4:  # Italic text (often captions)
                                        figures_text.append(span.get("text", ""))
                except Exception:
                    pass
            
            doc.close()
            
            # Parse sections
            sections = self._parse_sections(full_text)
            
            return ProcessingResult(
                success=True,
                full_text=full_text.strip(),
                sections=sections,
                figures_text=figures_text,
                metadata={"method": "pymupdf", "pages": len(doc)}
            )
            
        except Exception as e:
            return ProcessingResult(
                success=False,
                error_message=f"PyMuPDF extraction failed: {e}"
            )
    
    async def _extract_with_pypdf2(self, pdf_path: Path) -> ProcessingResult:
        """Extract text using PyPDF2 (basic but reliable)."""
        import PyPDF2
        
        try:
            full_text = ""
            
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                for page_num, page in enumerate(pdf_reader.pages):
                    page_text = page.extract_text()
                    if page_text:
                        full_text += f"\n--- Page {page_num + 1} ---\n{page_text}\n"
            
            # Parse sections
            sections = self._parse_sections(full_text)
            
            return ProcessingResult(
                success=True,
                full_text=full_text.strip(),
                sections=sections,
                metadata={"method": "pypdf2", "pages": len(pdf_reader.pages)}
            )
            
        except Exception as e:
            return ProcessingResult(
                success=False,
                error_message=f"PyPDF2 extraction failed: {e}"
            )
    
    def _parse_sections(self, text: str) -> Dict[str, str]:
        """Parse text into sections (Abstract, Introduction, Methods, etc.)."""
        sections = {}
        
        # Common section headers in academic papers
        section_patterns = {
            "abstract": r"(?i)(?:^|\n)\s*(?:abstract|summary)\s*(?:\n|$)",
            "introduction": r"(?i)(?:^|\n)\s*(?:introduction|background)\s*(?:\n|$)",
            "methods": r"(?i)(?:^|\n)\s*(?:methods?|methodology|materials?\s+and\s+methods?)\s*(?:\n|$)",
            "results": r"(?i)(?:^|\n)\s*(?:results?|findings?)\s*(?:\n|$)",
            "discussion": r"(?i)(?:^|\n)\s*(?:discussion|analysis)\s*(?:\n|$)",
            "conclusion": r"(?i)(?:^|\n)\s*(?:conclusions?|summary|concluding\s+remarks?)\s*(?:\n|$)",
            "references": r"(?i)(?:^|\n)\s*(?:references?|bibliography|citations?)\s*(?:\n|$)"
        }
        
        # Find section boundaries
        section_starts = {}
        for section_name, pattern in section_patterns.items():
            match = re.search(pattern, text)
            if match:
                section_starts[section_name] = match.end()
        
        # Extract section content
        sorted_sections = sorted(section_starts.items(), key=lambda x: x[1])
        
        for i, (section_name, start_pos) in enumerate(sorted_sections):
            end_pos = sorted_sections[i + 1][1] if i + 1 < len(sorted_sections) else len(text)
            section_text = text[start_pos:end_pos].strip()
            
            # Clean up section text
            section_text = re.sub(r'\n\s*---\s*Page\s+\d+\s*---\s*\n', '\n', section_text)
            section_text = re.sub(r'\n{3,}', '\n\n', section_text)
            
            if section_text:
                sections[section_name] = section_text
        
        return sections
    
    def _table_to_text(self, table: List[List[str]]) -> str:
        """Convert table to readable text format."""
        if not table:
            return ""
        
        # Simple table to text conversion
        text_lines = []
        for row in table:
            if row:
                cleaned_row = [str(cell).strip() if cell else "" for cell in row]
                text_lines.append(" | ".join(cleaned_row))
        
        return "\n".join(text_lines)
    
    def _generate_pdf_filename(self, paper: Paper) -> str:
        """Generate consistent filename for PDF storage."""
        # Use paper ID or create from title/source
        if paper.doi:
            base_name = paper.doi.replace("/", "_").replace(":", "_")
        elif paper.arxiv_id:
            base_name = f"arxiv_{paper.arxiv_id}"
        elif paper.pubmed_id:
            base_name = f"pubmed_{paper.pubmed_id}"
        else:
            # Use hash of title
            title_hash = hashlib.md5(paper.title.encode()).hexdigest()[:12]
            base_name = f"{paper.source}_{title_hash}"
        
        return f"{base_name}.pdf"
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get processing statistics."""
        return {
            "available_methods": self.available_methods,
            "storage_path": str(self.storage_path),
            "total_pdfs": len(list(self.storage_path.glob("*.pdf")))
        }


# Convenience function for batch processing
async def process_papers_batch(papers: List[Paper]) -> List[Tuple[Paper, ProcessingResult]]:
    """Process multiple papers in batch."""
    async with PDFProcessor() as processor:
        results = []
        
        for paper in papers:
            result = await processor.process_paper(paper)
            results.append((paper, result))
        
        return results


# Convenience function for single paper
async def process_single_paper(paper: Paper) -> ProcessingResult:
    """Process a single paper's PDF."""
    async with PDFProcessor() as processor:
        return await processor.process_paper(paper)