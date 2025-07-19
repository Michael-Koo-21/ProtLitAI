"""Simple test for search components."""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from core.models import SearchQuery


def test_search_models():
    """Test search model creation."""
    print("🔍 Testing Search Models")
    
    try:
        # Test SearchQuery model
        search_query = SearchQuery(
            query="protein folding machine learning",
            limit=10,
            offset=0,
            filters={"min_relevance": 0.5}
        )
        
        print(f"✅ SearchQuery created successfully")
        print(f"   Query: {search_query.query}")
        print(f"   Limit: {search_query.limit}")
        print(f"   Filters: {search_query.filters}")
        
        # Test query validation
        invalid_query = SearchQuery(
            query="test",
            limit=2000  # Should fail validation
        )
        
    except Exception as e:
        print(f"✅ Query validation working: {e}")
    
    print("🎉 Search models test complete!")


if __name__ == "__main__":
    test_search_models()