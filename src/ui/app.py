"""ProtLitAI Application Entry Point."""

import sys
import os
from typing import Optional

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QPixmap, QIcon

from .main_window import MainWindow
from ..core.logging import get_logger
from ..core.config import config


class ProtLitAIApplication(QApplication):
    """Main ProtLitAI application class."""
    
    def __init__(self, argv):
        super().__init__(argv)
        
        self.logger = get_logger("application")
        self.settings = config.settings
        
        # Application properties
        self.setApplicationName("ProtLitAI")
        self.setApplicationDisplayName("ProtLitAI")
        self.setApplicationVersion("1.0.0")
        self.setOrganizationName("ProtLitAI Project")
        self.setOrganizationDomain("protlitai.org")
        
        # Set application icon (if available)
        self._set_application_icon()
        
        # Main window
        self.main_window: Optional[MainWindow] = None
        
        self.logger.info("ProtLitAI application initialized")
    
    def _set_application_icon(self):
        """Set application icon if available."""
        try:
            # Look for icon file
            icon_paths = [
                "assets/icon.png",
                "assets/icon.icns",
                "icon.png"
            ]
            
            for icon_path in icon_paths:
                if os.path.exists(icon_path):
                    icon = QIcon(icon_path)
                    self.setWindowIcon(icon)
                    self.logger.debug("Application icon set", path=icon_path)
                    break
        except Exception as e:
            self.logger.debug("Could not set application icon", error=str(e))
    
    def create_main_window(self) -> MainWindow:
        """Create and configure the main window."""
        if self.main_window is None:
            self.main_window = MainWindow()
            
            # Connect application-level signals
            self.main_window.search_requested.connect(self._handle_search_request)
            self.main_window.page_changed.connect(self._handle_page_change)
            
            self.logger.info("Main window created")
        
        return self.main_window
    
    def show_main_window(self):
        """Show the main application window."""
        window = self.create_main_window()
        window.show()
        window.raise_()
        window.activateWindow()
        
        self.logger.info("Main window displayed")
    
    def _handle_search_request(self, query: str):
        """Handle search request from UI."""
        self.logger.info("Search requested", query=query)
        
        # TODO: Integrate with search engine
        if self.main_window:
            self.main_window.update_status(f"Searching for: {query}")
    
    def _handle_page_change(self, page_id: str):
        """Handle page change in UI."""
        self.logger.debug("Page changed", page=page_id)
        
        # TODO: Update any page-specific functionality
        if self.main_window:
            self.main_window.update_status(f"Viewing {page_id}")


def run_application():
    """Run the ProtLitAI application."""
    # Create application
    app = ProtLitAIApplication(sys.argv)
    
    # Show main window
    app.show_main_window()
    
    # Start event loop
    return app.exec()


if __name__ == "__main__":
    sys.exit(run_application())