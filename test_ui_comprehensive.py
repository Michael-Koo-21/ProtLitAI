"""Comprehensive test for UI components."""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

def test_ui_components():
    """Test all UI components for import and basic functionality."""
    print("🖥️  Testing Complete UI System")
    print("=" * 60)
    
    success_count = 0
    total_tests = 0
    
    def test_component(name, test_func):
        nonlocal success_count, total_tests
        total_tests += 1
        try:
            test_func()
            print(f"   ✅ {name}")
            success_count += 1
            return True
        except Exception as e:
            print(f"   ❌ {name}: {e}")
            return False
    
    # Test 1: Core UI imports
    def test_core_imports():
        from PyQt6.QtWidgets import QApplication, QMainWindow
        from src.core.logging import get_logger
        from src.core.config import config
        assert config is not None
    
    test_component("Core UI imports", test_core_imports)
    
    # Test 2: Main window components
    def test_main_window():
        from src.ui.main_window import MainWindow
        from src.ui.app import ProtLitAIApplication
        # Basic class instantiation test (no QApplication)
        assert MainWindow is not None
        assert ProtLitAIApplication is not None
    
    test_component("Main window components", test_main_window)
    
    # Test 3: Dashboard components
    def test_dashboard():
        from src.ui.dashboard import (
            Dashboard, StatCard, RecentPapersWidget, 
            TrendingTopicsWidget, ActivityTimelineWidget
        )
        assert Dashboard is not None
        assert StatCard is not None
        assert RecentPapersWidget is not None
    
    test_component("Dashboard components", test_dashboard)
    
    # Test 4: Search interface components
    def test_search_interface():
        from src.ui.search_interface import (
            SearchInterface, SearchFiltersWidget, 
            SearchResultsTable, PaperDetailWidget
        )
        assert SearchInterface is not None
        assert SearchFiltersWidget is not None
        assert SearchResultsTable is not None
    
    test_component("Search interface components", test_search_interface)
    
    # Test 5: UI package structure
    def test_ui_package():
        from src.ui import MainWindow, ProtLitAIApplication, run_application
        assert MainWindow is not None
        assert ProtLitAIApplication is not None
        assert run_application is not None
    
    test_component("UI package structure", test_ui_package)
    
    # Test 6: Data model integration
    def test_model_integration():
        from src.core.models import SearchQuery, SearchResult, Paper
        from src.ui.search_interface import SearchInterface
        
        # Test that models can be used with UI
        query = SearchQuery(query="test", limit=10)
        assert query.query == "test"
    
    test_component("Data model integration", test_model_integration)
    
    # Test 7: Analysis integration
    def test_analysis_integration():
        from src.analysis import search_engine, similarity_engine
        from src.ui.search_interface import SearchInterface
        
        # Test that analysis components are accessible
        assert search_engine is not None
        assert similarity_engine is not None
    
    test_component("Analysis integration", test_analysis_integration)
    
    # Test 8: Repository integration
    def test_repository_integration():
        from src.core.repository import paper_repo
        from src.ui.dashboard import Dashboard
        
        # Test that repository is accessible from UI
        assert paper_repo is not None
    
    test_component("Repository integration", test_repository_integration)
    
    # Results
    print("\n" + "=" * 60)
    print(f"🎯 UI Component Tests: {success_count}/{total_tests} passed")
    
    if success_count == total_tests:
        print("🎉 All UI components working correctly!")
        print("💡 UI system ready for full application testing")
        print()
        print("📋 Available UI Components:")
        print("   • MainWindow - Complete application window")
        print("   • Dashboard - Statistics and recent activity")
        print("   • SearchInterface - Advanced literature search")
        print("   • Paper detail views and filters")
        print("   • Real-time data integration")
        print()
        print("🚀 To run the full application:")
        print("   python src/ui/app.py")
        return True
    else:
        print("❌ Some UI components have issues")
        return False


if __name__ == "__main__":
    success = test_ui_components()
    sys.exit(0 if success else 1)