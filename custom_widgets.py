import pandas as pd
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
                           QPushButton, QTableView, QAbstractItemView, QHeaderView,
                           QComboBox, QTabWidget, QMessageBox, QSpinBox, QSplitter, QLineEdit, QFileDialog,
                           QStyle, QGroupBox)
from PyQt5.QtCore import Qt, QAbstractTableModel, QModelIndex, QSize
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QApplication

class PandasModel(QAbstractTableModel):
    """Model for displaying Pandas DataFrame in QTableView"""
    
    def __init__(self, data):
        super().__init__()
        self._data = data

    def rowCount(self, parent=None):
        return self._data.shape[0]

    def columnCount(self, parent=None):
        return self._data.shape[1]

    def data(self, index, role=Qt.DisplayRole):
        if index.isValid():
            if role == Qt.DisplayRole:
                value = self._data.iloc[index.row(), index.column()]
                # Format different data types appropriately
                if isinstance(value, pd.Series):
                    # Handle Series objects by returning a string representation
                    return str(value.values)
                elif hasattr(value, '__iter__') and not isinstance(value, str):
                    # Handle other iterable values like arrays or lists
                    return str(value)
                elif pd.isna(value):
                    return ""
                elif isinstance(value, float):
                    # Format floats with 2 decimal places
                    try:
                        return f"{float(value):.2f}"
                    except:
                        return str(value)
                else:
                    return str(value)
            elif role == Qt.TextAlignmentRole:
                value = self._data.iloc[index.row(), index.column()]
                # Right align numbers
                if isinstance(value, (int, float)) or pd.api.types.is_numeric_dtype(type(value)):
                    return Qt.AlignRight | Qt.AlignVCenter
        return None

    def headerData(self, section, orientation, role):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return str(self._data.columns[section])
        elif orientation == Qt.Vertical and role == Qt.DisplayRole:
            try:
                return str(self._data.index[section])
            except:
                return str(section + 1)
        return None

class DataFrameViewer(QWidget):
    """Widget for viewing Pandas DataFrames with filtering capabilities"""
    
    def __init__(self, df=None, parent=None):
        super().__init__(parent)
        self.df = df
        self.filtered_df = df
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Collapsible filter controls
        self.filter_group = QGroupBox("🔍 Arama / Filtrele")
        self.filter_group.setCheckable(True)
        self.filter_group.setChecked(False)  # Varsayılan olarak kapalı
        self.filter_group.setStyleSheet("QGroupBox { font-weight: bold; font-size: 11pt; border: 1px solid #e0e0e0; border-radius: 6px; margin-top: 6px; padding: 4px 8px; background: #f8f9fa; } QGroupBox::indicator { width: 18px; height: 18px; }")
        self.filter_group.toggled.connect(lambda checked: self.filter_panel.setVisible(checked))

        self.filter_panel = QWidget()
        filter_layout = QHBoxLayout(self.filter_panel)
        filter_layout.setContentsMargins(10, 10, 10, 10)
        filter_layout.setSpacing(10)
        
        # Column selector
        column_label = QLabel("Sütun:")
        column_label.setStyleSheet("font-weight: bold;")
        self.column_selector = QComboBox()
        self.column_selector.setMinimumWidth(150)
        self.column_selector.setStyleSheet("""
            QComboBox {
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                padding: 5px 10px;
                background-color: white;
            }
            QComboBox:hover {
                border-color: #bdbdbd;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 20px;
                border-left: none;
            }
        """)
        self.column_selector.currentIndexChanged.connect(self.update_filter_values)
        filter_layout.addWidget(column_label)
        filter_layout.addWidget(self.column_selector)
        
        # Value selector
        value_label = QLabel("Değer:")
        value_label.setStyleSheet("font-weight: bold;")
        self.value_selector = QComboBox()
        self.value_selector.setMinimumWidth(200)
        self.value_selector.setStyleSheet("""
            QComboBox {
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                padding: 5px 10px;
                background-color: white;
            }
            QComboBox:hover {
                border-color: #bdbdbd;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 20px;
                border-left: none;
            }
        """)
        filter_layout.addWidget(value_label)
        filter_layout.addWidget(self.value_selector)
        
        # Apply filter button
        self.apply_btn = QPushButton("Filtre Uygula")
        self.apply_btn.setStyleSheet("""
            QPushButton {
                background-color: #26a69a;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #00897b;
            }
            QPushButton:pressed {
                background-color: #00796b;
            }
        """)
        self.apply_btn.clicked.connect(self.apply_filter)
        filter_layout.addWidget(self.apply_btn)
        
        # Clear filter button
        self.clear_btn = QPushButton("Filtreyi Temizle")
        self.clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #ff7043;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #f4511e;
            }
            QPushButton:pressed {
                background-color: #e64a19;
            }
        """)
        self.clear_btn.clicked.connect(self.clear_filter)
        filter_layout.addWidget(self.clear_btn)
        
        filter_layout.addStretch()
        
        # Row count label
        self.row_count_label = QLabel("Satır sayısı: 0")
        self.row_count_label.setStyleSheet("font-weight: bold; color: #616161; padding: 5px 10px; background-color: #f5f5f5; border-radius: 4px;")
        filter_layout.addWidget(self.row_count_label)
        
        # Paneli groupbox'a ekle
        self.filter_group.setLayout(QVBoxLayout())
        self.filter_group.layout().addWidget(self.filter_panel)
        self.filter_panel.setVisible(False)
        layout.addWidget(self.filter_group)
        
        # Table view
        self.table_view = QTableView()
        self.table_view.setSortingEnabled(True)
        self.table_view.setAlternatingRowColors(True)
        self.table_view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_view.setStyleSheet("""
            QTableView {
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                background-color: white;
                gridline-color: #f0f0f0;
                selection-background-color: #e3f2fd;
                selection-color: #212121;
                alternate-background-color: #fafafa;
            }
            QTableView::item {
                padding: 6px;
                border: none;
            }
            QHeaderView::section {
                background-color: #f5f5f5;
                padding: 8px;
                border: none;
                border-bottom: 1px solid #e0e0e0;
                font-weight: bold;
            }
        """)
        layout.addWidget(self.table_view)
        
        # Update UI if DataFrame is provided
        if self.df is not None:
            self.set_dataframe(self.df)
    
    def set_dataframe(self, df):
        """Set the DataFrame and update the UI"""
        self.df = df
        self.filtered_df = df
        
        # Update column selector
        self.column_selector.clear()
        if df is not None:
            for column in df.columns:
                self.column_selector.addItem(column)
        
        # Update the table view
        self.update_table_view()
        
        # Update row count
        self.update_row_count()
    
    def update_filter_values(self):
        """Update the filter values based on the selected column"""
        if self.df is None:
            return
        
        self.value_selector.clear()
        
        # Get the selected column
        column = self.column_selector.currentText()
        if not column:
            return
        
        # Add an 'All' option
        self.value_selector.addItem("Tümü")
        
        # Get unique values from the column
        try:
            unique_values = sorted(self.df[column].dropna().unique())
            for value in unique_values:
                self.value_selector.addItem(str(value))
        except:
            # Handle errors (e.g., if column doesn't exist)
            pass
    
    def apply_filter(self):
        """Apply the selected filter"""
        if self.df is None:
            return
        
        column = self.column_selector.currentText()
        value_text = self.value_selector.currentText()
        
        if value_text == "Tümü":
            # Show all values
            self.filtered_df = self.df
        else:
            # Filter the DataFrame
            try:
                # Handle different data types appropriately
                col_dtype = self.df[column].dtype
                if pd.api.types.is_numeric_dtype(col_dtype):
                    try:
                        # Try to convert to numeric
                        value = float(value_text)
                    except:
                        value = value_text
                else:
                    value = value_text
                
                # Apply the filter
                self.filtered_df = self.df[self.df[column] == value]
            except Exception as e:
                QMessageBox.warning(self, "Filtre Hatası", str(e))
                return
        
        # Update the table view
        self.update_table_view()
        
        # Update row count
        self.update_row_count()
    
    def clear_filter(self):
        """Clear the filter and show all data"""
        self.filtered_df = self.df
        self.update_table_view()
        self.update_row_count()
    
    def update_table_view(self):
        """Update the table view with the current (filtered) DataFrame"""
        if self.filtered_df is None:
            return
        
        model = PandasModel(self.filtered_df)
        self.table_view.setModel(model)
        
        # Auto-resize columns to content
        self.table_view.resizeColumnsToContents()
        
        # Limit column width to avoid very wide columns
        for i in range(model.columnCount()):
            width = min(self.table_view.columnWidth(i), 300)
            self.table_view.setColumnWidth(i, width)
    
    def update_row_count(self):
        """Update the row count label"""
        count = 0 if self.filtered_df is None else len(self.filtered_df)
        total = 0 if self.df is None else len(self.df)
        self.row_count_label.setText(f"Satır sayısı: {count} / {total}")

class CheckResultsWidget(QWidget):
    """Widget for displaying check results"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Tabs for different views of results
        self.tabs = QTabWidget()
        
        # Raw data view tab
        self.data_tab = QWidget()
        data_layout = QVBoxLayout(self.data_tab)
        
        # Results list and detail views
        self.results_splitter = QSplitter(Qt.Vertical)
        
        # Top: Results list
        self.results_list = QListWidget()
        self.results_list.setSelectionMode(QAbstractItemView.SingleSelection)
        self.results_list.itemClicked.connect(self.on_result_item_clicked)
        self.results_splitter.addWidget(self.results_list)
        
        # Bottom: Detail view
        self.details_view = QTableView()
        self.details_view.setAlternatingRowColors(True)
        self.details_view.setSortingEnabled(True)
        self.results_splitter.addWidget(self.details_view)
        
        # Set size proportions
        self.results_splitter.setSizes([100, 300])
        data_layout.addWidget(self.results_splitter)
        
        # Details tab
        self.details_tab = QWidget()
        details_layout = QVBoxLayout(self.details_tab)
        
        # Statistics table
        self.stats_view = QTableView()
        self.stats_view.setAlternatingRowColors(True)
        details_layout.addWidget(QLabel("Özet İstatistikler:"))
        details_layout.addWidget(self.stats_view)
        
        # Summary table
        self.summary_view = QTableView()
        self.summary_view.setAlternatingRowColors(True)
        details_layout.addWidget(QLabel("Özet Sonuçlar:"))
        details_layout.addWidget(self.summary_view)
        
        # Export to Excel button for details
        details_export_layout = QHBoxLayout()
        details_export_layout.setContentsMargins(5, 5, 5, 5)
        details_export_layout.addStretch()
        self.details_export_btn = QPushButton("Detayları Excel'e Aktar")
        self.details_export_btn.clicked.connect(self.export_details_to_excel)
        details_export_layout.addWidget(self.details_export_btn)
        details_layout.addLayout(details_export_layout)
        
        # HTML report tab
        self.html_tab = QWidget()
        html_layout = QVBoxLayout(self.html_tab)
        
        self.html_view = QWebEngineView()
        html_layout.addWidget(self.html_view)
        
        # Add all tabs to the tab widget
        self.tabs.addTab(self.data_tab, "Veri Görünümü")
        self.tabs.addTab(self.details_tab, "Detaylar")
        self.tabs.addTab(self.html_tab, "Görsel Rapor")
        
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(self.tabs)
        
        # Store check results
        self.check_results = {}
        self.current_result = None
        
    def set_check_results(self, results, source_df=None):
        """Set check results data and update the UI"""
        self.check_results = results
        
        # Clear previous results
        self.results_list.clear()
        self.clear_details()
        
        # Add results to the list
        for check_name, check_result in results.items():
            status = check_result.get("status", "")
            item = QListWidgetItem(check_name)
            
            # Set color based on status
            if status == "ok":
                item.setForeground(QColor("green"))
                item.setIcon(self.style().standardIcon(QStyle.SP_DialogApplyButton))
            elif status == "warning":
                item.setForeground(QColor("orange"))
                item.setIcon(self.style().standardIcon(QStyle.SP_MessageBoxWarning))
            elif status == "error":
                item.setForeground(QColor("red"))
                item.setIcon(self.style().standardIcon(QStyle.SP_MessageBoxCritical))
            
            # Store check result as item data
            item.setData(Qt.UserRole, check_name)
            
            self.results_list.addItem(item)
        
        # Select the first item if available
        if self.results_list.count() > 0:
            self.results_list.setCurrentRow(0)
            self.on_result_item_clicked(self.results_list.item(0))
            
    def on_result_item_clicked(self, item):
        """Show details for the selected check result"""
        if item is None:
            return
        
        check_name = item.data(Qt.UserRole)
        if check_name in self.check_results:
            self.current_result = self.check_results[check_name]
            
            # Show details if available
            if "data" in self.current_result and self.current_result["data"] is not None:
                    self.show_details(self.current_result["data"])
            
            # Show HTML report if available
            if "html_report" in self.current_result:
                self.set_html_report(self.current_result["html_report"])
            
            # Show summary if available
            if "summary" in self.current_result:
                self.show_summary(self.current_result["summary"])
            
    def show_details(self, data):
        """Show data details in the table view"""
        if isinstance(data, pd.DataFrame):
            model = PandasModel(data)
            self.details_view.setModel(model)
            self.details_view.resizeColumnsToContents()
            
            # Enable sorting
            self.details_view.setSortingEnabled(True)
            
    def set_html_report(self, html_content):
        """Set HTML content for the report view"""
        if html_content:
            self.html_view.setHtml(html_content)
            
            # HTML rapor sekmesine geçiş yap ve görünür olduğundan emin ol
            if hasattr(self, 'detail_tabs'):
                self.detail_tabs.setCurrentIndex(0)  # HTML sekmesi
            elif hasattr(self, 'tabs'):
                self.tabs.setCurrentWidget(self.html_tab)
            
    def show_summary(self, summary_data):
        """Show summary data if available"""
        if isinstance(summary_data, pd.DataFrame):
            # You can add summary display logic here if needed
            pass
    
    def export_to_excel(self):
        """Export all results to Excel"""
        if not self.current_result:
            QMessageBox.warning(self, "Uyarı", "Aktarılacak veri bulunamadı")
            return
        
        # Get file save location
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Excel Dosyasını Kaydet", "", "Excel Files (*.xlsx)"
        )
        
        if file_path:
            try:
                # Add .xlsx extension if not provided
                if not file_path.lower().endswith('.xlsx'):
                    file_path += '.xlsx'
                
                # Create Excel writer
                with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                    # Write data if available
                    if "data" in self.current_result and isinstance(self.current_result["data"], pd.DataFrame):
                        self.current_result["data"].to_excel(writer, sheet_name='Veri Detayları', index=False)
                    
                    # If summary exists, write to another sheet
                    if "summary" in self.current_result and isinstance(self.current_result["summary"], pd.DataFrame):
                        self.current_result["summary"].to_excel(writer, sheet_name='Özet', index=True)
                
                QMessageBox.information(self, "Bilgi", f"Veriler başarıyla Excel dosyasına aktarıldı:\n{file_path}")
                
            except Exception as e:
                QMessageBox.critical(self, "Hata", f"Excel'e aktarma hatası: {str(e)}")
    
    def export_details_to_excel(self):
        """Export details data to Excel"""
        if not self.current_result or "data" not in self.current_result:
            QMessageBox.warning(self, "Uyarı", "Aktarılacak veri bulunamadı")
            return
        
        data = self.current_result["data"]
        if not isinstance(data, pd.DataFrame):
            QMessageBox.warning(self, "Uyarı", "Aktarılacak veri DataFrame formatında değil")
            return
        
        # Get file save location
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Detay Verileri Excel'e Kaydet", "", "Excel Files (*.xlsx)"
        )
        
        if file_path:
            try:
                # Add .xlsx extension if not provided
                if not file_path.lower().endswith('.xlsx'):
                    file_path += '.xlsx'
                
                # Export to Excel
                data.to_excel(file_path, index=False)
                QMessageBox.information(self, "Bilgi", f"Detay verileri başarıyla Excel dosyasına aktarıldı:\n{file_path}")
                
            except Exception as e:
                QMessageBox.critical(self, "Hata", f"Excel'e aktarma hatası: {str(e)}")
    
    def clear_details(self):
        """Clear all detail views"""
        self.details_view.setModel(None)
        self.stats_view.setModel(None)
        self.summary_view.setModel(None)
        self.html_view.setHtml("")

    def add_results(self, results, html_content=None):
        """Add new results to the widget"""
        # Store the results
        self.check_results.update(results)
        
        # Add to results list
        for check_name, check_result in results.items():
            # Check if item already exists
            existing_items = [self.results_list.item(i) for i in range(self.results_list.count())]
            existing_names = [item.data(Qt.UserRole) for item in existing_items if item]
            
            if check_name not in existing_names:
                status = check_result.get("status", "")
                item = QListWidgetItem(check_name)
                
                # Set color based on status
                if status == "ok":
                    item.setForeground(QColor("green"))
                    item.setIcon(self.style().standardIcon(QStyle.SP_DialogApplyButton))
                elif status == "warning":
                    item.setForeground(QColor("orange"))
                    item.setIcon(self.style().standardIcon(QStyle.SP_MessageBoxWarning))
                elif status == "error":
                    item.setForeground(QColor("red"))
                    item.setIcon(self.style().standardIcon(QStyle.SP_MessageBoxCritical))
                else:
                    item.setIcon(self.style().standardIcon(QStyle.SP_FileDialogDetailedView))
                
                # Store check result as item data
                item.setData(Qt.UserRole, check_name)
                self.results_list.addItem(item)
        
        # If HTML content is provided, add it to the result
        if html_content and results:
            first_result_name = list(results.keys())[0]
            if first_result_name in self.check_results:
                self.check_results[first_result_name]["html_report"] = html_content
        
        # Select the newly added item
        if results:
            new_result_name = list(results.keys())[0]
            for i in range(self.results_list.count()):
                item = self.results_list.item(i)
                if item and item.data(Qt.UserRole) == new_result_name:
                    self.results_list.setCurrentItem(item)
                    self.on_result_item_clicked(item)
                    break