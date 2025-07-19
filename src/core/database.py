"""Database connection and management for ProtLitAI."""

import sqlite3
import duckdb
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from contextlib import asynccontextmanager, contextmanager
import threading
from concurrent.futures import ThreadPoolExecutor

from .config import config
from .logging import get_logger


class DatabaseManager:
    """Manages SQLite and DuckDB connections with thread safety."""
    
    def __init__(self):
        self.logger = get_logger("database")
        self._sqlite_connections = threading.local()
        self._duckdb_connections = threading.local()
        self._lock = threading.Lock()
        self._initialized = False
        self._executor = ThreadPoolExecutor(max_workers=4)
    
    def initialize(self) -> None:
        """Initialize database connections and schema."""
        with self._lock:
            if self._initialized:
                return
            
            self.logger.info("Initializing database connections")
            
            # Ensure database directories exist
            db_paths = config.get_db_paths()
            for db_path in db_paths.values():
                Path(db_path).parent.mkdir(parents=True, exist_ok=True)
            
            # Initialize schema
            self._initialize_schema()
            
            # Test connections
            self._test_connections()
            self._initialized = True
            
            self.logger.info("Database initialization complete")
    
    def _initialize_schema(self) -> None:
        """Initialize database schema."""
        from .schema import schema_manager
        
        # Initialize SQLite schema
        with self.get_sqlite_connection() as conn:
            schema_manager.migrate_schema(conn)
            validation_result = schema_manager.validate_schema(conn)
            
            if not validation_result["valid"]:
                self.logger.error("Schema validation failed", 
                                issues=validation_result["issues"])
                raise RuntimeError("Database schema validation failed")
        
        # Initialize DuckDB schema
        try:
            with self.get_duckdb_connection() as conn:
                schema_manager.create_duckdb_schema(conn)
        except Exception as e:
            self.logger.warning("DuckDB schema initialization failed", error=str(e))
            # Don't fail completely if DuckDB schema fails
    
    def _test_connections(self) -> None:
        """Test database connections."""
        try:
            # Test SQLite
            with self.get_sqlite_connection() as conn:
                conn.execute("SELECT 1").fetchone()
            
            # Test DuckDB
            with self.get_duckdb_connection() as conn:
                conn.execute("SELECT 1").fetchone()
                
            self.logger.info("Database connection tests passed")
            
        except Exception as e:
            self.logger.error("Database connection test failed", error=str(e))
            raise
    
    @contextmanager
    def get_sqlite_connection(self):
        """Get a thread-local SQLite connection."""
        if not hasattr(self._sqlite_connections, 'connection'):
            db_path = config.get_db_paths()["literature"]
            self._sqlite_connections.connection = sqlite3.connect(
                db_path,
                timeout=30.0,
                check_same_thread=False
            )
            # Configure SQLite for performance
            self._configure_sqlite(self._sqlite_connections.connection)
        
        try:
            yield self._sqlite_connections.connection
        except Exception as e:
            self.logger.error("SQLite error", error=str(e))
            # Rollback on error
            self._sqlite_connections.connection.rollback()
            raise
    
    @contextmanager
    def get_duckdb_connection(self):
        """Get a thread-local DuckDB connection."""
        if not hasattr(self._duckdb_connections, 'connection'):
            db_path = config.get_db_paths()["analytics"]
            self._duckdb_connections.connection = duckdb.connect(db_path)
        
        try:
            yield self._duckdb_connections.connection
        except Exception as e:
            self.logger.error("DuckDB error", error=str(e))
            raise
    
    def _configure_sqlite(self, conn: sqlite3.Connection) -> None:
        """Configure SQLite connection for optimal performance."""
        # Enable WAL mode for better concurrency
        conn.execute("PRAGMA journal_mode=WAL")
        
        # Increase cache size (64MB)
        conn.execute("PRAGMA cache_size=-65536")
        
        # Faster synchronization
        conn.execute("PRAGMA synchronous=NORMAL")
        
        # Memory-mapped I/O
        conn.execute("PRAGMA mmap_size=268435456")  # 256MB
        
        # Optimize for read-heavy workloads
        conn.execute("PRAGMA temp_store=MEMORY")
        conn.execute("PRAGMA page_size=4096")
        
        # Enable foreign keys
        conn.execute("PRAGMA foreign_keys=ON")
        
        self.logger.debug("SQLite connection configured for performance")
    
    async def execute_async(self, query: str, params: Tuple = (), 
                           database: str = "sqlite") -> List[Dict[str, Any]]:
        """Execute query asynchronously."""
        loop = asyncio.get_event_loop()
        
        if database == "sqlite":
            return await loop.run_in_executor(
                self._executor, 
                self._execute_sqlite, 
                query, 
                params
            )
        elif database == "duckdb":
            return await loop.run_in_executor(
                self._executor, 
                self._execute_duckdb, 
                query, 
                params
            )
        else:
            raise ValueError(f"Unknown database: {database}")
    
    def _execute_sqlite(self, query: str, params: Tuple = ()) -> List[Dict[str, Any]]:
        """Execute SQLite query synchronously."""
        with self.get_sqlite_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, params)
            
            if query.strip().upper().startswith(('INSERT', 'UPDATE', 'DELETE')):
                conn.commit()
                return [{"affected_rows": cursor.rowcount}]
            else:
                return [dict(row) for row in cursor.fetchall()]
    
    def _execute_duckdb(self, query: str, params: Tuple = ()) -> List[Dict[str, Any]]:
        """Execute DuckDB query synchronously."""
        with self.get_duckdb_connection() as conn:
            result = conn.execute(query, params).fetchall()
            
            if result:
                # Get column names
                columns = [desc[0] for desc in conn.description]
                return [dict(zip(columns, row)) for row in result]
            return []
    
    def bulk_insert(self, table: str, data: List[Dict[str, Any]], 
                   database: str = "sqlite") -> int:
        """Perform bulk insert operation."""
        if not data:
            return 0
        
        if database == "sqlite":
            return self._bulk_insert_sqlite(table, data)
        elif database == "duckdb":
            return self._bulk_insert_duckdb(table, data)
        else:
            raise ValueError(f"Unknown database: {database}")
    
    def _bulk_insert_sqlite(self, table: str, data: List[Dict[str, Any]]) -> int:
        """Bulk insert into SQLite."""
        with self.get_sqlite_connection() as conn:
            # Get column names from first record
            columns = list(data[0].keys())
            placeholders = ','.join(['?' for _ in columns])
            
            query = f"INSERT INTO {table} ({','.join(columns)}) VALUES ({placeholders})"
            
            # Convert dicts to tuples in correct order
            values = [tuple(record[col] for col in columns) for record in data]
            
            cursor = conn.executemany(query, values)
            conn.commit()
            
            self.logger.log_database_operation(
                "bulk_insert", table, cursor.rowcount, 0.0
            )
            
            return cursor.rowcount
    
    def _bulk_insert_duckdb(self, table: str, data: List[Dict[str, Any]]) -> int:
        """Bulk insert into DuckDB."""
        with self.get_duckdb_connection() as conn:
            # Convert data to list of tuples
            columns = list(data[0].keys())
            placeholders = ','.join(['?' for _ in columns])
            
            query = f"INSERT INTO {table} ({','.join(columns)}) VALUES ({placeholders})"
            
            values = [tuple(record[col] for col in columns) for record in data]
            
            for value_tuple in values:
                conn.execute(query, value_tuple)
            
            self.logger.log_database_operation(
                "bulk_insert", table, len(data), 0.0
            )
            
            return len(data)
    
    def health_check(self) -> Dict[str, Any]:
        """Perform database health check."""
        health = {"status": "healthy", "databases": {}}
        
        try:
            # SQLite health check
            with self.get_sqlite_connection() as conn:
                result = conn.execute("PRAGMA integrity_check").fetchone()
                health["databases"]["sqlite"] = {
                    "status": "ok" if result[0] == "ok" else "error",
                    "integrity": result[0]
                }
        except Exception as e:
            health["databases"]["sqlite"] = {
                "status": "error", 
                "error": str(e)
            }
            health["status"] = "degraded"
        
        try:
            # DuckDB health check
            with self.get_duckdb_connection() as conn:
                conn.execute("SELECT 1").fetchone()
                health["databases"]["duckdb"] = {"status": "ok"}
        except Exception as e:
            health["databases"]["duckdb"] = {
                "status": "error", 
                "error": str(e)
            }
            health["status"] = "degraded"
        
        return health
    
    def close_connections(self) -> None:
        """Close all database connections."""
        self.logger.info("Closing database connections")
        
        # Close SQLite connections
        if hasattr(self._sqlite_connections, 'connection'):
            self._sqlite_connections.connection.close()
            delattr(self._sqlite_connections, 'connection')
        
        # Close DuckDB connections  
        if hasattr(self._duckdb_connections, 'connection'):
            self._duckdb_connections.connection.close()
            delattr(self._duckdb_connections, 'connection')
        
        # Shutdown executor
        self._executor.shutdown(wait=True)
        
        self.logger.info("Database connections closed")


# Global database manager instance
db_manager = DatabaseManager()