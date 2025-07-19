"""Test script for UI components."""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

def test_ui_imports():
    """Test UI component imports."""
    print("🖥️  Testing UI Components")
    print("=" * 50)
    
    try:
        print("1. Testing PyQt6 import...")
        from PyQt6.QtWidgets import QApplication
        print("   ✅ PyQt6 available")
        
        print("2. Testing UI modules...")
        from src.ui import MainWindow, ProtLitAIApplication
        print("   ✅ UI modules imported successfully")
        
        print("3. Testing MainWindow creation...")
        # Create a minimal QApplication for testing
        app = QApplication([])
        window = MainWindow()
        print("   ✅ MainWindow created successfully")
        print(f"   ✅ Window title: {window.windowTitle()}")
        print(f"   ✅ Window size: {window.size().width()}x{window.size().height()}")
        
        print("4. Testing application class...")
        app_instance = ProtLitAIApplication([])
        print("   ✅ ProtLitAIApplication created successfully")
        print(f"   ✅ App name: {app_instance.applicationName()}")
        print(f"   ✅ App version: {app_instance.applicationVersion()}")
        
        print("\n" + "=" * 50)
        print("🎉 UI components test completed successfully!")
        print("💡 To see the actual UI, run: python src/ui/app.py")
        
    except ImportError as e:
        print(f"   ❌ Import error: {e}")
        print("   💡 Make sure PyQt6 is installed: pip install PyQt6")
        
    except Exception as e:
        print(f"   ❌ Error: {e}")


if __name__ == "__main__":
    test_ui_imports()