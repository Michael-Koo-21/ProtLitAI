# Technical Design Document: Protein Design Literature Intelligence Engine (ProtLitAI)

## Architecture Overview
**Project:** Protein Design Literature Intelligence Engine (ProtLitAI)  
**Version:** 1.0.0  
**Last Updated:** July 18, 2025  
**Lead Architect:** AI Development Team

### System Architecture Diagram
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Data Sources  │───▶│  Collection API │───▶│  NLP Pipeline   │
│  PubMed/arXiv   │    │   Schedulers    │    │  spaCy/BERT     │
│   bioRxiv/GS    │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │                        │
                                ▼                        ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   macOS App     │◀───│  SQLite + FTS5  │◀───│  Embedding      │
│   PyQt6/Native  │    │   DuckDB        │    │   Generation    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                        │
         ▼                       ▼                        ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Export/Reports │    │  Local Storage  │    │   ML Models     │
│   PDF/CSV/BibTeX│    │   ~/Literature  │    │  M2 Optimized   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Technology Stack
- **Frontend/UI:**
  - PyQt6 or Tkinter for native macOS interface
  - Plotly for interactive data visualization
  - matplotlib/seaborn for static charts
  - Rich for terminal-based progress displays

- **Backend/Core:**
  - Python 3.11 with M2 optimization
  - FastAPI for internal service APIs
  - asyncio for concurrent processing
  - APScheduler for automated tasks

- **Database:**
  - SQLite with FTS5 for full-text search
  - DuckDB for analytical queries
  - JSON files for configuration
  - Local file system for PDF storage

- **Machine Learning:**
  - PyTorch with MPS (Metal Performance Shaders)
  - Sentence Transformers for embeddings
  - spaCy with en_core_sci_lg for biomedical NER
  - Transformers library for summarization
  - scikit-learn for clustering and classification

- **External APIs:**
  - requests/httpx for HTTP clients
  - feedparser for RSS monitoring
  - BeautifulSoup4 for web scraping
  - PyPDF2/pdfplumber for PDF processing

## Component Architecture

### Application Structure
```
protlitai/
├── src/
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── models.py
│   │   └── logging.py
│   ├── collectors/
│   │   ├── __init__.py
│   │   ├── base_collector.py
│   │   ├── pubmed_collector.py
│   │   ├── arxiv_collector.py
│   │   ├── biorxiv_collector.py
│   │   └── scholar_collector.py
│   ├── processing/
│   │   ├── __init__.py
│   │   ├── pdf_processor.py
│   │   ├── nlp_pipeline.py
│   │   ├── embedding_generator.py
│   │   └── entity_extractor.py
│   ├── analysis/
│   │   ├── __init__.py
│   │   ├── trend_analyzer.py
│   │   ├── similarity_engine.py
│   │   ├── competitive_intel.py
│   │   └── report_generator.py
│   ├── ui/
│   │   ├── __init__.py
│   │   ├── main_window.py
│   │   ├── search_interface.py
│   │   ├── dashboard.py
│   │   └── settings_dialog.py
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── file_handler.py
│   │   ├── api_helpers.py
│   │   └── validators.py
│   └── main.py
├── models/
│   ├── sentence_transformers/
│   ├── spacy_models/
│   └── custom_models/
├── data/
│   ├── literature.db
│   ├── analytics.db
│   └── configs/
├── cache/
│   ├── pdfs/
│   ├── embeddings/
│   └── temp/
├── tests/
├── docs/
├── requirements.txt
├── setup.py
└── README.md
```

## Database Design

### SQLite Schema Design
```sql
-- Main literature database
CREATE TABLE papers (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    abstract TEXT,
    authors TEXT, -- JSON array
    journal TEXT,
    publication_date DATE,
    doi TEXT UNIQUE,
    arxiv_id TEXT,
    pubmed_id INTEGER,
    pdf_url TEXT,
    local_pdf_path TEXT,
    full_text TEXT,
    paper_type TEXT, -- 'journal', 'preprint', 'patent'
    source TEXT, -- 'pubmed', 'arxiv', 'biorxiv'
    relevance_score REAL,
    processing_status TEXT DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Full-text search index
CREATE VIRTUAL TABLE papers_fts USING fts5(
    title, abstract, full_text, authors,
    content='papers',
    content_rowid='rowid'
);

-- Authors and affiliations
CREATE TABLE authors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    normalized_name TEXT,
    orcid TEXT,
    h_index INTEGER,
    affiliations TEXT, -- JSON array
    research_areas TEXT, -- JSON array
    first_seen DATE,
    last_seen DATE
);

-- Extracted entities (proteins, methods, companies)
CREATE TABLE entities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    paper_id TEXT,
    entity_text TEXT,
    entity_type TEXT, -- 'protein', 'method', 'company', 'gene'
    confidence REAL,
    start_position INTEGER,
    end_position INTEGER,
    context TEXT,
    FOREIGN KEY (paper_id) REFERENCES papers(id)
);

-- Paper embeddings for semantic search
CREATE TABLE embeddings (
    paper_id TEXT PRIMARY KEY,
    embedding BLOB, -- Serialized numpy array
    model_version TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (paper_id) REFERENCES papers(id)
);

-- Research trends tracking
CREATE TABLE trends (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic_name TEXT,
    keywords TEXT, -- JSON array
    paper_count INTEGER,
    time_period_start DATE,
    time_period_end DATE,
    growth_rate REAL,
    significance_score REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- User preferences and alerts
CREATE TABLE user_settings (
    key TEXT PRIMARY KEY,
    value TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Alert definitions
CREATE TABLE alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    query TEXT,
    keywords TEXT, -- JSON array
    entities TEXT, -- JSON array
    frequency TEXT, -- 'daily', 'weekly'
    last_triggered TIMESTAMP,
    is_active BOOLEAN DEFAULT 1
);
```

### DuckDB Analytics Schema
```sql
-- Optimized for analytical queries
CREATE TABLE paper_analytics AS
SELECT 
    DATE_TRUNC('month', publication_date) as month,
    journal,
    COUNT(*) as paper_count,
    AVG(relevance_score) as avg_relevance
FROM papers 
GROUP BY month, journal;

-- Citation network analysis
CREATE TABLE citation_network (
    citing_paper_id TEXT,
    cited_paper_id TEXT,
    citation_count INTEGER,
    PRIMARY KEY (citing_paper_id, cited_paper_id)
);
```

## NLP and ML Pipeline Design

### Text Processing Pipeline Architecture
The NLP pipeline will process literature through multiple stages:

**Stage 1: Text Preprocessing**
- Remove non-ASCII characters and normalize whitespace
- Extract main text content from PDF structure
- Separate abstract, introduction, methods, results, and conclusions
- Handle special characters and mathematical notation

**Stage 2: Named Entity Recognition**
- Use spaCy biomedical model (en_core_sci_lg) for entity extraction
- Target entities: proteins, genes, methods, companies, institutions
- Confidence scoring for each extracted entity
- Position tracking within document structure

**Stage 3: Embedding Generation**
- Sentence Transformers model (all-MiniLM-L6-v2) for semantic embeddings
- Document-level embeddings for entire papers
- Section-level embeddings for granular search
- Batch processing for efficiency on M2 hardware

**Stage 4: Summarization and Key Phrase Extraction**
- BART-large-CNN model for abstractive summarization
- Key phrase extraction using statistical and neural methods
- Topic classification based on biomedical taxonomy
- Relevance scoring relative to protein design domain

### M2 Hardware Optimization Strategy
The system will be optimized specifically for Apple M2 architecture:

**Memory Management**
- Batch size optimization (32-64 documents) based on available unified memory
- Dynamic memory allocation with 80% maximum usage threshold
- Regular cache clearing using torch.mps.empty_cache()
- Progressive loading for large document collections

**Neural Engine Utilization**
- MPS (Metal Performance Shaders) backend for PyTorch operations
- ONNX Runtime integration for Neural Engine acceleration
- Quantized models (8-bit) for faster inference
- Parallel processing across M2's 8-core GPU

**Storage Optimization**
- Local model caching to minimize re-downloads
- Efficient file I/O using async operations
- SSD-optimized database queries with proper indexing
- Background processing during idle periods

## API Integration Design

### External API Integration Architecture
The system will integrate with multiple external APIs using standardized patterns:

**PubMed E-utilities Integration**
- Rate limiting: 10 requests per second compliance
- Authentication: Optional API key for higher limits
- Search strategy: Incremental daily updates using date filters
- Error handling: Exponential backoff with 3 retry attempts
- Data validation: Schema validation for returned XML/JSON

**arXiv API Integration**
- RSS feed monitoring for real-time updates
- OAI-PMH protocol for bulk metadata harvesting
- Category filtering: cs.LG, q-bio.BM, physics.bio-ph
- Update frequency: Every 6 hours for new submissions
- PDF download: Direct access with respectful rate limiting

**bioRxiv and medRxiv Monitoring**
- Web scraping approach using BeautifulSoup
- RSS feed parsing for new preprints
- Content extraction: Title, abstract, authors, DOI
- PDF processing: Automated download and text extraction
- Update schedule: Twice daily (morning and evening)

**Google Scholar Monitoring**
- Scholarly library for programmatic access
- Alert-based monitoring for specific keywords
- Rate limiting: 100 requests per hour
- Citation tracking: Reference network building
- Institution filtering: Focus on key research organizations

### Rate Limiting and Error Handling Strategy
All external API interactions will implement robust error handling:

**Rate Limiting Implementation**
- Token bucket algorithm for request throttling
- Per-API customizable rate limits
- Queue-based request management
- Priority system for critical updates
- Automatic retry with exponential backoff

**Error Recovery Mechanisms**
- Network timeout handling (30-second default)
- HTTP error code specific responses (429, 503, etc.)
- Graceful degradation during API outages
- Cached fallback data for offline operation
- Comprehensive logging for debugging and monitoring

## Search and Analytics Engine

### Semantic Search Engine Architecture
The search system will implement hybrid search combining multiple approaches:

**Multi-Modal Search Strategy**
- Semantic similarity search using document embeddings
- Keyword-based full-text search with SQLite FTS5
- Entity-based search targeting proteins, methods, companies
- Citation network traversal for related paper discovery
- Temporal filtering with publication date ranges

**Search Result Ranking Algorithm**
- Weighted combination of semantic similarity (40%), keyword relevance (30%), recency (20%), and citation count (10%)
- Personalization based on user interaction history
- Boost factors for high-impact journals and established authors
- Domain-specific relevance scoring for protein design focus
- Machine learning model for continuous ranking improvement

**Query Processing Pipeline**
- Natural language query parsing and intent recognition
- Automatic query expansion using biomedical ontologies
- Synonym mapping for protein names and technical terms
- Boolean query construction from natural language
- Result caching for frequently accessed searches

### Trend Analysis System Architecture
The trend analysis component will identify emerging research patterns:

**Topic Modeling Framework**
- BERTopic implementation with biomedical embeddings
- UMAP dimensionality reduction for topic visualization
- HDBSCAN clustering for dynamic topic discovery
- Temporal topic evolution tracking
- Statistical significance testing for trend validation

**Trend Detection Algorithms**
- Time-series analysis of publication volumes by topic
- Growth rate calculation with seasonal adjustment
- Novelty detection for emerging research areas
- Competitive landscape mapping by institution/company
- Predictive modeling for future research directions

**Analytical Reporting Framework**
- Automated daily, weekly, and monthly trend reports
- Interactive visualizations using Plotly
- Export capabilities for presentations and documents
- Alert system for significant trend changes
- Historical trend comparison and benchmarking

## User Interface Design

### Native macOS Application Design
The user interface will be implemented as a native macOS application with modern design principles:

**Main Window Architecture**
- Split-view layout with resizable sidebar (25%) and main content area (75%)
- Native macOS toolbar with search integration
- Tab-based navigation for multiple concurrent views
- Status bar with real-time system information
- Menu bar integration following macOS Human Interface Guidelines

**Interface Component Specifications**
- **Sidebar Navigation**: Hierarchical tree view with icons for Dashboard, Search, Trends, Alerts, Settings
- **Search Interface**: Spotlight-style search with auto-complete and recent queries
- **Results Display**: Table view with sortable columns and preview pane
- **Dashboard Widgets**: Card-based layout with drag-and-drop customization
- **Settings Panel**: Tabbed preferences window with form validation

**Visual Design Standards**
- System font (SF Pro) with appropriate text sizes and weights
- Native macOS color scheme with automatic dark mode support
- Consistent spacing using 8px grid system
- Subtle animations for state transitions
- Accessibility support with VoiceOver compatibility

### Dashboard Component Design
The dashboard will provide an at-a-glance overview of literature activity:

**Summary Statistics Cards**
- Today's new papers count with trend indicator
- Total papers in database with growth metrics
- Active alerts count with recent trigger status
- Processing queue status with estimated completion time

**Recent Papers Widget**
- List view showing last 20 papers with relevance scores
- Thumbnail images for papers with figures
- Quick action buttons (save, share, alert)
- Filtering by source (PubMed, arXiv, bioRxiv)

**Trending Topics Visualization**
- Word cloud representation of emerging terms
- Bar chart showing topic frequency over time
- Interactive elements for drilling down into topics
- Export functionality for reports and presentations

**Activity Timeline**
- Line chart showing daily paper collection volumes
- Overlay indicators for significant events or alerts
- Zoom functionality for different time periods
- Correlation analysis with external events

## Performance Optimization Strategy

### M2 Hardware Optimization
The system will be specifically optimized for Apple M2 MacBook Pro performance characteristics:

**Memory Management Strategy**
- Dynamic batch size determination based on available unified memory (8GB, 16GB, or 32GB configurations)
- Memory usage monitoring with automatic throttling at 80% capacity
- Intelligent caching with LRU eviction for embeddings and processed documents
- Background garbage collection during idle periods

**Neural Processing Optimization**
- MPS (Metal Performance Shaders) backend utilization for all ML operations
- Neural Engine acceleration through ONNX Runtime optimization
- Model quantization (8-bit integers) for faster inference with minimal accuracy loss
- Asynchronous processing pipeline to maximize CPU and GPU utilization

**Storage Performance**
- SSD-optimized database configuration with appropriate page sizes
- Write-ahead logging (WAL) mode for concurrent read/write operations
- Batch insert operations for new literature entries
- Automatic database maintenance and optimization scheduling

### Database Performance Strategy
The database system will be optimized for both analytical and transactional workloads:

**SQLite Optimization Configuration**
- WAL mode for better concurrency and crash recovery
- Increased cache size (64MB) for frequently accessed data
- PRAGMA optimizations for faster query execution
- Connection pooling for multiple concurrent operations

**Indexing Strategy**
- Composite indexes for common query patterns (date + relevance, author + journal)
- Full-text search indexes using FTS5 with custom tokenizers
- Spatial indexes for embedding similarity searches
- Automatic index maintenance and statistics updates

**Query Optimization Patterns**
- Prepared statements for frequently executed queries
- Query result caching with TTL-based invalidation
- Batch operations for bulk data updates
- Asynchronous query execution for non-blocking operations

## Monitoring and Logging Architecture

### System Monitoring Framework
Comprehensive monitoring will track system performance and health:

**Performance Metrics Collection**
- API response times for all external services
- Database query execution times and resource usage
- ML model inference times and throughput
- Memory usage patterns and garbage collection cycles
- Network bandwidth utilization and error rates

**Application Health Monitoring**
- Background task execution status and completion rates
- Literature collection success rates by source
- Search query performance and user satisfaction metrics
- Alert system accuracy and false positive rates
- User interface responsiveness and error tracking

### Logging Strategy
Structured logging will provide comprehensive system observability:

**Log Level Classification**
- DEBUG: Detailed execution flow for development and troubleshooting
- INFO: Normal operational events and milestone completion
- WARNING: Recoverable errors and performance degradation
- ERROR: Failed operations requiring investigation
- CRITICAL: System failures requiring immediate attention

**Log Data Structure**
- Timestamp with microsecond precision
- Component and function identification
- User context and session information
- Performance metrics and resource usage
- Error details with stack traces when applicable

**Log Management**
- Rolling file logs with automatic compression and archival
- Configurable retention periods (90 days default)
- Search capabilities across historical logs
- Export functionality for external analysis tools

## Deployment Strategy

### Local Development Environment
The application will be designed for seamless local deployment:

**Environment Configuration**
- Python virtual environment with pinned dependencies
- Environment variable management for API keys and configuration
- Local model downloads with automatic verification
- Database initialization with schema migration support

**Installation Process**
- Homebrew-based dependency installation for system requirements
- pip-based Python package installation with M2 optimizations
- Automated setup script for initial configuration
- User-friendly error messages and recovery suggestions

### Data Migration and Backup
Robust data management will ensure system reliability:

**Backup Strategy**
- Automated daily backups to local storage
- Optional iCloud Drive synchronization for cloud backup
- Export functionality for data portability
- Incremental backup to minimize storage overhead

**Migration Support**
- Database schema versioning with automatic upgrades
- Data validation during migration processes
- Rollback capabilities for failed migrations
- User notification and confirmation for major changes

## Security and Privacy Design

### Data Protection Framework
Local-first architecture will prioritize user data privacy:

**Data Encryption**
- FileVault integration for at-rest encryption
- API key encryption using macOS Keychain
- Secure temporary file handling with automatic cleanup
- Network communication over HTTPS/TLS only

**Privacy Protection**
- No user data transmission to external services beyond API requirements
- Local processing for all sensitive operations
- Configurable data retention policies
- User control over data sharing and export

**Access Control**
- macOS user account isolation
- File system permission validation
- API key rotation and expiration handling
- Audit logging for sensitive operations

### Compliance Considerations
The system will adhere to relevant privacy and security standards:

**Publisher Terms of Service**
- Rate limiting compliance for all external APIs
- Respectful web scraping with appropriate delays
- Copyright respect for downloaded content
- Attribution and citation for all sourced materials

**Data Handling Best Practices**
- Minimal data collection principles
- Purpose limitation for collected data
- User transparency about data usage
- Secure disposal of temporary and cached data