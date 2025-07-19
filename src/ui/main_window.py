"""Main application window for ProtLitAI."""

import sys
from typing import Dict, Any, Optional
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QMenuBar, QStatusBar, QToolBar, QTreeWidget, QTreeWidgetItem,
    QStackedWidget, QLabel, QFrame, QPushButton, QLineEdit, QMessageBox
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread, QSize
from PyQt6.QtGui import QIcon, QAction, QPixmap, QFont, QPalette

from ..core.logging import get_logger
from ..core.config import config
from .dashboard import Dashboard, DashboardController
from .search_interface import SearchInterface


class MainWindow(QMainWindow):
    """Main application window with modern macOS design."""
    
    # Signals
    search_requested = pyqtSignal(str)
    page_changed = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.logger = get_logger("main_window")
        self.settings = config.settings
        
        # Window state
        self.current_page = "dashboard"
        self.pages = {}
        
        self.logger.info("Initializing main window")
        self._setup_ui()
        self._setup_menu_bar()
        self._setup_status_bar()
        self._setup_connections()
        
        # Start with dashboard
        self._show_page("dashboard")
    
    def _setup_ui(self):
        """Set up the main user interface."""
        # Window properties
        self.setWindowTitle("ProtLitAI - Protein Design Literature Intelligence")
        self.setMinimumSize(1200, 800)
        self.resize(1400, 1000)
        
        # Apply macOS-style appearance
        self._apply_macos_styling()
        
        # Central widget with splitter
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Create splitter for sidebar and content
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)
        
        # Sidebar
        self.sidebar = self._create_sidebar()
        splitter.addWidget(self.sidebar)
        
        # Content area
        self.content_stack = self._create_content_area()
        splitter.addWidget(self.content_stack)
        
        # Set splitter proportions (25% sidebar, 75% content)
        splitter.setSizes([300, 1100])
        splitter.setCollapsible(0, False)  # Sidebar can't be collapsed completely
    
    def _apply_macos_styling(self):
        """Apply macOS-style visual design."""
        # Set window background
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
                color: #333333;
            }
            
            QMenuBar {
                background-color: transparent;
                border: none;
                font-size: 13px;
            }
            
            QMenuBar::item {
                background-color: transparent;
                padding: 4px 8px;
                margin: 2px;
                border-radius: 4px;
            }
            
            QMenuBar::item:selected {
                background-color: #007AFF;
                color: white;
            }
            
            QStatusBar {
                background-color: #e8e8e8;
                border-top: 1px solid #d0d0d0;
                font-size: 11px;
                color: #666666;
            }
        """)
    
    def _create_sidebar(self) -> QWidget:
        """Create the sidebar navigation."""
        sidebar_frame = QFrame()
        sidebar_frame.setFixedWidth(250)
        sidebar_frame.setStyleSheet("""
            QFrame {
                background-color: #ffffff;
                border-right: 1px solid #e0e0e0;
            }
        """)
        
        layout = QVBoxLayout(sidebar_frame)
        layout.setContentsMargins(0, 10, 0, 0)
        layout.setSpacing(0)
        
        # App logo/title
        title_label = QLabel("ProtLitAI")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: #007AFF;
                padding: 10px;
                margin-bottom: 10px;
            }
        """)
        layout.addWidget(title_label)
        
        # Quick search
        search_container = QWidget()
        search_layout = QVBoxLayout(search_container)
        search_layout.setContentsMargins(15, 0, 15, 10)
        
        self.quick_search = QLineEdit()
        self.quick_search.setPlaceholderText("Quick search...")
        self.quick_search.setStyleSheet("""
            QLineEdit {
                padding: 8px 12px;
                border: 1px solid #d0d0d0;
                border-radius: 6px;
                font-size: 13px;
                background-color: #f8f8f8;
            }
            QLineEdit:focus {
                border-color: #007AFF;
                background-color: white;
            }
        """)
        search_layout.addWidget(self.quick_search)
        layout.addWidget(search_container)
        
        # Navigation tree
        self.nav_tree = QTreeWidget()
        self.nav_tree.setHeaderHidden(True)
        self.nav_tree.setRootIsDecorated(False)
        self.nav_tree.setStyleSheet("""
            QTreeWidget {
                background-color: transparent;
                border: none;
                font-size: 13px;
                outline: none;
            }
            QTreeWidget::item {
                padding: 8px 15px;
                border: none;
                color: #333333;
            }
            QTreeWidget::item:hover {
                background-color: #f0f0f0;
            }
            QTreeWidget::item:selected {
                background-color: #007AFF;
                color: white;
            }
        """)
        
        # Add navigation items
        nav_items = [
            ("Dashboard", "dashboard", "📊"),
            ("Search", "search", "🔍"),
            ("Trends", "trends", "📈"),
            ("Alerts", "alerts", "🔔"),
            ("Analytics", "analytics", "📊"),
            ("Settings", "settings", "⚙️")
        ]
        
        for title, page_id, icon in nav_items:
            item = QTreeWidgetItem([f"{icon}  {title}"])
            item.setData(0, Qt.ItemDataRole.UserRole, page_id)
            self.nav_tree.addTopLevelItem(item)
        
        layout.addWidget(self.nav_tree)
        layout.addStretch()
        
        return sidebar_frame
    
    def _create_content_area(self) -> QStackedWidget:
        """Create the main content area."""
        stack = QStackedWidget()
        
        # Create placeholder pages
        self.pages = {
            "dashboard": self._create_dashboard_page(),
            "search": self._create_search_page(),
            "trends": self._create_trends_page(),
            "alerts": self._create_alerts_page(),
            "analytics": self._create_analytics_page(),
            "settings": self._create_settings_page()
        }
        
        # Add pages to stack
        for page_widget in self.pages.values():
            stack.addWidget(page_widget)
        
        return stack
    
    def _create_dashboard_page(self) -> QWidget:
        """Create the dashboard page."""
        dashboard = Dashboard()
        
        # Connect dashboard signals
        dashboard.search_requested.connect(self._handle_dashboard_search)
        dashboard.paper_selected.connect(self._handle_paper_selected)
        
        return dashboard
    
    def _create_search_page(self) -> QWidget:
        """Create the search page."""
        search_interface = SearchInterface()
        
        # Connect search interface signals
        search_interface.search_performed.connect(self._handle_search_performed)
        search_interface.paper_selected.connect(self._handle_paper_selected)
        
        # Store reference for external access
        self.search_interface = search_interface
        
        return search_interface
    
    def _create_trends_page(self) -> QWidget:
        """Create the trends analysis page."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 30, 30, 30)
        
        title = QLabel("Research Trends")
        title.setStyleSheet("""
            QLabel {
                font-size: 24px;
                font-weight: bold;
                color: #333333;
                margin-bottom: 20px;
            }
        """)
        layout.addWidget(title)
        
        # Placeholder content
        content = QLabel("Trend analysis will be displayed here...")
        content.setStyleSheet("""
            QLabel {
                font-size: 14px;
                color: #888888;
                text-align: center;
                padding: 40px;
                background-color: white;
                border-radius: 8px;
                border: 1px solid #e0e0e0;
            }
        """)
        layout.addWidget(content)
        
        return page
    
    def _create_alerts_page(self) -> QWidget:
        """Create the alerts management page."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 30, 30, 30)
        
        title = QLabel("Literature Alerts")
        title.setStyleSheet("""
            QLabel {
                font-size: 24px;
                font-weight: bold;
                color: #333333;
                margin-bottom: 20px;
            }
        """)
        layout.addWidget(title)
        
        # Placeholder content
        content = QLabel("Alert management will be available here...")
        content.setStyleSheet("""
            QLabel {
                font-size: 14px;
                color: #888888;
                text-align: center;
                padding: 40px;
                background-color: white;
                border-radius: 8px;
                border: 1px solid #e0e0e0;
            }
        """)
        layout.addWidget(content)
        
        return page
    
    def _create_analytics_page(self) -> QWidget:
        """Create the analytics page."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 30, 30, 30)
        
        title = QLabel("Analytics & Insights")
        title.setStyleSheet("""
            QLabel {
                font-size: 24px;
                font-weight: bold;
                color: #333333;
                margin-bottom: 20px;
            }
        """)
        layout.addWidget(title)
        
        # Placeholder content
        content = QLabel("Advanced analytics will be displayed here...")
        content.setStyleSheet("""
            QLabel {
                font-size: 14px;
                color: #888888;
                text-align: center;
                padding: 40px;
                background-color: white;
                border-radius: 8px;
                border: 1px solid #e0e0e0;
            }
        """)
        layout.addWidget(content)
        
        return page
    
    def _create_settings_page(self) -> QWidget:
        """Create the settings page."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 30, 30, 30)
        
        title = QLabel("Settings")
        title.setStyleSheet("""
            QLabel {
                font-size: 24px;
                font-weight: bold;
                color: #333333;
                margin-bottom: 20px;
            }
        """)
        layout.addWidget(title)
        
        # Placeholder content
        content = QLabel("Application settings will be available here...")
        content.setStyleSheet("""
            QLabel {
                font-size: 14px;
                color: #888888;
                text-align: center;
                padding: 40px;
                background-color: white;
                border-radius: 8px;
                border: 1px solid #e0e0e0;
            }
        """)
        layout.addWidget(content)
        
        return page
    
    def _setup_menu_bar(self):
        """Set up the macOS-style menu bar."""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("File")
        
        new_action = QAction("New Search", self)
        new_action.setShortcut("Cmd+N")
        file_menu.addAction(new_action)
        
        open_action = QAction("Open...", self)
        open_action.setShortcut("Cmd+O")
        file_menu.addAction(open_action)
        
        file_menu.addSeparator()
        
        quit_action = QAction("Quit ProtLitAI", self)
        quit_action.setShortcut("Cmd+Q")
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)
        
        # Edit menu
        edit_menu = menubar.addMenu("Edit")
        
        search_action = QAction("Search Literature", self)
        search_action.setShortcut("Cmd+F")
        search_action.triggered.connect(self._focus_search)
        edit_menu.addAction(search_action)
        
        # View menu
        view_menu = menubar.addMenu("View")
        
        dashboard_action = QAction("Dashboard", self)
        dashboard_action.setShortcut("Cmd+1")
        dashboard_action.triggered.connect(lambda: self._show_page("dashboard"))
        view_menu.addAction(dashboard_action)
        
        search_action = QAction("Search", self)
        search_action.setShortcut("Cmd+2")
        search_action.triggered.connect(lambda: self._show_page("search"))
        view_menu.addAction(search_action)
        
        trends_action = QAction("Trends", self)
        trends_action.setShortcut("Cmd+3")
        trends_action.triggered.connect(lambda: self._show_page("trends"))
        view_menu.addAction(trends_action)
        
        # Help menu
        help_menu = menubar.addMenu("Help")
        
        about_action = QAction("About ProtLitAI", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)
    
    def _setup_status_bar(self):
        """Set up the status bar."""
        self.status_bar = self.statusBar()
        self.status_bar.showMessage("Ready")
        
        # Add permanent widgets to status bar
        self.status_label = QLabel("Ready")
        self.status_bar.addWidget(self.status_label)
        
        # Connection status
        self.connection_label = QLabel("Database: Connected")
        self.status_bar.addPermanentWidget(self.connection_label)
    
    def _setup_connections(self):
        """Set up signal connections."""
        # Navigation tree
        self.nav_tree.itemClicked.connect(self._on_nav_item_clicked)
        
        # Search
        self.quick_search.returnPressed.connect(self._on_quick_search)
        if hasattr(self, 'main_search'):
            self.main_search.returnPressed.connect(self._on_main_search)
    
    def _show_page(self, page_id: str):
        """Show a specific page."""
        if page_id in self.pages:
            page_widget = self.pages[page_id]
            self.content_stack.setCurrentWidget(page_widget)
            self.current_page = page_id
            
            # Update navigation selection
            for i in range(self.nav_tree.topLevelItemCount()):
                item = self.nav_tree.topLevelItem(i)
                if item.data(0, Qt.ItemDataRole.UserRole) == page_id:
                    self.nav_tree.setCurrentItem(item)
                    break
            
            # Update status
            self.status_label.setText(f"Viewing: {page_id.title()}")
            
            # Emit signal
            self.page_changed.emit(page_id)
            
            self.logger.debug("Page changed", page=page_id)
    
    def _on_nav_item_clicked(self, item):
        """Handle navigation item click."""
        page_id = item.data(0, Qt.ItemDataRole.UserRole)
        if page_id:
            self._show_page(page_id)
    
    def _focus_search(self):
        """Focus on search functionality."""
        self._show_page("search")
        if hasattr(self, 'main_search'):
            self.main_search.setFocus()
    
    def _on_quick_search(self):
        """Handle quick search."""
        query = self.quick_search.text().strip()
        if query:
            self.search_requested.emit(query)
            self._show_page("search")
            self.quick_search.clear()
    
    def _on_main_search(self):
        """Handle main search."""
        if hasattr(self, 'search_interface'):
            # Delegate to search interface
            pass
    
    def _show_about(self):
        """Show about dialog."""
        about_text = """
        <h3>ProtLitAI</h3>
        <p>Protein Design Literature Intelligence Engine</p>
        
        <p><b>Version:</b> 1.0.0</p>
        <p><b>Built for:</b> macOS with Apple Silicon optimization</p>
        
        <p>ProtLitAI helps researchers stay current with protein design 
        literature through AI-powered analysis and monitoring.</p>
        
        <p><small>© 2025 ProtLitAI Project</small></p>
        """
        
        QMessageBox.about(self, "About ProtLitAI", about_text)
    
    def update_status(self, message: str):
        """Update status bar message."""
        self.status_label.setText(message)
        self.logger.debug("Status updated", message=message)
    
    def closeEvent(self, event):
        """Handle window close event."""
        self.logger.info("Application closing")
        event.accept()
    
    def _handle_dashboard_search(self, query: str):
        """Handle search request from dashboard."""
        self.logger.debug("Search requested from dashboard", query=query)
        
        # Switch to search page and set query
        self._show_page("search")
        if hasattr(self, 'search_interface') and query:
            self.search_interface.set_search_query(query)
    
    def _handle_search_performed(self, results):
        """Handle search completion."""
        self.logger.debug("Search performed", 
                         total_results=results.total_count,
                         query_time=results.query_time)
        
        # Update status
        self.update_status(f"Found {results.total_count} papers in {results.query_time:.2f}s")
    
    def _handle_paper_selected(self, paper_id: str):
        """Handle paper selection."""
        self.logger.debug("Paper selected", paper_id=paper_id)
        
        # Update status
        self.update_status(f"Viewing paper: {paper_id}")
        
        # Future: Open paper detail view or send to external handler


def main():
    """Run the application."""
    app = QApplication(sys.argv)
    
    # Set application properties
    app.setApplicationName("ProtLitAI")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("ProtLitAI")
    
    # Create main window
    window = MainWindow()
    window.show()
    
    # Start event loop
    sys.exit(app.exec())


if __name__ == "__main__":
    main()