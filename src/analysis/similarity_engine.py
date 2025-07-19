"""Similarity search engine for semantic paper matching."""

import numpy as np
import sqlite3
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime
from sklearn.metrics.pairwise import cosine_similarity

from core.database import db_manager
from core.models import Paper, SearchQuery, SearchResult, Embedding
from core.repository import paper_repo, embedding_repo
from core.logging import get_logger, PerformanceLogger


class SimilarityEngine:
    """Semantic similarity search engine."""
    
    def __init__(self):
        self.logger = get_logger("similarity_engine")
        self._embedding_cache = {}
        self._cache_size_limit = 1000
    
    def find_similar_papers(
        self, 
        paper_id: str, 
        limit: int = 10,
        threshold: float = 0.5
    ) -> List[Tuple[Paper, float]]:
        """Find papers similar to the given paper."""
        with PerformanceLogger(self.logger, "find_similar_papers", 
                             paper_id=paper_id, limit=limit):
            
            # Get query paper embedding
            query_embedding = embedding_repo.get_by_paper(paper_id)
            if not query_embedding:
                self.logger.warning("No embedding found", paper_id=paper_id)
                return []
            
            # Get all embeddings (with caching)
            all_embeddings = self._get_all_embeddings()
            if not all_embeddings:
                return []
            
            # Calculate similarities
            query_vector = np.array(query_embedding.embedding).reshape(1, -1)
            embedding_matrix = np.array([emb["vector"] for emb in all_embeddings])
            
            similarities = cosine_similarity(query_vector, embedding_matrix)[0]
            
            # Filter and sort results
            results = []
            for i, (similarity, embedding_data) in enumerate(zip(similarities, all_embeddings)):
                if (similarity >= threshold and 
                    embedding_data["paper_id"] != paper_id):
                    
                    paper = paper_repo.get_by_id(embedding_data["paper_id"])
                    if paper:
                        results.append((paper, float(similarity)))
            
            # Sort by similarity score (descending)
            results.sort(key=lambda x: x[1], reverse=True)
            
            self.logger.info("Similar papers found", 
                           query_paper=paper_id, 
                           results_count=len(results[:limit]))
            
            return results[:limit]
    
    def semantic_search(
        self, 
        query_vector: List[float], 
        limit: int = 50,
        threshold: float = 0.3
    ) -> List[Tuple[Paper, float]]:
        """Perform semantic search using query vector."""
        with PerformanceLogger(self.logger, "semantic_search", limit=limit):
            
            # Get all embeddings
            all_embeddings = self._get_all_embeddings()
            if not all_embeddings:
                return []
            
            # Calculate similarities
            query_vector_np = np.array(query_vector).reshape(1, -1)
            embedding_matrix = np.array([emb["vector"] for emb in all_embeddings])
            
            similarities = cosine_similarity(query_vector_np, embedding_matrix)[0]
            
            # Filter and collect results
            results = []
            for similarity, embedding_data in zip(similarities, all_embeddings):
                if similarity >= threshold:
                    paper = paper_repo.get_by_id(embedding_data["paper_id"])
                    if paper:
                        results.append((paper, float(similarity)))
            
            # Sort by similarity score (descending)
            results.sort(key=lambda x: x[1], reverse=True)
            
            self.logger.info("Semantic search completed", 
                           results_count=len(results[:limit]),
                           threshold=threshold)
            
            return results[:limit]
    
    def get_embedding_statistics(self) -> Dict[str, Any]:
        """Get embedding collection statistics."""
        with db_manager.get_sqlite_connection() as conn:
            stats = {}
            
            # Total embeddings
            stats["total_embeddings"] = conn.execute(
                "SELECT COUNT(*) FROM embeddings"
            ).fetchone()[0]
            
            # Embeddings by model version
            model_stats = conn.execute("""
                SELECT model_version, COUNT(*) as count 
                FROM embeddings 
                GROUP BY model_version
            """).fetchall()
            stats["by_model"] = {row[0]: row[1] for row in model_stats}
            
            # Recent embeddings (last 7 days)
            stats["recent_count"] = conn.execute("""
                SELECT COUNT(*) FROM embeddings 
                WHERE created_at >= datetime('now', '-7 days')
            """).fetchone()[0]
            
            return stats
    
    def _get_all_embeddings(self) -> List[Dict[str, Any]]:
        """Get all embeddings with caching."""
        cache_key = "all_embeddings"
        
        if cache_key in self._embedding_cache:
            cached_data, timestamp = self._embedding_cache[cache_key]
            # Cache valid for 1 hour
            if (datetime.utcnow() - timestamp).seconds < 3600:
                return cached_data
        
        # Fetch from database
        embeddings = []
        with db_manager.get_sqlite_connection() as conn:
            conn.row_factory = sqlite3.Row
            results = conn.execute("""
                SELECT paper_id, embedding, model_version 
                FROM embeddings
            """).fetchall()
            
            for row in results:
                # Deserialize embedding
                embedding_array = np.frombuffer(row["embedding"], dtype=np.float32)
                embeddings.append({
                    "paper_id": row["paper_id"],
                    "vector": embedding_array,
                    "model_version": row["model_version"]
                })
        
        # Update cache
        self._embedding_cache[cache_key] = (embeddings, datetime.utcnow())
        
        # Manage cache size
        if len(self._embedding_cache) > self._cache_size_limit:
            # Remove oldest entry
            oldest_key = min(self._embedding_cache.keys(), 
                           key=lambda k: self._embedding_cache[k][1])
            del self._embedding_cache[oldest_key]
        
        self.logger.debug("Embeddings loaded", count=len(embeddings))
        return embeddings
    
    def clear_cache(self) -> None:
        """Clear the embedding cache."""
        self._embedding_cache.clear()
        self.logger.info("Embedding cache cleared")
    
    def recommend_papers(
        self, 
        user_history: List[str], 
        limit: int = 20,
        diversity_factor: float = 0.3
    ) -> List[Tuple[Paper, float]]:
        """Recommend papers based on user reading history."""
        with PerformanceLogger(self.logger, "recommend_papers", 
                             history_size=len(user_history), limit=limit):
            
            if not user_history:
                # Return recent high-relevance papers
                papers = paper_repo.get_recent(limit=limit)
                return [(paper, 1.0) for paper in papers if paper.relevance_score and paper.relevance_score > 0.7]
            
            # Get embeddings for user history
            history_embeddings = []
            for paper_id in user_history:
                embedding = embedding_repo.get_by_paper(paper_id)
                if embedding:
                    history_embeddings.append(np.array(embedding.embedding))
            
            if not history_embeddings:
                return []
            
            # Create user profile vector (average of history)
            user_profile = np.mean(history_embeddings, axis=0)
            
            # Find similar papers
            candidates = self.semantic_search(
                query_vector=user_profile.tolist(),
                limit=limit * 3,  # Get more candidates for diversity
                threshold=0.2
            )
            
            # Apply diversity filtering
            recommendations = self._apply_diversity_filter(
                candidates, 
                limit=limit,
                diversity_factor=diversity_factor
            )
            
            self.logger.info("Recommendations generated", 
                           user_history_size=len(user_history),
                           recommendations_count=len(recommendations))
            
            return recommendations
    
    def _apply_diversity_filter(
        self, 
        candidates: List[Tuple[Paper, float]], 
        limit: int,
        diversity_factor: float
    ) -> List[Tuple[Paper, float]]:
        """Apply diversity filtering to recommendations."""
        if len(candidates) <= limit:
            return candidates
        
        selected = []
        remaining = candidates.copy()
        
        # Always select the top candidate
        if remaining:
            selected.append(remaining.pop(0))
        
        while len(selected) < limit and remaining:
            best_score = -1
            best_idx = -1
            
            for i, (candidate_paper, similarity) in enumerate(remaining):
                # Calculate diversity score
                diversity_score = self._calculate_diversity_score(
                    candidate_paper, [paper for paper, _ in selected]
                )
                
                # Combined score: similarity + diversity
                combined_score = (1 - diversity_factor) * similarity + diversity_factor * diversity_score
                
                if combined_score > best_score:
                    best_score = combined_score
                    best_idx = i
            
            if best_idx >= 0:
                selected.append(remaining.pop(best_idx))
            else:
                break
        
        return selected
    
    def _calculate_diversity_score(self, candidate: Paper, selected: List[Paper]) -> float:
        """Calculate diversity score for a candidate paper."""
        if not selected:
            return 1.0
        
        # Simple diversity based on journal and author overlap
        diversity_score = 1.0
        
        for selected_paper in selected:
            # Journal diversity
            if candidate.journal and selected_paper.journal:
                if candidate.journal == selected_paper.journal:
                    diversity_score *= 0.8
            
            # Author diversity
            if candidate.authors and selected_paper.authors:
                common_authors = set(candidate.authors) & set(selected_paper.authors)
                if common_authors:
                    diversity_score *= (1 - len(common_authors) / max(len(candidate.authors), len(selected_paper.authors)))
        
        return max(diversity_score, 0.1)  # Minimum diversity score


# Global similarity engine instance
similarity_engine = SimilarityEngine()