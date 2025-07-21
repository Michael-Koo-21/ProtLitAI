# ProtLitAI Deployment Guide

## Production Deployment Guide for Local Installation

**Target Audience:** System administrators, developers, and researchers setting up ProtLitAI  
**System Requirements:** macOS with Apple Silicon, Python 3.11+  
**Deployment Type:** Local single-user installation  
**Estimated Setup Time:** 30-60 minutes

---

## Table of Contents

1. [Pre-Deployment Checklist](#pre-deployment-checklist)
2. [System Requirements Verification](#system-requirements-verification)
3. [Step-by-Step Deployment](#step-by-step-deployment)
4. [Configuration](#configuration)
5. [First Run and Validation](#first-run-and-validation)
6. [Production Setup](#production-setup)
7. [Maintenance and Updates](#maintenance-and-updates)
8. [Troubleshooting](#troubleshooting)

---

## Pre-Deployment Checklist

### Hardware Requirements
- [ ] Apple Silicon Mac (M1, M1 Pro/Max, M2, M2 Pro/Max)
- [ ] Minimum 8GB RAM (16GB+ recommended for large collections)
- [ ] 10GB+ free disk space (5GB for models, 5GB+ for literature database)
- [ ] Stable internet connection (minimum 10 Mbps for model downloads)

### Software Requirements
- [ ] macOS 12.0 Monterey or later
- [ ] Xcode Command Line Tools
- [ ] Homebrew package manager
- [ ] Python 3.11 or later
- [ ] Git version control

### Network Access Requirements
- [ ] Access to PubMed API (ncbi.nlm.nih.gov)
- [ ] Access to arXiv.org
- [ ] Access to bioRxiv.org and medRxiv.org
- [ ] Access to Hugging Face model hub (huggingface.co)
- [ ] Firewall allows HTTPS connections on port 443

### Optional API Keys
- [ ] PubMed API key (for higher rate limits)
- [ ] OpenAI API key (for enhanced summarization features)

---

## System Requirements Verification

### 1. Hardware Check
```bash
# Check macOS version
sw_vers

# Check hardware type (should show Apple Silicon)
uname -m  # Should return "arm64"

# Check available memory
system_profiler SPHardwareDataType | grep "Memory"

# Check available disk space
df -h
```

**Expected Output:**
```
ProductVersion: 12.0 or higher
arm64
Memory: 8 GB or higher
Available space: 10GB+ on main volume
```

### 2. Software Prerequisites
```bash
# Install Xcode Command Line Tools (if not installed)
xcode-select --install

# Install Homebrew (if not installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Python 3.11
brew install python@3.11

# Verify Python installation
python3.11 --version  # Should show 3.11.x

# Install Git (if not installed)
brew install git
```

### 3. Network Connectivity Test
```bash
# Test API endpoints
curl -I https://pubmed.ncbi.nlm.nih.gov/
curl -I https://arxiv.org/
curl -I https://www.biorxiv.org/
curl -I https://huggingface.co/

# All should return HTTP 200 or 30x responses
```

---

## Step-by-Step Deployment

### Step 1: Repository Setup

```bash
# Create project directory
cd ~/Documents  # or your preferred location
mkdir ProtLitAI-Production
cd ProtLitAI-Production

# Clone repository (replace with actual repo URL)
git clone <repository-url> .

# Verify project structure
ls -la
# Should show: src/, requirements.txt, README.md, etc.
```

### Step 2: Python Environment Setup

```bash
# Create isolated virtual environment
python3.11 -m venv protlitai-env

# Activate environment
source protlitai-env/bin/activate

# Upgrade pip and setuptools
pip install --upgrade pip setuptools wheel

# Verify environment
which python  # Should show path to virtual environment
python --version  # Should show 3.11.x
```

### Step 3: Dependency Installation

```bash
# Install all Python dependencies
pip install -r requirements.txt

# This will install ~60 packages including:
# - PyTorch with MPS support
# - sentence-transformers
# - spaCy and biomedical models
# - SQLite and DuckDB
# - FastAPI, PyQt6, and other components

# Verify critical installations
python -c "import torch; print(f'PyTorch: {torch.__version__}, MPS: {torch.backends.mps.is_available()}')"
python -c "import sentence_transformers; print('SentenceTransformers: OK')"
python -c "import spacy; print('spaCy: OK')"
```

**Expected Output:**
```
PyTorch: 2.1.2, MPS: True
SentenceTransformers: OK
spaCy: OK
```

### Step 4: Environment Configuration

```bash
# Create configuration file
cp .env.example .env

# Edit configuration (use nano, vim, or your preferred editor)
nano .env
```

**Minimal Configuration (.env):**
```bash
# Database configuration
DATABASE_PATH=./data/literature.db
LOG_LEVEL=INFO

# Optional: API keys (recommended for production)
PUBMED_API_KEY=your_pubmed_key_here
OPENAI_API_KEY=your_openai_key_here

# Performance settings for M2
EMBEDDING_BATCH_SIZE=8
MAX_CONCURRENT_DOWNLOADS=4
ENABLE_MPS_ACCELERATION=true

# Collection settings
MAX_PAPERS_PER_SOURCE=500
COLLECTION_TIMEOUT=600
```

### Step 5: Directory Structure Creation

```bash
# Create required directories
mkdir -p data cache/pdfs cache/temp logs models backups

# Set appropriate permissions
chmod 755 data cache logs models backups
chmod 700 cache/pdfs cache/temp  # More restrictive for downloaded content

# Verify structure
tree -L 2 .
```

### Step 6: Database Initialization

```bash
# Initialize database schema
python -c "
from src.core.database import db_manager
db_manager.initialize()
print('Database initialized successfully')
"
```

**Expected Output:**
```
Database initialized successfully
```

### Step 7: ML Model Download and Initialization

```bash
# This is the longest step - downloads ~550MB of models
python initialize_models.py
```

**Expected Output:**
```
🚀 ProtLitAI ML Model Initialization
✅ System Requirements: READY
🤖 Initializing ML Models
✅ Sentence Transformer loaded in X.Xs
✅ spaCy model loaded in X.Xs
🎉 All models initialized successfully!
```

**Timing Expectations:**
- Fast internet (50+ Mbps): 2-3 minutes
- Average internet (10-25 Mbps): 5-10 minutes
- Slow internet (<10 Mbps): 10-20 minutes

---

## Configuration

### Production Configuration Settings

#### 1. Performance Tuning
```bash
# Add to .env file based on your M2 configuration

# For M2 8GB RAM:
EMBEDDING_BATCH_SIZE=4
MAX_CONCURRENT_DOWNLOADS=2
DATABASE_CACHE_SIZE=32MB
PDF_PROCESSING_THREADS=2

# For M2 16GB RAM:
EMBEDDING_BATCH_SIZE=8
MAX_CONCURRENT_DOWNLOADS=4
DATABASE_CACHE_SIZE=64MB
PDF_PROCESSING_THREADS=4

# For M2 32GB+ RAM:
EMBEDDING_BATCH_SIZE=16
MAX_CONCURRENT_DOWNLOADS=8
DATABASE_CACHE_SIZE=128MB
PDF_PROCESSING_THREADS=6
```

#### 2. Collection Schedule Configuration
```bash
# Add to .env for automated collection
ENABLE_DAILY_COLLECTION=true
DAILY_COLLECTION_TIME=06:00
ENABLE_WEEKLY_COLLECTION=true
WEEKLY_COLLECTION_DAY=sunday
WEEKLY_COLLECTION_TIME=02:00
```

#### 3. API Rate Limiting
```bash
# Conservative settings for API compliance
RATE_LIMIT_PUBMED=8      # requests per second (default: 10)
RATE_LIMIT_ARXIV=1       # requests per second
RATE_LIMIT_BIORXIV=0.5   # requests per second

# Retry settings
API_RETRY_ATTEMPTS=3
API_RETRY_BACKOFF=exponential
```

#### 4. Storage Management
```bash
# Automatic cleanup settings
ENABLE_AUTO_CLEANUP=true
LOG_RETENTION_DAYS=30
TEMP_FILE_RETENTION_HOURS=24
PDF_CACHE_SIZE_LIMIT=5GB
EMBEDDING_CACHE_SIZE_LIMIT=2GB
```

### Security Configuration

#### 1. API Key Management
```bash
# Store sensitive keys in macOS Keychain (recommended)
security add-generic-password -a protlitai -s pubmed_api -w "your_pubmed_key"
security add-generic-password -a protlitai -s openai_api -w "your_openai_key"

# Update .env to use keychain
PUBMED_API_KEY_KEYCHAIN=pubmed_api
OPENAI_API_KEY_KEYCHAIN=openai_api
```

#### 2. Data Protection
```bash
# Enable FileVault for full disk encryption (recommended)
sudo fdesetup enable

# Set restrictive permissions on data directory
chmod 700 data/
chmod 600 data/*.db
```

---

## First Run and Validation

### 1. System Health Check
```bash
# Run comprehensive system check
python -c "
from src.utils.diagnostics import SystemDiagnostics
diag = SystemDiagnostics()
report = diag.full_system_check()
print(report)
"
```

### 2. Test Collection
```bash
# Run small test collection
python production_collection.py --mode test

# Expected: 10-30 papers collected successfully
```

### 3. Search Functionality Test
```bash
# Test search engine
python -c "
from src.analysis.search_engine import SearchEngine
engine = SearchEngine()
results = engine.search('protein design')
print(f'Found {len(results)} papers')
for i, paper in enumerate(results[:3]):
    print(f'{i+1}. {paper.title[:60]}...')
"
```

### 4. UI Application Test
```bash
# Launch main application
python -m src.ui.app

# Should open native macOS application window
# Navigate through Dashboard, Search, and Settings to verify functionality
```

### 5. Performance Benchmark
```bash
# Run performance tests
python -c "
from src.processing.ml_models import get_model_manager
manager = get_model_manager()
stats = manager.benchmark_performance()
print(f'Embedding generation: {stats[\"embeddings_per_second\"]:.1f} texts/sec')
print(f'Memory usage: {stats[\"memory_usage\"]}')
"
```

**Expected Performance (M2):**
- Embedding generation: 8-15 texts/second
- Search response time: <2 seconds
- Memory usage: <2GB during normal operation

---

## Production Setup

### 1. Automated Daily Collection

#### Create Launch Daemon (macOS)
```bash
# Create launch daemon plist
sudo nano /Library/LaunchDaemons/com.protlitai.dailycollection.plist
```

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.protlitai.dailycollection</string>
    <key>ProgramArguments</key>
    <array>
        <string>/path/to/protlitai-env/bin/python</string>
        <string>/path/to/ProtLitAI-Production/production_collection.py</string>
        <string>--mode</string>
        <string>daily</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>6</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    <key>RunAtLoad</key>
    <false/>
    <key>StandardOutPath</key>
    <string>/path/to/ProtLitAI-Production/logs/daily_collection.log</string>
    <key>StandardErrorPath</key>
    <string>/path/to/ProtLitAI-Production/logs/daily_collection_error.log</string>
</dict>
</plist>
```

```bash
# Load the launch daemon
sudo launchctl load /Library/LaunchDaemons/com.protlitai.dailycollection.plist

# Verify it's loaded
sudo launchctl list | grep protlitai
```

### 2. Log Rotation Setup

```bash
# Create logrotate configuration
nano /usr/local/etc/logrotate.d/protlitai
```

```bash
/path/to/ProtLitAI-Production/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    create 644 user staff
    postrotate
        # Signal application to reopen log files if needed
        killall -USR1 python || true
    endscript
}
```

### 3. Backup Strategy

#### Automated Database Backup
```bash
# Create backup script
nano backup_protlitai.sh
```

```bash
#!/bin/bash
BACKUP_DIR="/Users/$(whoami)/Documents/ProtLitAI-Backups"
SOURCE_DIR="/path/to/ProtLitAI-Production"
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Backup database
cp "$SOURCE_DIR/data/literature.db" "$BACKUP_DIR/literature_$DATE.db"

# Backup configuration
cp "$SOURCE_DIR/.env" "$BACKUP_DIR/config_$DATE.env"

# Compress old backups (keep last 30 days)
find "$BACKUP_DIR" -name "literature_*.db" -mtime +30 -exec gzip {} \;

# Remove very old backups (keep last 90 days)
find "$BACKUP_DIR" -name "literature_*.db.gz" -mtime +90 -delete

echo "Backup completed: literature_$DATE.db"
```

```bash
# Make executable and test
chmod +x backup_protlitai.sh
./backup_protlitai.sh
```

### 4. Monitoring Setup

#### Health Check Script
```bash
# Create monitoring script
nano monitor_protlitai.py
```

```python
#!/usr/bin/env python3
"""ProtLitAI Health Monitoring Script"""
import sys
import json
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.utils.diagnostics import SystemDiagnostics
from src.core.config import config

def main():
    diag = SystemDiagnostics()
    status = diag.quick_health_check()
    
    timestamp = datetime.now().isoformat()
    
    # Log health status
    health_log = {
        "timestamp": timestamp,
        "status": status.overall_status,
        "database_size": status.database_size,
        "papers_count": status.papers_count,
        "disk_usage": status.disk_usage,
        "memory_usage": status.memory_usage,
        "errors": status.errors
    }
    
    # Write to health log
    with open("logs/health.log", "a") as f:
        f.write(json.dumps(health_log) + "\n")
    
    # Exit with error code if unhealthy
    if status.overall_status != "healthy":
        print(f"HEALTH CHECK FAILED: {status.overall_status}")
        print(f"Errors: {status.errors}")
        sys.exit(1)
    
    print("Health check passed")
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
```

```bash
# Test health check
python monitor_protlitai.py
```

---

## Maintenance and Updates

### Daily Maintenance Tasks

#### 1. Log Review (2 minutes)
```bash
# Check for errors in logs
grep -i error logs/protlitai.log | tail -10

# Check collection status
grep "COLLECTION SUMMARY" logs/protlitai.log | tail -1

# Check system health
tail -5 logs/health.log
```

#### 2. Disk Space Monitoring
```bash
# Check disk usage
du -sh data/ cache/ logs/ models/

# Clean temporary files if needed
find cache/temp -type f -mtime +1 -delete
```

### Weekly Maintenance Tasks

#### 1. Database Optimization (5 minutes)
```bash
# Run database maintenance
python -c "
from src.utils.maintenance import DatabaseMaintenance
maintenance = DatabaseMaintenance()
maintenance.optimize_database()
maintenance.rebuild_indexes()
print('Database maintenance completed')
"
```

#### 2. Performance Review
```bash
# Generate weekly performance report
python -c "
from src.analysis.report_generator import ReportGenerator
generator = ReportGenerator()
report = generator.weekly_performance_report()
print(report)
"
```

### Monthly Maintenance Tasks

#### 1. Model Updates
```bash
# Check for model updates
python -c "
from src.processing.ml_models import get_model_manager
manager = get_model_manager()
updates = manager.check_for_updates()
if updates:
    print(f'Updates available: {updates}')
    # manager.update_models()  # Uncomment to auto-update
else:
    print('All models up to date')
"
```

#### 2. Full System Backup
```bash
# Create comprehensive backup
tar -czf "protlitai_backup_$(date +%Y%m%d).tar.gz" \
    --exclude='cache/temp' \
    --exclude='logs/*.log' \
    data/ models/ .env backup_protlitai.sh
```

### Update Procedures

#### Application Updates
```bash
# Pull latest code
git fetch origin
git pull origin main

# Update dependencies
pip install --upgrade -r requirements.txt

# Run migration if needed
python -c "
from src.core.database import db_manager
db_manager.run_migrations()
"

# Test updated system
python production_collection.py --mode test
```

#### Python Package Updates
```bash
# List outdated packages
pip list --outdated

# Update specific packages (be careful with major version changes)
pip install --upgrade sentence-transformers spacy torch

# Re-run model initialization if ML packages updated
python initialize_models.py
```

---

## Troubleshooting

### Installation Issues

#### 1. Python Version Conflicts
**Problem:** Multiple Python versions causing conflicts

```bash
# Solution: Use specific Python version
/usr/local/bin/python3.11 -m venv protlitai-env
source protlitai-env/bin/activate
which python  # Verify correct version
```

#### 2. PyTorch MPS Not Available
**Problem:** `torch.backends.mps.is_available()` returns `False`

```bash
# Check macOS version
sw_vers  # Must be 12.0+

# Reinstall PyTorch with MPS support
pip uninstall torch
pip install torch

# Verify MPS support
python -c "import torch; print(torch.backends.mps.is_available())"
```

#### 3. Model Download Failures
**Problem:** Network timeouts during model downloads

```bash
# Set longer timeout
export HF_HUB_DOWNLOAD_TIMEOUT=300

# Use mirror if available
export HF_ENDPOINT=https://huggingface.co

# Retry model initialization
python initialize_models.py
```

### Runtime Issues

#### 1. Database Lock Errors
**Problem:** `database is locked` errors

```bash
# Find and kill processes using database
lsof data/literature.db
kill -9 <PID>

# Restart database connection
python -c "
from src.core.database import db_manager
db_manager.close_connections()
db_manager.initialize()
"
```

#### 2. Memory Issues on M2
**Problem:** Out of memory errors during collection

```bash
# Reduce batch sizes
export EMBEDDING_BATCH_SIZE=4
export MAX_CONCURRENT_DOWNLOADS=2

# Clear MPS cache
python -c "import torch; torch.mps.empty_cache()"

# Restart collection
python production_collection.py --mode test
```

#### 3. API Rate Limiting
**Problem:** Too many API requests

```bash
# Check current rate limits
grep -i "rate limit" logs/protlitai.log

# Reduce collection frequency
export MAX_PAPERS_PER_SOURCE=50
export RATE_LIMIT_PUBMED=5

# Wait and retry
sleep 300
python production_collection.py --mode test
```

### Data Issues

#### 1. Corrupted Database
**Problem:** Database corruption errors

```bash
# Check database integrity
sqlite3 data/literature.db "PRAGMA integrity_check;"

# If corrupted, restore from backup
cp backups/literature_YYYYMMDD.db data/literature.db

# Rebuild indexes
python -c "
from src.core.database import db_manager
db_manager.rebuild_fts_index()
"
```

#### 2. Missing Papers
**Problem:** Expected papers not appearing in search

```bash
# Check FTS index
sqlite3 data/literature.db "SELECT count(*) FROM papers_fts;"

# Rebuild full-text search index
python -c "
from src.core.database import db_manager
db_manager.rebuild_fts_index()
"

# Re-run collection
python production_collection.py --mode daily
```

### Performance Issues

#### 1. Slow Search Performance
**Problem:** Search taking >5 seconds

```bash
# Check database size
ls -lh data/literature.db

# Optimize database
sqlite3 data/literature.db "VACUUM; ANALYZE;"

# Clear query cache
rm -rf cache/search_cache/*
```

#### 2. High CPU Usage
**Problem:** Constant high CPU usage

```bash
# Check running processes
ps aux | grep python

# Monitor system resources
top -pid $(pgrep -f protlitai)

# Adjust performance settings
export EMBEDDING_BATCH_SIZE=2
export PDF_PROCESSING_THREADS=1
```

### Getting Support

#### Generate Diagnostic Report
```bash
# Create comprehensive diagnostic report
python -c "
from src.utils.diagnostics import SystemDiagnostics
diag = SystemDiagnostics()
report = diag.generate_support_report()
with open('diagnostic_report.txt', 'w') as f:
    f.write(report)
print('Diagnostic report saved to diagnostic_report.txt')
"
```

#### Collect System Information
```bash
# System info script
echo "=== ProtLitAI Diagnostic Information ===" > system_info.txt
echo "Date: $(date)" >> system_info.txt
echo "macOS: $(sw_vers -productVersion)" >> system_info.txt
echo "Hardware: $(uname -m)" >> system_info.txt
echo "Python: $(python --version)" >> system_info.txt
echo "PyTorch: $(python -c 'import torch; print(torch.__version__)')" >> system_info.txt
echo "MPS Available: $(python -c 'import torch; print(torch.backends.mps.is_available())')" >> system_info.txt
echo "" >> system_info.txt
echo "=== Recent Errors ===" >> system_info.txt
grep -i error logs/protlitai.log | tail -20 >> system_info.txt
```

---

## Post-Deployment Checklist

### Validation Tests
- [ ] ML models loaded successfully
- [ ] Database schema created and accessible  
- [ ] API connections working (PubMed, arXiv, bioRxiv)
- [ ] Test collection completed without errors
- [ ] Search functionality returning results
- [ ] UI application launches and navigates properly
- [ ] Performance benchmarks within acceptable range

### Production Readiness
- [ ] Daily collection scheduled and tested
- [ ] Log rotation configured
- [ ] Backup strategy implemented and tested
- [ ] Health monitoring in place
- [ ] API keys configured securely
- [ ] File permissions set appropriately
- [ ] Documentation accessible to users

### Monitoring Setup
- [ ] Log monitoring configured
- [ ] Disk space monitoring active
- [ ] Performance metrics collection enabled
- [ ] Error alerting configured
- [ ] Health check scripts scheduled

---

**Deployment Complete! 🎉**

Your ProtLitAI system is now ready for production use. The system will:
- Automatically collect literature daily at 6 AM
- Process papers with ML pipeline
- Store in local database with search capabilities
- Provide native macOS interface for research

**Next Steps:**
1. Run first daily collection: `python production_collection.py --mode daily`
2. Launch application: `python -m src.ui.app`
3. Configure user alerts and preferences
4. Review daily logs for first week of operation

**Support:** Consult USER_GUIDE.md for detailed usage instructions