"""Trend analysis system for identifying emerging research directions."""

import json
import sqlite3
import numpy as np
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
from scipy import stats

from core.database import db_manager
from core.models import Paper, Trend, EntityType
from core.repository import paper_repo, entity_repo
from core.logging import get_logger, PerformanceLogger


class TrendAnalyzer:
    """Advanced trend analysis for research literature."""
    
    def __init__(self):
        self.logger = get_logger("trend_analyzer")
        self.min_papers_for_trend = 5
        self.trend_cache = {}
        self.cache_ttl = 3600  # 1 hour
    
    def analyze_temporal_trends(
        self, 
        time_window_days: int = 90,
        min_growth_rate: float = 0.1
    ) -> List[Dict[str, Any]]:
        """Analyze temporal trends in research topics."""
        with PerformanceLogger(self.logger, "analyze_temporal_trends", 
                             window_days=time_window_days):
            
            # Get papers from the specified time window
            cutoff_date = datetime.utcnow() - timedelta(days=time_window_days)
            papers = self._get_papers_since(cutoff_date)
            
            if len(papers) < self.min_papers_for_trend:
                self.logger.warning("Insufficient papers for trend analysis", 
                                  paper_count=len(papers))
                return []
            
            # Group papers by time periods (weekly)
            time_series = self._group_papers_by_time(papers, period_days=7)
            
            # Extract topics for each time period
            topic_evolution = self._track_topic_evolution(time_series)
            
            # Identify trending topics
            trends = self._identify_trending_topics(
                topic_evolution, 
                min_growth_rate=min_growth_rate
            )
            
            # Calculate statistical significance
            significant_trends = self._validate_trend_significance(trends)
            
            self.logger.info("Temporal trend analysis completed", 
                           total_trends=len(significant_trends),
                           time_window=time_window_days)
            
            return significant_trends
    
    def analyze_entity_trends(
        self, 
        entity_type: Optional[EntityType] = None,
        time_window_days: int = 180
    ) -> List[Dict[str, Any]]:
        """Analyze trends in specific entity types (proteins, methods, etc.)."""
        with PerformanceLogger(self.logger, "analyze_entity_trends", 
                             entity_type=entity_type):
            
            cutoff_date = datetime.utcnow() - timedelta(days=time_window_days)
            
            # Get entity trends from database
            with db_manager.get_sqlite_connection() as conn:
                # Query for entity frequencies over time
                where_clause = "WHERE p.publication_date >= ?"
                params = [cutoff_date]
                
                if entity_type:
                    where_clause += " AND e.entity_type = ?"
                    params.append(entity_type.value if hasattr(entity_type, 'value') else entity_type)
                
                cursor = conn.execute(f"""
                    SELECT 
                        e.entity_text,
                        e.entity_type,
                        DATE(p.publication_date) as pub_date,
                        COUNT(*) as frequency,
                        AVG(e.confidence) as avg_confidence
                    FROM entities e
                    JOIN papers p ON e.paper_id = p.id
                    {where_clause}
                    GROUP BY e.entity_text, e.entity_type, DATE(p.publication_date)
                    HAVING COUNT(*) >= 2
                    ORDER BY pub_date, frequency DESC
                """, params)
                
                entity_data = cursor.fetchall()
            
            # Analyze trends for each entity
            entity_trends = self._analyze_entity_time_series(entity_data)
            
            # Rank by trend strength
            ranked_trends = sorted(
                entity_trends, 
                key=lambda x: x['trend_score'], 
                reverse=True
            )
            
            self.logger.info("Entity trend analysis completed", 
                           entity_type=entity_type,
                           trends_found=len(ranked_trends))
            
            return ranked_trends[:50]  # Return top 50 trends
    
    def analyze_competitive_landscape(
        self, 
        time_window_days: int = 365
    ) -> Dict[str, Any]:
        """Analyze competitive landscape and institutional trends."""
        with PerformanceLogger(self.logger, "analyze_competitive_landscape"):
            
            cutoff_date = datetime.utcnow() - timedelta(days=time_window_days)
            
            # Analyze institutional publication patterns
            institution_trends = self._analyze_institutional_trends(cutoff_date)
            
            # Analyze collaboration networks
            collaboration_trends = self._analyze_collaboration_trends(cutoff_date)
            
            # Analyze research focus shifts
            focus_trends = self._analyze_research_focus_trends(cutoff_date)
            
            competitive_analysis = {
                'institutional_trends': institution_trends,
                'collaboration_trends': collaboration_trends,
                'research_focus_trends': focus_trends,
                'analysis_date': datetime.utcnow().isoformat(),
                'time_window_days': time_window_days
            }
            
            self.logger.info("Competitive landscape analysis completed")
            
            return competitive_analysis
    
    def generate_trend_report(
        self, 
        include_entities: bool = True,
        include_competitive: bool = True,
        time_window_days: int = 90
    ) -> Dict[str, Any]:
        """Generate comprehensive trend analysis report."""
        with PerformanceLogger(self.logger, "generate_trend_report"):
            
            report = {
                'generated_at': datetime.utcnow().isoformat(),
                'time_window_days': time_window_days,
                'summary': {}
            }
            
            # Temporal trends
            temporal_trends = self.analyze_temporal_trends(time_window_days)
            report['temporal_trends'] = temporal_trends
            report['summary']['temporal_trends_count'] = len(temporal_trends)
            
            # Entity trends
            if include_entities:
                entity_trends = {}
                for entity_type in EntityType:
                    trends = self.analyze_entity_trends(entity_type, time_window_days)
                    if trends:
                        entity_trends[entity_type.value] = trends[:10]  # Top 10 per type
                
                report['entity_trends'] = entity_trends
                report['summary']['entity_types_analyzed'] = len(entity_trends)
            
            # Competitive analysis
            if include_competitive:
                competitive_data = self.analyze_competitive_landscape(time_window_days)
                report['competitive_landscape'] = competitive_data
            
            # Generate insights
            report['insights'] = self._generate_insights(report)
            
            self.logger.info("Comprehensive trend report generated", 
                           temporal_trends=len(temporal_trends),
                           includes_entities=include_entities,
                           includes_competitive=include_competitive)
            
            return report
    
    def _get_papers_since(self, cutoff_date: datetime) -> List[Paper]:
        """Get papers published since cutoff date."""
        with db_manager.get_sqlite_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM papers 
                WHERE publication_date >= ? 
                  AND full_text IS NOT NULL 
                  AND full_text != ''
                ORDER BY publication_date DESC
            """, (cutoff_date,))
            
            papers = []
            for row in cursor.fetchall():
                papers.append(paper_repo._row_to_paper(row))
            
            return papers
    
    def _group_papers_by_time(
        self, 
        papers: List[Paper], 
        period_days: int = 7
    ) -> Dict[str, List[Paper]]:
        """Group papers by time periods."""
        time_groups = defaultdict(list)
        
        for paper in papers:
            if paper.publication_date:
                # Calculate period start date
                days_since_epoch = (paper.publication_date - datetime(1970, 1, 1)).days
                period_start = days_since_epoch // period_days * period_days
                period_key = str(datetime(1970, 1, 1) + timedelta(days=period_start))
                
                time_groups[period_key].append(paper)
        
        return dict(time_groups)
    
    def _track_topic_evolution(
        self, 
        time_series: Dict[str, List[Paper]]
    ) -> Dict[str, Dict[str, Any]]:
        """Track how topics evolve over time."""
        topic_evolution = {}
        
        for period, papers in time_series.items():
            if len(papers) < 3:  # Skip periods with too few papers
                continue
            
            # Extract topics using TF-IDF and clustering
            texts = []
            for paper in papers:
                # Combine title and abstract for topic modeling
                text = (paper.title or '') + ' ' + (paper.abstract or '')
                if text.strip():
                    texts.append(text.strip())
            
            if len(texts) < 3:
                continue
            
            # TF-IDF vectorization
            vectorizer = TfidfVectorizer(
                max_features=100,
                stop_words='english',
                ngram_range=(1, 2),
                min_df=2
            )
            
            try:
                tfidf_matrix = vectorizer.fit_transform(texts)
                feature_names = vectorizer.get_feature_names_out()
                
                # Simple clustering to identify topics
                n_clusters = min(5, len(texts) // 2)
                if n_clusters >= 2:
                    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
                    clusters = kmeans.fit_predict(tfidf_matrix)
                    
                    # Extract top terms for each cluster
                    topics = []
                    for i in range(n_clusters):
                        cluster_center = kmeans.cluster_centers_[i]
                        top_indices = cluster_center.argsort()[-10:][::-1]
                        top_terms = [feature_names[idx] for idx in top_indices]
                        
                        # Calculate topic strength
                        cluster_papers = [papers[j] for j, c in enumerate(clusters) if c == i]
                        topic_strength = len(cluster_papers) / len(papers)
                        
                        topics.append({
                            'terms': top_terms,
                            'strength': topic_strength,
                            'paper_count': len(cluster_papers)
                        })
                    
                    topic_evolution[period] = {
                        'topics': topics,
                        'total_papers': len(papers),
                        'period_date': period
                    }
            
            except Exception as e:
                self.logger.debug("Topic extraction failed for period", 
                                period=period, error=str(e))
        
        return topic_evolution
    
    def _identify_trending_topics(
        self, 
        topic_evolution: Dict[str, Dict[str, Any]],
        min_growth_rate: float = 0.1
    ) -> List[Dict[str, Any]]:
        """Identify topics with significant growth trends."""
        trending_topics = []
        
        # Group by similar topics across time periods
        topic_time_series = defaultdict(list)
        
        for period, period_data in topic_evolution.items():
            period_date = datetime.fromisoformat(period)
            
            for topic in period_data['topics']:
                # Create a simple topic signature from top terms
                topic_signature = ' '.join(topic['terms'][:3])
                
                topic_time_series[topic_signature].append({
                    'date': period_date,
                    'strength': topic['strength'],
                    'paper_count': topic['paper_count'],
                    'terms': topic['terms']
                })
        
        # Analyze trends for each topic
        for topic_signature, time_points in topic_time_series.items():
            if len(time_points) < 3:  # Need at least 3 time points
                continue
            
            # Sort by date
            time_points.sort(key=lambda x: x['date'])
            
            # Calculate trend
            dates = [(tp['date'] - time_points[0]['date']).days for tp in time_points]
            strengths = [tp['strength'] for tp in time_points]
            
            if len(dates) >= 3:
                # Linear regression for trend
                slope, intercept, r_value, p_value, std_err = stats.linregress(dates, strengths)
                
                if slope > min_growth_rate and p_value < 0.05:
                    trending_topics.append({
                        'topic_signature': topic_signature,
                        'terms': time_points[-1]['terms'][:10],  # Latest terms
                        'growth_rate': slope,
                        'r_squared': r_value ** 2,
                        'p_value': p_value,
                        'recent_strength': time_points[-1]['strength'],
                        'recent_paper_count': time_points[-1]['paper_count'],
                        'trend_score': slope * (r_value ** 2) * (1 - p_value)
                    })
        
        return trending_topics
    
    def _validate_trend_significance(
        self, 
        trends: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Validate statistical significance of trends."""
        significant_trends = []
        
        for trend in trends:
            # Apply multiple criteria for significance
            is_significant = (
                trend['p_value'] < 0.05 and  # Statistical significance
                trend['r_squared'] > 0.3 and  # Good fit
                trend['recent_paper_count'] >= self.min_papers_for_trend  # Sufficient volume
            )
            
            if is_significant:
                # Add significance confidence score
                confidence = (
                    (1 - trend['p_value']) * 0.4 +  # Statistical confidence
                    trend['r_squared'] * 0.3 +       # Fit quality
                    min(trend['recent_paper_count'] / 20, 1.0) * 0.3  # Volume confidence
                )
                
                trend['significance_confidence'] = confidence
                significant_trends.append(trend)
        
        return significant_trends
    
    def _analyze_entity_time_series(
        self, 
        entity_data: List[Tuple]
    ) -> List[Dict[str, Any]]:
        """Analyze time series data for entities."""
        entity_trends = []
        
        # Group by entity
        entity_groups = defaultdict(list)
        for row in entity_data:
            entity_key = (row[0], row[1])  # (entity_text, entity_type)
            entity_groups[entity_key].append({
                'date': datetime.fromisoformat(row[2]),
                'frequency': row[3],
                'confidence': row[4]
            })
        
        # Analyze trend for each entity
        for (entity_text, entity_type), time_points in entity_groups.items():
            if len(time_points) < 3:
                continue
            
            # Sort by date
            time_points.sort(key=lambda x: x['date'])
            
            # Calculate trend metrics
            dates = [(tp['date'] - time_points[0]['date']).days for tp in time_points]
            frequencies = [tp['frequency'] for tp in time_points]
            
            if len(dates) >= 3:
                slope, intercept, r_value, p_value, std_err = stats.linregress(dates, frequencies)
                
                # Calculate additional metrics
                total_mentions = sum(frequencies)
                recent_frequency = np.mean(frequencies[-3:])  # Last 3 data points
                avg_confidence = np.mean([tp['confidence'] for tp in time_points])
                
                # Trend score combining multiple factors
                trend_score = (
                    slope * 0.4 +  # Growth rate
                    (r_value ** 2) * 0.3 +  # Fit quality
                    (recent_frequency / max(frequencies)) * 0.2 +  # Recent activity
                    avg_confidence * 0.1  # Confidence in extractions
                )
                
                entity_trends.append({
                    'entity_text': entity_text,
                    'entity_type': entity_type,
                    'growth_rate': slope,
                    'r_squared': r_value ** 2,
                    'p_value': p_value,
                    'total_mentions': total_mentions,
                    'recent_frequency': recent_frequency,
                    'avg_confidence': avg_confidence,
                    'trend_score': trend_score,
                    'time_span_days': max(dates),
                    'data_points': len(time_points)
                })
        
        return entity_trends
    
    def _analyze_institutional_trends(self, cutoff_date: datetime) -> List[Dict[str, Any]]:
        """Analyze publication trends by institution."""
        # This would analyze author affiliations to identify institutional trends
        # For now, return placeholder data
        return []
    
    def _analyze_collaboration_trends(self, cutoff_date: datetime) -> Dict[str, Any]:
        """Analyze collaboration network trends."""
        # This would analyze co-authorship patterns
        # For now, return placeholder data
        return {}
    
    def _analyze_research_focus_trends(self, cutoff_date: datetime) -> List[Dict[str, Any]]:
        """Analyze shifts in research focus areas."""
        # This would analyze changes in research themes over time
        # For now, return placeholder data
        return []
    
    def _generate_insights(self, report: Dict[str, Any]) -> List[str]:
        """Generate human-readable insights from trend analysis."""
        insights = []
        
        # Insights from temporal trends
        temporal_trends = report.get('temporal_trends', [])
        if temporal_trends:
            top_trend = max(temporal_trends, key=lambda x: x['trend_score'])
            insights.append(
                f"Fastest growing research area: '{' '.join(top_trend['terms'][:3])}' "
                f"with {top_trend['growth_rate']:.2%} growth rate"
            )
        
        # Insights from entity trends
        entity_trends = report.get('entity_trends', {})
        for entity_type, trends in entity_trends.items():
            if trends:
                top_entity = trends[0]
                insights.append(
                    f"Trending {entity_type}: '{top_entity['entity_text']}' "
                    f"({top_entity['total_mentions']} mentions, "
                    f"{top_entity['growth_rate']:.1f} growth rate)"
                )
        
        # Summary insights
        if len(temporal_trends) > 5:
            insights.append(f"Identified {len(temporal_trends)} significant emerging trends")
        
        return insights


# Global trend analyzer instance
trend_analyzer = TrendAnalyzer()