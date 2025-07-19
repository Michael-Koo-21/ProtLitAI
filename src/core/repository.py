"""Data access layer for ProtLitAI."""

import json
import sqlite3
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from core.database import db_manager
from core.models import Paper, Author, Entity, Embedding, Trend, Alert
from core.logging import get_logger, PerformanceLogger


class PaperRepository:
    """Repository for paper data access."""
    
    def __init__(self):
        self.logger = get_logger("paper_repository")
    
    def create(self, paper: Paper) -> str:
        """Create a new paper record."""
        with PerformanceLogger(self.logger, "create_paper"):
            with db_manager.get_sqlite_connection() as conn:
                cursor = conn.execute("""
                    INSERT INTO papers (
                        id, title, abstract, authors, journal, publication_date,
                        doi, arxiv_id, pubmed_id, pdf_url, local_pdf_path, full_text,
                        paper_type, source, relevance_score, processing_status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    paper.id, paper.title, paper.abstract, 
                    json.dumps(paper.authors), paper.journal, paper.publication_date,
                    paper.doi, paper.arxiv_id, paper.pubmed_id, paper.pdf_url,
                    paper.local_pdf_path, paper.full_text, 
                    paper.paper_type.value if hasattr(paper.paper_type, 'value') else paper.paper_type,
                    paper.source.value if hasattr(paper.source, 'value') else paper.source, 
                    paper.relevance_score, 
                    paper.processing_status.value if hasattr(paper.processing_status, 'value') else paper.processing_status
                ))
                conn.commit()
                
                self.logger.info("Paper created", paper_id=paper.id)
                return paper.id
    
    def get_by_id(self, paper_id: str) -> Optional[Paper]:
        """Get paper by ID."""
        with PerformanceLogger(self.logger, "get_paper_by_id"):
            with db_manager.get_sqlite_connection() as conn:
                conn.row_factory = sqlite3.Row
                result = conn.execute(
                    "SELECT * FROM papers WHERE id = ?", (paper_id,)
                ).fetchone()
                
                if result:
                    return self._row_to_paper(result)
                return None
    
    def get_by_doi(self, doi: str) -> Optional[Paper]:
        """Get paper by DOI."""
        with PerformanceLogger(self.logger, "get_paper_by_doi"):
            with db_manager.get_sqlite_connection() as conn:
                conn.row_factory = sqlite3.Row
                result = conn.execute(
                    "SELECT * FROM papers WHERE doi = ?", (doi,)
                ).fetchone()
                
                if result:
                    return self._row_to_paper(result)
                return None
    
    def search(self, query: str, limit: int = 50, offset: int = 0) -> List[Paper]:
        """Search papers using full-text search."""
        with PerformanceLogger(self.logger, "search_papers", query=query):
            with db_manager.get_sqlite_connection() as conn:
                conn.row_factory = sqlite3.Row
                results = conn.execute("""
                    SELECT p.* FROM papers p
                    JOIN papers_fts fts ON p.rowid = fts.rowid
                    WHERE papers_fts MATCH ?
                    ORDER BY rank
                    LIMIT ? OFFSET ?
                """, (query, limit, offset)).fetchall()
                
                papers = [self._row_to_paper(row) for row in results]
                self.logger.info("Papers searched", 
                               query=query, results_count=len(papers))
                return papers
    
    def get_recent(self, limit: int = 20) -> List[Paper]:
        """Get recently added papers."""
        with PerformanceLogger(self.logger, "get_recent_papers"):
            with db_manager.get_sqlite_connection() as conn:
                conn.row_factory = sqlite3.Row
                results = conn.execute("""
                    SELECT * FROM papers 
                    ORDER BY created_at DESC 
                    LIMIT ?
                """, (limit,)).fetchall()
                
                return [self._row_to_paper(row) for row in results]
    
    def get_by_source(self, source: str, limit: int = 100) -> List[Paper]:
        """Get papers by source."""
        with PerformanceLogger(self.logger, "get_papers_by_source", source=source):
            with db_manager.get_sqlite_connection() as conn:
                conn.row_factory = sqlite3.Row
                results = conn.execute("""
                    SELECT * FROM papers 
                    WHERE source = ?
                    ORDER BY publication_date DESC 
                    LIMIT ?
                """, (source, limit)).fetchall()
                
                return [self._row_to_paper(row) for row in results]
    
    def update_processing_status(self, paper_id: str, status: str) -> None:
        """Update paper processing status."""
        with db_manager.get_sqlite_connection() as conn:
            conn.execute("""
                UPDATE papers 
                SET processing_status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (status, paper_id))
            conn.commit()
            
            self.logger.debug("Paper processing status updated", 
                            paper_id=paper_id, status=status)
    
    def update_full_text(self, paper_id: str, full_text: str) -> None:
        """Update paper full text."""
        with db_manager.get_sqlite_connection() as conn:
            conn.execute("""
                UPDATE papers 
                SET full_text = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (full_text, paper_id))
            conn.commit()
            
            self.logger.debug("Paper full text updated", paper_id=paper_id)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get paper statistics."""
        with db_manager.get_sqlite_connection() as conn:
            stats = {}
            
            # Total papers
            stats["total_papers"] = conn.execute(
                "SELECT COUNT(*) FROM papers"
            ).fetchone()[0]
            
            # Papers by source
            source_stats = conn.execute("""
                SELECT source, COUNT(*) as count 
                FROM papers 
                GROUP BY source
            """).fetchall()
            stats["by_source"] = {row[0]: row[1] for row in source_stats}
            
            # Papers by status
            status_stats = conn.execute("""
                SELECT processing_status, COUNT(*) as count 
                FROM papers 
                GROUP BY processing_status
            """).fetchall()
            stats["by_status"] = {row[0]: row[1] for row in status_stats}
            
            # Recent activity (last 7 days)
            stats["recent_count"] = conn.execute("""
                SELECT COUNT(*) FROM papers 
                WHERE created_at >= datetime('now', '-7 days')
            """).fetchone()[0]
            
            return stats
    
    def _row_to_paper(self, row: sqlite3.Row) -> Paper:
        """Convert database row to Paper model."""
        return Paper(
            id=row["id"],
            title=row["title"],
            abstract=row["abstract"],
            authors=json.loads(row["authors"]) if row["authors"] else [],
            journal=row["journal"],
            publication_date=datetime.fromisoformat(row["publication_date"]) 
                           if row["publication_date"] else None,
            doi=row["doi"],
            arxiv_id=row["arxiv_id"],
            pubmed_id=row["pubmed_id"],
            pdf_url=row["pdf_url"],
            local_pdf_path=row["local_pdf_path"],
            full_text=row["full_text"],
            paper_type=row["paper_type"],
            source=row["source"],
            relevance_score=row["relevance_score"],
            processing_status=row["processing_status"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"])
        )


class EntityRepository:
    """Repository for entity data access."""
    
    def __init__(self):
        self.logger = get_logger("entity_repository")
    
    def create_entities(self, entities: List[Entity]) -> int:
        """Create multiple entity records."""
        if not entities:
            return 0
        
        with PerformanceLogger(self.logger, "create_entities", count=len(entities)):
            with db_manager.get_sqlite_connection() as conn:
                entity_data = [
                    (e.paper_id, e.entity_text, 
                     e.entity_type.value if hasattr(e.entity_type, 'value') else e.entity_type,
                     e.confidence, e.start_position, e.end_position, e.context)
                    for e in entities
                ]
                
                cursor = conn.executemany("""
                    INSERT INTO entities (
                        paper_id, entity_text, entity_type, confidence,
                        start_position, end_position, context
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, entity_data)
                
                conn.commit()
                return cursor.rowcount
    
    def get_by_paper(self, paper_id: str) -> List[Entity]:
        """Get entities for a specific paper."""
        with db_manager.get_sqlite_connection() as conn:
            conn.row_factory = sqlite3.Row
            results = conn.execute("""
                SELECT * FROM entities 
                WHERE paper_id = ?
                ORDER BY confidence DESC
            """, (paper_id,)).fetchall()
            
            return [self._row_to_entity(row) for row in results]
    
    def get_by_type(self, entity_type: str, limit: int = 100) -> List[Entity]:
        """Get entities by type."""
        with db_manager.get_sqlite_connection() as conn:
            conn.row_factory = sqlite3.Row
            results = conn.execute("""
                SELECT * FROM entities 
                WHERE entity_type = ?
                ORDER BY confidence DESC
                LIMIT ?
            """, (entity_type, limit)).fetchall()
            
            return [self._row_to_entity(row) for row in results]
    
    def _row_to_entity(self, row: sqlite3.Row) -> Entity:
        """Convert database row to Entity model."""
        return Entity(
            id=row["id"],
            paper_id=row["paper_id"],
            entity_text=row["entity_text"],
            entity_type=row["entity_type"],
            confidence=row["confidence"],
            start_position=row["start_position"],
            end_position=row["end_position"],
            context=row["context"]
        )


class EmbeddingRepository:
    """Repository for embedding data access."""
    
    def __init__(self):
        self.logger = get_logger("embedding_repository")
    
    def create(self, embedding: Embedding) -> None:
        """Create embedding record."""
        import numpy as np
        
        with db_manager.get_sqlite_connection() as conn:
            # Serialize embedding as binary
            embedding_blob = np.array(embedding.embedding, dtype=np.float32).tobytes()
            
            conn.execute("""
                INSERT OR REPLACE INTO embeddings (
                    paper_id, embedding, model_version
                ) VALUES (?, ?, ?)
            """, (embedding.paper_id, embedding_blob, embedding.model_version))
            conn.commit()
    
    def get_by_paper(self, paper_id: str) -> Optional[Embedding]:
        """Get embedding for a paper."""
        import numpy as np
        
        with db_manager.get_sqlite_connection() as conn:
            conn.row_factory = sqlite3.Row
            result = conn.execute("""
                SELECT * FROM embeddings WHERE paper_id = ?
            """, (paper_id,)).fetchone()
            
            if result:
                # Deserialize embedding
                embedding_array = np.frombuffer(result["embedding"], dtype=np.float32)
                
                return Embedding(
                    paper_id=result["paper_id"],
                    embedding=embedding_array.tolist(),
                    model_version=result["model_version"],
                    created_at=datetime.fromisoformat(result["created_at"])
                )
            return None


# Repository instances
paper_repo = PaperRepository()
entity_repo = EntityRepository()
embedding_repo = EmbeddingRepository()