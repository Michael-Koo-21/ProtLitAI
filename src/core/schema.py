"""Database schema definitions for ProtLitAI."""

from typing import List, Dict, Any
from pathlib import Path
import sqlite3
import duckdb

from core.config import config
from core.logging import get_logger


class SchemaManager:
    """Manages database schema creation and migration."""
    
    def __init__(self):
        self.logger = get_logger("schema")
        self.current_version = 1
    
    def get_sqlite_schema(self) -> List[str]:
        """Get SQLite schema creation statements."""
        return [
            # Papers table
            """
            CREATE TABLE IF NOT EXISTS papers (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                abstract TEXT,
                authors TEXT,  -- JSON array
                journal TEXT,
                publication_date DATE,
                doi TEXT UNIQUE,
                arxiv_id TEXT,
                pubmed_id INTEGER,
                pdf_url TEXT,
                local_pdf_path TEXT,
                full_text TEXT,
                paper_type TEXT DEFAULT 'journal',  -- 'journal', 'preprint', 'patent'
                source TEXT NOT NULL,  -- 'pubmed', 'arxiv', 'biorxiv'
                relevance_score REAL CHECK (relevance_score >= 0 AND relevance_score <= 1),
                processing_status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            
            # Create indexes for papers table
            """
            CREATE INDEX IF NOT EXISTS idx_papers_source ON papers(source)
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_papers_publication_date ON papers(publication_date)
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_papers_relevance_score ON papers(relevance_score)
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_papers_processing_status ON papers(processing_status)
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_papers_journal ON papers(journal)
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_papers_doi ON papers(doi)
            """,
            
            # Full-text search index
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS papers_fts USING fts5(
                title, 
                abstract, 
                full_text, 
                authors,
                content='papers',
                content_rowid='rowid'
            )
            """,
            
            # FTS triggers for automatic indexing
            """
            CREATE TRIGGER IF NOT EXISTS papers_fts_insert AFTER INSERT ON papers BEGIN
                INSERT INTO papers_fts(rowid, title, abstract, full_text, authors) 
                VALUES (NEW.rowid, NEW.title, NEW.abstract, NEW.full_text, NEW.authors);
            END
            """,
            """
            CREATE TRIGGER IF NOT EXISTS papers_fts_update AFTER UPDATE ON papers BEGIN
                UPDATE papers_fts SET 
                    title = NEW.title, 
                    abstract = NEW.abstract, 
                    full_text = NEW.full_text, 
                    authors = NEW.authors 
                WHERE rowid = NEW.rowid;
            END
            """,
            """
            CREATE TRIGGER IF NOT EXISTS papers_fts_delete AFTER DELETE ON papers BEGIN
                DELETE FROM papers_fts WHERE rowid = OLD.rowid;
            END
            """,
            
            # Authors table
            """
            CREATE TABLE IF NOT EXISTS authors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                normalized_name TEXT,
                orcid TEXT,
                h_index INTEGER,
                affiliations TEXT,  -- JSON array
                research_areas TEXT,  -- JSON array
                first_seen DATE,
                last_seen DATE,
                UNIQUE(normalized_name)
            )
            """,
            
            # Authors indexes
            """
            CREATE INDEX IF NOT EXISTS idx_authors_name ON authors(name)
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_authors_normalized_name ON authors(normalized_name)
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_authors_orcid ON authors(orcid)
            """,
            
            # Extracted entities table
            """
            CREATE TABLE IF NOT EXISTS entities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                paper_id TEXT NOT NULL,
                entity_text TEXT NOT NULL,
                entity_type TEXT NOT NULL,  -- 'protein', 'method', 'company', 'gene'
                confidence REAL NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
                start_position INTEGER,
                end_position INTEGER,
                context TEXT,
                FOREIGN KEY (paper_id) REFERENCES papers(id) ON DELETE CASCADE
            )
            """,
            
            # Entities indexes
            """
            CREATE INDEX IF NOT EXISTS idx_entities_paper_id ON entities(paper_id)
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(entity_type)
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_entities_text ON entities(entity_text)
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_entities_confidence ON entities(confidence)
            """,
            
            # Paper embeddings table
            """
            CREATE TABLE IF NOT EXISTS embeddings (
                paper_id TEXT PRIMARY KEY,
                embedding BLOB NOT NULL,  -- Serialized numpy array
                model_version TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (paper_id) REFERENCES papers(id) ON DELETE CASCADE
            )
            """,
            
            # Research trends table
            """
            CREATE TABLE IF NOT EXISTS trends (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic_name TEXT NOT NULL,
                keywords TEXT,  -- JSON array
                paper_count INTEGER NOT NULL CHECK (paper_count >= 0),
                time_period_start DATE NOT NULL,
                time_period_end DATE NOT NULL,
                growth_rate REAL,
                significance_score REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            
            # Trends indexes
            """
            CREATE INDEX IF NOT EXISTS idx_trends_topic_name ON trends(topic_name)
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_trends_time_period ON trends(time_period_start, time_period_end)
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_trends_paper_count ON trends(paper_count)
            """,
            
            # User settings table
            """
            CREATE TABLE IF NOT EXISTS user_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            
            # Alerts table
            """
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                query TEXT NOT NULL,
                keywords TEXT,  -- JSON array
                entities TEXT,  -- JSON array
                frequency TEXT DEFAULT 'daily' CHECK (frequency IN ('daily', 'weekly', 'monthly')),
                last_triggered TIMESTAMP,
                is_active BOOLEAN DEFAULT 1
            )
            """,
            
            # Schema version table
            """
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER PRIMARY KEY,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            
            # Insert current schema version
            """
            INSERT OR IGNORE INTO schema_version (version) VALUES (1)
            """
        ]
    
    def get_duckdb_schema(self) -> List[str]:
        """Get DuckDB schema creation statements for analytics."""
        return [
            # Paper analytics view
            """
            CREATE TABLE IF NOT EXISTS paper_analytics AS 
            SELECT 
                DATE_TRUNC('month', CAST(publication_date AS DATE)) as month,
                journal,
                source,
                paper_type,
                COUNT(*) as paper_count,
                AVG(relevance_score) as avg_relevance,
                MIN(publication_date) as earliest_date,
                MAX(publication_date) as latest_date
            FROM sqlite_scan('{}', 'papers') 
            WHERE publication_date IS NOT NULL
            GROUP BY month, journal, source, paper_type
            """.format(config.get_db_paths()["literature"]),
            
            # Citation network table
            """
            CREATE TABLE IF NOT EXISTS citation_network (
                citing_paper_id TEXT,
                cited_paper_id TEXT,
                citation_count INTEGER DEFAULT 1,
                PRIMARY KEY (citing_paper_id, cited_paper_id)
            )
            """,
            
            # Author collaboration network
            """
            CREATE TABLE IF NOT EXISTS author_collaborations (
                author1_id INTEGER,
                author2_id INTEGER,
                collaboration_count INTEGER DEFAULT 1,
                first_collaboration DATE,
                last_collaboration DATE,
                PRIMARY KEY (author1_id, author2_id)
            )
            """,
            
            # Topic evolution tracking
            """
            CREATE TABLE IF NOT EXISTS topic_evolution (
                topic_id TEXT,
                time_period DATE,
                paper_count INTEGER,
                keyword_frequency TEXT,  -- JSON
                representative_papers TEXT,  -- JSON array of paper IDs
                PRIMARY KEY (topic_id, time_period)
            )
            """,
            
            # Performance metrics table
            """
            CREATE TABLE IF NOT EXISTS performance_metrics (
                metric_name TEXT,
                metric_value REAL,
                component TEXT,
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        ]
    
    def create_sqlite_schema(self, conn: sqlite3.Connection) -> None:
        """Create SQLite schema."""
        self.logger.info("Creating SQLite schema")
        
        schema_statements = self.get_sqlite_schema()
        
        for statement in schema_statements:
            try:
                conn.execute(statement)
                self.logger.debug("Executed schema statement successfully")
            except Exception as e:
                self.logger.error("Failed to execute schema statement", 
                                error=str(e), statement=statement[:100])
                raise
        
        conn.commit()
        self.logger.info("SQLite schema created successfully")
    
    def create_duckdb_schema(self, conn: duckdb.DuckDBPyConnection) -> None:
        """Create DuckDB schema for analytics."""
        self.logger.info("Creating DuckDB analytics schema")
        
        # Install and load sqlite scanner extension
        try:
            conn.execute("INSTALL sqlite_scanner")
            conn.execute("LOAD sqlite_scanner")
            self.logger.debug("SQLite scanner extension loaded")
        except Exception as e:
            self.logger.warning("Could not load sqlite scanner extension", error=str(e))
        
        schema_statements = self.get_duckdb_schema()
        
        for statement in schema_statements:
            try:
                conn.execute(statement)
                self.logger.debug("Executed DuckDB schema statement successfully")
            except Exception as e:
                self.logger.error("Failed to execute DuckDB schema statement",
                                error=str(e), statement=statement[:100])
                # Don't raise for DuckDB schema errors as they're less critical
                continue
        
        self.logger.info("DuckDB analytics schema created successfully")
    
    def get_schema_version(self, conn: sqlite3.Connection) -> int:
        """Get current schema version."""
        try:
            result = conn.execute("SELECT MAX(version) FROM schema_version").fetchone()
            return result[0] if result and result[0] is not None else 0
        except sqlite3.OperationalError:
            # Table doesn't exist yet
            return 0
    
    def migrate_schema(self, conn: sqlite3.Connection, target_version: int = None) -> None:
        """Migrate schema to target version."""
        if target_version is None:
            target_version = self.current_version
        
        current_version = self.get_schema_version(conn)
        
        if current_version >= target_version:
            self.logger.info("Schema is up to date", 
                           current_version=current_version,
                           target_version=target_version)
            return
        
        self.logger.info("Migrating schema", 
                        from_version=current_version,
                        to_version=target_version)
        
        # For now, we only have version 1, so just create the schema
        if current_version == 0:
            self.create_sqlite_schema(conn)
        
        # Future migrations would go here
        # if current_version < 2:
        #     self.migrate_to_version_2(conn)
        
        self.logger.info("Schema migration completed")
    
    def validate_schema(self, conn: sqlite3.Connection) -> Dict[str, Any]:
        """Validate schema integrity."""
        validation_results = {"valid": True, "issues": []}
        
        # Check if required tables exist
        required_tables = [
            "papers", "papers_fts", "authors", "entities", 
            "embeddings", "trends", "user_settings", "alerts", "schema_version"
        ]
        
        for table in required_tables:
            try:
                conn.execute(f"SELECT 1 FROM {table} LIMIT 1")
            except sqlite3.OperationalError:
                validation_results["valid"] = False
                validation_results["issues"].append(f"Missing table: {table}")
        
        # Check FTS integrity
        try:
            conn.execute("INSERT INTO papers_fts(papers_fts) VALUES('integrity-check')")
        except sqlite3.OperationalError as e:
            validation_results["valid"] = False
            validation_results["issues"].append(f"FTS integrity issue: {e}")
        
        # Check indexes
        expected_indexes = [
            "idx_papers_source", "idx_papers_publication_date",
            "idx_entities_paper_id", "idx_authors_name"
        ]
        
        existing_indexes = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index'"
        ).fetchall()
        existing_index_names = {row[0] for row in existing_indexes}
        
        for index in expected_indexes:
            if index not in existing_index_names:
                validation_results["issues"].append(f"Missing index: {index}")
        
        self.logger.info("Schema validation completed", 
                        valid=validation_results["valid"],
                        issues_count=len(validation_results["issues"]))
        
        return validation_results


# Global schema manager instance
schema_manager = SchemaManager()