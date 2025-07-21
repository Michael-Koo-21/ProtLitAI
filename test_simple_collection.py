#!/usr/bin/env python3
"""
Simple test of core collection functionality
"""

import sys
import asyncio
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from core.config import config
from core.database import db_manager
from core.repository import PaperRepository
from collectors.pubmed_collector import PubMedCollector


async def test_simple_collection():
    """Test basic collection functionality."""
    print("🧪 Testing Simple Collection")
    print("-" * 50)
    
    # Initialize database
    print("Initializing database...")
    db_manager.initialize()
    
    # Test PubMed collection
    print("Testing PubMed collection...")
    async with PubMedCollector() as collector:
        # Get a small sample of recent papers
        from datetime import datetime, timedelta
        date_from = datetime.now() - timedelta(days=7)
        
        papers = []
        async for paper in collector.search_papers(
            query="protein design",
            max_results=3,
            date_from=date_from
        ):
            papers.append(paper)
        
        print(f"Found {len(papers)} papers:")
        for i, paper in enumerate(papers, 1):
            print(f"{i}. {paper.title[:60]}...")
            print(f"   Journal: {paper.journal}")
            print(f"   Authors: {len(paper.authors)} authors")
            print(f"   PMID: {paper.pubmed_id}")
            print()
        
        # Store in database
        if papers:
            paper_repo = PaperRepository()
            stored = 0
            for paper in papers:
                result = paper_repo.create(paper)
                if result:
                    stored += 1
            
            print(f"Stored {stored}/{len(papers)} papers in database")
        
    # Cleanup
    db_manager.close_connections()
    print("✅ Simple collection test completed")


if __name__ == "__main__":
    asyncio.run(test_simple_collection())