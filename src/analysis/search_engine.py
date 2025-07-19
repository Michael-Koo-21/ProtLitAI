"""Hybrid search engine combining multiple search strategies."""

import json
import sqlite3
from typing import List, Dict, Optional, Tuple, Any, Set
from datetime import datetime, timedelta

from core.database import db_manager
from core.models import Paper, SearchQuery, SearchResult, EntityType
from core.repository import paper_repo, entity_repo
from core.logging import get_logger, PerformanceLogger
from analysis.similarity_engine import similarity_engine


class HybridSearchEngine:
    """Advanced search engine combining semantic, keyword, and entity-based search."""
    
    def __init__(self):
        self.logger = get_logger("search_engine")
        self.query_cache = {}
        self.cache_ttl = 300  # 5 minutes
    
    def search(self, search_query: SearchQuery) -> SearchResult:
        """Perform hybrid search combining multiple strategies."""
        start_time = datetime.utcnow()
        
        with PerformanceLogger(self.logger, "hybrid_search", 
                             query=search_query.query):
            
            # Check cache first
            cache_key = self._generate_cache_key(search_query)
            cached_result = self._get_cached_result(cache_key)
            if cached_result:
                return cached_result
            
            # Combine different search strategies
            results = []
            
            # 1. Semantic search (if query is long enough)
            if len(search_query.query.split()) >= 3:
                semantic_results = self._semantic_search(search_query)
                results.extend(semantic_results)
            
            # 2. Keyword-based full-text search
            keyword_results = self._keyword_search(search_query)
            results.extend(keyword_results)
            
            # 3. Entity-based search
            entity_results = self._entity_search(search_query)
            results.extend(entity_results)
            
            # 4. Apply filters
            filtered_results = self._apply_filters(results, search_query.filters)
            
            # 5. Remove duplicates and rank
            final_results = self._deduplicate_and_rank(filtered_results)
            
            # 6. Apply pagination
            total_count = len(final_results)
            paginated_results = final_results[
                search_query.offset:search_query.offset + search_query.limit
            ]
            
            # 7. Generate facets
            facets = self._generate_facets(final_results)
            
            # Create search result
            query_time = (datetime.utcnow() - start_time).total_seconds()
            result = SearchResult(
                papers=paginated_results,
                total_count=total_count,
                query_time=query_time,
                facets=facets
            )
            
            # Cache result
            self._cache_result(cache_key, result)
            
            self.logger.info("Hybrid search completed", 
                           query=search_query.query,
                           total_results=total_count,
                           query_time=query_time)
            
            return result
    
    def _semantic_search(self, search_query: SearchQuery) -> List[Tuple[Paper, float, str]]:
        """Perform semantic search using embeddings."""
        try:
            # This would need integration with embedding generation
            # For now, return empty list
            # TODO: Integrate with embedding generator to get query vector
            results = []
            
            self.logger.debug("Semantic search completed", 
                            results_count=len(results))
            return results
            
        except Exception as e:
            self.logger.error("Semantic search failed", error=str(e))
            return []
    
    def _keyword_search(self, search_query: SearchQuery) -> List[Tuple[Paper, float, str]]:
        """Perform keyword-based full-text search."""
        results = []
        
        try:
            # Prepare FTS query
            fts_query = self._prepare_fts_query(search_query.query)
            
            with db_manager.get_sqlite_connection() as conn:
                conn.row_factory = sqlite3.Row
                
                # Execute FTS search with ranking
                cursor = conn.execute("""
                    SELECT p.*, 
                           rank(matchinfo(fts)) as relevance_score,
                           snippet(papers_fts, '<mark>', '</mark>', '...', -1, 32) as snippet
                    FROM papers p
                    JOIN papers_fts fts ON p.rowid = fts.rowid
                    WHERE papers_fts MATCH ?
                    ORDER BY relevance_score DESC
                """, (fts_query,))
                
                for row in cursor.fetchall():
                    paper = paper_repo._row_to_paper(row)
                    # Normalize FTS relevance score to 0-1 range
                    score = min(row["relevance_score"] / 100.0, 1.0)
                    snippet = row["snippet"] or ""
                    
                    results.append((paper, score, "keyword"))
            
            self.logger.debug("Keyword search completed", 
                            query=fts_query,
                            results_count=len(results))
            
        except Exception as e:
            self.logger.error("Keyword search failed", 
                            query=search_query.query, 
                            error=str(e))
        
        return results
    
    def _entity_search(self, search_query: SearchQuery) -> List[Tuple[Paper, float, str]]:
        """Perform entity-based search."""
        results = []
        
        try:
            # Extract potential entities from query
            query_terms = search_query.query.lower().split()
            
            with db_manager.get_sqlite_connection() as conn:
                conn.row_factory = sqlite3.Row
                
                # Search for papers containing entities matching query terms
                placeholders = ','.join(['?' for _ in query_terms])
                cursor = conn.execute(f"""
                    SELECT DISTINCT p.*, e.entity_text, e.entity_type, e.confidence
                    FROM papers p
                    JOIN entities e ON p.id = e.paper_id
                    WHERE LOWER(e.entity_text) IN ({placeholders})
                       OR e.entity_text LIKE ?
                    ORDER BY e.confidence DESC
                """, query_terms + [f"%{search_query.query}%"])
                
                paper_scores = {}
                for row in cursor.fetchall():
                    paper_id = row["id"]
                    confidence = row["confidence"]
                    
                    if paper_id not in paper_scores:
                        paper = paper_repo._row_to_paper(row)
                        paper_scores[paper_id] = {
                            'paper': paper,
                            'score': confidence,
                            'entities': []
                        }
                    else:
                        # Boost score for multiple matching entities
                        paper_scores[paper_id]['score'] = max(
                            paper_scores[paper_id]['score'],
                            confidence
                        )
                    
                    paper_scores[paper_id]['entities'].append({
                        'text': row["entity_text"],
                        'type': row["entity_type"],
                        'confidence': confidence
                    })
                
                # Convert to results format
                for paper_data in paper_scores.values():
                    results.append((
                        paper_data['paper'], 
                        paper_data['score'], 
                        "entity"
                    ))
            
            self.logger.debug("Entity search completed", 
                            results_count=len(results))
            
        except Exception as e:
            self.logger.error("Entity search failed", 
                            query=search_query.query, 
                            error=str(e))
        
        return results
    
    def _apply_filters(
        self, 
        results: List[Tuple[Paper, float, str]], 
        filters: Dict[str, Any]
    ) -> List[Tuple[Paper, float, str]]:
        """Apply search filters to results."""
        if not filters:
            return results
        
        filtered_results = []
        
        for paper, score, source in results:
            include = True
            
            # Date range filter
            if 'date_from' in filters or 'date_to' in filters:
                if paper.publication_date:
                    pub_date = paper.publication_date
                    if 'date_from' in filters:
                        date_from = datetime.fromisoformat(filters['date_from'])
                        if pub_date < date_from:
                            include = False
                    if 'date_to' in filters:
                        date_to = datetime.fromisoformat(filters['date_to'])
                        if pub_date > date_to:
                            include = False
                else:
                    # Exclude papers without publication date if date filter is applied
                    include = False
            
            # Journal filter
            if 'journals' in filters and filters['journals']:
                if not paper.journal or paper.journal not in filters['journals']:
                    include = False
            
            # Source filter
            if 'sources' in filters and filters['sources']:
                if paper.source not in filters['sources']:
                    include = False
            
            # Author filter
            if 'authors' in filters and filters['authors']:
                author_match = any(
                    author.lower() in ' '.join(paper.authors).lower()
                    for author in filters['authors']
                )
                if not author_match:
                    include = False
            
            # Relevance score filter
            if 'min_relevance' in filters:
                if not paper.relevance_score or paper.relevance_score < filters['min_relevance']:
                    include = False
            
            # Paper type filter
            if 'paper_types' in filters and filters['paper_types']:
                if paper.paper_type not in filters['paper_types']:
                    include = False
            
            if include:
                filtered_results.append((paper, score, source))
        
        self.logger.debug("Filters applied", 
                        original_count=len(results),
                        filtered_count=len(filtered_results))
        
        return filtered_results
    
    def _deduplicate_and_rank(
        self, 
        results: List[Tuple[Paper, float, str]]
    ) -> List[Paper]:
        """Remove duplicates and rank results by combined score."""
        
        # Group by paper ID and combine scores
        paper_scores = {}
        
        for paper, score, source in results:
            if paper.id not in paper_scores:
                paper_scores[paper.id] = {
                    'paper': paper,
                    'scores': {},
                    'total_score': 0.0
                }
            
            # Store best score for each source type
            if source not in paper_scores[paper.id]['scores']:
                paper_scores[paper.id]['scores'][source] = score
            else:
                paper_scores[paper.id]['scores'][source] = max(
                    paper_scores[paper.id]['scores'][source], score
                )
        
        # Calculate combined scores with weights
        score_weights = {
            'semantic': 0.4,
            'keyword': 0.3,
            'entity': 0.3
        }
        
        for paper_data in paper_scores.values():
            total_score = 0.0
            total_weight = 0.0
            
            for source, score in paper_data['scores'].items():
                weight = score_weights.get(source, 0.2)
                total_score += score * weight
                total_weight += weight
            
            # Apply additional ranking factors
            paper = paper_data['paper']
            
            # Recency boost (papers from last 30 days get 20% boost)
            if paper.publication_date:
                days_old = (datetime.utcnow() - paper.publication_date).days
                if days_old <= 30:
                    total_score *= 1.2
                elif days_old <= 90:
                    total_score *= 1.1
            
            # Relevance score boost
            if paper.relevance_score:
                total_score *= (0.8 + 0.2 * paper.relevance_score)
            
            # Normalize by total weight
            if total_weight > 0:
                total_score /= total_weight
            
            paper_data['total_score'] = total_score
        
        # Sort by combined score
        ranked_papers = sorted(
            paper_scores.values(),
            key=lambda x: x['total_score'],
            reverse=True
        )
        
        return [item['paper'] for item in ranked_papers]
    
    def _generate_facets(self, papers: List[Paper]) -> Dict[str, Any]:
        """Generate search facets from results."""
        facets = {}
        
        if not papers:
            return facets
        
        # Journal facets
        journals = {}
        for paper in papers:
            if paper.journal:
                journals[paper.journal] = journals.get(paper.journal, 0) + 1
        facets['journals'] = dict(sorted(journals.items(), key=lambda x: x[1], reverse=True)[:20])
        
        # Source facets
        sources = {}
        for paper in papers:
            sources[paper.source] = sources.get(paper.source, 0) + 1
        facets['sources'] = sources
        
        # Publication year facets
        years = {}
        for paper in papers:
            if paper.publication_date:
                year = paper.publication_date.year
                years[str(year)] = years.get(str(year), 0) + 1
        facets['years'] = dict(sorted(years.items(), reverse=True)[:10])
        
        # Paper type facets
        types = {}
        for paper in papers:
            types[paper.paper_type] = types.get(paper.paper_type, 0) + 1
        facets['paper_types'] = types
        
        return facets
    
    def _prepare_fts_query(self, query: str) -> str:
        """Prepare query for FTS5 search."""
        # Remove special characters and prepare for FTS
        terms = []
        for term in query.strip().split():
            # Remove special characters
            clean_term = ''.join(c for c in term if c.isalnum() or c in '-_')
            if len(clean_term) >= 2:
                # Add wildcard for partial matching
                terms.append(f"{clean_term}*")
        
        return ' '.join(terms)
    
    def _generate_cache_key(self, search_query: SearchQuery) -> str:
        """Generate cache key for search query."""
        # Create deterministic hash of query parameters
        key_data = {
            'query': search_query.query,
            'filters': search_query.filters,
            'limit': search_query.limit,
            'offset': search_query.offset,
            'sort_by': search_query.sort_by,
            'sort_order': search_query.sort_order
        }
        return f"search_{hash(json.dumps(key_data, sort_keys=True))}"
    
    def _get_cached_result(self, cache_key: str) -> Optional[SearchResult]:
        """Get cached search result if valid."""
        if cache_key in self.query_cache:
            result, timestamp = self.query_cache[cache_key]
            if (datetime.utcnow() - timestamp).seconds < self.cache_ttl:
                self.logger.debug("Cache hit", cache_key=cache_key)
                return result
            else:
                # Remove expired cache entry
                del self.query_cache[cache_key]
        return None
    
    def _cache_result(self, cache_key: str, result: SearchResult) -> None:
        """Cache search result."""
        # Limit cache size
        if len(self.query_cache) >= 100:
            # Remove oldest entry
            oldest_key = min(self.query_cache.keys(), 
                           key=lambda k: self.query_cache[k][1])
            del self.query_cache[oldest_key]
        
        self.query_cache[cache_key] = (result, datetime.utcnow())
        self.logger.debug("Result cached", cache_key=cache_key)
    
    def clear_cache(self) -> None:
        """Clear search cache."""
        self.query_cache.clear()
        self.logger.info("Search cache cleared")
    
    def get_search_suggestions(self, partial_query: str, limit: int = 10) -> List[str]:
        """Get search suggestions based on partial query."""
        suggestions = []
        
        try:
            with db_manager.get_sqlite_connection() as conn:
                # Get suggestions from paper titles and entity names
                cursor = conn.execute("""
                    SELECT DISTINCT title FROM papers 
                    WHERE title LIKE ? 
                    ORDER BY LENGTH(title)
                    LIMIT ?
                """, (f"%{partial_query}%", limit // 2))
                
                for row in cursor.fetchall():
                    suggestions.append(row[0])
                
                # Get entity suggestions
                cursor = conn.execute("""
                    SELECT DISTINCT entity_text FROM entities 
                    WHERE entity_text LIKE ? 
                    ORDER BY confidence DESC, LENGTH(entity_text)
                    LIMIT ?
                """, (f"%{partial_query}%", limit - len(suggestions)))
                
                for row in cursor.fetchall():
                    if row[0] not in suggestions:
                        suggestions.append(row[0])
        
        except Exception as e:
            self.logger.error("Failed to get search suggestions", 
                            query=partial_query, error=str(e))
        
        return suggestions[:limit]


# Global search engine instance
search_engine = HybridSearchEngine()