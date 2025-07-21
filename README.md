# ProtLitAI - Protein Design Literature Intelligence Engine

## 🚀 **Production Ready** - Complete AI-powered system for protein design literature intelligence

A comprehensive, locally-deployed AI system that automatically monitors, analyzes, and synthesizes protein design literature from multiple sources with advanced ML capabilities optimized for Apple Silicon.

## ✨ Overview

ProtLitAI revolutionizes how research teams stay current with protein design literature by:

- **Automated Collection**: Daily monitoring of PubMed, arXiv, bioRxiv, and medRxiv
- **AI-Powered Analysis**: Semantic search, entity recognition, and trend analysis  
- **Real-Time Intelligence**: Instant alerts and comprehensive digest reports
- **Competitive Intelligence**: Track competitors, collaborations, and emerging players
- **Local-First Privacy**: Complete data control with no cloud dependencies
- **M2 Hardware Optimized**: Native Apple Silicon acceleration with MPS

## 🎯 Key Features

### Literature Collection & Processing
- ✅ **Multi-Source Aggregation**: PubMed, arXiv, bioRxiv, medRxiv integration
- ✅ **Smart PDF Processing**: Multi-method text extraction with fallback support
- ✅ **ML Processing Pipeline**: Semantic embeddings + biomedical entity recognition
- ✅ **Automatic Deduplication**: Cross-source paper matching and consolidation

### Search & Discovery  
- ✅ **Hybrid Search Engine**: Combines semantic similarity + keyword + entity search
- ✅ **Natural Language Queries**: "CRISPR protein engineering last month"
- ✅ **Advanced Filtering**: Date, journal, author, institution, relevance filters
- ✅ **Similarity Recommendations**: Find related papers automatically

### Analytics & Intelligence
- ✅ **Trend Analysis**: Topic modeling with statistical significance testing
- ✅ **Competitive Intelligence**: Organization tracking and collaboration networks
- ✅ **Research Gap Detection**: Identify underexplored areas with potential
- ✅ **Performance Dashboard**: Real-time system and collection metrics

### User Interface
- ✅ **Native macOS App**: PyQt6-based interface following Apple design guidelines
- ✅ **Interactive Dashboard**: Real-time stats, recent papers, trending topics
- ✅ **Advanced Search Interface**: Filters, results table, paper detail views
- ✅ **Export Capabilities**: PDF, CSV, BibTeX format support

## 🚀 Quick Start

### System Requirements
- **Hardware**: Apple Silicon Mac (M1/M2) with 8GB+ RAM
- **Software**: macOS 12.0+, Python 3.11+
- **Storage**: 10GB free space (5GB for models + 5GB+ for literature)
- **Network**: Stable internet for initial model download and literature collection

### Installation (5 minutes)

```bash
# 1. Clone and setup project
git clone <repository-url> ProtLitAI
cd ProtLitAI
python3.11 -m venv venv
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Initialize ML models (downloads ~550MB)
python initialize_models.py

# 4. Run test collection (collect sample papers)
python production_collection.py --mode test

# 5. Launch application
python -m src.ui.app
```

**That's it!** Your ProtLitAI system is ready for production use.

### First Day Usage

```bash
# Collect recent papers (runs in 30-60 seconds)
python production_collection.py --mode daily

# Launch the application
python -m src.ui.app

# View dashboard with new papers and trends
# Use search interface to find specific topics
# Configure alerts for topics of interest
```

## Project Structure

```
protlitai/
├── src/
│   ├── core/           # Core application components
│   ├── collectors/     # Literature collection modules
│   ├── processing/     # NLP and text processing
│   ├── analysis/       # Search and analytics
│   ├── ui/            # User interface
│   └── utils/         # Utility functions
├── models/            # ML model storage
├── data/              # Database files
├── cache/             # PDF and embedding cache
├── tests/             # Test suite
└── docs/              # Documentation
```

## Configuration

### Environment Variables

Key configuration options in `.env`:

```bash
# API Keys
PUBMED_API_KEY=your_key_here
OPENAI_API_KEY=your_key_here  # Optional

# ML Models
EMBEDDING_MODEL=all-MiniLM-L6-v2
DEVICE=mps  # M2 optimization

# Rate Limits
PUBMED_RATE_LIMIT=10.0
ARXIV_RATE_LIMIT=1.0
```

### Database Paths

- Literature database: `data/literature.db`
- Analytics database: `data/analytics.db`
- PDF cache: `cache/pdfs/`
- Model cache: `models/`

## Development

### Running Tests

```bash
pytest tests/ -v
```

### Code Style

```bash
# Format code
black src/

# Lint code
flake8 src/

# Type checking
mypy src/
```

### Adding New Features

1. Create feature branch
2. Implement following existing patterns
3. Add comprehensive tests
4. Update documentation
5. Submit pull request

## Architecture

### Core Components

- **Configuration Management**: Environment-based settings with validation
- **Database Layer**: SQLite + DuckDB hybrid for literature and analytics
- **Repository Pattern**: Clean data access abstraction
- **Structured Logging**: Comprehensive observability
- **Schema Management**: Automated database migrations

### ML Pipeline

- **Embedding Generation**: Sentence transformers for semantic search
- **Entity Recognition**: spaCy biomedical models
- **Topic Modeling**: BERTopic for trend analysis
- **M2 Optimization**: MPS acceleration for inference

## Performance

Optimized for Apple M2 MacBook Pro:

- Literature processing: 500-1000 papers daily
- Search response: <2 seconds for 95% of queries
- Memory usage: Efficient operation within 8GB RAM
- Storage: <100GB total footprint

## API Integration

### Supported Sources

- **PubMed**: E-utilities API with rate limiting
- **arXiv**: RSS feeds and OAI-PMH protocol
- **bioRxiv**: Web scraping with respectful delays
- **Google Scholar**: Programmatic access via scholarly

### Rate Limiting

All external APIs implement robust rate limiting and error handling to ensure compliance with terms of service.

## Security & Privacy

- **Local-First**: No user data transmitted beyond API requirements
- **Encryption**: API keys stored securely in macOS Keychain
- **File Permissions**: Proper isolation and access control
- **Audit Logging**: Comprehensive activity tracking

## Troubleshooting

### Common Issues

1. **Database Connection Errors**
   - Ensure proper file permissions
   - Check available disk space
   - Verify SQLite installation

2. **ML Model Loading**
   - Confirm internet connectivity for downloads
   - Check available memory
   - Verify MPS device availability

3. **API Rate Limiting**
   - Adjust rate limits in configuration
   - Check API key validity
   - Monitor request patterns

### Support

For issues and questions:
1. Check the troubleshooting guide
2. Review logs in `logs/protlitai.log`
3. Create GitHub issue with reproduction steps

## License

[License details to be added]

## Contributing

Contributions welcome! Please read the contributing guidelines and submit pull requests for any improvements.

## Roadmap

- [ ] Web-based UI interface
- [ ] Real-time collaboration features
- [ ] Advanced visualization components
- [ ] Multi-language support
- [ ] Cloud deployment options

---

**Version**: 1.0.0  
**Last Updated**: July 18, 2025