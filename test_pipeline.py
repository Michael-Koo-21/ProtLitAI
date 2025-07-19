#!/usr/bin/env python3
"""Integration test for the complete data collection pipeline."""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from collectors.pubmed_collector import collect_pubmed_papers
from collectors.arxiv_collector import collect_arxiv_papers
from processing.pdf_processor import process_single_paper
from core.logging import setup_logging


async def test_complete_pipeline():
    """Test the complete data collection and processing pipeline."""
    setup_logging()
    
    print("=" * 80)
    print("TESTING COMPLETE LITERATURE COLLECTION PIPELINE")
    print("=" * 80)
    
    try:
        # Test 1: Collect from PubMed
        print("\n1. Testing PubMed Collection...")
        pubmed_papers = await collect_pubmed_papers(days_back=30, max_papers=2)
        print(f"✅ PubMed: Collected {len(pubmed_papers)} papers")
        
        # Test 2: Collect from arXiv
        print("\n2. Testing arXiv Collection...")
        arxiv_papers = await collect_arxiv_papers(days_back=7, max_papers=2, use_rss=True)
        print(f"✅ arXiv: Collected {len(arxiv_papers)} papers")
        
        # Test 3: Show collected papers
        all_papers = pubmed_papers + arxiv_papers
        print(f"\n3. Total Papers Collected: {len(all_papers)}")
        print("-" * 60)
        
        for i, paper in enumerate(all_papers, 1):
            print(f"\nPaper {i}:")
            print(f"  Title: {paper.title[:80]}{'...' if len(paper.title) > 80 else ''}")
            print(f"  Source: {paper.source}")
            print(f"  Date: {paper.publication_date}")
            if paper.pubmed_id:
                print(f"  PMID: {paper.pubmed_id}")
            if paper.arxiv_id:
                print(f"  arXiv ID: {paper.arxiv_id}")
            if paper.pdf_url:
                print(f"  PDF URL: {paper.pdf_url[:60]}{'...' if len(paper.pdf_url) > 60 else ''}")
        
        # Test 4: PDF Processing (if any papers have PDF URLs)
        papers_with_pdfs = [p for p in all_papers if p.pdf_url]
        if papers_with_pdfs:
            print(f"\n4. Testing PDF Processing on {len(papers_with_pdfs)} papers with PDF URLs...")
            
            # Process first paper with PDF
            test_paper = papers_with_pdfs[0]
            print(f"   Processing: {test_paper.title[:60]}...")
            
            result = await process_single_paper(test_paper)
            
            if result.success:
                print("✅ PDF Processing: Success!")
                print(f"   Extracted {len(result.full_text)} characters of text")
                print(f"   Found {len(result.sections)} sections")
                print(f"   Method used: {result.metadata.get('method', 'unknown')}")
                print(f"   Processing time: {result.processing_time:.2f}s")
                
                # Show extracted sections
                if result.sections:
                    print("   Sections found:", list(result.sections.keys()))
                
                # Show preview of text
                if result.full_text:
                    preview = result.full_text[:200].replace('\n', ' ')
                    print(f"   Text preview: {preview}...")
            else:
                print(f"❌ PDF Processing failed: {result.error_message}")
        else:
            print("\n4. No papers with PDF URLs found for processing test")
        
        print("\n" + "=" * 80)
        print("PIPELINE TEST COMPLETED SUCCESSFULLY!")
        print("=" * 80)
        
        # Summary
        print(f"\nSummary:")
        print(f"- PubMed papers: {len(pubmed_papers)}")
        print(f"- arXiv papers: {len(arxiv_papers)}")
        print(f"- Total papers: {len(all_papers)}")
        print(f"- Papers with PDFs: {len(papers_with_pdfs)}")
        print(f"- Ready for next phase: NLP Processing")
        
    except Exception as e:
        print(f"\n❌ Pipeline test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_complete_pipeline())