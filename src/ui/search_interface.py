"""Search interface and results display components."""

from typing import Dict, Any, List, Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, 
    QFrame, QPushButton, QLineEdit, QComboBox, QCheckBox,
    QTableWidget, QTableWidgetItem, QSplitter, QTextEdit,
    QProgressBar, QGroupBox, QScrollArea, QHeaderView,
    QAbstractItemView, QMenu
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread, QSize, QSortFilterProxyModel
from PyQt6.QtGui import QFont, QPalette, QPixmap, QPainter, QColor, QAction

from core.logging import get_logger
from core.models import SearchQuery, SearchResult, Paper
from analysis import search_engine


class SearchFiltersWidget(QGroupBox):
    """Advanced search filters widget."""
    
    filters_changed = pyqtSignal(dict)
    
    def __init__(self):
        super().__init__("Search Filters")
        self.logger = get_logger("search_filters")
        self._setup_ui()
    
    def _setup_ui(self):
        """Set up the filters UI."""
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
        layout.setContentsMargins(15, 10, 15, 15)
        layout.setSpacing(12)
        
        # Date range filter
        date_layout = QVBoxLayout()
        date_label = QLabel("Publication Date")
        date_label.setStyleSheet("font-size: 12px; font-weight: bold; color: #555;")
        date_layout.addWidget(date_label)
        
        date_row = QHBoxLayout()
        self.date_from = QLineEdit()
        self.date_from.setPlaceholderText("From (YYYY-MM-DD)")
        self.date_from.setStyleSheet(self._get_input_style())
        date_row.addWidget(self.date_from)
        
        self.date_to = QLineEdit()
        self.date_to.setPlaceholderText("To (YYYY-MM-DD)")
        self.date_to.setStyleSheet(self._get_input_style())
        date_row.addWidget(self.date_to)
        
        date_layout.addLayout(date_row)
        layout.addLayout(date_layout)
        
        # Source filter
        source_layout = QVBoxLayout()
        source_label = QLabel("Sources")
        source_label.setStyleSheet("font-size: 12px; font-weight: bold; color: #555;")
        source_layout.addWidget(source_label)
        
        self.source_checkboxes = {}
        sources = ["PubMed", "arXiv", "bioRxiv", "medRxiv"]
        
        source_grid = QGridLayout()
        for i, source in enumerate(sources):
            checkbox = QCheckBox(source)
            checkbox.setChecked(True)
            checkbox.setStyleSheet("font-size: 12px; color: #333;")
            self.source_checkboxes[source.lower()] = checkbox
            source_grid.addWidget(checkbox, i // 2, i % 2)
        
        source_layout.addLayout(source_grid)
        layout.addLayout(source_layout)
        
        # Journal filter
        journal_layout = QVBoxLayout()
        journal_label = QLabel("Journal")
        journal_label.setStyleSheet("font-size: 12px; font-weight: bold; color: #555;")
        journal_layout.addWidget(journal_label)
        
        self.journal_input = QLineEdit()
        self.journal_input.setPlaceholderText("Journal name (optional)")
        self.journal_input.setStyleSheet(self._get_input_style())
        journal_layout.addWidget(self.journal_input)
        layout.addLayout(journal_layout)
        
        # Author filter
        author_layout = QVBoxLayout()
        author_label = QLabel("Author")
        author_label.setStyleSheet("font-size: 12px; font-weight: bold; color: #555;")
        author_layout.addWidget(author_label)
        
        self.author_input = QLineEdit()
        self.author_input.setPlaceholderText("Author name (optional)")
        self.author_input.setStyleSheet(self._get_input_style())
        author_layout.addWidget(self.author_input)
        layout.addLayout(author_layout)
        
        # Relevance threshold
        relevance_layout = QVBoxLayout()
        relevance_label = QLabel("Minimum Relevance")
        relevance_label.setStyleSheet("font-size: 12px; font-weight: bold; color: #555;")
        relevance_layout.addWidget(relevance_label)
        
        self.relevance_combo = QComboBox()
        self.relevance_combo.addItems(["Any", "0.3+", "0.5+", "0.7+", "0.9+"])
        self.relevance_combo.setStyleSheet(self._get_input_style())
        relevance_layout.addWidget(self.relevance_combo)
        layout.addLayout(relevance_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        apply_button = QPushButton("Apply Filters")
        apply_button.setStyleSheet("""
            QPushButton {
                background-color: #007AFF;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0056D6;
            }
        """)
        apply_button.clicked.connect(self._apply_filters)
        button_layout.addWidget(apply_button)
        
        clear_button = QPushButton("Clear")
        clear_button.setStyleSheet("""
            QPushButton {
                background-color: #f0f0f0;
                color: #333;
                border: 1px solid #d0d0d0;
                padding: 8px 16px;
                border-radius: 4px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
        """)
        clear_button.clicked.connect(self._clear_filters)
        button_layout.addWidget(clear_button)
        
        layout.addLayout(button_layout)
        layout.addStretch()
    
    def _get_input_style(self) -> str:
        """Get standard input field style."""
        return """
            QLineEdit, QComboBox {
                padding: 6px 8px;
                border: 1px solid #d0d0d0;
                border-radius: 4px;
                font-size: 12px;
                color: #333333;
                background-color: #fafafa;
            }
            QLineEdit:focus, QComboBox:focus {
                border-color: #007AFF;
                color: #000000;
                background-color: white;
            }
            QComboBox QAbstractItemView {
                color: #333333;
                background-color: white;
                selection-background-color: #007AFF;
                selection-color: white;
            }
        """
    
    def _apply_filters(self):
        """Apply current filter settings."""
        filters = {}
        
        # Date filters
        if self.date_from.text().strip():
            filters['date_from'] = self.date_from.text().strip()
        if self.date_to.text().strip():
            filters['date_to'] = self.date_to.text().strip()
        
        # Source filters
        selected_sources = []
        for source, checkbox in self.source_checkboxes.items():
            if checkbox.isChecked():
                selected_sources.append(source)
        if selected_sources:
            filters['sources'] = selected_sources
        
        # Journal filter
        if self.journal_input.text().strip():
            filters['journals'] = [self.journal_input.text().strip()]
        
        # Author filter
        if self.author_input.text().strip():
            filters['authors'] = [self.author_input.text().strip()]
        
        # Relevance filter
        relevance_text = self.relevance_combo.currentText()
        if relevance_text != "Any":
            filters['min_relevance'] = float(relevance_text.replace('+', ''))
        
        self.filters_changed.emit(filters)
        self.logger.debug("Filters applied", filters=filters)
    
    def _clear_filters(self):
        """Clear all filters."""
        self.date_from.clear()
        self.date_to.clear()
        self.journal_input.clear()
        self.author_input.clear()
        self.relevance_combo.setCurrentIndex(0)
        
        for checkbox in self.source_checkboxes.values():
            checkbox.setChecked(True)
        
        self.filters_changed.emit({})
        self.logger.debug("Filters cleared")


class SearchResultsTable(QTableWidget):
    """Table widget for displaying search results."""
    
    paper_selected = pyqtSignal(str)  # paper_id
    paper_context_menu = pyqtSignal(str, object)  # paper_id, position
    
    def __init__(self):
        super().__init__()
        self.logger = get_logger("search_results_table")
        self.papers = []
        self._setup_ui()
    
    def _setup_ui(self):
        """Set up the table UI."""
        # Table properties
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setSortingEnabled(True)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        
        # Columns
        columns = ["Title", "Authors", "Journal", "Date", "Source", "Relevance"]
        self.setColumnCount(len(columns))
        self.setHorizontalHeaderLabels(columns)
        
        # Column widths
        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)  # Title
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)  # Authors
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # Journal
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # Date
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)  # Source
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)  # Relevance
        
        # Styling
        self.setStyleSheet("""
            QTableWidget {
                background-color: white;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                gridline-color: #f0f0f0;
                font-size: 12px;
            }
            QTableWidget::item {
                padding: 8px;
                border-bottom: 1px solid #f5f5f5;
                color: #333333;
            }
            QTableWidget::item:selected {
                background-color: #e3f2fd;
                color: #1976d2;
            }
            QTableWidget::item:hover {
                background-color: #f8f8f8;
            }
            QHeaderView::section {
                background-color: #fafafa;
                border: none;
                border-bottom: 2px solid #e0e0e0;
                padding: 8px;
                font-weight: bold;
                color: #555;
            }
        """)
        
        # Connections
        self.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.customContextMenuRequested.connect(self._show_context_menu)
    
    def update_results(self, papers: List[Paper]):
        """Update table with new search results."""
        self.papers = papers
        self.setRowCount(len(papers))
        
        for row, paper in enumerate(papers):
            # Title
            title_item = QTableWidgetItem(paper.title or "Untitled")
            title_item.setData(Qt.ItemDataRole.UserRole, paper.id)
            title_item.setToolTip(paper.abstract or "No abstract available")
            self.setItem(row, 0, title_item)
            
            # Authors
            authors_text = ", ".join(paper.authors[:3]) if paper.authors else "Unknown"
            if len(paper.authors) > 3:
                authors_text += f" +{len(paper.authors) - 3} more"
            authors_item = QTableWidgetItem(authors_text)
            authors_item.setToolTip(", ".join(paper.authors))
            self.setItem(row, 1, authors_item)
            
            # Journal
            journal_item = QTableWidgetItem(paper.journal or "—")
            self.setItem(row, 2, journal_item)
            
            # Date
            date_text = paper.publication_date.strftime("%Y-%m-%d") if paper.publication_date else "—"
            date_item = QTableWidgetItem(date_text)
            self.setItem(row, 3, date_item)
            
            # Source
            source_item = QTableWidgetItem(paper.source.upper() if paper.source else "—")
            self.setItem(row, 4, source_item)
            
            # Relevance
            relevance_text = f"{paper.relevance_score:.2f}" if paper.relevance_score else "—"
            relevance_item = QTableWidgetItem(relevance_text)
            self.setItem(row, 5, relevance_item)
        
        self.logger.debug("Search results updated", count=len(papers))
    
    def _on_item_double_clicked(self, item):
        """Handle item double click."""
        row = item.row()
        if 0 <= row < len(self.papers):
            paper_id = self.papers[row].id
            self.paper_selected.emit(paper_id)
    
    def _show_context_menu(self, position):
        """Show context menu for table items."""
        item = self.itemAt(position)
        if item:
            row = item.row()
            if 0 <= row < len(self.papers):
                paper_id = self.papers[row].id
                global_position = self.mapToGlobal(position)
                self.paper_context_menu.emit(paper_id, global_position)


class PaperDetailWidget(QFrame):
    """Widget for displaying paper details."""
    
    def __init__(self):
        super().__init__()
        self.logger = get_logger("paper_detail")
        self.current_paper = None
        self._setup_ui()
    
    def _setup_ui(self):
        """Set up the detail widget UI."""
        self.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Title
        self.title_label = QLabel("Select a paper to view details")
        self.title_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #333333;
                padding-bottom: 10px;
            }
        """)
        self.title_label.setWordWrap(True)
        layout.addWidget(self.title_label)
        
        # Metadata
        self.metadata_label = QLabel("")
        self.metadata_label.setStyleSheet("""
            QLabel {
                font-size: 12px;
                color: #666666;
                padding-bottom: 10px;
            }
        """)
        layout.addWidget(self.metadata_label)
        
        # Abstract
        self.abstract_label = QLabel("Abstract")
        self.abstract_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                font-weight: bold;
                color: #333333;
                margin-top: 10px;
            }
        """)
        layout.addWidget(self.abstract_label)
        
        self.abstract_text = QTextEdit()
        self.abstract_text.setReadOnly(True)
        self.abstract_text.setStyleSheet("""
            QTextEdit {
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                padding: 10px;
                font-size: 13px;
                line-height: 1.4;
                color: #333333;
                background-color: #fafafa;
            }
        """)
        layout.addWidget(self.abstract_text)
        
        # Actions
        actions_layout = QHBoxLayout()
        
        self.view_full_button = QPushButton("📄 View Full Paper")
        self.view_full_button.setStyleSheet("""
            QPushButton {
                background-color: #007AFF;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0056D6;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.view_full_button.setEnabled(False)
        actions_layout.addWidget(self.view_full_button)
        
        self.similar_button = QPushButton("🔍 Find Similar")
        self.similar_button.setStyleSheet("""
            QPushButton {
                background-color: #34C759;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #28A745;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.similar_button.setEnabled(False)
        actions_layout.addWidget(self.similar_button)
        
        actions_layout.addStretch()
        layout.addLayout(actions_layout)
        
        layout.addStretch()
    
    def show_paper(self, paper: Paper):
        """Display paper details."""
        self.current_paper = paper
        
        # Update title
        self.title_label.setText(paper.title or "Untitled")
        
        # Update metadata
        metadata_parts = []
        if paper.authors:
            authors_text = ", ".join(paper.authors[:3])
            if len(paper.authors) > 3:
                authors_text += f" et al. ({len(paper.authors)} authors)"
            metadata_parts.append(f"Authors: {authors_text}")
        
        if paper.journal:
            metadata_parts.append(f"Journal: {paper.journal}")
        
        if paper.publication_date:
            metadata_parts.append(f"Published: {paper.publication_date.strftime('%Y-%m-%d')}")
        
        if paper.source:
            metadata_parts.append(f"Source: {paper.source.upper()}")
        
        if paper.relevance_score:
            metadata_parts.append(f"Relevance: {paper.relevance_score:.2f}")
        
        self.metadata_label.setText(" • ".join(metadata_parts))
        
        # Update abstract
        abstract_text = paper.abstract or "No abstract available."
        self.abstract_text.setPlainText(abstract_text)
        
        # Enable buttons
        self.view_full_button.setEnabled(bool(paper.local_pdf_path or paper.pdf_url))
        self.similar_button.setEnabled(True)
        
        self.logger.debug("Paper details displayed", paper_id=paper.id)
    
    def clear(self):
        """Clear the detail view."""
        self.current_paper = None
        self.title_label.setText("Select a paper to view details")
        self.metadata_label.setText("")
        self.abstract_text.setPlainText("")
        self.view_full_button.setEnabled(False)
        self.similar_button.setEnabled(False)


class SearchInterface(QWidget):
    """Main search interface widget."""
    
    # Signals
    search_performed = pyqtSignal(SearchResult)
    paper_selected = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.logger = get_logger("search_interface")
        self.current_filters = {}
        self.current_results = None
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Set up the search interface UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        # Search header
        header_layout = QVBoxLayout()
        
        title_label = QLabel("Literature Search")
        title_label.setStyleSheet("""
            QLabel {
                font-size: 24px;
                font-weight: bold;
                color: #333333;
                margin-bottom: 10px;
            }
        """)
        header_layout.addWidget(title_label)
        
        # Search bar
        search_layout = QHBoxLayout()
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(
            "Search literature... (e.g., 'protein folding machine learning', 'CRISPR gene editing')"
        )
        self.search_input.setStyleSheet("""
            QLineEdit {
                padding: 12px 16px;
                border: 2px solid #d0d0d0;
                border-radius: 8px;
                font-size: 16px;
                color: #000000;
                background-color: white;
            }
            QLineEdit:focus {
                border-color: #007AFF;
                color: #000000;
            }
        """)
        self.search_input.returnPressed.connect(self._perform_search)
        search_layout.addWidget(self.search_input)
        
        search_button = QPushButton("🔍 Search")
        search_button.setStyleSheet("""
            QPushButton {
                background-color: #007AFF;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 8px;
                font-size: 16px;
                font-weight: bold;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #0056D6;
            }
            QPushButton:pressed {
                background-color: #004AAD;
            }
        """)
        search_button.clicked.connect(self._perform_search)
        search_layout.addWidget(search_button)
        
        header_layout.addLayout(search_layout)
        layout.addLayout(header_layout)
        
        # Main content area
        content_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left side - Filters
        self.filters_widget = SearchFiltersWidget()
        self.filters_widget.setMaximumWidth(300)
        self.filters_widget.filters_changed.connect(self._on_filters_changed)
        content_splitter.addWidget(self.filters_widget)
        
        # Right side - Results and details
        results_splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Results section
        results_container = QWidget()
        results_layout = QVBoxLayout(results_container)
        results_layout.setContentsMargins(0, 0, 0, 0)
        
        # Results header
        results_header_layout = QHBoxLayout()
        
        self.results_label = QLabel("Search results will appear here")
        self.results_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                font-weight: bold;
                color: #333333;
            }
        """)
        results_header_layout.addWidget(self.results_label)
        
        results_header_layout.addStretch()
        
        # Export button
        export_button = QPushButton("📥 Export")
        export_button.setStyleSheet("""
            QPushButton {
                background-color: #f0f0f0;
                color: #333;
                border: 1px solid #d0d0d0;
                padding: 6px 12px;
                border-radius: 4px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
        """)
        results_header_layout.addWidget(export_button)
        
        results_layout.addLayout(results_header_layout)
        
        # Results table
        self.results_table = SearchResultsTable()
        self.results_table.paper_selected.connect(self._on_paper_selected)
        results_layout.addWidget(self.results_table)
        
        results_splitter.addWidget(results_container)
        
        # Paper detail
        self.paper_detail = PaperDetailWidget()
        results_splitter.addWidget(self.paper_detail)
        
        # Set splitter proportions (60% results, 40% details)
        results_splitter.setSizes([600, 400])
        
        content_splitter.addWidget(results_splitter)
        
        # Set main splitter proportions (25% filters, 75% results+details)
        content_splitter.setSizes([300, 900])
        
        layout.addWidget(content_splitter)
        
        # Progress bar (initially hidden)
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #d0d0d0;
                border-radius: 4px;
                text-align: center;
                font-size: 12px;
            }
            QProgressBar::chunk {
                background-color: #007AFF;
                border-radius: 3px;
            }
        """)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
    
    def _perform_search(self):
        """Perform search with current query and filters."""
        query_text = self.search_input.text().strip()
        
        if not query_text:
            self.logger.warning("Empty search query")
            return
        
        self.logger.info("Performing search", query=query_text, filters=self.current_filters)
        
        # Show progress
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate
        
        try:
            # Create search query
            search_query = SearchQuery(
                query=query_text,
                filters=self.current_filters,
                limit=100
            )
            
            # Perform search
            results = search_engine.search(search_query)
            
            # Update UI
            self._display_results(results)
            
            # Emit signal
            self.search_performed.emit(results)
            
        except Exception as e:
            self.logger.error("Search failed", error=str(e))
            self.results_label.setText(f"Search failed: {str(e)}")
            
        finally:
            self.progress_bar.setVisible(False)
    
    def _display_results(self, results: SearchResult):
        """Display search results."""
        self.current_results = results
        
        # Update results label
        self.results_label.setText(
            f"Found {results.total_count} papers "
            f"(showing {len(results.papers)}) "
            f"in {results.query_time:.3f}s"
        )
        
        # Update table
        self.results_table.update_results(results.papers)
        
        # Clear detail view
        self.paper_detail.clear()
        
        self.logger.info("Search results displayed", 
                        total=results.total_count,
                        shown=len(results.papers))
    
    def _on_filters_changed(self, filters: Dict[str, Any]):
        """Handle filter changes."""
        self.current_filters = filters
        self.logger.debug("Search filters updated", filters=filters)
        
        # Re-search if we have a query
        if self.search_input.text().strip():
            self._perform_search()
    
    def _on_paper_selected(self, paper_id: str):
        """Handle paper selection."""
        if self.current_results:
            # Find the paper
            for paper in self.current_results.papers:
                if paper.id == paper_id:
                    self.paper_detail.show_paper(paper)
                    self.paper_selected.emit(paper_id)
                    break
    
    def set_search_query(self, query: str):
        """Set search query from external source."""
        self.search_input.setText(query)
        if query.strip():
            self._perform_search()