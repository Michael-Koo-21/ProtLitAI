"""Simple test for UI component imports without QApplication."""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

def test_ui_imports_only():
    """Test UI component imports without creating QApplication."""
    print("🖥️  Testing UI Component Imports")
    print("=" * 50)
    
    try:
        print("1. Testing PyQt6 import...")
        from PyQt6.QtWidgets import QApplication, QMainWindow
        print("   ✅ PyQt6 widgets available")
        
        print("2. Testing core dependencies...")
        from src.core.logging import get_logger
        from src.core.config import config
        print("   ✅ Core dependencies available")
        
        print("3. Testing UI module structure...")
        from src.ui.main_window import MainWindow
        from src.ui.app import ProtLitAIApplication
        print("   ✅ UI classes imported successfully")
        
        print("4. Testing UI package...")
        from src.ui import MainWindow as MW, ProtLitAIApplication as PA
        print("   ✅ UI package structure working")
        
        print("\n" + "=" * 50)
        print("🎉 UI import tests completed successfully!")
        print("💡 UI framework ready for development")
        print("⚠️  Full UI testing requires proper macOS display environment")
        
        return True
        
    except ImportError as e:
        print(f"   ❌ Import error: {e}")
        return False
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False


if __name__ == "__main__":
    success = test_ui_imports_only()
    sys.exit(0 if success else 1)