#!/usr/bin/env python3
"""
Production Literature Collection Script for ProtLitAI
Implements automated data collection from multiple sources with proper error handling and monitoring
"""

import sys
import asyncio
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Optional
import signal

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from core.config import config
from core.database import db_manager
from core.logging import get_logger
from core.repository import PaperRepository
from collectors.pubmed_collector import PubMedCollector
from collectors.arxiv_collector import ArxivCollector
from collectors.biorxiv_collector import BiorxivCollector
from processing.ml_models import get_model_manager
from core.models import Paper


class ProductionCollectionManager:
    """Manages production literature collection with monitoring and error handling."""
    
    def __init__(self):
        self.logger = get_logger("production_collection")
        self.paper_repo = PaperRepository()
        self.ml_manager = None
        self.is_running = False
        self.total_collected = 0
        self.errors = []
        
    async def initialize(self):
        """Initialize all components for production collection."""
        self.logger.info("Initializing production collection system...")
        
        try:
            # Initialize database
            db_manager.initialize()
            self.logger.info("Database initialized successfully")
            
            # Initialize ML models (this will take time on first run)
            self.logger.info("Initializing ML models (may take several minutes on first run)...")
            self.ml_manager = get_model_manager()
            self.ml_manager.warmup_models()
            self.logger.info("ML models initialized and warmed up")
            
            self.is_running = True
            self.logger.info("Production collection system ready")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize production collection: {e}")
            raise
    
    async def collect_pubmed_papers(self, days_back: int = 7, max_papers: int = 100) -> List[Paper]:
        """Collect recent papers from PubMed."""
        self.logger.info(f"Starting PubMed collection (last {days_back} days, max {max_papers} papers)")
        
        try:
            async with PubMedCollector() as collector:
                from datetime import datetime, timedelta
                date_from = datetime.now() - timedelta(days=days_back)
                
                papers = []
                async for paper in collector.search_papers(
                    query="protein design OR protein engineering OR computational protein design",
                    max_results=max_papers,
                    date_from=date_from
                ):
                    papers.append(paper)
                    if len(papers) >= max_papers:
                        break
                
                self.logger.info(f"Successfully collected {len(papers)} papers from PubMed")
                return papers
                
        except Exception as e:
            error_msg = f"PubMed collection failed: {e}"
            self.logger.error(error_msg)
            self.errors.append(error_msg)
            return []
    
    async def collect_arxiv_papers(self, days_back: int = 7, max_papers: int = 50) -> List[Paper]:
        """Collect recent papers from arXiv."""
        self.logger.info(f"Starting arXiv collection (last {days_back} days, max {max_papers} papers)")
        
        try:
            async with ArxivCollector() as collector:
                from datetime import datetime, timedelta
                date_from = datetime.now() - timedelta(days=days_back)
                
                papers = []
                async for paper in collector.search_papers(
                    query="protein design OR protein folding OR machine learning protein",
                    max_results=max_papers,
                    date_from=date_from
                ):
                    papers.append(paper)
                    if len(papers) >= max_papers:
                        break
                
                self.logger.info(f"Successfully collected {len(papers)} papers from arXiv")
                return papers
                
        except Exception as e:
            error_msg = f"arXiv collection failed: {e}"
            self.logger.error(error_msg)
            self.errors.append(error_msg)
            return []
    
    async def collect_biorxiv_papers(self, days_back: int = 7, max_papers: int = 30) -> List[Paper]:
        """Collect recent papers from bioRxiv."""
        self.logger.info(f"Starting bioRxiv collection (last {days_back} days, max {max_papers} papers)")
        
        try:
            async with BiorxivCollector() as collector:
                from datetime import datetime, timedelta
                date_from = datetime.now() - timedelta(days=days_back)
                
                papers = []
                async for paper in collector.search_papers(
                    query="protein design OR protein engineering",
                    max_results=max_papers,
                    date_from=date_from
                ):
                    papers.append(paper)
                    if len(papers) >= max_papers:
                        break
                
                self.logger.info(f"Successfully collected {len(papers)} papers from bioRxiv")
                return papers
                
        except Exception as e:
            error_msg = f"bioRxiv collection failed: {e}"
            self.logger.error(error_msg)
            self.errors.append(error_msg)
            return []
    
    async def process_and_store_papers(self, papers: List[Paper]) -> int:
        """Process papers with ML pipeline and store in database."""
        stored_count = 0
        
        if not papers:
            return stored_count
            
        self.logger.info(f"Processing and storing {len(papers)} papers...")
        
        for paper in papers:
            try:
                # Check if paper already exists
                existing = self.paper_repo.get_by_id(paper.id)
                if existing:
                    self.logger.debug(f"Paper {paper.id} already exists, skipping")
                    continue
                
                # Generate embeddings if abstract is available
                if paper.abstract and self.ml_manager:
                    try:
                        embeddings = self.ml_manager.generate_embeddings([paper.abstract])
                        if embeddings is not None and len(embeddings) > 0:
                            # Store embedding separately if needed
                            self.logger.debug(f"Generated embedding for paper {paper.id}")
                    except Exception as e:
                        self.logger.warning(f"Failed to generate embedding for {paper.id}: {e}")
                
                # Store paper in database
                result = self.paper_repo.create(paper)
                if result:
                    stored_count += 1
                    self.logger.debug(f"Stored paper: {paper.title[:50]}...")
                
            except Exception as e:
                error_msg = f"Failed to process paper {paper.id}: {e}"
                self.logger.error(error_msg)
                self.errors.append(error_msg)
        
        self.logger.info(f"Successfully processed and stored {stored_count} papers")
        return stored_count
    
    async def run_daily_collection(self, days_back: int = 1) -> dict:
        """Run daily literature collection from all sources."""
        start_time = datetime.now()
        self.logger.info(f"Starting daily collection run at {start_time}")
        
        results = {
            "start_time": start_time,
            "sources": {},
            "total_collected": 0,
            "total_stored": 0,
            "errors": [],
            "duration": None
        }
        
        # Collect from all sources in parallel
        collection_tasks = [
            self.collect_pubmed_papers(days_back=days_back, max_papers=50),
            self.collect_arxiv_papers(days_back=days_back, max_papers=25),
            self.collect_biorxiv_papers(days_back=days_back, max_papers=15)
        ]
        
        try:
            pubmed_papers, arxiv_papers, biorxiv_papers = await asyncio.gather(*collection_tasks)
            
            # Store results by source
            results["sources"]["pubmed"] = len(pubmed_papers)
            results["sources"]["arxiv"] = len(arxiv_papers)
            results["sources"]["biorxiv"] = len(biorxiv_papers)
            
            # Combine all papers
            all_papers = pubmed_papers + arxiv_papers + biorxiv_papers
            results["total_collected"] = len(all_papers)
            
            # Process and store papers
            stored_count = await self.process_and_store_papers(all_papers)
            results["total_stored"] = stored_count
            
            # Update totals
            self.total_collected += stored_count
            
        except Exception as e:
            error_msg = f"Collection run failed: {e}"
            self.logger.error(error_msg)
            results["errors"].append(error_msg)
        
        # Calculate duration
        end_time = datetime.now()
        results["duration"] = (end_time - start_time).total_seconds()
        results["errors"] = self.errors.copy()
        
        # Log summary
        self.logger.info(f"Daily collection completed in {results['duration']:.1f}s")
        self.logger.info(f"Collected: {results['total_collected']}, Stored: {results['total_stored']}")
        
        if results["errors"]:
            self.logger.warning(f"Encountered {len(results['errors'])} errors during collection")
        
        return results
    
    async def run_weekly_collection(self) -> dict:
        """Run comprehensive weekly collection (last 7 days)."""
        self.logger.info("Starting weekly comprehensive collection")
        return await self.run_daily_collection(days_back=7)
    
    async def shutdown(self):
        """Gracefully shutdown the collection system."""
        self.logger.info("Shutting down production collection system")
        self.is_running = False
        
        if self.ml_manager:
            try:
                self.ml_manager.cleanup()
            except Exception as e:
                self.logger.warning(f"Error during ML manager cleanup: {e}")
        
        try:
            db_manager.close_connections()
        except Exception as e:
            self.logger.warning(f"Error closing database connections: {e}")
        
        self.logger.info("Production collection system shutdown complete")


async def main():
    """Main entry point for production collection."""
    # Set up signal handlers for graceful shutdown
    manager = ProductionCollectionManager()
    
    def signal_handler(signum, frame):
        print(f"\nReceived signal {signum}, initiating graceful shutdown...")
        asyncio.create_task(manager.shutdown())
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Initialize system
        await manager.initialize()
        
        # Run collection based on command line arguments
        import argparse
        parser = argparse.ArgumentParser(description="ProtLitAI Production Literature Collection")
        parser.add_argument("--mode", choices=["daily", "weekly", "test"], default="daily",
                          help="Collection mode: daily (last 1 day), weekly (last 7 days), test (small sample)")
        parser.add_argument("--days", type=int, default=None,
                          help="Override number of days to look back")
        
        args = parser.parse_args()
        
        if args.mode == "test":
            # Quick test collection
            print("Running test collection (small sample)...")
            results = await manager.run_daily_collection(days_back=1)
            
        elif args.mode == "weekly":
            print("Running weekly collection...")
            results = await manager.run_weekly_collection()
            
        else:  # daily
            days = args.days if args.days else 1
            print(f"Running daily collection (last {days} days)...")
            results = await manager.run_daily_collection(days_back=days)
        
        # Print summary
        print("\n" + "="*60)
        print("COLLECTION SUMMARY")
        print("="*60)
        print(f"Duration: {results['duration']:.1f} seconds")
        print(f"Total papers collected: {results['total_collected']}")
        print(f"Total papers stored: {results['total_stored']}")
        print(f"Sources:")
        for source, count in results['sources'].items():
            print(f"  - {source}: {count} papers")
        
        if results['errors']:
            print(f"\nErrors encountered: {len(results['errors'])}")
            for error in results['errors'][:5]:  # Show first 5 errors
                print(f"  - {error}")
        
        print(f"\nTotal papers in database: {manager.total_collected}")
        
    except KeyboardInterrupt:
        print("\nCollection interrupted by user")
    except Exception as e:
        print(f"Collection failed: {e}")
        return 1
    finally:
        await manager.shutdown()
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)