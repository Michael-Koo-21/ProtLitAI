"""Competitive intelligence module for tracking organizations and researchers."""

import json
import sqlite3
import re
from typing import List, Dict, Optional, Tuple, Any, Set
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import networkx as nx

from core.database import db_manager
from core.models import Paper, Author, EntityType
from core.repository import paper_repo, entity_repo
from core.logging import get_logger, PerformanceLogger


class CompetitiveIntelligence:
    """Competitive intelligence analysis for organizations and researchers."""
    
    def __init__(self):
        self.logger = get_logger("competitive_intel")
        
        # Common company/institution patterns
        self.company_patterns = [
            r'\b(?:Inc|LLC|Ltd|Corp|Corporation|Company|Co\.)\b',
            r'\b(?:Pharmaceuticals?|Pharma|Biotech|Biotechnology)\b',
            r'\b(?:University|Institute|Laboratory|Lab|Research)\b',
            r'\b(?:Google|Microsoft|Apple|Amazon|Meta|OpenAI)\b',
            r'\b(?:Roche|Novartis|Pfizer|Merck|Johnson|Bristol)\b'
        ]
        
        # Research institution indicators
        self.institution_indicators = [
            'university', 'institute', 'laboratory', 'lab', 'research',
            'hospital', 'medical center', 'clinic', 'college', 'school'
        ]
    
    def track_organization_activity(
        self, 
        organization_name: str,
        time_window_days: int = 365
    ) -> Dict[str, Any]:
        """Track research activity for a specific organization."""
        with PerformanceLogger(self.logger, "track_organization_activity", 
                             org=organization_name):
            
            cutoff_date = datetime.utcnow() - timedelta(days=time_window_days)
            
            # Find papers associated with the organization
            papers = self._find_organization_papers(organization_name, cutoff_date)
            
            if not papers:
                return {
                    'organization': organization_name,
                    'papers_found': 0,
                    'activity_summary': None
                }
            
            # Analyze activity patterns
            activity_analysis = {
                'organization': organization_name,
                'papers_found': len(papers),
                'time_window_days': time_window_days,
                'analysis_date': datetime.utcnow().isoformat(),
                
                # Publication timeline
                'publication_timeline': self._analyze_publication_timeline(papers),
                
                # Research areas
                'research_areas': self._identify_research_areas(papers),
                
                # Collaboration patterns
                'collaborations': self._analyze_collaborations(papers, organization_name),
                
                # Key researchers
                'key_researchers': self._identify_key_researchers(papers),
                
                # Publication venues
                'publication_venues': self._analyze_publication_venues(papers),
                
                # Recent focus
                'recent_trends': self._analyze_recent_trends(papers, days=90)
            }
            
            self.logger.info("Organization activity tracked", 
                           org=organization_name,
                           papers=len(papers))
            
            return activity_analysis
    
    def compare_organizations(
        self, 
        org_names: List[str],
        time_window_days: int = 365
    ) -> Dict[str, Any]:
        """Compare research activity between multiple organizations."""
        with PerformanceLogger(self.logger, "compare_organizations", 
                             orgs=len(org_names)):
            
            # Analyze each organization
            org_data = {}
            for org_name in org_names:
                org_data[org_name] = self.track_organization_activity(
                    org_name, time_window_days
                )
            
            # Comparative analysis
            comparison = {
                'organizations': org_names,
                'time_window_days': time_window_days,
                'analysis_date': datetime.utcnow().isoformat(),
                'individual_analysis': org_data,
                'comparative_metrics': self._generate_comparative_metrics(org_data),
                'competitive_landscape': self._analyze_competitive_landscape(org_data)
            }
            
            return comparison
    
    def identify_emerging_competitors(
        self, 
        research_areas: List[str],
        time_window_days: int = 180,
        min_papers: int = 3
    ) -> List[Dict[str, Any]]:
        """Identify emerging competitors in specific research areas."""
        with PerformanceLogger(self.logger, "identify_emerging_competitors", 
                             areas=len(research_areas)):
            
            cutoff_date = datetime.utcnow() - timedelta(days=time_window_days)
            
            # Find papers in target research areas
            relevant_papers = self._find_papers_by_research_areas(
                research_areas, cutoff_date
            )
            
            # Extract organizations from these papers
            organizations = self._extract_organizations_from_papers(relevant_papers)
            
            # Filter by minimum activity threshold
            active_orgs = {
                org: data for org, data in organizations.items() 
                if data['paper_count'] >= min_papers
            }
            
            # Calculate emergence metrics
            emerging_competitors = []
            for org_name, org_data in active_orgs.items():
                emergence_score = self._calculate_emergence_score(
                    org_data, time_window_days
                )
                
                if emergence_score > 0.3:  # Threshold for "emerging"
                    emerging_competitors.append({
                        'organization': org_name,
                        'paper_count': org_data['paper_count'],
                        'recent_activity': org_data['recent_activity'],
                        'emergence_score': emergence_score,
                        'key_areas': org_data['research_areas'][:5],
                        'growth_trend': org_data['growth_trend']
                    })
            
            # Sort by emergence score
            emerging_competitors.sort(
                key=lambda x: x['emergence_score'], 
                reverse=True
            )
            
            self.logger.info("Emerging competitors identified", 
                           competitors=len(emerging_competitors),
                           research_areas=len(research_areas))
            
            return emerging_competitors[:20]  # Top 20
    
    def analyze_researcher_network(
        self, 
        target_researchers: List[str],
        time_window_days: int = 730  # 2 years
    ) -> Dict[str, Any]:
        """Analyze collaboration networks around target researchers."""
        with PerformanceLogger(self.logger, "analyze_researcher_network", 
                             researchers=len(target_researchers)):
            
            cutoff_date = datetime.utcnow() - timedelta(days=time_window_days)
            
            # Find papers by target researchers
            researcher_papers = {}
            for researcher in target_researchers:
                papers = self._find_researcher_papers(researcher, cutoff_date)
                researcher_papers[researcher] = papers
            
            # Build collaboration network
            network = self._build_collaboration_network(researcher_papers)
            
            # Analyze network properties
            network_analysis = {
                'target_researchers': target_researchers,
                'time_window_days': time_window_days,
                'analysis_date': datetime.utcnow().isoformat(),
                'network_metrics': self._calculate_network_metrics(network),
                'key_collaborators': self._identify_key_collaborators(network),
                'research_clusters': self._identify_research_clusters(network),
                'influence_metrics': self._calculate_influence_metrics(researcher_papers)
            }
            
            return network_analysis
    
    def _find_organization_papers(
        self, 
        organization: str, 
        cutoff_date: datetime
    ) -> List[Paper]:
        """Find papers associated with an organization."""
        papers = []
        
        with db_manager.get_sqlite_connection() as conn:
            conn.row_factory = sqlite3.Row
            
            # Search in authors field (which contains affiliations)
            cursor = conn.execute("""
                SELECT * FROM papers 
                WHERE publication_date >= ? 
                  AND (authors LIKE ? OR authors LIKE ?)
                ORDER BY publication_date DESC
            """, (
                cutoff_date, 
                f"%{organization}%", 
                f"%{organization.lower()}%"
            ))
            
            for row in cursor.fetchall():
                paper = paper_repo._row_to_paper(row)
                
                # Additional validation - check if organization is in affiliations
                if self._validate_organization_affiliation(paper, organization):
                    papers.append(paper)
        
        return papers
    
    def _validate_organization_affiliation(
        self, 
        paper: Paper, 
        organization: str
    ) -> bool:
        """Validate that the organization is actually affiliated with the paper."""
        org_lower = organization.lower()
        
        # Check in authors list
        for author in paper.authors:
            if org_lower in author.lower():
                return True
        
        # Check in abstract/title for institutional mentions
        text_to_check = (paper.title or '') + ' ' + (paper.abstract or '')
        if org_lower in text_to_check.lower():
            return True
        
        return False
    
    def _analyze_publication_timeline(self, papers: List[Paper]) -> Dict[str, Any]:
        """Analyze publication timeline patterns."""
        timeline_data = defaultdict(int)
        
        for paper in papers:
            if paper.publication_date:
                month_key = paper.publication_date.strftime('%Y-%m')
                timeline_data[month_key] += 1
        
        # Calculate trends
        months = sorted(timeline_data.keys())
        if len(months) >= 3:
            recent_months = months[-3:]
            earlier_months = months[:-3] if len(months) > 3 else months[:-1]
            
            recent_avg = sum(timeline_data[m] for m in recent_months) / len(recent_months)
            earlier_avg = sum(timeline_data[m] for m in earlier_months) / len(earlier_months)
            
            trend = "increasing" if recent_avg > earlier_avg else "decreasing"
        else:
            trend = "insufficient_data"
        
        return {
            'monthly_counts': dict(timeline_data),
            'total_months': len(months),
            'trend': trend,
            'peak_month': max(timeline_data.items(), key=lambda x: x[1]) if timeline_data else None
        }
    
    def _identify_research_areas(self, papers: List[Paper]) -> List[Dict[str, Any]]:
        """Identify main research areas from papers."""
        # Extract keywords from titles and abstracts
        text_corpus = []
        for paper in papers:
            text = (paper.title or '') + ' ' + (paper.abstract or '')
            text_corpus.append(text.lower())
        
        # Simple keyword extraction (could be enhanced with NLP)
        research_keywords = Counter()
        protein_terms = ['protein', 'enzyme', 'antibody', 'peptide', 'structure', 'folding']
        method_terms = ['machine learning', 'deep learning', 'ai', 'algorithm', 'prediction']
        bio_terms = ['drug', 'therapeutic', 'disease', 'cancer', 'treatment', 'clinical']
        
        all_terms = protein_terms + method_terms + bio_terms
        
        for text in text_corpus:
            for term in all_terms:
                if term in text:
                    research_keywords[term] += 1
        
        # Group into research areas
        research_areas = []
        if research_keywords:
            top_keywords = research_keywords.most_common(10)
            for keyword, count in top_keywords:
                research_areas.append({
                    'area': keyword,
                    'paper_count': count,
                    'percentage': count / len(papers) * 100
                })
        
        return research_areas
    
    def _analyze_collaborations(
        self, 
        papers: List[Paper], 
        org_name: str
    ) -> Dict[str, Any]:
        """Analyze collaboration patterns."""
        collaborating_orgs = Counter()
        external_authors = set()
        
        for paper in papers:
            # Extract potential collaborating organizations
            for author in paper.authors:
                # Simple heuristic: if author string contains org indicators
                # and it's different from the target org
                author_lower = author.lower()
                if any(indicator in author_lower for indicator in self.institution_indicators):
                    if org_name.lower() not in author_lower:
                        # Extract organization name (simplified)
                        org_match = re.search(r'([^,]+(?:university|institute|lab|hospital))', 
                                            author_lower)
                        if org_match:
                            collaborating_orgs[org_match.group(1).strip()] += 1
                
                # Track external authors
                if org_name.lower() not in author_lower:
                    external_authors.add(author.split(',')[0] if ',' in author else author)
        
        return {
            'collaborating_organizations': dict(collaborating_orgs.most_common(10)),
            'external_author_count': len(external_authors),
            'collaboration_rate': len(collaborating_orgs) / len(papers) if papers else 0
        }
    
    def _identify_key_researchers(self, papers: List[Paper]) -> List[Dict[str, Any]]:
        """Identify key researchers from papers."""
        author_stats = defaultdict(lambda: {'papers': 0, 'first_author': 0, 'last_author': 0})
        
        for paper in papers:
            authors = paper.authors
            if authors:
                # Track all authors
                for author in authors:
                    clean_author = author.split(',')[0] if ',' in author else author
                    author_stats[clean_author]['papers'] += 1
                
                # Track first and last authors (common indicators of seniority)
                if len(authors) > 0:
                    first_author = authors[0].split(',')[0] if ',' in authors[0] else authors[0]
                    author_stats[first_author]['first_author'] += 1
                
                if len(authors) > 1:
                    last_author = authors[-1].split(',')[0] if ',' in authors[-1] else authors[-1]
                    author_stats[last_author]['last_author'] += 1
        
        # Convert to list and sort by paper count
        key_researchers = []
        for author, stats in author_stats.items():
            if stats['papers'] >= 2:  # Minimum threshold
                key_researchers.append({
                    'name': author,
                    'total_papers': stats['papers'],
                    'first_author_papers': stats['first_author'],
                    'last_author_papers': stats['last_author'],
                    'leadership_score': stats['first_author'] + stats['last_author'] * 1.5
                })
        
        key_researchers.sort(key=lambda x: x['total_papers'], reverse=True)
        return key_researchers[:15]  # Top 15
    
    def _analyze_publication_venues(self, papers: List[Paper]) -> Dict[str, Any]:
        """Analyze publication venue preferences."""
        venues = Counter()
        sources = Counter()
        
        for paper in papers:
            if paper.journal:
                venues[paper.journal] += 1
            sources[paper.source] += 1
        
        return {
            'top_journals': dict(venues.most_common(10)),
            'source_distribution': dict(sources),
            'venue_diversity': len(venues)
        }
    
    def _analyze_recent_trends(self, papers: List[Paper], days: int = 90) -> Dict[str, Any]:
        """Analyze recent research trends."""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        recent_papers = [p for p in papers if p.publication_date and p.publication_date >= cutoff_date]
        
        if not recent_papers:
            return {'recent_papers': 0, 'trends': []}
        
        # Analyze recent research areas
        recent_areas = self._identify_research_areas(recent_papers)
        
        return {
            'recent_papers': len(recent_papers),
            'recent_areas': recent_areas[:5],
            'activity_level': len(recent_papers) / (days / 30)  # Papers per month
        }
    
    def _find_papers_by_research_areas(
        self, 
        research_areas: List[str], 
        cutoff_date: datetime
    ) -> List[Paper]:
        """Find papers related to specific research areas."""
        papers = []
        
        # Create search query for research areas
        search_terms = []
        for area in research_areas:
            search_terms.extend(area.lower().split())
        
        # Remove duplicates and common words
        search_terms = list(set(term for term in search_terms 
                              if len(term) > 3 and term not in ['the', 'and', 'for', 'with']))
        
        if not search_terms:
            return papers
        
        with db_manager.get_sqlite_connection() as conn:
            conn.row_factory = sqlite3.Row
            
            # Build query with multiple search terms
            where_conditions = []
            params = [cutoff_date]
            
            for term in search_terms[:5]:  # Limit to first 5 terms
                where_conditions.append("(title LIKE ? OR abstract LIKE ?)")
                params.extend([f"%{term}%", f"%{term}%"])
            
            if where_conditions:
                where_clause = " AND (" + " OR ".join(where_conditions) + ")"
                
                cursor = conn.execute(f"""
                    SELECT * FROM papers 
                    WHERE publication_date >= ? {where_clause}
                    ORDER BY publication_date DESC
                    LIMIT 500
                """, params)
                
                for row in cursor.fetchall():
                    papers.append(paper_repo._row_to_paper(row))
        
        return papers
    
    def _extract_organizations_from_papers(self, papers: List[Paper]) -> Dict[str, Dict[str, Any]]:
        """Extract organizations and their activity metrics from papers."""
        organizations = defaultdict(lambda: {
            'paper_count': 0,
            'papers': [],
            'research_areas': Counter(),
            'recent_activity': 0,
            'monthly_activity': defaultdict(int),
            'growth_trend': 0
        })
        
        recent_cutoff = datetime.utcnow() - timedelta(days=90)
        
        for paper in papers:
            # Extract organization names from author affiliations
            for author in paper.authors:
                orgs = self._extract_org_names_from_author(author)
                
                for org in orgs:
                    org_data = organizations[org]
                    org_data['paper_count'] += 1
                    org_data['papers'].append(paper)
                    
                    # Track recent activity
                    if paper.publication_date and paper.publication_date >= recent_cutoff:
                        org_data['recent_activity'] += 1
                    
                    # Track monthly activity
                    if paper.publication_date:
                        month_key = paper.publication_date.strftime('%Y-%m')
                        org_data['monthly_activity'][month_key] += 1
                    
                    # Extract research areas
                    text = (paper.title or '') + ' ' + (paper.abstract or '')
                    keywords = self._extract_keywords(text)
                    for keyword in keywords:
                        org_data['research_areas'][keyword] += 1
        
        # Calculate growth trends
        for org_name, org_data in organizations.items():
            monthly_data = org_data['monthly_activity']
            if len(monthly_data) >= 3:
                months = sorted(monthly_data.keys())
                recent_months = months[-2:]
                earlier_months = months[:-2]
                
                if earlier_months:
                    recent_avg = sum(monthly_data[m] for m in recent_months) / len(recent_months)
                    earlier_avg = sum(monthly_data[m] for m in earlier_months) / len(earlier_months)
                    
                    org_data['growth_trend'] = (recent_avg - earlier_avg) / earlier_avg if earlier_avg > 0 else 0
        
        return dict(organizations)
    
    def _extract_org_names_from_author(self, author_string: str) -> List[str]:
        """Extract organization names from author affiliation string."""
        orgs = []
        
        # Simple pattern matching for common organization indicators
        for pattern in self.company_patterns:
            matches = re.findall(pattern, author_string, re.IGNORECASE)
            for match in matches:
                # Extract surrounding context as organization name
                org_context = re.search(rf'.{{0,30}}{re.escape(match)}.{{0,30}}', 
                                      author_string, re.IGNORECASE)
                if org_context:
                    org_name = org_context.group().strip()
                    if len(org_name) > 5:  # Minimum length filter
                        orgs.append(org_name)
        
        return orgs
    
    def _extract_keywords(self, text: str, max_keywords: int = 5) -> List[str]:
        """Extract keywords from text."""
        # Simple keyword extraction
        words = re.findall(r'\b\w{4,}\b', text.lower())
        
        # Filter common words and focus on domain-specific terms
        domain_keywords = [
            'protein', 'enzyme', 'antibody', 'peptide', 'structure', 'folding',
            'machine', 'learning', 'algorithm', 'prediction', 'model',
            'drug', 'therapeutic', 'treatment', 'disease', 'clinical'
        ]
        
        relevant_words = [word for word in words if word in domain_keywords]
        word_counts = Counter(relevant_words)
        
        return [word for word, _ in word_counts.most_common(max_keywords)]
    
    def _calculate_emergence_score(
        self, 
        org_data: Dict[str, Any], 
        time_window_days: int
    ) -> float:
        """Calculate emergence score for an organization."""
        # Factors: recent activity, growth trend, research diversity
        
        # Recent activity score (0-1)
        activity_score = min(org_data['recent_activity'] / 10, 1.0)
        
        # Growth trend score (0-1)
        growth_score = max(0, min(org_data['growth_trend'], 1.0))
        
        # Research diversity score (0-1)
        diversity_score = min(len(org_data['research_areas']) / 5, 1.0)
        
        # Volume score (0-1)
        volume_score = min(org_data['paper_count'] / 20, 1.0)
        
        # Weighted combination
        emergence_score = (
            activity_score * 0.3 +
            growth_score * 0.3 +
            diversity_score * 0.2 +
            volume_score * 0.2
        )
        
        return emergence_score
    
    def _find_researcher_papers(self, researcher: str, cutoff_date: datetime) -> List[Paper]:
        """Find papers by a specific researcher."""
        papers = []
        
        with db_manager.get_sqlite_connection() as conn:
            conn.row_factory = sqlite3.Row
            
            cursor = conn.execute("""
                SELECT * FROM papers 
                WHERE publication_date >= ? 
                  AND authors LIKE ?
                ORDER BY publication_date DESC
            """, (cutoff_date, f"%{researcher}%"))
            
            for row in cursor.fetchall():
                paper = paper_repo._row_to_paper(row)
                # Validate that the researcher is actually an author
                if any(researcher.lower() in author.lower() for author in paper.authors):
                    papers.append(paper)
        
        return papers
    
    def _build_collaboration_network(
        self, 
        researcher_papers: Dict[str, List[Paper]]
    ) -> nx.Graph:
        """Build collaboration network graph."""
        network = nx.Graph()
        
        for researcher, papers in researcher_papers.items():
            network.add_node(researcher, papers=len(papers))
            
            for paper in papers:
                for author in paper.authors:
                    clean_author = author.split(',')[0] if ',' in author else author
                    if clean_author != researcher:
                        network.add_node(clean_author)
                        
                        if network.has_edge(researcher, clean_author):
                            network[researcher][clean_author]['weight'] += 1
                        else:
                            network.add_edge(researcher, clean_author, weight=1)
        
        return network
    
    def _calculate_network_metrics(self, network: nx.Graph) -> Dict[str, Any]:
        """Calculate network analysis metrics."""
        metrics = {
            'total_nodes': network.number_of_nodes(),
            'total_edges': network.number_of_edges(),
            'density': nx.density(network),
            'average_clustering': nx.average_clustering(network) if network.number_of_nodes() > 2 else 0
        }
        
        if network.number_of_nodes() > 0:
            # Centrality measures
            degree_centrality = nx.degree_centrality(network)
            betweenness_centrality = nx.betweenness_centrality(network)
            
            metrics['most_connected'] = max(degree_centrality.items(), key=lambda x: x[1])
            metrics['most_influential'] = max(betweenness_centrality.items(), key=lambda x: x[1])
        
        return metrics
    
    def _identify_key_collaborators(self, network: nx.Graph) -> List[Dict[str, Any]]:
        """Identify key collaborators in the network."""
        collaborators = []
        
        degree_centrality = nx.degree_centrality(network)
        betweenness_centrality = nx.betweenness_centrality(network)
        
        for node in network.nodes():
            collaborators.append({
                'name': node,
                'connections': network.degree(node),
                'degree_centrality': degree_centrality[node],
                'betweenness_centrality': betweenness_centrality[node],
                'papers': network.nodes[node].get('papers', 0)
            })
        
        collaborators.sort(key=lambda x: x['degree_centrality'], reverse=True)
        return collaborators[:20]
    
    def _identify_research_clusters(self, network: nx.Graph) -> List[Dict[str, Any]]:
        """Identify research clusters in the collaboration network."""
        if network.number_of_nodes() < 3:
            return []
        
        try:
            # Use community detection
            communities = nx.community.greedy_modularity_communities(network)
            
            clusters = []
            for i, community in enumerate(communities):
                if len(community) >= 3:  # Minimum cluster size
                    clusters.append({
                        'cluster_id': i,
                        'size': len(community),
                        'members': list(community)
                    })
            
            return clusters
        except:
            return []
    
    def _calculate_influence_metrics(
        self, 
        researcher_papers: Dict[str, List[Paper]]
    ) -> Dict[str, Any]:
        """Calculate influence metrics for researchers."""
        influence_metrics = {}
        
        for researcher, papers in researcher_papers.items():
            metrics = {
                'total_papers': len(papers),
                'recent_papers': len([p for p in papers 
                                    if p.publication_date and 
                                    p.publication_date >= datetime.utcnow() - timedelta(days=365)]),
                'avg_relevance': sum([p.relevance_score for p in papers 
                                        if p.relevance_score]) / len([p for p in papers if p.relevance_score]) if any(p.relevance_score for p in papers) else 0,
                'publication_span_days': 0
            }
            
            # Calculate publication span
            if papers:
                dates = [p.publication_date for p in papers if p.publication_date]
                if len(dates) > 1:
                    metrics['publication_span_days'] = (max(dates) - min(dates)).days
            
            influence_metrics[researcher] = metrics
        
        return influence_metrics
    
    def _generate_comparative_metrics(
        self, 
        org_data: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate comparative metrics between organizations."""
        metrics = {
            'publication_counts': {},
            'research_focus_overlap': {},
            'activity_trends': {}
        }
        
        for org_name, data in org_data.items():
            metrics['publication_counts'][org_name] = data['papers_found']
            
            if 'recent_trends' in data and 'activity_level' in data['recent_trends']:
                metrics['activity_trends'][org_name] = data['recent_trends']['activity_level']
        
        return metrics
    
    def _analyze_competitive_landscape(
        self, 
        org_data: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze competitive landscape between organizations."""
        landscape = {
            'market_leaders': [],
            'emerging_players': [],
            'collaboration_opportunities': []
        }
        
        # Identify market leaders (high publication volume)
        for org_name, data in org_data.items():
            paper_count = data['papers_found']
            if paper_count > 20:  # Threshold for market leader
                landscape['market_leaders'].append({
                    'organization': org_name,
                    'papers': paper_count
                })
        
        return landscape


# Global competitive intelligence instance
competitive_intel = CompetitiveIntelligence()