"""Test script for search and analytics components."""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from datetime import datetime, timedelta
from core.models import SearchQuery, Paper, SourceType, PaperType, ProcessingStatus
from core.repository import paper_repo
from analysis import search_engine, similarity_engine, trend_analyzer, competitive_intel


def test_search_and_analytics():
    """Test search and analytics functionality."""
    print("🔍 Testing Search and Analytics Components")
    print("=" * 60)
    
    # Test 1: Basic search functionality
    print("\n1. Testing Hybrid Search Engine")
    try:
        search_query = SearchQuery(
            query="protein folding machine learning",
            limit=10
        )
        
        result = search_engine.search(search_query)
        print(f"   ✅ Search completed in {result.query_time:.3f}s")
        print(f"   ✅ Found {result.total_count} total results")
        print(f"   ✅ Returned {len(result.papers)} papers")
        print(f"   ✅ Generated {len(result.facets)} facet categories")
        
    except Exception as e:
        print(f"   ❌ Search engine test failed: {e}")
    
    # Test 2: Search suggestions
    print("\n2. Testing Search Suggestions")
    try:
        suggestions = search_engine.get_search_suggestions("protein", limit=5)
        print(f"   ✅ Generated {len(suggestions)} search suggestions")
        if suggestions:
            print(f"   ✅ Sample suggestions: {suggestions[:3]}")
        
    except Exception as e:
        print(f"   ❌ Search suggestions test failed: {e}")
    
    # Test 3: Similarity engine
    print("\n3. Testing Similarity Engine")
    try:
        # Get embedding statistics
        stats = similarity_engine.get_embedding_statistics()
        print(f"   ✅ Embedding statistics: {stats}")
        
        # Test recommendations (with empty history)
        recommendations = similarity_engine.recommend_papers([], limit=5)
        print(f"   ✅ Generated {len(recommendations)} recommendations")
        
    except Exception as e:
        print(f"   ❌ Similarity engine test failed: {e}")
    
    # Test 4: Trend analysis
    print("\n4. Testing Trend Analyzer")
    try:
        # Analyze temporal trends
        trends = trend_analyzer.analyze_temporal_trends(time_window_days=180)
        print(f"   ✅ Identified {len(trends)} temporal trends")
        
        # Generate trend report
        report = trend_analyzer.generate_trend_report(
            include_entities=False,  # Skip entity analysis for now
            include_competitive=False,  # Skip competitive analysis for now
            time_window_days=90
        )
        print(f"   ✅ Generated trend report with {len(report.get('insights', []))} insights")
        
    except Exception as e:
        print(f"   ❌ Trend analyzer test failed: {e}")
    
    # Test 5: Competitive intelligence
    print("\n5. Testing Competitive Intelligence")
    try:
        # Test organization tracking (with sample org)
        org_activity = competitive_intel.track_organization_activity(
            "University", 
            time_window_days=365
        )
        print(f"   ✅ Tracked organization activity: {org_activity['papers_found']} papers found")
        
        # Test emerging competitors identification
        emerging = competitive_intel.identify_emerging_competitors(
            ["protein design", "machine learning"],
            time_window_days=180
        )
        print(f"   ✅ Identified {len(emerging)} emerging competitors")
        
    except Exception as e:
        print(f"   ❌ Competitive intelligence test failed: {e}")
    
    # Test 6: Database integration
    print("\n6. Testing Database Integration")
    try:
        # Get paper statistics
        stats = paper_repo.get_statistics()
        print(f"   ✅ Database statistics: {stats}")
        
        # Test recent papers retrieval
        recent_papers = paper_repo.get_recent(limit=5)
        print(f"   ✅ Retrieved {len(recent_papers)} recent papers")
        
    except Exception as e:
        print(f"   ❌ Database integration test failed: {e}")
    
    print("\n" + "=" * 60)
    print("🎉 Search and Analytics Testing Complete!")


if __name__ == "__main__":
    test_search_and_analytics()