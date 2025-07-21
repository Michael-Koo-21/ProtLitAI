# ProtLitAI User Guide

## Complete Guide to Using the Protein Design Literature Intelligence Engine

**Version:** 1.0.0  
**Last Updated:** July 21, 2025  
**System Requirements:** macOS with Apple Silicon (M1/M2), Python 3.11+

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Installation](#installation)
3. [First Time Setup](#first-time-setup)
4. [Core Features](#core-features)
5. [Daily Usage](#daily-usage)
6. [Advanced Features](#advanced-features)
7. [Troubleshooting](#troubleshooting)
8. [Performance Optimization](#performance-optimization)

---

## Quick Start

### 1. Install Dependencies
```bash
# Clone the repository
git clone <repository-url>
cd ProtLitAI

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install requirements
pip install -r requirements.txt
```

### 2. Initialize System
```bash
# Download and initialize ML models
python initialize_models.py

# Run test collection
python production_collection.py --mode test
```

### 3. Launch Application
```bash
# Start the main interface
python -m src.ui.app
```

---

## Installation

### System Requirements

**Hardware:**
- Apple Silicon Mac (M1, M1 Pro/Max, M2, M2 Pro/Max)
- Minimum 8GB RAM (16GB recommended)
- 5GB free disk space (for models and literature cache)
- Stable internet connection

**Software:**
- macOS 12.0 or later
- Python 3.11+
- Homebrew (optional, for dependencies)

### Step-by-Step Installation

#### 1. Python Environment Setup
```bash
# Install Python 3.11 (if not already installed)
brew install python@3.11

# Verify Python version
python3.11 --version
```

#### 2. Project Setup
```bash
# Clone repository
cd ~/Development  # or your preferred directory
git clone <repository-url> ProtLitAI
cd ProtLitAI

# Create isolated virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip setuptools wheel
```

#### 3. Install Dependencies
```bash
# Install all required packages
pip install -r requirements.txt

# Verify critical packages
python -c "import torch; print(f'PyTorch: {torch.__version__}, MPS: {torch.backends.mps.is_available()}')"
```

#### 4. Environment Configuration
```bash
# Create environment configuration file
cp .env.example .env

# Edit configuration (optional)
nano .env
```

**Key Environment Variables:**
```bash
# Optional: PubMed API key for higher rate limits
PUBMED_API_KEY=your_api_key_here

# Optional: OpenAI API key for enhanced features
OPENAI_API_KEY=your_openai_key_here

# Database path (default: ./data/literature.db)
DATABASE_PATH=./data/literature.db

# Log level (DEBUG, INFO, WARNING, ERROR)
LOG_LEVEL=INFO
```

---

## First Time Setup

### 1. Initialize ML Models
This step downloads and configures the required machine learning models:

```bash
python initialize_models.py
```

**What this does:**
- Downloads sentence-transformers model (~500MB)
- Downloads spaCy biomedical model (~50MB)
- Configures MPS acceleration for M2 hardware
- Tests model functionality
- **Expected time:** 2-5 minutes (depending on internet speed)

**Example output:**
```
🚀 ProtLitAI ML Model Initialization
✅ PyTorch 2.1.2 installed
✅ MPS acceleration available
✅ Sentence Transformer loaded in 0.4s
✅ spaCy model loaded in 0.5s
🎉 All models initialized successfully!
```

### 2. Create Database Schema
```bash
# Initialize database (happens automatically)
python -c "from src.core.database import db_manager; db_manager.initialize()"
```

### 3. Run Test Collection
Collect a small sample of papers to verify everything works:

```bash
python production_collection.py --mode test
```

**This will:**
- Test connections to PubMed, arXiv, and bioRxiv
- Collect 10-20 recent papers
- Process them with ML pipeline
- Store in local database
- **Expected time:** 30-60 seconds

---

## Core Features

### 1. Literature Collection

#### Automatic Daily Collection
```bash
# Collect papers from last 24 hours
python production_collection.py --mode daily

# Collect papers from last 7 days
python production_collection.py --mode weekly

# Custom timeframe
python production_collection.py --mode daily --days 3
```

#### Manual Collection
```bash
# Launch interactive collection
python -c "
from src.collectors.pubmed_collector import PubMedCollector
import asyncio

async def collect():
    async with PubMedCollector() as collector:
        async for paper in collector.search_papers('protein design', max_results=10):
            print(f'Found: {paper.title}')

asyncio.run(collect())
"
```

### 2. Search and Analysis

#### Basic Search
```bash
# Simple search
python -c "
from src.analysis.search_engine import SearchEngine
search = SearchEngine()
results = search.search('protein folding machine learning')
for paper in results[:5]:
    print(f'{paper.title} - {paper.journal}')
"
```

#### Advanced Search
```bash
# Semantic similarity search
python -c "
from src.analysis.similarity_engine import SimilarityEngine
similarity = SimilarityEngine()
results = similarity.find_similar('AlphaFold protein structure prediction')
for paper, score in results[:5]:
    print(f'{score:.3f}: {paper.title}')
"
```

### 3. Trend Analysis
```bash
# Analyze research trends
python -c "
from src.analysis.trend_analyzer import TrendAnalyzer
analyzer = TrendAnalyzer()
trends = analyzer.analyze_trends(days=30)
for trend in trends[:5]:
    print(f'{trend.topic}: {trend.paper_count} papers, growth: {trend.growth_rate:.2f}')
"
```

### 4. Competitive Intelligence
```bash
# Track competitor research
python -c "
from src.analysis.competitive_intel import CompetitiveIntelligence
ci = CompetitiveIntelligence()
orgs = ci.get_active_organizations(days=30)
for org, count in orgs[:10]:
    print(f'{org}: {count} papers')
"
```

---

## Daily Usage

### Morning Research Briefing

#### 1. Daily Collection (5 minutes)
```bash
# Collect yesterday's papers
python production_collection.py --mode daily

# Check collection summary
tail -20 logs/protlitai.log
```

#### 2. Review New Papers
```bash
# Launch main interface
python -m src.ui.app
```

**Main Dashboard shows:**
- New papers from last 24 hours
- Trending topics
- Recent alerts
- System status

#### 3. Search for Specific Topics
Use the search interface to find papers on specific proteins, methods, or companies:
- Natural language queries: "CRISPR protein engineering"
- Entity searches: "@company:Google @protein:EGFR"
- Date filters: Published in last week, month, year

### Weekly Analysis (15 minutes)

#### 1. Comprehensive Collection
```bash
# Collect full week of papers
python production_collection.py --mode weekly
```

#### 2. Trend Analysis
```bash
# Generate trend report
python -c "
from src.analysis.trend_analyzer import TrendAnalyzer
analyzer = TrendAnalyzer()
report = analyzer.generate_weekly_report()
print(report)
"
```

#### 3. Competitive Intelligence Review
- Review competitor publication activity
- Identify new researchers entering the field
- Track collaboration patterns

---

## Advanced Features

### 1. Custom Alerts

#### Create Keyword Alerts
```python
from src.core.models import Alert
from src.core.repository import AlertRepository

alert_repo = AlertRepository()
alert = Alert(
    name="AlphaFold Updates",
    query="AlphaFold OR protein structure prediction",
    keywords=["alphafold", "structure prediction"],
    frequency="daily"
)
alert_repo.create(alert)
```

#### Monitor Specific Companies
```python
alert = Alert(
    name="DeepMind Research",
    query="@company:DeepMind OR @affiliation:'DeepMind'",
    frequency="weekly"
)
```

### 2. Custom Data Export

#### Export Search Results
```python
from src.analysis.search_engine import SearchEngine
from src.utils.export import PaperExporter

search = SearchEngine()
results = search.search("machine learning protein design", limit=100)

exporter = PaperExporter()
exporter.to_csv(results, "ml_protein_papers.csv")
exporter.to_bibtex(results, "ml_protein_papers.bib")
```

#### Generate Custom Reports
```python
from src.analysis.report_generator import ReportGenerator

generator = ReportGenerator()
report = generator.create_custom_report(
    topic="Protein Design Trends Q3 2025",
    date_range=(start_date, end_date),
    include_trends=True,
    include_competitive=True
)
report.save_pdf("protein_design_q3_report.pdf")
```

### 3. API Integration

#### PubMed API Configuration
```bash
# Add your PubMed API key for higher rate limits
export PUBMED_API_KEY="your_key_here"

# Or add to .env file
echo "PUBMED_API_KEY=your_key_here" >> .env
```

#### Custom Collection Schedules
```python
from src.collectors.collection_scheduler import CollectionScheduler

scheduler = CollectionScheduler()

# Schedule daily collection at 6 AM
scheduler.schedule_daily_collection(
    time="06:00",
    sources=["pubmed", "arxiv", "biorxiv"]
)

# Schedule weekly deep collection on Sundays
scheduler.schedule_weekly_collection(
    day="sunday",
    time="02:00",
    deep_collection=True
)
```

### 4. Performance Monitoring

#### System Health Check
```bash
# Check system status
python -c "
from src.core.health import HealthChecker
checker = HealthChecker()
status = checker.full_health_check()
print(status.summary())
"
```

#### Performance Metrics
```bash
# View performance statistics
python -c "
from src.processing.ml_models import get_model_manager
manager = get_model_manager()
stats = manager.get_performance_stats()
print(f'Device: {stats[\"device\"]}')
print(f'Memory: {stats[\"memory_usage\"]}')
"
```

---

## Troubleshooting

### Common Issues

#### 1. ML Models Not Loading
**Error:** `OSError: [Errno 2] No such file or directory: 'models/'`

**Solution:**
```bash
# Re-run model initialization
python initialize_models.py

# Check model directory
ls -la models/
```

#### 2. Database Connection Errors
**Error:** `sqlite3.OperationalError: database is locked`

**Solution:**
```bash
# Stop all ProtLitAI processes
pkill -f protlitai

# Check for lock files
ls -la data/*.db*

# Restart database
python -c "from src.core.database import db_manager; db_manager.initialize()"
```

#### 3. API Rate Limiting
**Warning:** `Rate limit exceeded for PubMed API`

**Solutions:**
- Add PUBMED_API_KEY to environment
- Reduce collection frequency
- Use smaller batch sizes

#### 4. Memory Issues on M2
**Error:** `RuntimeError: MPS backend out of memory`

**Solutions:**
```python
# Reduce batch size
export EMBEDDING_BATCH_SIZE=8

# Clear MPS cache
python -c "import torch; torch.mps.empty_cache()"
```

#### 5. PDF Processing Failures
**Warning:** `Failed to extract text from PDF`

**Normal:** Some PDFs are protected or corrupted. The system will skip these and continue.

### Performance Issues

#### Slow Search Performance
```bash
# Rebuild search indexes
python -c "
from src.core.database import db_manager
db_manager.rebuild_fts_index()
"
```

#### High Memory Usage
```bash
# Clear embedding cache
python -c "
from src.processing.ml_models import get_model_manager
manager = get_model_manager()
manager.clear_cache()
"
```

#### Disk Space Issues
```bash
# Clean old logs
find logs/ -name "*.log" -mtime +30 -delete

# Clean temporary files
rm -rf cache/temp/*

# Archive old papers (optional)
python -c "
from src.utils.maintenance import DatabaseMaintenance
maintenance = DatabaseMaintenance()
maintenance.archive_old_papers(days=365)
"
```

### Getting Help

#### Log Analysis
```bash
# Check recent errors
grep -i error logs/protlitai.log | tail -20

# Monitor real-time logs
tail -f logs/protlitai.log
```

#### Debug Mode
```bash
# Run with debug logging
export LOG_LEVEL=DEBUG
python production_collection.py --mode test
```

#### System Information
```bash
# Generate system report
python -c "
from src.utils.diagnostics import SystemDiagnostics
diag = SystemDiagnostics()
report = diag.generate_report()
print(report)
"
```

---

## Performance Optimization

### M2 Hardware Optimization

#### 1. Memory Management
```bash
# Optimal settings for different M2 configurations
# M2 8GB:
export EMBEDDING_BATCH_SIZE=4
export MAX_CONCURRENT_DOWNLOADS=2

# M2 16GB:
export EMBEDDING_BATCH_SIZE=8
export MAX_CONCURRENT_DOWNLOADS=4

# M2 32GB:
export EMBEDDING_BATCH_SIZE=16
export MAX_CONCURRENT_DOWNLOADS=8
```

#### 2. Model Optimization
```python
# Enable model quantization (faster inference)
from src.core.config import config
config.settings.enable_model_quantization = True

# Use MPS acceleration
config.settings.force_mps_acceleration = True
```

#### 3. Database Optimization
```bash
# Optimize database settings
python -c "
from src.core.database import db_manager
db_manager.optimize_for_m2()
"
```

### Collection Optimization

#### 1. Smart Scheduling
- Run daily collections during low-usage hours
- Use weekly collections for comprehensive updates
- Avoid peak API hours (usually 9-11 AM EST)

#### 2. Source Prioritization
```python
# Configure source priorities
config.settings.source_priorities = {
    "pubmed": 1.0,      # Highest priority
    "arxiv": 0.8,       # High priority  
    "biorxiv": 0.6      # Medium priority
}
```

#### 3. Relevance Filtering
```python
# Configure relevance thresholds
config.settings.relevance_threshold = 0.7  # Higher = more selective
config.settings.enable_smart_filtering = True
```

---

## Appendix

### A. Configuration Reference

#### Environment Variables
```bash
# Core Settings
DATABASE_PATH=./data/literature.db
LOG_LEVEL=INFO
LOG_ROTATION_SIZE=10MB
LOG_RETENTION_DAYS=30

# API Configuration
PUBMED_API_KEY=optional
OPENAI_API_KEY=optional
RATE_LIMIT_PUBMED=10
RATE_LIMIT_ARXIV=1

# ML Configuration
EMBEDDING_MODEL=all-MiniLM-L6-v2
SPACY_MODEL=en_core_web_sm
EMBEDDING_BATCH_SIZE=8
ENABLE_MPS_ACCELERATION=true

# Collection Settings
MAX_PAPERS_PER_SOURCE=100
COLLECTION_TIMEOUT=300
PDF_DOWNLOAD_TIMEOUT=30
```

#### Model Paths
```
models/
├── sentence-transformers/
│   └── all-MiniLM-L6-v2/
├── spacy/
│   └── en_core_web_sm/
└── custom/
    └── protein_classifier/
```

#### Data Structure
```
data/
├── literature.db          # Main SQLite database
├── analytics.db           # DuckDB analytics
├── embeddings/            # Cached embeddings
└── backups/              # Daily backups

cache/
├── pdfs/                 # Downloaded PDFs
├── temp/                 # Temporary files
└── models/               # Model cache

logs/
├── protlitai.log         # Main application log
├── collection.log        # Collection-specific log
└── performance.log       # Performance metrics
```

### B. API Reference

#### Core Classes
- `PaperRepository`: Database operations for papers
- `SearchEngine`: Hybrid search functionality
- `TrendAnalyzer`: Trend analysis and reporting
- `CollectionManager`: Literature collection orchestration

#### Key Methods
```python
# Search
search_engine.search(query, limit=50, filters={})
search_engine.semantic_search(query, similarity_threshold=0.7)

# Collection
collector.search_papers(query, max_results=100, date_from=datetime)
collector.download_pdf(paper_url)

# Analysis
analyzer.analyze_trends(days=30)
analyzer.detect_emerging_topics()
```

### C. Database Schema
```sql
-- Core tables
papers              -- Paper metadata and content
authors             -- Author information and affiliations  
entities            -- Extracted entities (proteins, methods, etc.)
embeddings          -- Semantic embeddings
trends              -- Trend analysis results
alerts              -- User-defined alerts

-- Indexes
idx_papers_date     -- Publication date index
idx_papers_journal  -- Journal index
idx_embeddings_hash -- Embedding similarity index
fts_papers          -- Full-text search index
```

---

**Need More Help?**
- Check the logs: `logs/protlitai.log`
- Run diagnostics: `python -c "from src.utils.diagnostics import SystemDiagnostics; SystemDiagnostics().generate_report()"`
- View system status: Dashboard → System Status
- Consult technical documentation: `design.md`, `tasks.md`

---

**Last Updated:** July 21, 2025  
**Version:** 1.0.0  
**Contact:** Development Team