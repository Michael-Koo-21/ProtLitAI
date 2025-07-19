#!/usr/bin/env python3
"""Test script for PubMed collector."""

import asyncio
import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from collectors.pubmed_collector import collect_pubmed_papers
from core.logging import setup_logging


async def test_pubmed_collection():
    """Test PubMed paper collection."""
    # Setup logging
    setup_logging()
    
    print("Testing PubMed collection...")
    print("Collecting recent protein design papers (last 30 days, max 5 papers)")
    
    try:
        papers = await collect_pubmed_papers(
            days_back=30,
            max_papers=5
        )
        
        print(f"\nCollected {len(papers)} papers:")
        print("-" * 80)
        
        for i, paper in enumerate(papers, 1):
            print(f"\n{i}. {paper.title}")
            print(f"   Authors: {', '.join(paper.authors[:3])}{'...' if len(paper.authors) > 3 else ''}")
            print(f"   Journal: {paper.journal}")
            print(f"   Date: {paper.publication_date}")
            print(f"   PMID: {paper.pubmed_id}")
            print(f"   DOI: {paper.doi}")
            if paper.abstract:
                abstract_preview = paper.abstract[:200] + "..." if len(paper.abstract) > 200 else paper.abstract
                print(f"   Abstract: {abstract_preview}")
        
        print(f"\nTest completed successfully! Collected {len(papers)} papers.")
        
    except Exception as e:
        print(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_pubmed_collection())