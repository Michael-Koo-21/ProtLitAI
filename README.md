# ProtLitAI - Protein Design Literature Intelligence Engine

A comprehensive AI-powered system for monitoring, analyzing, and synthesizing protein design literature from multiple sources.

## Overview

ProtLitAI revolutionizes how research teams stay current with protein design literature by automatically monitoring, extracting, and synthesizing research from all major scientific databases. The system provides real-time intelligence on field developments, competitive analysis, and strategic research opportunities.

## Features

- **Multi-Source Literature Aggregation**: Monitors PubMed, arXiv, bioRxiv, and Google Scholar
- **AI-Powered Analysis**: Semantic search, entity recognition, and trend analysis
- **Real-Time Intelligence**: Automated alerts and daily digest reports
- **Competitive Intelligence**: Track competitor activities and institutional research
- **Local-First Architecture**: Complete data privacy and control
- **M2 Optimized**: Native optimization for Apple Silicon performance

## Quick Start

### Prerequisites

- macOS with Apple Silicon (M1/M2)
- Python 3.11+
- 8GB+ RAM recommended

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd ProtLitAI
   ```

2. **Set up virtual environment**
   ```bash
   python3.11 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and preferences
   ```

5. **Initialize the database**
   ```bash
   cd src
   python -c "from core.database import db_manager; db_manager.initialize()"
   ```

### Basic Usage

```bash
# Start the application
cd src
python main.py
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