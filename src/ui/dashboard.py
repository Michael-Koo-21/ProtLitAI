"""Dashboard component with statistics and visualizations."""

from typing import Dict, Any, List, Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, 
    QFrame, QPushButton, QScrollArea, QProgressBar, QListWidget,
    QListWidgetItem, QGroupBox, QSplitter
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread, QSize
from PyQt6.QtGui import QFont, QPalette, QPixmap, QPainter, QColor

from core.logging import get_logger
from core.repository import paper_repo


class StatCard(QFrame):
    """Statistics card widget."""
    
    def __init__(self, title: str, value: str, subtitle: str = "", icon: str = "📊"):
        super().__init__()
        self.title = title
        self.value = value
        self.subtitle = subtitle
        self.icon = icon
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Set up the card UI."""
        self.setFixedSize(200, 120)
        self.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                margin: 5px;
            }
            QFrame:hover {
                border-color: #007AFF;
                box-shadow: 0 2px 8px rgba(0, 122, 255, 0.2);
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 12, 15, 12)
        layout.setSpacing(8)
        
        # Icon and title row
        top_layout = QHBoxLayout()
        
        icon_label = QLabel(self.icon)
        icon_label.setStyleSheet("font-size: 20px;")
        top_layout.addWidget(icon_label)
        
        title_label = QLabel(self.title)
        title_label.setStyleSheet("""
            QLabel {
                font-size: 12px;
                color: #666666;
                font-weight: normal;
            }
        """)
        top_layout.addWidget(title_label)
        top_layout.addStretch()
        
        layout.addLayout(top_layout)
        
        # Value
        value_label = QLabel(self.value)
        value_label.setStyleSheet("""
            QLabel {
                font-size: 24px;
                font-weight: bold;
                color: #333333;
            }
        """)
        layout.addWidget(value_label)
        
        # Subtitle
        if self.subtitle:
            subtitle_label = QLabel(self.subtitle)
            subtitle_label.setStyleSheet("""
                QLabel {
                    font-size: 10px;
                    color: #888888;
                }
            """)
            layout.addWidget(subtitle_label)
        
        layout.addStretch()
    
    def update_value(self, value: str, subtitle: str = None):
        """Update the card value."""
        self.value = value
        if subtitle is not None:
            self.subtitle = subtitle
        self._setup_ui()


class RecentPapersWidget(QGroupBox):
    """Widget showing recent papers."""
    
    paper_selected = pyqtSignal(str)  # paper_id
    
    def __init__(self):
        super().__init__("Recent Papers")
        self.logger = get_logger("recent_papers_widget")
        self._setup_ui()
        self._load_recent_papers()
    
    def _setup_ui(self):
        """Set up the widget UI."""
        self.setStyleSheet("""
            QGroupBox {
                font-size: 14px;
                font-weight: bold;
                color: #333333;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                padding-top: 15px;
                margin-top: 10px;
                background-color: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 8px 0 8px;
                background-color: white;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Papers list
        self.papers_list = QListWidget()
        self.papers_list.setStyleSheet("""
            QListWidget {
                border: none;
                background-color: transparent;
                font-size: 13px;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #f0f0f0;
                border-radius: 4px;
                margin: 2px 0;
                color: #333333;
            }
            QListWidget::item:hover {
                background-color: #f8f8f8;
            }
            QListWidget::item:selected {
                background-color: #e3f2fd;
                color: #1976d2;
            }
        """)
        self.papers_list.itemClicked.connect(self._on_paper_clicked)
        
        layout.addWidget(self.papers_list)
        
        # Refresh button
        refresh_button = QPushButton("🔄 Refresh")
        refresh_button.setStyleSheet("""
            QPushButton {
                background-color: #f0f0f0;
                border: 1px solid #d0d0d0;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
        """)
        refresh_button.clicked.connect(self._load_recent_papers)
        layout.addWidget(refresh_button)
    
    def _load_recent_papers(self):
        """Load recent papers from database."""
        try:
            papers = paper_repo.get_recent(limit=10)
            self.papers_list.clear()
            
            for paper in papers:
                item_text = f"📄 {paper.title[:60]}..."
                if len(paper.title) <= 60:
                    item_text = f"📄 {paper.title}"
                
                # Add subtitle with journal and date
                subtitle = ""
                if paper.journal:
                    subtitle += paper.journal
                if paper.publication_date:
                    if subtitle:
                        subtitle += " • "
                    subtitle += paper.publication_date.strftime("%Y-%m-%d")
                
                if subtitle:
                    item_text += f"\n   {subtitle}"
                
                item = QListWidgetItem(item_text)
                item.setData(Qt.ItemDataRole.UserRole, paper.id)
                self.papers_list.addItem(item)
            
            self.logger.debug("Recent papers loaded", count=len(papers))
            
        except Exception as e:
            self.logger.error("Failed to load recent papers", error=str(e))
            error_item = QListWidgetItem("❌ Failed to load papers")
            self.papers_list.addItem(error_item)
    
    def _on_paper_clicked(self, item):
        """Handle paper item click."""
        paper_id = item.data(Qt.ItemDataRole.UserRole)
        if paper_id:
            self.paper_selected.emit(paper_id)


class TrendingTopicsWidget(QGroupBox):
    """Widget showing trending research topics."""
    
    def __init__(self):
        super().__init__("Trending Topics")
        self.logger = get_logger("trending_topics_widget")
        self._setup_ui()
        self._load_trending_topics()
    
    def _setup_ui(self):
        """Set up the widget UI."""
        self.setStyleSheet("""
            QGroupBox {
                font-size: 14px;
                font-weight: bold;
                color: #333333;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                padding-top: 15px;
                margin-top: 10px;
                background-color: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 8px 0 8px;
                background-color: white;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Topics list
        self.topics_list = QListWidget()
        self.topics_list.setStyleSheet("""
            QListWidget {
                border: none;
                background-color: transparent;
                font-size: 13px;
            }
            QListWidget::item {
                padding: 6px;
                border-radius: 4px;
                margin: 1px 0;
                color: #333333;
            }
        """)
        
        layout.addWidget(self.topics_list)
    
    def _load_trending_topics(self):
        """Load trending topics."""
        try:
            # Placeholder data for now
            trending_topics = [
                ("🧬 Protein Folding", "↗️ +15%"),
                ("🤖 Machine Learning", "↗️ +12%"),
                ("💊 Drug Discovery", "↗️ +8%"),
                ("🔬 AlphaFold", "↗️ +6%"),
                ("⚗️ Structure Prediction", "↗️ +5%")
            ]
            
            self.topics_list.clear()
            
            for topic, trend in trending_topics:
                item_text = f"{topic}\n   {trend}"
                item = QListWidgetItem(item_text)
                self.topics_list.addItem(item)
            
            self.logger.debug("Trending topics loaded")
            
        except Exception as e:
            self.logger.error("Failed to load trending topics", error=str(e))


class ActivityTimelineWidget(QGroupBox):
    """Widget showing activity timeline."""
    
    def __init__(self):
        super().__init__("Activity Timeline")
        self.logger = get_logger("activity_timeline_widget")
        self._setup_ui()
        self._load_activity_data()
    
    def _setup_ui(self):
        """Set up the widget UI."""
        self.setStyleSheet("""
            QGroupBox {
                font-size: 14px;
                font-weight: bold;
                color: #333333;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                padding-top: 15px;
                margin-top: 10px;
                background-color: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 8px 0 8px;
                background-color: white;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Simple timeline visualization
        self.timeline_label = QLabel("📊 Timeline chart will be displayed here")
        self.timeline_label.setStyleSheet("""
            QLabel {
                padding: 20px;
                text-align: center;
                color: #888888;
                font-size: 12px;
            }
        """)
        layout.addWidget(self.timeline_label)
    
    def _load_activity_data(self):
        """Load activity timeline data."""
        try:
            # This would integrate with actual analytics
            self.timeline_label.setText("📈 Recent activity:\n\n" +
                                      "Today: 25 papers\n" +
                                      "Yesterday: 18 papers\n" +
                                      "This week: 156 papers")
            
            self.logger.debug("Activity timeline loaded")
            
        except Exception as e:
            self.logger.error("Failed to load activity timeline", error=str(e))


class Dashboard(QWidget):
    """Main dashboard widget."""
    
    # Signals
    search_requested = pyqtSignal(str)
    paper_selected = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.logger = get_logger("dashboard")
        self.stats_cards = {}
        
        self._setup_ui()
        self._load_dashboard_data()
        
        # Auto-refresh timer
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self._refresh_data)
        self.refresh_timer.start(60000)  # Refresh every minute
    
    def _setup_ui(self):
        """Set up the dashboard UI."""
        # Main scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: #f5f5f5;
            }
        """)
        
        # Content widget
        content_widget = QWidget()
        scroll_area.setWidget(content_widget)
        
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll_area)
        
        # Content layout
        layout = QVBoxLayout(content_widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        # Title section
        title_layout = QHBoxLayout()
        
        title_label = QLabel("Dashboard")
        title_label.setStyleSheet("""
            QLabel {
                font-size: 28px;
                font-weight: bold;
                color: #333333;
                margin-bottom: 10px;
            }
        """)
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        
        # Quick search button
        quick_search_btn = QPushButton("🔍 Quick Search")
        quick_search_btn.setStyleSheet("""
            QPushButton {
                background-color: #007AFF;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 6px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0056D6;
            }
        """)
        quick_search_btn.clicked.connect(lambda: self.search_requested.emit(""))
        title_layout.addWidget(quick_search_btn)
        
        layout.addLayout(title_layout)
        
        # Statistics cards
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(10)
        
        self.stats_cards = {
            'total_papers': StatCard("Total Papers", "0", "In database", "📚"),
            'recent_papers': StatCard("Recent", "0", "Last 7 days", "🆕"),
            'trending': StatCard("Trending", "0", "Hot topics", "📈"),
            'alerts': StatCard("Alerts", "0", "Active", "🔔")
        }
        
        for card in self.stats_cards.values():
            stats_layout.addWidget(card)
        
        stats_layout.addStretch()
        layout.addLayout(stats_layout)
        
        # Content sections
        content_layout = QHBoxLayout()
        content_layout.setSpacing(15)
        
        # Left column
        left_column = QVBoxLayout()
        
        # Recent papers
        self.recent_papers = RecentPapersWidget()
        self.recent_papers.paper_selected.connect(self.paper_selected.emit)
        left_column.addWidget(self.recent_papers)
        
        content_layout.addLayout(left_column, 2)
        
        # Right column
        right_column = QVBoxLayout()
        
        # Trending topics
        self.trending_topics = TrendingTopicsWidget()
        right_column.addWidget(self.trending_topics)
        
        # Activity timeline
        self.activity_timeline = ActivityTimelineWidget()
        right_column.addWidget(self.activity_timeline)
        
        content_layout.addLayout(right_column, 1)
        
        layout.addLayout(content_layout)
        layout.addStretch()
    
    def _load_dashboard_data(self):
        """Load dashboard data from database."""
        try:
            # Load statistics
            stats = paper_repo.get_statistics()
            
            # Update stat cards
            self.stats_cards['total_papers'].update_value(
                str(stats.get('total_papers', 0))
            )
            
            self.stats_cards['recent_papers'].update_value(
                str(stats.get('recent_count', 0))
            )
            
            # Count trending topics (placeholder)
            self.stats_cards['trending'].update_value("5")
            
            # Count alerts (placeholder) 
            self.stats_cards['alerts'].update_value("2")
            
            self.logger.debug("Dashboard data loaded", stats=stats)
            
        except Exception as e:
            self.logger.error("Failed to load dashboard data", error=str(e))
            
            # Show error state
            for card in self.stats_cards.values():
                card.update_value("–", "Error loading")
    
    def _refresh_data(self):
        """Refresh dashboard data."""
        self.logger.debug("Refreshing dashboard data")
        self._load_dashboard_data()
        
        # Refresh child widgets
        if hasattr(self, 'recent_papers'):
            self.recent_papers._load_recent_papers()
    
    def refresh(self):
        """Public method to refresh dashboard."""
        self._refresh_data()


class DashboardController:
    """Controller for dashboard functionality."""
    
    def __init__(self, dashboard: Dashboard):
        self.dashboard = dashboard
        self.logger = get_logger("dashboard_controller")
        
        # Connect signals
        self.dashboard.search_requested.connect(self._handle_search_request)
        self.dashboard.paper_selected.connect(self._handle_paper_selected)
    
    def _handle_search_request(self, query: str):
        """Handle search request from dashboard."""
        self.logger.info("Search requested from dashboard", query=query)
        
        # This would be connected to the main application's search functionality
        pass
    
    def _handle_paper_selected(self, paper_id: str):
        """Handle paper selection from dashboard."""
        self.logger.info("Paper selected from dashboard", paper_id=paper_id)
        
        # This would open the paper detail view
        pass