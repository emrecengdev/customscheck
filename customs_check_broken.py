import os
import sys
import pandas as pd
import numpy as np
from PyQt5.QtWidgets import (QApplication, QMainWindow, QFileDialog, QTabWidget, 
                            QWidget, QVBoxLayout, QPushButton, QLabel, QTableView,
                            QHBoxLayout, QMessageBox, QProgressBar, QComboBox,
                            QListWidget, QGridLayout, QSplitter, QSizePolicy, QDialog, QDialogButtonBox, QAbstractItemView,
                            QSpinBox, QFrame, QTableWidget, QTableWidgetItem, QScrollArea)
from PyQt5.QtCore import Qt, QSize, QThread, pyqtSignal, QTimer
from PyQt5 import QtGui
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.backends.backend_qt5agg import FigureCanvas
from matplotlib.figure import Figure
import time

# Import XML processing functions from existing code
from xml_processor import extract_beyanname_fixed, process_all_xml_files, process_multiple_xml_files, merge_dataframes
from custom_widgets import PandasModel, DataFrameViewer, CheckResultsWidget

# Import analysis modules
from analysis_modules import (
    # Basic checks
    calculate_basic_stats, check_missing_values, check_duplicate_rows,
    check_value_consistency, check_numeric_range,
    
    # Analysis functions
    check_weight_consistency, check_currency_values, check_vergi_consistency,
    check_alici_satici_relationship,
    check_gtip_urun_kodu_consistency, check_rarely_used_currency,
    check_rarely_used_origin_country, check_rarely_used_origin_country_by_sender_gtip,
    check_rarely_used_payment_method,
    check_unit_price_increase, check_kdv_consistency,
    check_domestic_expense_variation, check_foreign_expense_variation,
    check_supalan_storage,
    
    # Summary functions
                     create_gtip_summary, create_country_summary, create_rejim_summary,
    create_gtip_country_cross,
    
    # Chart functions
    create_bar_chart, create_pie_chart,
    
    # UI components
    PivotWidget, ChartWidget
)

# Import specific modules
from analysis_modules.islem_niteligi_tutarlilik import kontrol_islem_niteligi_tutarlilik

# Örnekleme modülünü içe aktar
from sampling import BeyannameSampling

# QThread sınıfı ekliyorum (Excel işlemini arka planda yapacak)
class ExcelExportThread(QThread):
    # Sinyaller
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(bool, str, str)  # başarı/başarısız, mesaj, dosya yolu
    
    def __init__(self, sampling_tool, file_path):
        super().__init__()
        self.sampling_tool = sampling_tool
        self.file_path = file_path
        self.is_cancelled = False
    
    def run(self):
        try:
            # İlerleme bilgisi
            self.progress.emit(20, "Excel dosyası hazırlanıyor...")
            
            # Güvenlik kontrolü - timeout ekleme
            self.timer = QTimer()
            self.timer.setSingleShot(True)
            self.timer.timeout.connect(self.handle_timeout)
            self.timer.start(60000)  # 60 saniyelik timeout
            
            # Excel'e aktarma
            try:
                output_path = self.sampling_tool.export_to_excel(self.file_path)
                if self.is_cancelled:
                    return
                
                self.progress.emit(70, "Excel formatlanıyor...")
                
                # Excel dosyasını formatla
                self.sampling_tool.format_excel_report(output_path)
                if self.is_cancelled:
                    return
                
                # İşlem başarılı
                self.finished.emit(True, f"Örnekleme sonuçları Excel'e aktarıldı: {output_path}", output_path)
                
            except Exception as e:
                import traceback
                error_details = traceback.format_exc()
                print(f"Excel aktarma detaylı hata: {error_details}")
                
                error_msg = str(e)
                # Hata mesajını daha anlaşılır hale getir
                if "PermissionError" in error_details:
                    error_msg = f"Dosya erişim hatası: {self.file_path}\nDosya başka bir program tarafından kullanılıyor olabilir."
                elif "FileNotFoundError" in error_details:
                    error_msg = f"Dosya yolu bulunamadı: {self.file_path}"
                
                self.finished.emit(False, f"Excel'e aktarma hatası: {error_msg}", "")
            
            # Timer'ı durdur
            self.timer.stop()
                
        except Exception as e:
            # Genel hata durumunda
            import traceback
            print(f"Excel thread beklenmeyen hata: {str(e)}")
            print(traceback.format_exc())
            self.finished.emit(False, f"Beklenmeyen hata: {str(e)}", "")
    
    def handle_timeout(self):
        """İşlem zaman aşımına uğradığında çağrılır"""
        self.is_cancelled = True
        self.terminate()  # Thread'i sonlandır
        self.finished.emit(False, "İşlem zaman aşımına uğradı. Excel çok büyük olabilir.", "")
    
    def cancel(self):
        """İşlemi iptal et"""
        self.is_cancelled = True
        self.timer.stop()
        self.terminate()

class CustomsCheckApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Beyanname Kontrol Uygulaması")
        self.setGeometry(100, 100, 1200, 800)
        
        # Store loaded data
        self.all_dataframes = {}
        self.current_df = None
        self.merged_df = None  # Birleştirilmiş tüm veriler için
        
        # Excel thread değişkeni
        self.excel_thread = None
        self.cancel_dialog = None
        
        # Set application style
        self.apply_modern_style()
        
        self.init_ui()
        
        # Stabilite ayarları
        self.setup_application_stability()
        
        # Kısayol tuşlarını ayarla
        self.setup_shortcuts()
    
    def apply_modern_style(self):
        """Apply modern Apple-style theme to the application"""
        style_sheet = """
        /* Modern Apple-like Theme */
        QMainWindow {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #f8fafb, stop:1 #e8edf2);
            color: #1c1e21;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
        }
        
        /* Modern Tab Widget */
        QTabWidget {
            background: transparent;
            border: none;
        }
        
        QTabWidget::pane {
            background: rgba(255, 255, 255, 0.95);
            border: 1px solid rgba(0, 0, 0, 0.1);
            border-radius: 12px;
            margin: 0px;
            padding: 0px;
        }
        
        QTabWidget::tab-bar {
            left: 15px;
            top: 5px;
        }
        
        QTabBar::tab {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 rgba(255, 255, 255, 0.9), stop:1 rgba(248, 250, 251, 0.8));
            border: 1px solid rgba(0, 0, 0, 0.08);
            border-bottom: none;
            border-radius: 8px 8px 0px 0px;
            padding: 12px 24px;
            margin-right: 2px;
            margin-top: 3px;
            color: #4a5568;
            font-weight: 500;
            font-size: 13px;
            min-width: 120px;
        }
        
        QTabBar::tab:selected {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #ffffff, stop:1 #f7fafc);
            color: #2d3748;
            font-weight: 600;
            border-color: rgba(0, 0, 0, 0.1);
            margin-top: 0px;
        }
        
        QTabBar::tab:hover:!selected {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 rgba(255, 255, 255, 0.95), stop:1 rgba(247, 250, 252, 0.9));
            border-color: rgba(0, 0, 0, 0.12);
        }
        
        /* Modern Buttons */
        QPushButton {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #4299e1, stop:1 #3182ce);
            border: 1px solid rgba(49, 130, 206, 0.6);
            border-radius: 8px;
            padding: 10px 20px;
            color: white;
            font-weight: 600;
            font-size: 13px;
            min-height: 16px;
        }
        
        QPushButton:hover {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #3182ce, stop:1 #2c5aa0);
            border-color: rgba(44, 90, 160, 0.8);
        }
        
        QPushButton:pressed {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #2c5aa0, stop:1 #2a4d8f);
        }
        
        QPushButton[class="primary"] {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #4299e1, stop:1 #3182ce);
            border-color: rgba(49, 130, 206, 0.6);
        }
        
        QPushButton[class="success"] {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #48bb78, stop:1 #38a169);
            border-color: rgba(56, 161, 105, 0.6);
        }
        
        QPushButton[class="danger"] {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #f56565, stop:1 #e53e3e);
            border-color: rgba(229, 62, 62, 0.6);
        }
        
        /* Modern Inputs */
        QComboBox, QSpinBox, QLineEdit {
            background: rgba(255, 255, 255, 0.9);
            border: 1px solid rgba(226, 232, 240, 0.8);
            border-radius: 6px;
            padding: 8px 12px;
            font-size: 13px;
            color: #2d3748;
        }
        
        QComboBox:focus, QSpinBox:focus, QLineEdit:focus {
            border-color: #4299e1;
            background: rgba(255, 255, 255, 0.95);
        }
        
        /* Modern Tables */
        QTableView, QTableWidget {
            background: rgba(255, 255, 255, 0.95);
            border: 1px solid rgba(226, 232, 240, 0.8);
            border-radius: 8px;
            gridline-color: rgba(226, 232, 240, 0.6);
            selection-background-color: rgba(66, 153, 225, 0.2);
        }
        
        QTableView::item {
            padding: 8px;
            border: none;
        }
        
        QHeaderView::section {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 rgba(247, 250, 252, 0.95), stop:1 rgba(237, 242, 247, 0.9));
            border: 1px solid rgba(226, 232, 240, 0.8);
            border-radius: 0px;
            padding: 10px 8px;
            font-weight: 600;
            font-size: 12px;
            color: #4a5568;
        }
        
        /* Modern Progress Bar */
        QProgressBar {
            background: rgba(237, 242, 247, 0.8);
            border: 1px solid rgba(203, 213, 224, 0.6);
            border-radius: 8px;
            text-align: center;
            font-weight: 500;
            font-size: 12px;
            color: #2d3748;
        }
        
        QProgressBar::chunk {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #4299e1, stop:1 #63b3ed);
            border-radius: 6px;
        }
        
        /* Modern Labels */
        QLabel {
            color: #2d3748;
            font-size: 13px;
        }
        
        /* Modern Scroll Bars */
        QScrollBar:vertical {
            background: rgba(237, 242, 247, 0.6);
            width: 12px;
            border-radius: 6px;
            margin: 0px;
        }
        
        QScrollBar::handle:vertical {
            background: rgba(160, 174, 192, 0.8);
            border-radius: 6px;
            min-height: 20px;
        }
        
        QScrollBar::handle:vertical:hover {
            background: rgba(113, 128, 150, 0.9);
        }
        
        /* Modern Group Box */
        QGroupBox {
            background: rgba(255, 255, 255, 0.9);
            border: 1px solid rgba(226, 232, 240, 0.8);
            border-radius: 12px;
            margin-top: 20px;
            padding-top: 10px;
            font-weight: 600;
            font-size: 14px;
            color: #2d3748;
        }
        
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 15px;
            top: 8px;
            background: rgba(255, 255, 255, 0.95);
            padding: 4px 12px;
            border-radius: 6px;
            border: 1px solid rgba(226, 232, 240, 0.8);
        }
        
        /* Modern Menu Bar */
        QMenuBar {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 rgba(255, 255, 255, 0.98), stop:1 rgba(248, 250, 251, 0.95));
            border-bottom: 1px solid rgba(226, 232, 240, 0.8);
            padding: 4px 8px;
            font-size: 13px;
            font-weight: 500;
        }
        
        QMenuBar::item {
            background: transparent;
            padding: 8px 16px;
            border-radius: 6px;
            color: #4a5568;
        }
        
        QMenuBar::item:selected {
            background: rgba(190, 227, 248, 0.6);
            color: #2d3748;
        }
        
        /* Modern Context Menu */
        QMenu {
            background: rgba(255, 255, 255, 0.98);
            border: 1px solid rgba(0, 0, 0, 0.1);
            border-radius: 8px;
            padding: 4px;
            font-size: 13px;
        }
        
        QMenu::item {
            background: transparent;
            padding: 8px 16px;
            border-radius: 4px;
            color: #2d3748;
        }
        
        QMenu::item:selected {
            background: rgba(190, 227, 248, 0.8);
        }
        
        QMenu::separator {
            height: 1px;
            background: rgba(226, 232, 240, 0.8);
            margin: 4px 8px;
        }
        """
        self.setStyleSheet(style_sheet)
        
    def init_ui(self):
        """Initialize the user interface"""
        # Main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Top control panel
        control_panel = QWidget()
        control_panel.setObjectName("controlPanel")
        control_panel.setStyleSheet("""
            #controlPanel {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(255, 255, 255, 0.98), stop:1 rgba(248, 250, 251, 0.95));
                border: 1px solid rgba(226, 232, 240, 0.8);
                border-radius: 16px;
                padding: 15px;
                margin: 10px;
            }
        """)
        control_layout = QHBoxLayout(control_panel)
        control_layout.setContentsMargins(10, 10, 10, 10)
        control_layout.setSpacing(10)
        
        # Import XML button
        import_xml_btn = QPushButton("📁 XML Dosyası İçe Aktar")
        import_xml_btn.setProperty("class", "primary")
        import_xml_btn.clicked.connect(self.import_xml)
        control_layout.addWidget(import_xml_btn)
        
        # Import XML folder button
        import_folder_btn = QPushButton("📂 XML Klasörü İçe Aktar")
        import_folder_btn.setProperty("class", "primary")
        import_folder_btn.clicked.connect(self.import_xml_folder)
        control_layout.addWidget(import_folder_btn)
        
        # Batch import XML folder button
        batch_import_btn = QPushButton("⚡ Toplu XML İçe Aktar")
        batch_import_btn.setProperty("class", "success")
        batch_import_btn.clicked.connect(self.import_xml_folder)
        control_layout.addWidget(batch_import_btn)
        
        # Merge all dataframes button
        merge_all_btn = QPushButton("🔗 Tümünü Birleşik Göster")
        merge_all_btn.setProperty("class", "warning")
        merge_all_btn.clicked.connect(self.show_merged_dataframes)
        control_layout.addWidget(merge_all_btn)
        
        # File selector dropdown (will be populated after import)
        self.file_selector = QComboBox()
        self.file_selector.setMinimumWidth(300)
        self.file_selector.currentIndexChanged.connect(self.change_active_file)
        control_layout.addWidget(QLabel("Aktif Dosya:"))
        control_layout.addWidget(self.file_selector)
        
        # Status label
        self.status_label = QLabel("Henüz veri yüklenmedi")
        self.status_label.setStyleSheet("color: #757575; font-style: italic;")
        control_layout.addStretch()
        control_layout.addWidget(self.status_label)
        
        main_layout.addWidget(control_panel)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)
        
        # Tab widget for different views
        self.tabs = QTabWidget()
        self.tabs.setContentsMargins(0, 10, 0, 0)
        
        # Data tab
        self.data_tab = QWidget()
        data_layout = QVBoxLayout(self.data_tab)
        data_layout.setContentsMargins(10, 10, 10, 10)
        
        # Use DataFrameViewer instead of QTableView
        self.data_viewer = DataFrameViewer()
        data_layout.addWidget(self.data_viewer)
        
        self.tabs.addTab(self.data_tab, "Veri Görünümü")
        
        # Initialize pivot and chart widgets (these were missing)
        self.pivot_widget = PivotWidget()
        self.chart_widget = ChartWidget()
        
        # Analysis tab (sol panel + sağ panel)
        self.analysis_tab = QWidget()
        analysis_layout = QHBoxLayout(self.analysis_tab)
        analysis_layout.setContentsMargins(0, 0, 0, 0)
        
        self.left_panel = QFrame()
        self.left_panel.setFixedWidth(220)
        self.left_panel.setStyleSheet("""
            QFrame { 
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(255, 255, 255, 0.95), stop:1 rgba(248, 250, 251, 0.9));
                border: 1px solid rgba(226, 232, 240, 0.8);
                border-radius: 16px 0px 0px 16px;
                padding: 8px;
            }
            QPushButton {
                text-align: left;
                padding: 12px 16px;
                margin: 4px 0px;
                border-radius: 8px;
                font-weight: 500;
                font-size: 13px;
            }
            QLabel {
                font-weight: 600;
                font-size: 12px;
                color: #4a5568;
                text-transform: uppercase;
                letter-spacing: 0.5px;
                margin: 8px 0px 4px 0px;
            }
        """)
        
        left_layout = QVBoxLayout(self.left_panel)
        left_layout.setContentsMargins(12, 18, 8, 8)
        left_layout.setSpacing(10)
        
        left_layout.addWidget(QLabel("Temel Kontroller:"))
        
        # Tümünü Çalıştır butonu
        btn_run_all = QPushButton("🚀 Tümünü Çalıştır")
        btn_run_all.setProperty("class", "success")
        btn_run_all.clicked.connect(self.run_all_checks_auto)
        btn_run_all.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #4CAF50, stop:1 #45a049);
                color: white;
                font-weight: bold;
                border: none;
                padding: 14px 16px;
                margin: 6px 0px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #45a049, stop:1 #3d8b40);
            }
        """)
        left_layout.addWidget(btn_run_all)
        
        # Excel'e Aktar butonu
        btn_export_all = QPushButton("📊 Tüm Sonuçları Excel'e Aktar")
        btn_export_all.setProperty("class", "primary")
        btn_export_all.clicked.connect(self.export_all_results_to_excel)
        btn_export_all.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2196F3, stop:1 #1976D2);
                color: white;
                font-weight: bold;
                border: none;
                padding: 14px 16px;
                margin: 6px 0px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1976D2, stop:1 #1565C0);
            }
        """)
        left_layout.addWidget(btn_export_all)
        
        left_layout.addSpacing(10)
        left_layout.addWidget(QLabel("Bireysel Kontroller:"))
        
        btn_islem = QPushButton("🔍 İşlem Niteliği")
        btn_islem.clicked.connect(self.check_islem_niteligi_consistency)
        left_layout.addWidget(btn_islem)
        
        btn_gtip_tanim_detail = QPushButton("🔍 GTİP-Tanım Detay")
        btn_gtip_tanim_detail.clicked.connect(self.check_gtip_tanim_detail)
        left_layout.addWidget(btn_gtip_tanim_detail)
        
        btn_gtip_urun = QPushButton("🏷️ GTİP-Ürün Kodu")
        btn_gtip_urun.clicked.connect(self.check_gtip_urun_kodu_consistency)
        left_layout.addWidget(btn_gtip_urun)
        
        btn_alici_satici = QPushButton("🤝 Alıcı-Satıcı İlişkisi")
        btn_alici_satici.clicked.connect(self.check_alici_satici_relationship)
        left_layout.addWidget(btn_alici_satici)
        
        left_layout.addSpacing(10)
        left_layout.addWidget(QLabel("İstatistiksel Kontroller:"))
        
        btn_nadir_doviz = QPushButton("💱 Nadir Döviz")
        btn_nadir_doviz.clicked.connect(self.check_rarely_used_currency)
        left_layout.addWidget(btn_nadir_doviz)
        
        btn_nadir_ulke = QPushButton("🌍 Nadir Menşe Ülke")
        btn_nadir_ulke.clicked.connect(self.check_rarely_used_origin_country)
        left_layout.addWidget(btn_nadir_ulke)
        
        btn_nadir_ulke_gtip = QPushButton("🔍 Gönderici-GTİP Nadir Menşe")
        btn_nadir_ulke_gtip.clicked.connect(self.check_rarely_used_origin_country_by_sender_gtip)
        left_layout.addWidget(btn_nadir_ulke_gtip)
        
        btn_nadir_odeme = QPushButton("💳 Nadir Ödeme Şekli")
        btn_nadir_odeme.clicked.connect(self.check_rarely_used_payment_method)
        left_layout.addWidget(btn_nadir_odeme)
        
        btn_birim_fiyat = QPushButton("📈 Birim Fiyat Artışı")
        btn_birim_fiyat.clicked.connect(self.check_unit_price_increase)
        left_layout.addWidget(btn_birim_fiyat)
        
        left_layout.addSpacing(10)
        left_layout.addWidget(QLabel("Gider ve Değer Kontrolleri:"))
        
        btn_kdv = QPushButton("💸 KDV Tutarlılık")
        btn_kdv.clicked.connect(self.check_kdv_consistency)
        left_layout.addWidget(btn_kdv)
        
        btn_yurt_ici = QPushButton("🏠 Yurt İçi Gider")
        btn_yurt_ici.clicked.connect(self.check_domestic_expense_variation)
        left_layout.addWidget(btn_yurt_ici)
        
        btn_yurt_disi = QPushButton("🌏 Yurt Dışı Gider")
        btn_yurt_disi.clicked.connect(self.check_foreign_expense_variation)
        left_layout.addWidget(btn_yurt_disi)
        
        btn_supalan = QPushButton("🚢 Supalan-Depolama")
        btn_supalan.clicked.connect(self.check_supalan_storage)
        left_layout.addWidget(btn_supalan)
        
        left_layout.addStretch()
        
        self.right_panel = QFrame()
        right_layout = QVBoxLayout(self.right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        
        self.check_results_widget = CheckResultsWidget()
        right_layout.addWidget(self.check_results_widget)
        
        analysis_layout.addWidget(self.left_panel)
        analysis_layout.addWidget(self.right_panel)
        self.tabs.addTab(self.analysis_tab, "Analizler")
        
        # Örnekleme Sekmesi (Yeni)
        self.sampling_tab = QWidget()
        sampling_layout = QVBoxLayout(self.sampling_tab)
        sampling_layout.setContentsMargins(10, 10, 10, 10)
        
        # Kontrol paneli
        sampling_control = QWidget()
        sampling_control.setObjectName("samplingPanel")
        sampling_control.setStyleSheet("""
            #samplingPanel {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(255, 255, 255, 0.98), stop:1 rgba(248, 250, 251, 0.95));
                border: 1px solid rgba(226, 232, 240, 0.8);
                border-radius: 16px;
                padding: 20px;
                margin: 10px;
            }
        """)
        sampling_control_layout = QVBoxLayout(sampling_control)
        sampling_control_layout.setContentsMargins(10, 10, 10, 10)
        sampling_control_layout.setSpacing(15)
        
        # Başlık ve açıklama
        header_layout = QHBoxLayout()
        heading = QLabel("Beyanname Örnekleme")
        heading.setStyleSheet("font-size: 16px; font-weight: bold; color: #333;")
        header_layout.addWidget(heading)
        header_layout.addStretch()
        
        # Örnekleme oranı seçimi
        sample_rate_layout = QHBoxLayout()
        sample_rate_label = QLabel("Örnekleme Oranı (%):")
        sample_rate_label.setStyleSheet("font-weight: bold;")
        self.sample_rate_combo = QComboBox()
        self.sample_rate_combo.addItems(["5", "10", "15", "20", "25"])
        self.sample_rate_combo.setCurrentIndex(0)
        sample_rate_layout.addWidget(sample_rate_label)
        sample_rate_layout.addWidget(self.sample_rate_combo)
        sample_rate_layout.addStretch()
        
        # Min-max ayarları
        min_max_layout = QHBoxLayout()
        min_label = QLabel("Minimum Örnekleme Sayısı:")
        min_label.setStyleSheet("font-weight: bold;")
        self.min_sample_spin = QSpinBox()
        self.min_sample_spin.setRange(50, 500)
        self.min_sample_spin.setValue(100)
        self.min_sample_spin.setSingleStep(10)
        
        max_label = QLabel("Maksimum Örnekleme Sayısı:")
        max_label.setStyleSheet("font-weight: bold;")
        self.max_sample_spin = QSpinBox()
        self.max_sample_spin.setRange(100, 1000)
        self.max_sample_spin.setValue(150)
        self.max_sample_spin.setSingleStep(10)
        
        min_max_layout.addWidget(min_label)
        min_max_layout.addWidget(self.min_sample_spin)
        min_max_layout.addSpacing(20)
        min_max_layout.addWidget(max_label)
        min_max_layout.addWidget(self.max_sample_spin)
        min_max_layout.addStretch()
        
        # Butonlar
        buttons_layout = QHBoxLayout()
        
        # Örnekleme başlat butonu
        self.start_sampling_btn = QPushButton("🚀 Örnekleme Başlat")
        self.start_sampling_btn.setProperty("class", "success")
        self.start_sampling_btn.clicked.connect(self.start_sampling)
        
        # Excel'e aktar butonu
        self.export_excel_btn = QPushButton("📊 Excel'e Aktar")
        self.export_excel_btn.setProperty("class", "primary")
        self.export_excel_btn.clicked.connect(self.export_sampling_to_excel)
        self.export_excel_btn.setEnabled(False)  # Başlangıçta devre dışı
        
        # Temizle butonu
        self.clear_sampling_btn = QPushButton("🧹 Temizle")
        self.clear_sampling_btn.setProperty("class", "danger")
        self.clear_sampling_btn.clicked.connect(self.clear_sampling)
        self.clear_sampling_btn.setEnabled(False)  # Başlangıçta devre dışı
        
        buttons_layout.addWidget(self.start_sampling_btn)
        buttons_layout.addWidget(self.export_excel_btn)
        buttons_layout.addWidget(self.clear_sampling_btn)
        buttons_layout.addStretch()
        
        # Kontrol paneline tüm layout'ları ekle
        sampling_control_layout.addLayout(header_layout)
        sampling_control_layout.addWidget(QLabel("Bu modül, ithalat beyannamelerinden belirli kriterlere göre örnekleme yaparak faaliyet raporuna dahil edilecek beyannameleri seçer."))
        sampling_control_layout.addLayout(sample_rate_layout)
        sampling_control_layout.addLayout(min_max_layout)
        sampling_control_layout.addLayout(buttons_layout)
        
        # Kontrol panelini ana layout'a ekle
        sampling_layout.addWidget(sampling_control)
        
        # Sonuç gösterimi için tablo
        self.sampling_results_label = QLabel("Örnekleme Sonuçları")
        self.sampling_results_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #333;")
        sampling_layout.addWidget(self.sampling_results_label)
        
        # Örnekleme sonuçları viewer'ı
        self.sampling_viewer = DataFrameViewer()
        sampling_layout.addWidget(self.sampling_viewer)
        
        # İstatistik bilgileri
        self.sampling_stats_label = QLabel("Örnekleme henüz yapılmadı")
        self.sampling_stats_label.setStyleSheet("color: #757575; font-style: italic;")
        sampling_layout.addWidget(self.sampling_stats_label)
        
        # Örnekleme nesnesi
        self.sampling_tool = BeyannameSampling()
        
        # Sekmeyi ana tab widget'a ekle
        self.tabs.addTab(self.sampling_tab, "Örnekleme")
        
        # Dashboard tab - Simple initialization
        self.dashboard_tab = QWidget()
        self.tabs.addTab(self.dashboard_tab, "Dashboard")
        
        # Açılışta ilk sekme "Veri Görünümü" olarak ayarla
        self.tabs.setCurrentIndex(0)
        
        # Tab değişimi için event handler ekle
        self.tabs.currentChanged.connect(self.on_tab_changed)
        
        main_layout.addWidget(self.tabs)
        
        # QtWebEngine önbellek hatalarını önle
        self.configure_qt_web_engine()
    
    def _dashboard_card(self, title, value, color="#4299e1", icon="📊"):
        """Dashboard için modern istatistik kartı oluştur"""
        w = QWidget()
        w.setStyleSheet(f"""
            QWidget {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(255, 255, 255, 0.95), stop:1 rgba(248, 250, 251, 0.9));
                border: 1px solid rgba(226, 232, 240, 0.8);
                border-left: 4px solid {color};
                border-radius: 12px;
                padding: 20px;
                margin: 8px;
            }}
        """)
        w.setMinimumWidth(200)
        w.setMaximumWidth(280)
        w.setMinimumHeight(120)
        w.setMaximumHeight(140)
        
        layout = QVBoxLayout(w)
        layout.setContentsMargins(15, 12, 15, 12)
        layout.setSpacing(8)
        
        # İkon ve başlık satırı
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)
        
        # İkon
        icon_label = QLabel(icon)
        icon_label.setStyleSheet("""
            QLabel {
                font-size: 24px;
                background: rgba(66, 153, 225, 0.1);
                border-radius: 8px;
                padding: 8px;
                min-width: 20px;
                max-width: 40px;
                min-height: 20px;
                max-height: 40px;
            }
        """)
        icon_label.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(icon_label)
        
        # Başlık
        title_label = QLabel(title)
        title_label.setStyleSheet("""
            QLabel {
                font-size: 12px;
                font-weight: 600;
                color: #4a5568;
                text-transform: uppercase;
                letter-spacing: 0.5px;
                background: transparent;
            }
        """)
        title_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        title_label.setWordWrap(True)
        header_layout.addWidget(title_label, 1)
        
        layout.addLayout(header_layout)
        
        # Değer
        value_label = QLabel(str(value))
        value_label.setStyleSheet(f"""
            QLabel {{
                font-size: 28px;
                font-weight: 700;
                color: #1a202c;
                background: transparent;
                margin: 8px 0px;
            }}
        """)
        value_label.setAlignment(Qt.AlignLeft | Qt.AlignBottom)
        layout.addWidget(value_label)
        
        # Alt boşluk
        layout.addStretch()
        
        return w
    
    def _dashboard_summary_table(self, df):
        """Dashboard için özet tablo oluştur"""
        try:
            # En çok kullanılan 5 GTIP, ülke, rejim ve toplam tutar
            gtip_col = next((c for c in df.columns if c.lower().startswith("gtip")), None)
            ulke_col = next((c for c in df.columns if "ulke" in c.lower()), None)
            rejim_col = next((c for c in df.columns if "rejim" in c.lower()), None)
            tutar_col = next((c for c in df.columns if "tutar" in c.lower() or "fatura_miktari" in c.lower()), None)
            
            # Tablo oluştur
            table = QTableWidget(5, 4)
            table.setHorizontalHeaderLabels(["GTIP", "Ülke", "Rejim", "Toplam Tutar"])
            
            # GTIP sütunu
            if gtip_col and df[gtip_col].nunique() > 0:
                gtip_counts = df[gtip_col].value_counts()
                for i in range(min(5, len(gtip_counts))):
                    gtip_val = str(gtip_counts.index[i])[:15] + "..." if len(str(gtip_counts.index[i])) > 15 else str(gtip_counts.index[i])
                    table.setItem(i, 0, QTableWidgetItem(gtip_val))
            
            # Ülke sütunu
            if ulke_col and df[ulke_col].nunique() > 0:
                ulke_counts = df[ulke_col].value_counts()
                for i in range(min(5, len(ulke_counts))):
                    ulke_val = str(ulke_counts.index[i])
                    table.setItem(i, 1, QTableWidgetItem(ulke_val))
            
            # Rejim sütunu
            if rejim_col and df[rejim_col].nunique() > 0:
                rejim_counts = df[rejim_col].value_counts()
                for i in range(min(5, len(rejim_counts))):
                    rejim_val = str(rejim_counts.index[i])
                    table.setItem(i, 2, QTableWidgetItem(rejim_val))
            
            # Tutar sütunu
            if tutar_col and gtip_col and df[tutar_col].notna().any():
                try:
                    # Numerik tutarları dönüştür
                    df_temp = df.copy()
                    df_temp[tutar_col] = pd.to_numeric(df_temp[tutar_col], errors='coerce')
                    tutar_by_gtip = df_temp.groupby(gtip_col)[tutar_col].sum().sort_values(ascending=False)
                    
                    for i in range(min(5, len(tutar_by_gtip))):
                        tutar = f"{tutar_by_gtip.values[i]:,.0f}" if tutar_by_gtip.values[i] == tutar_by_gtip.values[i] else "0"
                        table.setItem(i, 3, QTableWidgetItem(tutar))
                except Exception:
                    # Tutar hesaplanamıyorsa boş bırak
                    pass
            
            # Boş hücreleri doldur
            for i in range(5):
                for j in range(4):
                    if table.item(i, j) is None:
                        table.setItem(i, j, QTableWidgetItem("-"))
            
            # Tablo ayarları
            table.setEditTriggers(QTableWidget.NoEditTriggers)
            table.setStyleSheet("""
                QTableWidget {
                    background: #fff; 
                    border-radius: 6px; 
                    font-size: 11px;
                    border: 1px solid #ddd;
                }
                QHeaderView::section {
                    background-color: #f5f5f5;
                    border: 1px solid #ddd;
                    padding: 5px;
                    font-weight: bold;
                }
            """)
            table.resizeColumnsToContents()
            table.setMaximumHeight(200)
            
            return table
            
        except Exception as e:
            print(f"Dashboard özet tablo hatası: {e}")
            # Hata durumunda basit bir mesaj döndür
            error_label = QLabel("Özet tablo oluşturulamadı")
            error_label.setStyleSheet("color: #999; font-style: italic;")
            return error_label
    
    def configure_qt_web_engine(self):
        """QtWebEngine kullanımı için yapılandırma"""
        try:
            from PyQt5.QtWebEngineWidgets import QWebEngineProfile
            
            # Ortak bir önbellek klasörü kullan
            profile = QWebEngineProfile.defaultProfile()
            app_data_dir = os.path.join(os.path.expanduser("~"), "AppData", "Local", "CustomsCheck")
            
            # Klasörü oluştur (yoksa)
            os.makedirs(app_data_dir, exist_ok=True)
            
            # Önbellek ve HTTP önbelleği için alt klasörler oluştur
            cache_dir = os.path.join(app_data_dir, "WebCache")
            http_cache_dir = os.path.join(app_data_dir, "HttpCache")
            
            try:
                os.makedirs(cache_dir, exist_ok=True)
                os.makedirs(http_cache_dir, exist_ok=True)
                
                # İzinleri kontrol et ve ayarla
                if not os.access(cache_dir, os.W_OK):
                    print(f"Uyarı: {cache_dir} klasörüne yazma izni yok")
                
                if not os.access(http_cache_dir, os.W_OK):
                    print(f"Uyarı: {http_cache_dir} klasörüne yazma izni yok")
            except Exception as e:
                print(f"Önbellek klasörü oluşturma hatası: {e}")
            
            # Önbellek ayarlarını yapılandır
            profile.setCachePath(cache_dir)
            profile.setHttpCachePath(http_cache_dir)
            profile.setPersistentCookiesPolicy(QWebEngineProfile.NoPersistentCookies)
            
            # Önbellek boyutunu sınırla
            profile.setHttpCacheType(QWebEngineProfile.DiskHttpCache)
            profile.setHttpCacheMaximumSize(5 * 1024 * 1024)  # 5 MB
            
            print("QtWebEngine önbellek yapılandırması tamamlandı")
            
        except ImportError:
            print("QtWebEngineWidgets modülü bulunamadı")
        except Exception as e:
            print(f"QtWebEngine yapılandırma hatası: {e}")
        
    def import_xml(self):
        """Import a single XML file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "XML Dosyası Seç", "", "XML Files (*.xml)"
        )
        
        if file_path:
            try:
                self.status_label.setText(f"İşleniyor: {os.path.basename(file_path)}")
                self.progress_bar.setVisible(True)
                self.progress_bar.setValue(50)
                
                # Process the XML file using existing function
                result = extract_beyanname_fixed(file_path)
                
                if 'dataframe' in result and result['dataframe'] is not None:
                    # Get the DataFrame directly from the result
                    df = result['dataframe']
                    
                    # Store the DataFrame
                    file_name = os.path.basename(file_path)
                    self.all_dataframes[file_name] = df
                    
                    # Update UI
                    self.update_file_selector()
                    self.file_selector.setCurrentText(file_name)
                    self.display_dataframe(df)
                    
                    self.status_label.setText(f"Yüklendi: {file_name} ({len(df)} satır, {len(df.columns)} sütun)")
                else:
                    QMessageBox.warning(self, "Hata", "DataFrame oluşturulamadı.")
                    self.status_label.setText("Hata: DataFrame oluşturulamadı")
                
                self.progress_bar.setVisible(False)
                
            except Exception as e:
                QMessageBox.critical(self, "Hata", f"XML işleme hatası: {str(e)}")
                self.status_label.setText("Hata oluştu")
                self.progress_bar.setVisible(False)
    
    def import_xml_folder(self):
        """Import all XML files from a folder"""
        folder_path = QFileDialog.getExistingDirectory(
            self, "XML Klasörü Seç"
        )
        
        if folder_path:
            try:
                self.status_label.setText(f"Klasör işleniyor: {folder_path}")
                self.progress_bar.setVisible(True)
                self.progress_bar.setValue(0)
                QApplication.processEvents()
                
                # 1. Dosyalar yükleniyor
                self.status_label.setText("XML dosyaları yükleniyor...")
                QApplication.processEvents()
                
                def update_progress(progress, message):
                    # progress: 0-1 arası float, 0-70 arası ölçekle
                    bar_value = int(progress * 70)
                    self.progress_bar.setValue(bar_value)
                    self.status_label.setText(message)
                    QApplication.processEvents()
                
                dataframes, error_messages = process_multiple_xml_files(
                    folder_path, 
                    progress_callback=update_progress
                )
                
                self.progress_bar.setValue(75)
                self.status_label.setText("Veriler birleştiriliyor...")
                QApplication.processEvents()
                
                # 2. Kısa bir bekleme animasyonu (0.2 sn)
                import time
                time.sleep(0.2)
                self.progress_bar.setValue(85)
                QApplication.processEvents()
                
                # 3. DataFrame'leri sakla
                self.all_dataframes.update(dataframes)
                
                # 4. UI'ı güncelle
                self.update_file_selector()
                if self.file_selector.count() > 0:
                    self.file_selector.setCurrentIndex(0)
                
                processed_count = len(dataframes)
                error_count = len(error_messages)
                
                if error_count > 0:
                    message = f"{processed_count} XML dosyası başarıyla işlendi, {error_count} dosyada hata oluştu."
                else:
                    message = f"{processed_count} XML dosyası başarıyla işlendi."
                
                self.progress_bar.setValue(95)
                self.status_label.setText(message + " Birleştirilen veri hazırlanıyor...")
                QApplication.processEvents()
                
                # 5. Birleştir ve göster
                self.show_merged_dataframes()
                self.progress_bar.setValue(100)
                self.status_label.setText("Tüm dosyalar başarıyla birleştirildi ve gösteriliyor.")
                QApplication.processEvents()
                
                # 6. Progress bar'ı kısa süre sonra gizle
                from PyQt5.QtCore import QTimer
                QTimer.singleShot(800, lambda: self.progress_bar.setVisible(False))
                
            except Exception as e:
                QMessageBox.critical(self, "Hata", f"Klasör işleme hatası: {str(e)}")
                self.status_label.setText("Hata oluştu")
                self.progress_bar.setVisible(False)
    
    def update_file_selector(self):
        """Update the file selector dropdown with loaded files"""
        self.file_selector.clear()
        self.file_selector.addItems(self.all_dataframes.keys())
    
    def change_active_file(self, index):
        """Change the active file when selected from dropdown"""
        # Dosya seçiciyi yeniden aktifleştir (birleştirme modundan çıkış)
        self.file_selector.setEnabled(True)
        
        # Pencere başlığını sıfırla
        self.setWindowTitle("Beyanname Kontrol Uygulaması")
        
        if index >= 0:
            file_name = self.file_selector.currentText()
            if file_name in self.all_dataframes:
                df = self.all_dataframes[file_name]
                self.display_dataframe(df)
    
    def display_dataframe(self, df):
        """Display a DataFrame in the data viewer and update other components"""
        self.current_df = df
        
        # Update data viewer
        self.data_viewer.set_dataframe(df)
        
        # Update analysis components
        self.pivot_widget.set_dataframe(df)
        self.chart_widget.set_dataframe(df)
        
        # Örnekleme aracını güncelle
        if hasattr(self, 'sampling_tool'):
            self.sampling_tool.set_dataframe(df)
            # Örnekleme daha önce yapıldıysa temizle
            if hasattr(self, 'export_excel_btn') and self.export_excel_btn.isEnabled():
                self.clear_sampling()
        
        # Update dashboard
        self.update_dashboard()
    
    def update_dashboard(self):
        """Update dashboard with current data"""
        # Dashboard tab'ının layout'unu kontrol et ve oluştur
        if self.dashboard_tab.layout() is None:
            layout = QVBoxLayout(self.dashboard_tab)
            layout.setContentsMargins(10, 10, 10, 10)
        else:
            layout = self.dashboard_tab.layout()
            # Eski widget'ları temizle
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()
        
        # İçeriği oluştur
        if self.current_df is None or (hasattr(self.current_df, 'empty') and self.current_df.empty):
            msg = QLabel("Dashboard için veri yüklenmedi. Lütfen bir XML dosyası yükleyin.")
            msg.setAlignment(Qt.AlignCenter)
            msg.setStyleSheet("font-size: 15px; color: #888; margin-top: 60px;")
            layout.addStretch()
            layout.addWidget(msg)
            layout.addStretch()
        else:
            df = self.current_df
            
            # Scroll area oluştur (çok fazla içerik olacak)
            scroll_area = QScrollArea()
            scroll_area.setWidgetResizable(True)
            scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            
            # Scroll içeriği
            scroll_content = QWidget()
            scroll_layout = QVBoxLayout(scroll_content)
            scroll_layout.setSpacing(15)
            scroll_layout.setContentsMargins(10, 10, 10, 10)
            
            # Başlık
            title_label = QLabel("🏛️ GÜMRİK YÖNETİM PANELİ")
            title_label.setStyleSheet("""
                font-size: 24px; 
                font-weight: bold; 
                color: #2c3e50; 
                margin-bottom: 20px; 
                text-align: center;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 #74b9ff, stop:1 #0984e3);
                color: white;
                padding: 15px;
                border-radius: 10px;
            """)
            title_label.setAlignment(Qt.AlignCenter)
            scroll_layout.addWidget(title_label)
            
            # İlk satır - Ana göstergeler
            row1 = QWidget()
            row1_layout = QGridLayout(row1)
            row1_layout.setSpacing(15)
            
            # Temel istatistikler hesapla
            total_rows = len(df)
            total_cols = len(df.columns)
            missing_values = df.isnull().sum().sum()
            
            # Beyanname sayısı
            beyanname_col = next((c for c in df.columns if "beyanname" in c.lower() and "no" in c.lower()), None)
            unique_beyannames = df[beyanname_col].nunique() if beyanname_col else total_rows
            
            # İstatistiki kıymet hesapla
            kiymet_cols = [c for c in df.columns if any(keyword in c.lower() for keyword in ["kiymet", "value", "fatura_miktari", "tutar"])]
            total_value = 0
            avg_value = 0
            max_value = 0
            if kiymet_cols:
                try:
                    for col in kiymet_cols:
                        numeric_vals = pd.to_numeric(df[col], errors='coerce').fillna(0)
                        total_value += numeric_vals.sum()
                    avg_value = total_value / unique_beyannames if unique_beyannames > 0 else 0
                    max_value = max([pd.to_numeric(df[col], errors='coerce').max() for col in kiymet_cols if not pd.to_numeric(df[col], errors='coerce').empty])
                except:
                    pass
            
            # Ağırlık hesapla
            agirlik_cols = [c for c in df.columns if "agirlik" in c.lower()]
            total_weight = 0
            avg_weight = 0
            if agirlik_cols:
                try:
                    for col in agirlik_cols:
                        numeric_vals = pd.to_numeric(df[col], errors='coerce').fillna(0)
                        total_weight += numeric_vals.sum()
                    avg_weight = total_weight / unique_beyannames if unique_beyannames > 0 else 0
                except:
                    pass
            
            # Firma sayısı
            firma_cols = [c for c in df.columns if any(keyword in c.lower() for keyword in ["firma", "ithalatci", "gonderen", "company"])]
            unique_firms = 0
            if firma_cols:
                unique_firms = df[firma_cols[0]].nunique()
            
            # GTIP sayısı
            gtip_col = next((c for c in df.columns if c.lower().startswith("gtip")), None)
            unique_gtips = df[gtip_col].nunique() if gtip_col else 0
            
            # Ülke sayısı
            ulke_col = next((c for c in df.columns if "ulke" in c.lower()), None)
            unique_countries = df[ulke_col].nunique() if ulke_col else 0
            
            # Döviz türü sayısı
            doviz_col = next((c for c in df.columns if "doviz" in c.lower()), None)
            unique_currencies = df[doviz_col].nunique() if doviz_col else 0
            
            # Kartları ekle - İlk satır (Ana göstergeler)
            row1_layout.addWidget(self._dashboard_card("TOPLAM SATIR", f"{total_rows:,}", "#4299e1", "📊"), 0, 0)
            row1_layout.addWidget(self._dashboard_card("BEYANNAME SAYISI", f"{unique_beyannames:,}", "#48bb78", "📜"), 0, 1)
            row1_layout.addWidget(self._dashboard_card("İSTATİSTİKİ KIYMET", f"₺{total_value:,.0f}", "#9f7aea", "💰"), 0, 2)
            row1_layout.addWidget(self._dashboard_card("TOPLAM AĞIRLIK", f"{total_weight:,.0f} KG", "#ed8936", "⚖️"), 0, 3)
            row1_layout.addWidget(self._dashboard_card("FIRMA SAYISI", f"{unique_firms:,}", "#38b2ac", "🏢"), 0, 4)
            
            scroll_layout.addWidget(row1)
            
            # İkinci satır - Ortalama ve detay göstergeler
            row2 = QWidget()
            row2_layout = QGridLayout(row2)
            row2_layout.setSpacing(15)
            
            row2_layout.addWidget(self._dashboard_card("ORTALAMA KIYMET", f"₺{avg_value:,.0f}", "#38b2ac", "📊"), 0, 0)
            row2_layout.addWidget(self._dashboard_card("MAX KIYMET", f"₺{max_value:,.0f}", "#f56565", "📈"), 0, 1)
            row2_layout.addWidget(self._dashboard_card("ORT. AĞIRLIK", f"{avg_weight:,.1f} KG", "#667eea", "⚖️"), 0, 2)
            row2_layout.addWidget(self._dashboard_card("GTİP TÜRÜ", f"{unique_gtips:,}", "#ed8936", "🏷️"), 0, 3)
            row2_layout.addWidget(self._dashboard_card("ÜLKE SAYISI", f"{unique_countries:,}", "#4299e1", "🌍"), 0, 4)
            
            scroll_layout.addWidget(row2)
            
            # Üçüncü satır - Kalite ve sistem göstergeleri
            row3 = QWidget()
            row3_layout = QGridLayout(row3)
            row3_layout.setSpacing(15)
            
            # Veri kalitesi hesapla
            completeness = ((len(df) * len(df.columns) - missing_values) / (len(df) * len(df.columns)) * 100) if len(df) > 0 else 0
            
            # KDV hesapla (varsa)
            kdv_cols = [c for c in df.columns if "kdv" in c.lower()]
            total_kdv = 0
            if kdv_cols:
                try:
                    for col in kdv_cols:
                        numeric_vals = pd.to_numeric(df[col], errors='coerce').fillna(0)
                        total_kdv += numeric_vals.sum()
                except:
                    pass
            
            # Gümrük vergisi hesapla (varsa)
            vergi_cols = [c for c in df.columns if "vergi" in c.lower() and "kdv" not in c.lower()]
            total_customs_duty = 0
            if vergi_cols:
                try:
                    for col in vergi_cols:
                        numeric_vals = pd.to_numeric(df[col], errors='coerce').fillna(0)
                        total_customs_duty += numeric_vals.sum()
                except:
                    pass
            
            row3_layout.addWidget(self._dashboard_card("VERİ TAMLIĞI", f"%{completeness:.1f}", "#48bb78", "✅"), 0, 0)
            row3_layout.addWidget(self._dashboard_card("TOPLAM KDV", f"₺{total_kdv:,.0f}", "#f56565", "💸"), 0, 1)
            row3_layout.addWidget(self._dashboard_card("GÜMRÜK VERGİSİ", f"₺{total_customs_duty:,.0f}", "#9f7aea", "🏛️"), 0, 2)
            row3_layout.addWidget(self._dashboard_card("DÖVİZ TÜRÜ", f"{unique_currencies:,}", "#ed8936", "💱"), 0, 3)
            row3_layout.addWidget(self._dashboard_card("EKSİK VERİ", f"{missing_values:,}", "#f56565", "❌"), 0, 4)
            
            scroll_layout.addWidget(row3)
            
            # Özet tablo
            try:
                summary_table = self._dashboard_summary_table(df)
                if summary_table:
                    summary_title = QLabel("📈 EN ÇOK KULLANILAN DEĞERLER")
                    summary_title.setStyleSheet("""
                        font-size: 16px; 
                        font-weight: bold; 
                        color: #2c3e50; 
                        margin: 20px 0 10px 0;
                        background: #ecf0f1;
                        padding: 10px;
                        border-radius: 5px;
                    """)
                    scroll_layout.addWidget(summary_title)
                    scroll_layout.addWidget(summary_table)
            except Exception as e:
                print(f"Özet tablo oluşturma hatası: {e}")
            
            # Grafikler bölümü
            try:
                from analysis_modules import create_bar_chart, create_pie_chart
                
                # Grafik başlığı
                chart_title = QLabel("📊 VERİ DAĞILIM GRAFİKLERİ VE ANALİZLER")
                chart_title.setStyleSheet("""
                    font-size: 16px; 
                    font-weight: bold; 
                    color: #2c3e50; 
                    margin: 20px 0 10px 0;
                    background: #3498db;
                    color: white;
                    padding: 10px;
                    border-radius: 5px;
                """)
                scroll_layout.addWidget(chart_title)
                
                # Grafik container'ı - 2 satır halinde
                charts_row1 = QWidget()
                charts_row1_layout = QHBoxLayout(charts_row1)
                charts_row1_layout.setSpacing(20)
                
                # GTIP dağılım grafiği
                if gtip_col and df[gtip_col].nunique() > 1:
                    try:
                        fig1 = create_bar_chart(df, gtip_col, title="GTIP Dağılımı (İlk 10)", limit=10)
                        if fig1:
                            from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
                            canvas1 = FigureCanvas(fig1)
                            canvas1.setMinimumHeight(300)
                            canvas1.setMaximumHeight(400)
                            charts_row1_layout.addWidget(canvas1)
                    except Exception as e:
                        print(f"GTIP grafiği oluşturma hatası: {e}")
                
                # Ülke dağılım grafiği
                if ulke_col and df[ulke_col].nunique() > 1:
                    try:
                        fig2 = create_pie_chart(df, ulke_col, title="Ülke Dağılımı (İlk 5)", limit=5)
                        if fig2:
                            from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
                            canvas2 = FigureCanvas(fig2)
                            canvas2.setMinimumHeight(300)
                            canvas2.setMaximumHeight(400)
                            charts_row1_layout.addWidget(canvas2)
                    except Exception as e:
                        print(f"Ülke grafiği oluşturma hatası: {e}")
                
                if charts_row1_layout.count() > 0:
                    scroll_layout.addWidget(charts_row1)
                
                # İkinci grafik satırı
                charts_row2 = QWidget()
                charts_row2_layout = QHBoxLayout(charts_row2)
                charts_row2_layout.setSpacing(20)
                
                # Rejim dağılım grafiği
                rejim_col = next((c for c in df.columns if "rejim" in c.lower()), None)
                if rejim_col and df[rejim_col].nunique() > 1:
                    try:
                        fig3 = create_pie_chart(df, rejim_col, title="Rejim Dağılımı", limit=8)
                        if fig3:
                            from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
                            canvas3 = FigureCanvas(fig3)
                            canvas3.setMinimumHeight(300)
                            canvas3.setMaximumHeight(400)
                            charts_row2_layout.addWidget(canvas3)
                    except Exception as e:
                        print(f"Rejim grafiği oluşturma hatası: {e}")
                
                # Döviz dağılım grafiği
                if doviz_col and df[doviz_col].nunique() > 1:
                    try:
                        fig4 = create_pie_chart(df, doviz_col, title="Döviz Türü Dağılımı", limit=6)
                        if fig4:
                            from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
                            canvas4 = FigureCanvas(fig4)
                            canvas4.setMinimumHeight(300)
                            canvas4.setMaximumHeight(400)
                            charts_row2_layout.addWidget(canvas4)
                    except Exception as e:
                        print(f"Döviz grafiği oluşturma hatası: {e}")
                
                if charts_row2_layout.count() > 0:
                    scroll_layout.addWidget(charts_row2)
                    
            except Exception as e:
                print(f"Grafik oluşturma genel hatası: {e}")
            
            # Scroll area'yı ayarla
            scroll_area.setWidget(scroll_content)
            layout.addWidget(scroll_area)
    
    # Check functions
    def run_all_checks(self):
        """Run all data checks"""
        if self.current_df is None:
            QMessageBox.warning(self, "Uyarı", "Veri yüklenmedi")
            return
        
        # İlerleme çubuğunu göster
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(10)
        self.status_label.setText("Tüm kontroller çalıştırılıyor...")
        QApplication.processEvents()
        
        results = {}
        
        # İlerleme bildirimi için fonksiyon
        def update_progress(value, message):
            # Değeri ölçeklendir (0-100 aralığına)
            scaled_value = int(10 + (value * 0.8))  # 10-90 arası
            self.progress_bar.setValue(scaled_value)
            self.status_label.setText(message)
            QApplication.processEvents()
        
        # Tüm kontrolleri çalıştır
        check_functions = [
            ("İşlem Niteliği Kontrolü", self._run_islem_niteligi_check),
            ("GTİP-Tanım Detay Analizi", self._run_gtip_tanim_detail_check),
            ("GTİP-Ürün Kodu Kontrolü", self._run_gtip_urun_check),
            ("Alıcı-Satıcı İlişki Kontrolü", self._run_alici_satici_check),
            ("Nadir Döviz Kontrolü", self._run_nadir_doviz_check),
            ("Nadir Menşe Ülke Kontrolü", self._run_nadir_ulke_check),
            ("Gönderici-GTİP Nadir Menşe Kontrolü", self._run_nadir_ulke_gtip_check),
            ("Nadir Ödeme Şekli Kontrolü", self._run_nadir_odeme_check),
            ("Birim Fiyat Artışı Kontrolü", self._run_birim_fiyat_check),
            ("KDV Tutarlılık Kontrolü", self._run_kdv_check),
            ("Yurt İçi Gider Kontrolü", self._run_yurt_ici_check),
            ("Yurt Dışı Gider Kontrolü", self._run_yurt_disi_check),
            ("Supalan-Depolama Kontrolü", self._run_supalan_check)
        ]
        
        total_checks = len(check_functions)
        for i, (check_name, check_func) in enumerate(check_functions):
            try:
                progress = 10 + (i * 80 / total_checks)
                self.progress_bar.setValue(int(progress))
                self.status_label.setText(f"{check_name} çalıştırılıyor...")
        QApplication.processEvents()
        
                result = check_func()
                if result:
                    results[check_name] = result
                    
            except Exception as e:
                print(f"{check_name} hatası: {str(e)}")
                results[check_name] = {
                    "status": "error",
                    "message": f"Kontrol sırasında hata: {str(e)}",
                    "type": "error"
                }
        
        # Sonuçları göster
        self.progress_bar.setValue(100)
        self.status_label.setText("Tüm kontroller tamamlandı!")
        
        # Sonuçları results widget'a ekle
        for check_name, result in results.items():
            if hasattr(self, 'check_results_widget'):
                self.check_results_widget.add_result(check_name, result)
        
        # 2 saniye sonra progress bar'ı gizle
        QTimer.singleShot(2000, lambda: self.progress_bar.setVisible(False))
        
        QMessageBox.information(self, "Tamamlandı", f"{len(results)} kontrol tamamlandı!")

    # Yardımcı kontrol fonksiyonları
    def _run_islem_niteligi_check(self):
        """İşlem Niteliği kontrolü çalıştır"""
        required_columns = ['Kalem_Islem_Niteligi', 'Odeme_sekli', 'Rejim']
        missing_columns = [col for col in required_columns if col not in self.current_df.columns]
        
        if missing_columns:
            return {
                "status": "error",
                "message": f"Gerekli sütunlar eksik: {', '.join(missing_columns)}",
                "type": "islem_niteligi_consistency"
            }
        
        try:
            # Kontrolleri yap (soru sormadan)
            bedelsiz_payment_filter = self.current_df['Odeme_sekli'].str.lower().str.contains('bedelsiz', na=False)
            incorrect_payment_code = self.current_df[bedelsiz_payment_filter & (self.current_df['Kalem_Islem_Niteligi'] != '99')]
            
            rejim_filter = self.current_df['Rejim'] == '6123'
            incorrect_rejim_code = self.current_df[rejim_filter & (self.current_df['Kalem_Islem_Niteligi'] != '61')]
            
            all_inconsistencies = pd.concat([incorrect_payment_code, incorrect_rejim_code]).drop_duplicates()
            
            if len(all_inconsistencies) > 0:
                return {
                    "status": "warning",
                    "message": f"{len(all_inconsistencies)} adet tutarsız işlem niteliği kodu bulundu.",
                    "data": all_inconsistencies,
                    "type": "islem_niteligi_consistency"
                }
            else:
                return {
                    "status": "ok",
                    "message": "Tüm işlem niteliği kodları ödeme şekli ve rejim kodu ile tutarlı.",
                    "type": "islem_niteligi_consistency"
                }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Kontrol sırasında hata: {str(e)}",
                "type": "islem_niteligi_consistency"
            }

    def _run_gtip_tanim_detail_check(self):
        """GTİP-Tanım Detay analizi çalıştır"""
        from analysis_modules.gtip_analysis import check_gtip_tanim_detail
        return check_gtip_tanim_detail(self.current_df)

    def _run_gtip_urun_check(self):
        """GTİP-Ürün Kodu kontrolü çalıştır"""
        from analysis_modules.gtip_analysis import check_gtip_urun_kodu_consistency
        return check_gtip_urun_kodu_consistency(self.current_df)

    def _run_alici_satici_check(self):
        """Alıcı-Satıcı ilişki kontrolü"""
        if self.current_df is None:
            QMessageBox.warning(self, "Uyarı", "Veri yüklenmedi")
            return
        
        try:
            # İşlem başladığını göster (soru sormadan)
            self.status_label.setText("Alıcı-Satıcı ilişki kontrolü çalışıyor...")
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(10)
            QApplication.processEvents()
            
            # Analiz fonksiyonunu çağır - doğru modülden
            from analysis_modules.relationship_analysis import check_alici_satici_relationship
            result = check_alici_satici_relationship(self.current_df)
            
            # İlerleme çubuğunu güncelle
            self.progress_bar.setValue(80)
            QApplication.processEvents()
            
            if result["status"] == "error":
                QMessageBox.warning(self, "Uyarı", result["message"])
                self.progress_bar.setVisible(False)
                self.status_label.setText(result["message"])
                return
            
            # Sonuçları widget'a aktar
            check_result = {
                "Alıcı-Satıcı İlişki Kontrolü": result
            }
            self.check_results_widget.set_check_results(check_result)
            
            # Sonuçları göster
            if result.get("data") is not None:
                self.check_results_widget.show_details(result["data"])
                
                # Özet tablosu oluştur
                summary_df = pd.DataFrame({
                    'Özet Bilgi': ['Tespit Edilen İşlem Sayısı', 'Durum'],
                    'Değer': [len(result["data"]), result["status"]]
                })
                self.check_results_widget.show_summary(summary_df)
            
            self.status_label.setText(result["message"])
            
            # İşlem tamamlandı
            self.progress_bar.setValue(100)
            self.progress_bar.setVisible(False)
            QApplication.processEvents()
            
        except Exception as e:
            error_msg = f"Alıcı-Satıcı ilişki kontrolü sırasında hata: {str(e)}"
            print(error_msg)
            QMessageBox.critical(self, "Hata", error_msg)
            self.status_label.setText("Hata oluştu")
            self.progress_bar.setVisible(False)

    def _run_nadir_doviz_check(self):
        """Nadir döviz kontrolü çalıştır"""
        from analysis_modules.rare_items import check_rarely_used_currency
        return check_rarely_used_currency(self.current_df)

    def _run_nadir_ulke_check(self):
        """Nadir menşe ülke kontrolü çalıştır"""
        from analysis_modules.rare_items import check_rarely_used_origin_country
        return check_rarely_used_origin_country(self.current_df)

    def _run_nadir_ulke_gtip_check(self):
        """Gönderici-GTİP nadir menşe kontrolü çalıştır"""
        from analysis_modules.rare_items import check_rarely_used_origin_country_by_sender_gtip
        return check_rarely_used_origin_country_by_sender_gtip(self.current_df)

    def _run_nadir_odeme_check(self):
        """Nadir ödeme şekli kontrolü çalıştır"""
        from analysis_modules.rare_items import check_rarely_used_payment_method
        return check_rarely_used_payment_method(self.current_df)

    def _run_birim_fiyat_check(self):
        """Birim fiyat artışı kontrolü çalıştır"""
        from analysis_modules.price_analysis import check_unit_price_increase
        return check_unit_price_increase(self.current_df)

    def _run_kdv_check(self):
        """KDV tutarlılık kontrolü çalıştır"""
        from analysis_modules.tax_analysis import check_kdv_consistency
        return check_kdv_consistency(self.current_df)

    def _run_yurt_ici_check(self):
        """Yurt içi gider kontrolü çalıştır"""
        from analysis_modules.expense_analysis import check_domestic_expense_variation
        return check_domestic_expense_variation(self.current_df)

    def _run_yurt_disi_check(self):
        """Yurt dışı gider kontrolü çalıştır"""
        from analysis_modules.expense_analysis import check_foreign_expense_variation
        return check_foreign_expense_variation(self.current_df)

    def _run_supalan_check(self):
        """Supalan-depolama kontrolü çalıştır"""
        from analysis_modules.storage_analysis import check_supalan_storage
        return check_supalan_storage(self.current_df)
    
    def check_missing_values(self):
        """Check for missing values"""
        if self.current_df is None:
            QMessageBox.warning(self, "Uyarı", "Veri yüklenmedi")
            return
        
        missing = check_missing_values(self.current_df)
        if missing is not None:
            result = {
                "Eksik Değer Kontrolü": {
                    "status": "warning" if not missing.empty else "ok",
                    "message": f"{missing.shape[0]} sütunda eksik değer bulundu." if not missing.empty else "Eksik değer bulunamadı.",
                    "data": missing
                }
            }
            self.check_results_widget.set_check_results(result)
            if not missing.empty:
                self.check_results_widget.show_details(missing)
        else:
            result = {
                "Eksik Değer Kontrolü": {
                    "status": "ok",
                    "message": "Eksik değer bulunamadı."
                }
            }
            self.check_results_widget.set_check_results(result)
    
    def check_duplicate_rows(self):
        """Check for duplicate rows"""
        if self.current_df is None:
            QMessageBox.warning(self, "Uyarı", "Veri yüklenmedi")
            return
        
        duplicates = check_duplicate_rows(self.current_df)
        result = {
            "Tekrarlanan Veri Kontrolü": {
                "status": "warning" if duplicates["duplicate_rows_all"] > 0 else "ok",
                "message": f"{duplicates['duplicate_rows_all']} tekrarlanan satır bulundu." if duplicates["duplicate_rows_all"] > 0 else "Tekrarlanan satır bulunamadı."
            }
        }
        self.check_results_widget.set_check_results(result)
        
        if duplicates["duplicate_rows_all"] > 0:
            # Show the duplicate rows
            duplicate_data = self.current_df[self.current_df.duplicated(keep='first')]
            self.check_results_widget.show_details(duplicate_data)
    
    def check_weight_consistency(self):
        """Check for weight consistency (Brut_agirlik >= Net_agirlik)"""
        if self.current_df is None:
            QMessageBox.warning(self, "Uyarı", "Veri yüklenmedi")
            return
        
        weight_check = check_weight_consistency(self.current_df)
        if weight_check is not None:
            result = {"Ağırlık Kontrolü": weight_check}
            self.check_results_widget.set_check_results(result)
            
            if weight_check["status"] == "warning" and "inconsistent_rows" in weight_check:
                self.check_results_widget.show_details(weight_check["inconsistent_rows"])
        else:
            result = {
                "Ağırlık Kontrolü": {
                    "status": "ok",
                    "message": "Ağırlık verisi kontrol edilemedi."
                }
            }
            self.check_results_widget.set_check_results(result)
    
    def check_islem_niteligi_consistency(self):
        """Check for Kalem_Islem_Niteligi consistency with payment method and regime code"""
        if self.current_df is None:
            QMessageBox.warning(self, "Uyarı", "Veri yüklenmedi")
            return
        
        try:
            # İşlem başladığını göster (soru sormadan)
            self.status_label.setText("İşlem Niteliği tutarlılık kontrolü çalışıyor...")
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(10)
            QApplication.processEvents()  # UI güncellemesi için
            
            # Modülü kullanarak kontrol yap
            self.progress_bar.setValue(50)
            QApplication.processEvents()
            
            result = kontrol_islem_niteligi_tutarlilik(self.current_df)
            
            self.progress_bar.setValue(80)
            QApplication.processEvents()
            
            # Sonuçları işle
            if result["status"] == "warning":
                # Hata bulundu
                check_result = {
                    "İşlem Niteliği Kontrolü": {
                        "status": "warning",
                        "message": result["message"],
                        "data": result["data"],
                        "type": "islem_niteligi_consistency",
                        "html_report": result["html_report"]
                    }
                }
                
                if "summary" in result:
                    check_result["İşlem Niteliği Kontrolü"]["summary"] = result["summary"]
                
                # Widget'a sonuçları gönder
                self.check_results_widget.set_check_results(check_result, self.current_df)
                
                # Tabloyu göster
                try:
                    self.check_results_widget.show_details(result["data"])
                    if "summary" in result:
                        self.check_results_widget.show_summary(result["summary"])
                except Exception as e:
                    print(f"Tablo gösterilirken hata: {str(e)}")
                
                self.status_label.setText(f"İşlem Niteliği Kontrolü: {result['message']}")
                
            elif result["status"] == "ok":
                # Kontrol başarılı
                check_result = {
                    "İşlem Niteliği Kontrolü": {
                        "status": "ok",
                        "message": result["message"],
                        "html_report": result["html_report"]
                    }
                }
                self.check_results_widget.set_check_results(check_result)
                self.status_label.setText("İşlem Niteliği Kontrolü: Tutarlılık kontrolü başarılı. Tüm veriler uyumlu.")
                
            else:
                # Hata durumu
                QMessageBox.critical(self, "Hata", result["message"])
                self.status_label.setText("İşlem Niteliği kontrolünde hata oluştu")
                
            self.progress_bar.setVisible(False)
            
        except Exception as e:
            # Hata durumunda kullanıcıyı bilgilendir
            error_msg = f"İşlem Niteliği kontrolü sırasında hata: {str(e)}"
            print(error_msg)
            QMessageBox.critical(self, "Hata", error_msg)
            self.status_label.setText("Hata oluştu")
            self.progress_bar.setVisible(False)
    
    def check_gtip_ticari_tanim_consistency(self):
        """Check for GTIP-Ticari Tanım consistency - REMOVED BY USER REQUEST"""
        QMessageBox.information(self, "Bilgi", "Bu özellik kaldırılmıştır.")
        return
    
    def check_alici_satici_relationship(self):
        """Alıcı-Satıcı ilişki kontrolü"""
        if self.current_df is None:
            QMessageBox.warning(self, "Uyarı", "Veri yüklenmedi")
            return
        
        try:
            # İşlem başladığını göster (soru sormadan)
            self.status_label.setText("Alıcı-Satıcı ilişki kontrolü çalışıyor...")
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(10)
            QApplication.processEvents()
            
            # Analiz fonksiyonunu çağır - doğru modülden
            from analysis_modules.relationship_analysis import check_alici_satici_relationship
            result = check_alici_satici_relationship(self.current_df)
            
            # İlerleme çubuğunu güncelle
            self.progress_bar.setValue(80)
            QApplication.processEvents()
            
            if result["status"] == "error":
                QMessageBox.warning(self, "Uyarı", result["message"])
                self.progress_bar.setVisible(False)
                self.status_label.setText(result["message"])
                return
            
            # Sonuçları widget'a aktar
            check_result = {
                "Alıcı-Satıcı İlişki Kontrolü": result
            }
            self.check_results_widget.set_check_results(check_result)
            
            # Sonuçları göster
            if result.get("data") is not None:
                self.check_results_widget.show_details(result["data"])
                
                # Özet tablosu oluştur
                summary_df = pd.DataFrame({
                    'Özet Bilgi': ['Tespit Edilen İşlem Sayısı', 'Durum'],
                    'Değer': [len(result["data"]), result["status"]]
                })
                self.check_results_widget.show_summary(summary_df)
            
            self.status_label.setText(result["message"])
            
            # İşlem tamamlandı
            self.progress_bar.setValue(100)
            self.progress_bar.setVisible(False)
            QApplication.processEvents()
            
        except Exception as e:
            error_msg = f"Alıcı-Satıcı ilişki kontrolü sırasında hata: {str(e)}"
            print(error_msg)
            QMessageBox.critical(self, "Hata", error_msg)
            self.status_label.setText("Hata oluştu")
            self.progress_bar.setVisible(False)

    def _generate_alici_satici_relationship_html(self, result, summary_df, sender_column):
        """Alıcı-Satıcı ilişki kontrolü için yönetici düzeyinde basit HTML rapor oluştur"""
        try:
            # Güvenli değerler için fallback
            if sender_column is None:
                sender_column = "Adi_unvani"  # Varsayılan sütun
            
            # Temel istatistikleri hesapla (güvenli şekilde)
            if sender_column in self.current_df.columns:
                total_companies = len(self.current_df[sender_column].dropna().unique())
            else:
                total_companies = 0
            total_transactions = len(self.current_df)
            
            # Sonuç tipine göre risk analizi
            if result.get("type") == "selected_companies":
                # Seçili firma kontrolü
                if result.get("data") is not None and not result["data"].empty:
                    # Gönderici sütunu varsa kullan, yoksa Adi_unvani kullan
                    if sender_column in result["data"].columns:
                        selected_companies_count = result["data"][sender_column].nunique()
                    elif "Adi_unvani" in result["data"].columns:
                        selected_companies_count = result["data"]["Adi_unvani"].nunique()
                        sender_column = "Adi_unvani"  # Güncelle
                    else:
                        selected_companies_count = 0
                    
                    if "Beyanname_no" in result["data"].columns:
                        problematic_beyannames = len(result["data"].drop_duplicates(subset=['Beyanname_no']))
                    else:
                        problematic_beyannames = len(result["data"])
                    
                    # Risk seviyesi belirleme (İlişki durumu 6 olanların sayısına göre)
                    if problematic_beyannames > 50:
                        overall_risk = "YÜKSEK"
                        risk_color = "#e74c3c"
                        risk_icon = "🚨"
                    elif problematic_beyannames > 10:
                        overall_risk = "ORTA"
                        risk_color = "#f39c12"
                        risk_icon = "⚠️"
                    else:
                        overall_risk = "DÜŞÜK"
                        risk_color = "#27ae60"
                        risk_icon = "✅"
                    
                    high_risk_companies = selected_companies_count if problematic_beyannames > 50 else 0
                    medium_risk_companies = selected_companies_count if 10 < problematic_beyannames <= 50 else 0
                    low_risk_companies = selected_companies_count if problematic_beyannames <= 10 else 0
                else:
                    selected_companies_count = 0
                    problematic_beyannames = 0
                    overall_risk = "DÜŞÜK"
                    risk_color = "#27ae60"
                    risk_icon = "✅"
                    high_risk_companies = 0
                    medium_risk_companies = 0
                    low_risk_companies = 0
                    
            elif result.get("type") == "all_senders_enhanced":
                # Gelişmiş analiz
                if result.get("data") is not None and "stats" in result:
                    firm_count = result.get("firm_count", 0)
                    total_beyanname_error_count = result.get("total_beyanname_error_count", 0)
                    
                    # Risk seviyesi belirleme (Hatalı beyanname oranına göre)
                    error_rate = (total_beyanname_error_count / total_transactions * 100) if total_transactions > 0 else 0
                    
                    if error_rate > 5:
                        overall_risk = "YÜKSEK"
                        risk_color = "#e74c3c"
                        risk_icon = "🚨"
                        high_risk_companies = firm_count
                        medium_risk_companies = 0
                        low_risk_companies = 0
                    elif error_rate > 1:
                        overall_risk = "ORTA"
                        risk_color = "#f39c12"
                        risk_icon = "⚠️"
                        high_risk_companies = 0
                        medium_risk_companies = firm_count
                        low_risk_companies = 0
                    else:
                        overall_risk = "DÜŞÜK"
                        risk_color = "#27ae60"
                        risk_icon = "✅"
                        high_risk_companies = 0
                        medium_risk_companies = 0
                        low_risk_companies = firm_count
                        
                    problematic_beyannames = total_beyanname_error_count
                else:
                    firm_count = 0
                    problematic_beyannames = 0
                    overall_risk = "DÜŞÜK"
                    risk_color = "#27ae60"
                    risk_icon = "✅"
                    high_risk_companies = 0
                    medium_risk_companies = 0
                    low_risk_companies = 0
            else:
                # Diğer kontrol türleri
                problematic_beyannames = 0
                overall_risk = "DÜŞÜK"
                risk_color = "#27ae60"
                risk_icon = "✅"
                high_risk_companies = 0
                medium_risk_companies = 0
                low_risk_companies = 0
            
            # Risk dağılımı yüzdeleri
            total_risk_companies = high_risk_companies + medium_risk_companies + low_risk_companies
            if total_risk_companies > 0:
                high_risk_pct = (high_risk_companies / total_risk_companies * 100)
                medium_risk_pct = (medium_risk_companies / total_risk_companies * 100)
                low_risk_pct = (low_risk_companies / total_risk_companies * 100)
            else:
                high_risk_pct = medium_risk_pct = low_risk_pct = 0
            
            # Yönetici özeti HTML
            html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <title>Alıcı-Satıcı Risk Analizi</title>
            <style>
                    body {{
                        font-family: 'Segoe UI', Arial, sans-serif;
                margin: 0;
                        padding: 20px;
                        background: #f8f9fa;
                    }}
                    .container {{
                        max-width: 1200px;
                        margin: 0 auto;
                        background: white;
                        border-radius: 10px;
                        box-shadow: 0 4px 20px rgba(0,0,0,0.1);
                        overflow: hidden;
                    }}
                    .header {{
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        color: white;
                        padding: 30px;
                        text-align: center;
                    }}
                    .header h1 {{
                        margin: 0;
                        font-size: 24px;
                        font-weight: 300;
                    }}
                    .executive-summary {{
                        padding: 30px;
                        background: #f8f9fa;
                        border-bottom: 3px solid #dee2e6;
                    }}
                    .risk-banner {{
                        background: {risk_color};
                        color: white;
                        padding: 20px;
                        text-align: center;
                        font-size: 20px;
                        font-weight: bold;
            margin-bottom: 20px;
                        border-radius: 8px;
                    }}
                    .metrics-grid {{
                        display: grid;
                        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                        gap: 20px;
                        margin: 20px 0;
                    }}
                    .metric-card {{
                        background: white;
                        padding: 20px;
                        border-radius: 8px;
                        text-align: center;
                        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                        border-left: 4px solid #3498db;
                    }}
                    .metric-value {{
                        font-size: 32px;
                        font-weight: bold;
                        color: #2c3e50;
                        margin-bottom: 5px;
                    }}
                    .metric-label {{
                        color: #7f8c8d;
                        font-size: 14px;
                        text-transform: uppercase;
                        letter-spacing: 1px;
                    }}
                    .action-required {{
                        background: #fff3cd;
                        border: 1px solid #ffeaa7;
                        border-radius: 8px;
                        padding: 20px;
                        margin: 20px 0;
                    }}
                    .action-required h3 {{
                        color: #856404;
                        margin-top: 0;
                    }}
                    .summary-table {{
                width: 100%;
                border-collapse: collapse;
                        margin: 20px 0;
                    }}
                    .summary-table th {{
                        background: #f8f9fa;
                        padding: 12px;
                text-align: left;
                        border-bottom: 2px solid #dee2e6;
                        font-weight: 600;
                    }}
                    .summary-table td {{
                padding: 12px;
                        border-bottom: 1px solid #dee2e6;
                    }}
                    .summary-table tr:hover {{
                        background: #f8f9fa;
                    }}
                    .recommendation {{
                        background: #e3f2fd;
                        border-left: 4px solid #2196f3;
                        padding: 20px;
                        margin: 20px 0;
                        border-radius: 0 8px 8px 0;
                    }}
                    .detail-table {{
                        width: 100%;
                        border-collapse: collapse;
                        margin: 20px 0;
                        font-size: 12px;
                    }}
                    .detail-table th {{
                        background: linear-gradient(135deg, #1565c0 0%, #1976d2 100%);
                        color: white;
                        padding: 10px 8px;
                        text-align: left;
                        font-weight: 600;
                    }}
                    .detail-table td {{
                        padding: 8px;
                        border-bottom: 1px solid #e0e0e0;
                        vertical-align: top;
                    }}
                    .detail-table tr:nth-child(even) {{
                        background-color: #f8f9fa;
                    }}
                    .detail-table tr:hover {{
                        background-color: #e3f2fd;
                    }}
                    .beyanname-badge {{
                        background: #17a2b8;
                        color: white;
                        padding: 3px 8px;
                        border-radius: 12px;
                        font-size: 10px;
                        font-weight: 500;
                        display: inline-block;
                    }}
                    .firma-name {{
                        font-weight: 500;
                        color: #424242;
                        max-width: 200px;
                        word-wrap: break-word;
                    }}
            </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>🏢 Alıcı-Satıcı İlişki Kontrolü</h1>
                        <p>Yönetici Özeti</p>
                    </div>
                    
                    <div class="executive-summary">
                        <div class="risk-banner">
                            {risk_icon} RİSK SEVİYESİ: {overall_risk}
                        </div>
                        
                        <div class="metrics-grid">
                            <div class="metric-card">
                                <div class="metric-value">{total_companies:,}</div>
                                <div class="metric-label">Toplam Şirket</div>
                    </div>
                            <div class="metric-card">
                                <div class="metric-value">{total_transactions:,}</div>
                                <div class="metric-label">Toplam İşlem</div>
                </div>
                            <div class="metric-card">
                                <div class="metric-value">{problematic_beyannames:,}</div>
                                <div class="metric-label">Sorunlu Beyanname</div>
                    </div>
                            <div class="metric-card">
                                <div class="metric-value">{high_risk_companies + medium_risk_companies:,}</div>
                                <div class="metric-label">İncelenmesi Gereken Şirket</div>
                        </div>
                </div>
                """
            
            # Kontrol türüne göre ek bilgi ekle
            if result.get("type") == "selected_companies":
                html += f"""
                        <div class="action-required">
                            <h3>📋 Seçili Firma Kontrolü</h3>
                            <p>Bu analiz seçilen firmaların <strong>ilişki durumu 6</strong> olan beyannamelerini listeler.</p>
                            <ul>
                                <li><strong>İlişki Durumu 6:</strong> Alıcı ve satıcı arasında dolaylı ya da dolaysız ilişki vardır</li>
                                <li>Bu beyannameler detaylı inceleme gerektirebilir</li>
                            </ul>
                    </div>
                """
                
                # Seçili firmalar için detaylı tablo ekle
                if result.get("data") is not None and not result["data"].empty:
                    data_df = result["data"]
                    
                    # Firma bazında grupla
                    if sender_column in data_df.columns:
                        firma_summary = data_df.groupby(sender_column).agg({
                            'Beyanname_no': 'nunique',
                            'Alici_satici_iliskisi': 'first'
                        }).reset_index()
                        firma_summary.columns = ['Firma', 'Beyanname_Sayisi', 'İlişki_Durumu']
                        firma_summary = firma_summary.sort_values('Beyanname_Sayisi', ascending=False)
                        
                        html += """
                                <h3 style="color: #2c3e50; margin: 20px 0;">📊 Seçili Firmaların Detayları</h3>
                                <table class="detail-table">
                                    <thead>
                                        <tr>
                                            <th style="width: 50%;">Firma Unvanı</th>
                                            <th style="width: 25%;">İlişki Durumu 6 Beyanname Sayısı</th>
                                            <th style="width: 25%;">İlişki Durumu</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                        """
                        
                        for _, row in firma_summary.iterrows():
                            firma = row['Firma']
                            beyanname_sayisi = row['Beyanname_Sayisi']
                            iliski_durumu = row['İlişki_Durumu']
                            
                            html += f"""
                                        <tr>
                                            <td><div class="firma-name">{firma}</div></td>
                                            <td><span class="beyanname-badge">{beyanname_sayisi} beyanname</span></td>
                                            <td>{iliski_durumu}</td>
                                        </tr>
                            """
                        
                        html += """
                                    </tbody>
                                </table>
                        """
                        
                        # Beyanname detayları
                        html += """
                                <h3 style="color: #2c3e50; margin: 20px 0;">📋 Tüm Beyanname Detayları</h3>
                                <table class="detail-table">
                                    <thead>
                                        <tr>
                                            <th style="width: 40%;">Firma Unvanı</th>
                                            <th style="width: 30%;">Beyanname No</th>
                                            <th style="width: 15%;">İlişki Durumu</th>
                                            <th style="width: 15%;">Durum</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                        """
                        
                        # Maksimum 50 beyanname göster
                        for _, row in data_df.head(50).iterrows():
                            firma = row.get(sender_column, '')
                            beyanname = row.get('Beyanname_no', '')
                            iliski_durumu = row.get('Alici_satici_iliskisi', '')
                            
                            html += f"""
                                        <tr>
                                            <td><div class="firma-name">{firma}</div></td>
                                            <td><span class="beyanname-badge">{beyanname}</span></td>
                                            <td>{iliski_durumu}</td>
                                            <td>⚠️ İnceleme Gerekli</td>
                                        </tr>
                            """
                        
                        if len(data_df) > 50:
                            html += f"""
                                        <tr>
                                            <td colspan="4" style="text-align: center; font-style: italic; padding: 15px; background-color: #f5f5f5;">
                                                <strong>📋 Toplam {len(data_df)} beyanname bulundu, ilk 50 tanesi gösterilmektedir.</strong>
                                            </td>
                                        </tr>
                            """
                        
                        html += """
                                    </tbody>
                                </table>
                        """
                        
            elif result.get("type") == "all_senders_enhanced":
                html += f"""
                        <div class="action-required">
                            <h3>🔍 Tutarsızlık Analizi</h3>
                            <p>Bu analiz <strong>aynı firmada hem ilişki durumu 0 hem de 6 olan beyannameleri</strong> tespit eder.</p>
                            <ul>
                                <li><strong>İlişki Durumu 0:</strong> Alıcı ve satıcı arasında ilişki yoktur</li>
                                <li><strong>İlişki Durumu 6:</strong> İlişki vardır ama fiyatı etkilememiştir</li>
                                <li>Aynı firmada her iki kodun kullanılması tutarsızlık gösterir</li>
                            </ul>
                </div>
                """
                
                # Tutarsız firmalar için detaylı tablo ekle
                if result.get("data") is not None and not result["data"].empty and "stats" in result:
                    stats_df = result["stats"]
                    data_df = result["data"]
                    
                    html += """
                            <h3 style="color: #2c3e50; margin: 20px 0;">📊 Tutarsız Firmaların Detayları</h3>
                            <div style="background: #e3f2fd; border: 1px solid #2196f3; border-radius: 6px; padding: 15px; margin: 15px 0;">
                                <strong>ℹ️ Bilgi:</strong> Sayılar <strong>benzersiz beyanname numarası</strong> bazındadır. 
                                Aynı beyanname numarasının farklı satırlarda görünmesi normaldir çünkü her satır ayrı kalem bilgisini temsil eder.
                            </div>
                            <table class="detail-table">
                                <thead>
                                    <tr>
                                        <th style="width: 35%;">Gönderici Firma</th>
                                        <th style="width: 15%;">İlişki Kodu 0<br><small>(Benzersiz Beyanname)</small></th>
                                        <th style="width: 15%;">İlişki Kodu 6<br><small>(Benzersiz Beyanname)</small></th>
                                        <th style="width: 15%;">Hatalı Kod</th>
                                        <th style="width: 20%;">Hatalı Beyanname Sayısı<br><small>(Benzersiz)</small></th>
                                    </tr>
                                </thead>
                                <tbody>
                    """
                    
                    for _, row in stats_df.iterrows():
                        firma = row['Firma']
                        kod_0_sayisi = row['Kod_0_Sayısı']
                        kod_6_sayisi = row['Kod_6_Sayısı']
                        hatali_kod = row['Hatalı_Kod']
                        hatali_beyanname_sayisi = row['Hatalı_Beyanname_Sayısı']
                        
                        # Hata oranına göre renk belirle
                        toplam = kod_0_sayisi + kod_6_sayisi
                        hata_orani = (hatali_beyanname_sayisi / toplam * 100) if toplam > 0 else 0
                        
                        if hata_orani > 50:
                            row_color = "#ffebee"
                            border_color = "#e74c3c"
                        elif hata_orani > 30:
                            row_color = "#fff3e0"
                            border_color = "#f39c12"
                        else:
                            row_color = "#f3e5f5"
                            border_color = "#9c27b0"
                        
                        html += f"""
                                    <tr style="background-color: {row_color}; border-left: 3px solid {border_color};">
                                        <td><div class="firma-name">{firma}</div></td>
                                        <td><span class="beyanname-badge" style="background: #4caf50;">{kod_0_sayisi} beyanname</span></td>
                                        <td><span class="beyanname-badge" style="background: #2196f3;">{kod_6_sayisi} beyanname</span></td>
                                        <td><span class="beyanname-badge" style="background: {border_color};">KOD {hatali_kod}</span></td>
                                        <td><span class="beyanname-badge" style="background: {border_color};">{hatali_beyanname_sayisi} hatalı</span></td>
                                    </tr>
                        """
                    
                    html += """
                                </tbody>
                            </table>
                    """
                    
                    # Tutarsız beyanname detayları
                    html += """
                            <h3 style="color: #2c3e50; margin: 20px 0;">📋 Hatalı Beyanname Detayları</h3>
                            <div style="background: #fff3cd; border: 1px solid #ffeaa7; border-radius: 6px; padding: 15px; margin: 15px 0;">
                                <strong>⚠️ Dikkat:</strong> Bu tabloda her beyanname <strong>sadece bir kez</strong> gösterilir. 
                                Beyanname birden fazla kalem içeriyorsa kalem sayısı belirtilir.
                            </div>
                            <table class="detail-table">
                                <thead>
                                    <tr>
                                        <th style="width: 30%;">Gönderici Firma</th>
                                        <th style="width: 25%;">Beyanname No<br><small>(Benzersiz)</small></th>
                                        <th style="width: 15%;">Kalem Sayısı</th>
                                        <th style="width: 15%;">Kullandığı İlişki Kodu</th>
                                        <th style="width: 15%;">Doğru Kod</th>
                                    </tr>
                                </thead>
                                <tbody>
                    """
                    
                    # Benzersiz beyanname listesi oluştur
                    unique_beyannames_data = []
                    
                    # Her beyanname için kalem sayısını hesapla
                    for beyanname_no in data_df['Beyanname_no'].unique()[:50]:  # İlk 50 benzersiz beyanname
                        beyanname_rows = data_df[data_df['Beyanname_no'] == beyanname_no]
                        first_row = beyanname_rows.iloc[0]  # İlk satırı al
                        kalem_sayisi = len(beyanname_rows)  # Kalem sayısı
                        
                        unique_beyannames_data.append({
                            'beyanname_no': beyanname_no,
                            'firma': first_row.get(sender_column, ''),
                            'kullandigi_kod': first_row.get('Alici_satici_iliskisi', ''),
                            'dogru_kod': first_row.get('Dogru_Kod', ''),
                            'kalem_sayisi': kalem_sayisi
                        })
                    
                    # Benzersiz beyannameleri göster
                    for beyanname_data in unique_beyannames_data:
                        firma = beyanname_data['firma']
                        beyanname_no = beyanname_data['beyanname_no']
                        kullandigi_kod = beyanname_data['kullandigi_kod']
                        dogru_kod = beyanname_data['dogru_kod']
                        kalem_sayisi = beyanname_data['kalem_sayisi']
                        
                        # Bu firmaya ait istatistikleri bul
                        firma_stats = stats_df[stats_df['Firma'] == firma]
                        if not firma_stats.empty:
                            kod_0_sayisi = firma_stats.iloc[0]['Kod_0_Sayısı']
                            kod_6_sayisi = firma_stats.iloc[0]['Kod_6_Sayısı']
                            firma_info = f"(Toplam: {kod_0_sayisi} benzersiz beyanname kod-0, {kod_6_sayisi} benzersiz beyanname kod-6)"
                        else:
                            firma_info = ""
                        
                        # Kalem sayısı badge rengi
                        if kalem_sayisi == 1:
                            kalem_color = "#6c757d"  # Gri - tek kalem
                        elif kalem_sayisi <= 5:
                            kalem_color = "#17a2b8"  # Mavi - az kalem
                        elif kalem_sayisi <= 10:
                            kalem_color = "#ffc107"  # Sarı - orta kalem
                        else:
                            kalem_color = "#dc3545"  # Kırmızı - çok kalem
                        
                        html += f"""
                                    <tr>
                                        <td>
                                            <div class="firma-name">{firma}</div>
                                            <small style="color: #7f8c8d;">{firma_info}</small>
                                        </td>
                                        <td><span class="beyanname-badge">{beyanname_no}</span></td>
                                        <td><span class="beyanname-badge" style="background: {kalem_color};">{kalem_sayisi} kalem</span></td>
                                        <td><span class="beyanname-badge" style="background: #e74c3c;">KOD {kullandigi_kod}</span></td>
                                        <td><span class="beyanname-badge" style="background: #27ae60;">KOD {dogru_kod}</span></td>
                                    </tr>
                        """
                    
                    total_unique_beyannames = len(data_df['Beyanname_no'].unique())
                    if total_unique_beyannames > 50:
                        html += f"""
                                    <tr>
                                        <td colspan="5" style="text-align: center; font-style: italic; padding: 15px; background-color: #f5f5f5;">
                                            <strong>📋 Toplam {total_unique_beyannames} benzersiz hatalı beyanname bulundu, 
                                            ilk 50 tanesi gösterilmektedir.</strong>
                                        </td>
                                    </tr>
                        """
                    
                    html += """
                                </tbody>
                            </table>
                    """
            
            # Özet tablosu varsa ekle
            if not summary_df.empty:
                html += f"""
                        <h3 style="color: #2c3e50; margin: 20px 0;">📊 Özet Tablo</h3>
                        {summary_df.to_html(index=False, classes="summary-table", escape=False)}
                """
            
            # Eylem gerektiren durumlar
            if problematic_beyannames > 0:
                html += f"""
                        <div class="action-required">
                            <h3>⚠️ Eylem Gerektiren Durumlar</h3>
                            <ul>
                                <li><strong>{problematic_beyannames:,} beyanname</strong> sorunlu olarak tespit edildi</li>
                                <li>Bu beyannameler detaylı incelenmeli</li>
                                <li>İlişki durumu beyanları gözden geçirilmeli</li>
                                <li>Gerekirse düzeltme işlemleri yapılmalı</li>
                            </ul>
                </div>
                """
            
            # Öneriler
            html += f"""
                        <div class="recommendation">
                            <h3>📋 Yönetici Önerileri</h3>
            """
            
            if problematic_beyannames > 100:
                html += """
                            <p><strong>Acil Eylem Gerekli!</strong></p>
                            <ul>
                                <li>Sorunlu beyannamelerin tüm işlemlerini gözden geçirin</li>
                                <li>İlişki durumu beyan süreçlerini iyileştirin</li>
                                <li>Personel eğitimi düzenleyin</li>
                            </ul>
                """
            elif problematic_beyannames > 0:
                html += """
                            <p><strong>Dikkatli İzleme Gerekli.</strong></p>
                            <ul>
                                <li>Sorunlu beyannameleri yakından takip edin</li>
                                <li>Düzenli kontroller yapın</li>
                                <li>Önleyici tedbirler alın</li>
                            </ul>
                """
            else:
                html += """
                            <p><strong>Mükemmel Performans!</strong></p>
                            <ul>
                                <li>Hiçbir sorun tespit edilmedi</li>
                                <li>Mevcut kontrol sistemini sürdürün</li>
                                <li>Düzenli izleme yapın</li>
                            </ul>
                """
            
            html += """
                        </div>
                    </div>
                </div>
            </body>
            </html>
            """
            
            return html
            
        except Exception as e:
            print(f"HTML rapor oluşturma detay hatası: {str(e)}")
            # Basit fallback HTML
            return f"""
            <!DOCTYPE html>
            <html>
            <head><meta charset="UTF-8"><title>Alıcı-Satıcı İlişki Kontrolü</title></head>
            <body>
                <h1>Alıcı-Satıcı İlişki Kontrolü</h1>
                <p>Rapor: {result.get('message', 'Sonuç bilinmiyor')}</p>
                <p>Tip: {result.get('type', 'Bilinmiyor')}</p>
                <p>HTML rapor oluşturulurken hata oluştu: {str(e)}</p>
            </body>
            </html>
            """

    def show_merged_dataframes(self):
        """Tüm dataframe'leri birleştir ve göster"""
        if not self.all_dataframes:
            QMessageBox.warning(self, "Uyarı", "Birleştirilecek veri bulunamadı")
            return
            
        try:
            # İlerleme çubuğunu göster
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(10)
            self.status_label.setText("Veriler birleştiriliyor...")
            QApplication.processEvents()
            
            # Tüm dataframe'leri birleştir
            dfs_to_merge = list(self.all_dataframes.values())
            
            if len(dfs_to_merge) == 1:
                # Tek bir dataframe varsa direkt onu göster
                merged_df = dfs_to_merge[0].copy()
            else:
                # Birden fazla dataframe'i birleştir
                merged_df = pd.concat(dfs_to_merge, ignore_index=True)
            
            # İlerleme çubuğunu güncelle
            self.progress_bar.setValue(50)
            self.status_label.setText("Birleştirilmiş veri gösteriliyor...")
            QApplication.processEvents()
            
            # Birleştirilmiş veriyi göster
            self.merged_df = merged_df
            self.display_dataframe(merged_df)
            
            # Başlık bilgisini değiştir
            file_count = len(self.all_dataframes)
            row_count = len(merged_df)
            self.setWindowTitle(f"Beyanname Kontrol Uygulaması - {file_count} Dosya Birleştirildi ({row_count} Satır)")
            
            # Dosya seçiciyi devre dışı bırak (birleştirme modunda)
            self.file_selector.setEnabled(False)
            
            # İlerleme çubuğunu gizle
            self.progress_bar.setVisible(False)
            self.status_label.setText(f"Toplam {file_count} dosya birleştirildi. Toplam {row_count} satır, {len(merged_df.columns)} sütun.")
            
            # Dashboard'u da güncelle (birleştirilmiş veriyle)
            self.update_dashboard()
            
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Veriler birleştirilirken hata oluştu: {str(e)}")
            self.progress_bar.setVisible(False)
            self.status_label.setText("Hata oluştu")
            return

    def create_gtip_summary(self):
        """Create GTIP summary pivot table"""
        QMessageBox.information(self, "Bilgi", "Bu özellik henüz tamamlanmamıştır")
    
    def create_country_summary(self):
        """Create country summary pivot table"""
        QMessageBox.information(self, "Bilgi", "Bu özellik henüz tamamlanmamıştır")
    
    def create_rejim_summary(self):
        """Create rejim summary pivot table"""
        QMessageBox.information(self, "Bilgi", "Bu özellik henüz tamamlanmamıştır")
    
    def create_gtip_country_cross(self):
        """Create GTIP-country cross pivot table"""
        QMessageBox.information(self, "Bilgi", "Bu özellik henüz tamamlanmamıştır")

    # Örnekleme fonksiyonları
    def start_sampling(self):
        """Örnekleme işlemini başlatır"""
        if self.current_df is None:
            QMessageBox.warning(self, "Uyarı", "Örnekleme yapılacak veri yüklenmemiş")
            return
        
        # Onay al
        reply = QMessageBox.question(
            self, 
            "Örnekleme Başlat", 
            "Tüm örnekleme kriterleri uygulanarak beyanname seçimi yapılacaktır. Devam etmek istiyor musunuz?",
            QMessageBox.Yes | QMessageBox.No, 
            QMessageBox.Yes
        )
        
        if reply == QMessageBox.No:
            return
        
        try:
            # İşleme başladığını göster
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(10)
            self.status_label.setText("Örnekleme yapılıyor...")
            QApplication.processEvents()
            
            # Parametreleri al
            sample_rate = float(self.sample_rate_combo.currentText()) / 100
            min_count = self.min_sample_spin.value()
            max_count = self.max_sample_spin.value()
            
            # İlerleme
            self.progress_bar.setValue(30)
            self.status_label.setText("Beyannameler seçiliyor...")
            QApplication.processEvents()
            
            # Örnekleme yap
            self.sampling_tool.set_dataframe(self.current_df)
            
            # İlerleme
            self.progress_bar.setValue(50)
            QApplication.processEvents()
            
            results_df = self.sampling_tool.run_sampling(
                min_sample_count=min_count,
                max_sample_count=max_count,
                sample_percentage=sample_rate
            )
            
            # İlerleme
            self.progress_bar.setValue(80)
            self.status_label.setText("Sonuçlar gösteriliyor...")
            QApplication.processEvents()
            
            # Sonuçları göster
            self.sampling_viewer.set_dataframe(results_df)
            
            # İstatistikleri güncelle
            total_beyannames = self.sampling_tool.sampling_stats.get('total_beyannames', 0)
            selected_count = len(self.sampling_tool.selected_beyannames)
            target_count = self.sampling_tool.sampling_stats.get('target_sample_count', 0)
            selection_rate = (selected_count / total_beyannames * 100) if total_beyannames > 0 else 0
            
            self.sampling_stats_label.setText(
                f"Toplam {total_beyannames} beyannameden {selected_count} tanesi seçildi. " +
                f"Hedef: {target_count} beyanname. " +
                f"Seçim oranı: %{selection_rate:.2f}"
            )
            
            # Butonları etkinleştir
            self.export_excel_btn.setEnabled(True)
            self.clear_sampling_btn.setEnabled(True)
            
            # İşlemi tamamla
            self.progress_bar.setValue(100)
            self.status_label.setText(f"Örnekleme tamamlandı. {selected_count} beyanname seçildi.")
            self.progress_bar.setVisible(False)
            
            # Örnekleme sekmesine geçiş yap
            self.tabs.setCurrentWidget(self.sampling_tab)
            
        except Exception as e:
            # Hata durumunda kullanıcıyı bilgilendir
            QMessageBox.critical(self, "Hata", f"Örnekleme sırasında hata oluştu: {str(e)}")
            self.status_label.setText("Örnekleme sırasında hata oluştu")
            self.progress_bar.setVisible(False)
    
    def export_sampling_to_excel(self):
        """Örnekleme sonuçlarını Excel dosyasına aktarır - Arka plan thread ile"""
        if not hasattr(self, 'sampling_tool') or not self.sampling_tool.selected_beyannames:
            QMessageBox.warning(self, "Uyarı", "Dışa aktarılacak örnekleme sonucu bulunamadı")
            return
        
        try:
            # Excel dosyası adı için kullanıcıdan dosya yolu al
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Excel Dosyasını Kaydet", "", "Excel Files (*.xlsx)"
            )
            
            if not file_path:
                return
            
            # Uzantı kontrolü
            if not file_path.endswith('.xlsx'):
                file_path += '.xlsx'
            
            # Dosya kullanımda mı kontrol et
            try:
                with open(file_path, 'a') as test_file:
                    pass
            except PermissionError:
                QMessageBox.critical(self, "Hata", 
                    f"Dosya başka bir program tarafından kullanılıyor veya açık durumda: {file_path}\n"
                    "Lütfen dosyayı kapatıp tekrar deneyin."
                )
                self.progress_bar.setVisible(False)
                self.status_label.setText("Excel'e aktarma başarısız: Dosya açık")
                return
            except Exception as e:
                QMessageBox.critical(self, "Hata", f"Dosya izin hatası: {str(e)}")
                self.progress_bar.setVisible(False)
                self.status_label.setText("Excel'e aktarma başarısız: Dosya hatası")
                return
            
            # Örneklemeyi kontrol et
            if len(self.sampling_tool.selected_beyannames) == 0:
                QMessageBox.warning(self, "Uyarı", "Seçilen beyanname bulunmuyor.")
                self.progress_bar.setVisible(False)
                self.status_label.setText("Excel'e aktarma başarısız: Seçilen beyanname yok")
                return
            
            # İlerleme çubuğunu göster
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(10)
            self.status_label.setText("Excel aktarma işlemi başlatılıyor...")
            QApplication.processEvents()
            
            # İptal butonu göster (QDialog içinde)
            self.cancel_dialog = QDialog(self)
            self.cancel_dialog.setWindowTitle("Excel'e Aktarma")
            self.cancel_dialog.setModal(True)
            self.cancel_dialog.setFixedSize(300, 100)
            
            dialog_layout = QVBoxLayout(self.cancel_dialog)
            dialog_layout.addWidget(QLabel("Excel aktarım işlemi çalışıyor...\nBu işlem veri boyutuna göre zaman alabilir."))
            
            cancel_btn = QPushButton("İptal")
            cancel_btn.clicked.connect(self.cancel_excel_export)
            dialog_layout.addWidget(cancel_btn)
            
            # Thread oluştur ve başlat
            self.excel_thread = ExcelExportThread(self.sampling_tool, file_path)
            
            # Thread sinyallerini bağla
            self.excel_thread.progress.connect(self.update_excel_progress)
            self.excel_thread.finished.connect(self.on_excel_export_finished)
            
            # Thread'i başlat
            self.excel_thread.start()
            
            # Dialog'u göster (non-blocking)
            self.cancel_dialog.show()
            
        except Exception as e:
            # Beklenmeyen hata durumunda
            import traceback
            print(f"Excel'e aktarma sırasında beklenmeyen hata: {str(e)}")
            print(traceback.format_exc())
            
            QMessageBox.critical(self, "Hata", f"Excel'e aktarma sırasında beklenmeyen bir hata oluştu: {str(e)}")
            self.status_label.setText("Excel'e aktarma sırasında beklenmeyen hata oluştu")
            self.progress_bar.setVisible(False)

    def update_excel_progress(self, value, message):
        """Excel export progress güncellemesi"""
        if hasattr(self, 'progress_bar'):
            self.progress_bar.setValue(value)
        if hasattr(self, 'status_label'):
            self.status_label.setText(message)
        QApplication.processEvents()

    def on_excel_export_finished(self, success, message, file_path):
        """Excel export thread tamamlandığında"""
        # İlerleme çubuğunu güncelle
        if hasattr(self, 'progress_bar'):
            self.progress_bar.setValue(100 if success else 0)
            self.progress_bar.setVisible(False)
        
        # Durum mesajını güncelle
        if hasattr(self, 'status_label'):
            self.status_label.setText(message)
        
        # İptal dialog'unu kapat
        if hasattr(self, 'cancel_dialog') and self.cancel_dialog:
            self.cancel_dialog.accept()
            self.cancel_dialog = None
        
        # Sonuç mesajını göster
        if success:
            QMessageBox.information(self, "İşlem Tamamlandı", f"Örnekleme sonuçları başarıyla Excel dosyasına aktarıldı:\n{file_path}")
        else:
            QMessageBox.warning(self, "İşlem Başarısız", message)

    def cancel_excel_export(self):
        """Excel export işlemini iptal et"""
        if hasattr(self, 'excel_thread') and self.excel_thread.isRunning():
            reply = QMessageBox.question(self, "İşlemi İptal Et", 
                                        "Excel aktarma işlemini iptal etmek istediğinizden emin misiniz?",
                                        QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            
            if reply == QMessageBox.Yes:
                # Thread'i iptal et
                self.excel_thread.cancel()
                
                # Dialog'u kapat
                if hasattr(self, 'cancel_dialog') and self.cancel_dialog:
                    self.cancel_dialog.accept()
                    self.cancel_dialog = None
                
                # İlerleme çubuğunu güncelle
                if hasattr(self, 'progress_bar'):
                    self.progress_bar.setVisible(False)
                
                # Durum mesajını güncelle
                if hasattr(self, 'status_label'):
                    self.status_label.setText("Excel aktarma işlemi iptal edildi")
                
                QMessageBox.information(self, "İşlem İptal Edildi", "Excel aktarma işlemi kullanıcı tarafından iptal edildi.")
        
    def clear_sampling(self):
        """Örnekleme sonuçlarını temizler"""
        if hasattr(self, 'sampling_tool'):
            # Örnekleme aracını temizle
            self.sampling_tool.selected_beyannames = set()
            self.sampling_tool.selection_reasons = {}
            
            # UI'ı temizle
            self.sampling_viewer.set_dataframe(None)
            self.sampling_stats_label.setText("Örnekleme henüz yapılmadı")
            
            # Butonları devre dışı bırak
            self.export_excel_btn.setEnabled(False)
            self.clear_sampling_btn.setEnabled(False)
            
            # Bilgi ver
            self.status_label.setText("Örnekleme sonuçları temizlendi")

    def setup_application_stability(self):
        """Uygulama stabilitesini arttırıcı ayarlar yapar"""
        # Ana uygulama için 5 dakikada bir otomatik kurtarma
        self.stability_timer = QTimer(self)
        self.stability_timer.timeout.connect(self.check_application_health)
        self.stability_timer.start(300000)  # 5 dakika
        
        # Hata yakalama hook'u
        sys.excepthook = self.global_exception_handler

    def check_application_health(self):
        """Uygulama sağlık kontrolü"""
        try:
            # Bellek ve diğer kaynakları temizle
            import gc
            gc.collect()
            
            # UI ile ilgili tüm bekleyen olayları işle
            QApplication.processEvents()
        except Exception as e:
            print(f"Sağlık kontrolü hatası: {str(e)}")

    def global_exception_handler(self, exctype, value, traceback):
        """Global exception handler - uygulama kapanmasını önler"""
        try:
            # Hatayı logla
            import traceback as tb
            error_msg = ''.join(tb.format_exception(exctype, value, traceback))
            print(f"Yakalanan hata:\n{error_msg}")
            
            # Kullanıcıya hatayı bildir ama kapanmayı önle
            QMessageBox.critical(
                self, 
                "Uygulama Hatası", 
                "Bir hata oluştu, ancak uygulama çalışmaya devam edecek.\n\n"
                f"Hata detayı: {str(value)}"
            )
        except:
            # Çift hata durumundan kaçın
            pass

    def check_gtip_urun_kodu_consistency(self):
        """GTİP-Ürün Kodu tutarlılık kontrolü"""
        if self.current_df is None:
            QMessageBox.warning(self, "Uyarı", "Veri yüklenmedi")
            return
        
        try:
            # İşlem başladığını göster (soru sormadan)
            self.status_label.setText("GTİP-Ürün Kodu tutarlılık kontrolü çalışıyor...")
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(10)
            QApplication.processEvents()
            
            # Analiz fonksiyonunu çağır
            gtip_urun_kodu_check = check_gtip_urun_kodu_consistency(self.current_df)
            
            # İşlem tamamlandığını göster
            self.progress_bar.setValue(60)
            QApplication.processEvents()
            
            if gtip_urun_kodu_check is not None:
                result = {
                    "GTIP-Ürün Kodu tutarlılık kontrolü": gtip_urun_kodu_check
                }
                
                # Sonuçları widget'a aktar
                self.check_results_widget.set_check_results(result)
                
                # HTML raporunu göster
                if "html_report" in gtip_urun_kodu_check:
                    self.check_results_widget.set_html_report(gtip_urun_kodu_check["html_report"])
                    self.check_results_widget.tabs.setCurrentIndex(3)
                
                    self.status_label.setText("GTİP-Ürün Kodu kontrolü tamamlandı")
            else:
                result = {
                    "GTIP-Ürün Kodu tutarlılık kontrolü": {
                        "status": "ok",
                        "message": "GTİP-Ürün Kodu kontrolü yapılamadı"
                    }
                }
                self.check_results_widget.set_check_results(result)
                self.status_label.setText("GTİP-Ürün Kodu kontrolü tamamlandı")
                
            self.progress_bar.setValue(100)
            self.progress_bar.setVisible(False)
        
        except Exception as e:
            error_msg = f"GTİP-Ürün Kodu kontrolü sırasında hata: {str(e)}"
            print(error_msg)
            QMessageBox.critical(self, "Hata", error_msg)
            self.status_label.setText("Hata oluştu")
            self.progress_bar.setVisible(False)

    def check_rarely_used_currency(self):
        """Nadiren kullanılan döviz kontrolü"""
        if self.current_df is None:
            QMessageBox.warning(self, "Uyarı", "Veri yüklenmedi")
            return
        
        try:
            # İşlem başladığını göster (soru sormadan)
            self.status_label.setText("Nadiren kullanılan döviz analizi çalışıyor...")
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(10)
            QApplication.processEvents()
            
            # Analiz fonksiyonunu çağır
            currency_check = check_rarely_used_currency(self.current_df)
            
            # İşlem tamamlandığını göster
            self.progress_bar.setValue(60)
            QApplication.processEvents()
            
            if currency_check is not None:
            result = {
                    "Nadiren Kullanılan Döviz Kontrolü": currency_check
            }
            
            # Sonuçları widget'a aktar
            self.check_results_widget.set_check_results(result)
            
            # HTML raporunu göster
            if "html_report" in currency_check:
                self.check_results_widget.set_html_report(currency_check["html_report"])
                    self.check_results_widget.tabs.setCurrentIndex(3)
                
                self.status_label.setText("Nadiren kullanılan döviz kontrolü tamamlandı")
            else:
                result = {
                    "Nadiren Kullanılan Döviz Kontrolü": {
                        "status": "ok",
                        "message": "Nadiren kullanılan döviz kontrolü yapılamadı"
                    }
                }
                self.check_results_widget.set_check_results(result)
                self.status_label.setText("Nadiren kullanılan döviz kontrolü tamamlandı")
            
            self.progress_bar.setValue(100)
            self.progress_bar.setVisible(False)
        
        except Exception as e:
            error_msg = f"Nadiren kullanılan döviz kontrolü sırasında hata: {str(e)}"
            print(error_msg)
            QMessageBox.critical(self, "Hata", error_msg)
            self.status_label.setText("Hata oluştu")
            self.progress_bar.setVisible(False)
            
    def check_rarely_used_origin_country(self):
        """Nadiren kullanılan menşe ülke kontrolü"""
        if self.current_df is None:
            QMessageBox.warning(self, "Uyarı", "Veri yüklenmedi")
            return
        
        try:
            # İşlem başladığını göster (soru sormadan)
            self.status_label.setText("Nadiren kullanılan menşe ülke analizi çalışıyor...")
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(10)
            QApplication.processEvents()
            
            # Analiz fonksiyonunu çağır
            origin_check = check_rarely_used_origin_country(self.current_df)
            
            # İşlem tamamlandığını göster
            self.progress_bar.setValue(60)
            QApplication.processEvents()
            
            if origin_check is not None:
                result = {
                    "Nadiren Kullanılan Menşe Ülke Kontrolü": origin_check
                }
                
                # Sonuçları widget'a aktar
                self.check_results_widget.set_check_results(result)
                
                # HTML raporunu göster
                if "html_report" in origin_check:
                    self.check_results_widget.set_html_report(origin_check["html_report"])
                    self.check_results_widget.tabs.setCurrentIndex(3)
                
                self.status_label.setText("Nadiren kullanılan menşe ülke kontrolü tamamlandı")
            else:
                result = {
                    "Nadiren Kullanılan Menşe Ülke Kontrolü": {
                        "status": "ok",
                        "message": "Nadiren kullanılan menşe ülke kontrolü yapılamadı"
                    }
                }
                self.check_results_widget.set_check_results(result)
                self.status_label.setText("Nadiren kullanılan menşe ülke kontrolü tamamlandı")
            
            self.progress_bar.setValue(100)
                self.progress_bar.setVisible(False)
            
        except Exception as e:
            error_msg = f"Nadiren kullanılan menşe ülke kontrolü sırasında hata: {str(e)}"
            print(error_msg)
            QMessageBox.critical(self, "Hata", error_msg)
            self.status_label.setText("Hata oluştu")
            self.progress_bar.setVisible(False)

    def check_rarely_used_origin_country_by_sender_gtip(self):
        """Gönderici-GTİP bazında nadir menşe ülke kontrolü"""
        if self.current_df is None:
            QMessageBox.warning(self, "Uyarı", "Veri yüklenmedi")
                return
            
        try:
            # İşlem başladığını göster (soru sormadan)
            self.status_label.setText("Gönderici-GTİP bazında nadir menşe ülke analizi çalışıyor...")
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(10)
            QApplication.processEvents()
            
            # Analiz fonksiyonunu çağır
            sender_gtip_check = check_rarely_used_origin_country_by_sender_gtip(self.current_df)
            
            # İşlem tamamlandığını göster
            self.progress_bar.setValue(60)
            QApplication.processEvents()
            
            if sender_gtip_check is not None:
            result = {
                    "Gönderici-GTİP Bazında Nadir Menşe Ülke Analizi": sender_gtip_check
            }
            
            # Sonuçları widget'a aktar
            self.check_results_widget.set_check_results(result)
            
            # HTML raporunu göster
                if "html_report" in sender_gtip_check:
                    self.check_results_widget.set_html_report(sender_gtip_check["html_report"])
                    self.check_results_widget.tabs.setCurrentIndex(3)
                
            # Tablo ve özet verilerini göster
                if "data" in sender_gtip_check and "summary" in sender_gtip_check:
                    self.check_results_widget.show_details(sender_gtip_check["data"])
                    self.check_results_widget.show_summary(sender_gtip_check["summary"])
                
                self.status_label.setText(sender_gtip_check["message"])
            else:
                result = {
                    "Gönderici-GTİP Bazında Nadir Menşe Ülke Analizi": {
                        "status": "ok",
                        "message": "Gönderici-GTİP bazında nadir menşe ülke kontrolü yapılamadı"
                    }
                }
                self.check_results_widget.set_check_results(result)
                self.status_label.setText("Gönderici-GTİP bazında nadir menşe ülke kontrolü tamamlandı")
            
            self.progress_bar.setValue(100)
            self.progress_bar.setVisible(False)
        
        except Exception as e:
            error_msg = f"Gönderici-GTİP bazında nadir menşe ülke analizi sırasında hata: {str(e)}"
            print(error_msg)
            QMessageBox.critical(self, "Hata", error_msg)
            self.status_label.setText("Hata oluştu")
            self.progress_bar.setVisible(False)
            
    def check_rarely_used_payment_method(self):
        """Nadiren kullanılan ödeme şekli kontrolü"""
        if self.current_df is None:
            QMessageBox.warning(self, "Uyarı", "Veri yüklenmedi")
            return
        
        try:
            # İşlem başladığını göster (soru sormadan)
            self.status_label.setText("Nadiren kullanılan ödeme şekli analizi çalışıyor...")
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(10)
            QApplication.processEvents()
            
            # Analiz fonksiyonunu çağır
            payment_check = check_rarely_used_payment_method(self.current_df)
            
            # İşlem tamamlandığını göster
            self.progress_bar.setValue(60)
            QApplication.processEvents()
            
            if payment_check is not None:
            result = {
                    "Nadiren Kullanılan Ödeme Şekli Kontrolü": payment_check
            }
            
            # Sonuçları widget'a aktar
            self.check_results_widget.set_check_results(result)
            
            # HTML raporunu göster
            if "html_report" in payment_check:
                self.check_results_widget.set_html_report(payment_check["html_report"])
                    self.check_results_widget.tabs.setCurrentIndex(3)
                
                self.status_label.setText("Nadiren kullanılan ödeme şekli kontrolü tamamlandı")
            else:
                result = {
                    "Nadiren Kullanılan Ödeme Şekli Kontrolü": {
                        "status": "ok",
                        "message": "Nadiren kullanılan ödeme şekli kontrolü yapılamadı"
                    }
                }
                self.check_results_widget.set_check_results(result)
                self.status_label.setText("Nadiren kullanılan ödeme şekli kontrolü tamamlandı")
            
            self.progress_bar.setValue(100)
            self.progress_bar.setVisible(False)
        
        except Exception as e:
            error_msg = f"Nadiren kullanılan ödeme şekli kontrolü sırasında hata: {str(e)}"
            print(error_msg)
            QMessageBox.critical(self, "Hata", error_msg)
            self.status_label.setText("Hata oluştu")
            self.progress_bar.setVisible(False)

    def check_unit_price_increase(self):
        """Birim fiyat artışı kontrolü"""
        if self.current_df is None:
            QMessageBox.warning(self, "Uyarı", "Veri yüklenmedi")
            return
        
        try:
            # İşlem başladığını göster (soru sormadan)
            self.status_label.setText("Birim fiyat artış analizi çalışıyor...")
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(10)
            QApplication.processEvents()
            
            # Analiz fonksiyonunu çağır
            price_check = check_unit_price_increase(self.current_df)
            
            # İşlem tamamlandığını göster
            self.progress_bar.setValue(60)
            QApplication.processEvents()
            
            if price_check is not None:
            result = {
                    "Birim Fiyat Artışı Kontrolü": price_check
            }
            
            # Sonuçları widget'a aktar
            self.check_results_widget.set_check_results(result)
            
            # HTML raporunu göster
            if "html_report" in price_check:
                self.check_results_widget.set_html_report(price_check["html_report"])
                    self.check_results_widget.tabs.setCurrentIndex(3)
                
                self.status_label.setText("Birim fiyat artışı kontrolü tamamlandı")
            else:
                result = {
                    "Birim Fiyat Artışı Kontrolü": {
                        "status": "ok",
                        "message": "Birim fiyat artışı kontrolü yapılamadı"
                    }
                }
                self.check_results_widget.set_check_results(result)
                self.status_label.setText("Birim fiyat artışı kontrolü tamamlandı")
            
            self.progress_bar.setValue(100)
            self.progress_bar.setVisible(False)
        
        except Exception as e:
            error_msg = f"Birim fiyat artışı kontrolü sırasında hata: {str(e)}"
            print(error_msg)
            QMessageBox.critical(self, "Hata", error_msg)
            self.status_label.setText("Hata oluştu")
            self.progress_bar.setVisible(False)

    def check_kdv_consistency(self):
        """KDV tutarlılık kontrolü"""
        if self.current_df is None:
            QMessageBox.warning(self, "Uyarı", "Veri yüklenmedi")
            return
        
        try:
            # İşlem başladığını göster (soru sormadan)
            self.status_label.setText("KDV tutarlılık kontrolü çalışıyor...")
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(10)
            QApplication.processEvents()
            
            # Analiz fonksiyonunu çağır
            kdv_check = check_kdv_consistency(self.current_df)
            
            # İşlem tamamlandığını göster
            self.progress_bar.setValue(60)
            QApplication.processEvents()
            
            if kdv_check is not None:
            result = {
                    "KDV Tutarlılık Kontrolü": kdv_check
            }
            
            # Sonuçları widget'a aktar
            self.check_results_widget.set_check_results(result)
            
            # HTML raporunu göster
            if "html_report" in kdv_check:
                self.check_results_widget.set_html_report(kdv_check["html_report"])
                    self.check_results_widget.tabs.setCurrentIndex(3)
                
                self.status_label.setText("KDV tutarlılık kontrolü tamamlandı")
            else:
                result = {
                    "KDV Tutarlılık Kontrolü": {
                        "status": "ok",
                        "message": "KDV tutarlılık kontrolü yapılamadı"
                    }
                }
                self.check_results_widget.set_check_results(result)
                self.status_label.setText("KDV tutarlılık kontrolü tamamlandı")
            
            self.progress_bar.setValue(100)
            self.progress_bar.setVisible(False)
        
        except Exception as e:
            error_msg = f"KDV tutarlılık kontrolü sırasında hata: {str(e)}"
            print(error_msg)
            QMessageBox.critical(self, "Hata", error_msg)
            self.status_label.setText("Hata oluştu")
            self.progress_bar.setVisible(False)

    def check_domestic_expense_variation(self):
        """Yurt içi gider kontrolü"""
        if self.current_df is None:
            QMessageBox.warning(self, "Uyarı", "Veri yüklenmedi")
            return
        
        try:
            # İşlem başladığını göster (soru sormadan)
            self.status_label.setText("Yurt içi gider analizi çalışıyor...")
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(10)
            QApplication.processEvents()
            
            # Analiz fonksiyonunu çağır
            domestic_check = check_domestic_expense_variation(self.current_df)
            
            # İşlem tamamlandığını göster
            self.progress_bar.setValue(60)
            QApplication.processEvents()
            
            if domestic_check is not None:
            result = {
                    "Yurt İçi Gider Kontrolü": domestic_check
            }
            
            # Sonuçları widget'a aktar
            self.check_results_widget.set_check_results(result)
            
            # HTML raporunu göster
                if "html_report" in domestic_check:
                    self.check_results_widget.set_html_report(domestic_check["html_report"])
                    self.check_results_widget.tabs.setCurrentIndex(3)
                
                self.status_label.setText("Yurt içi gider kontrolü tamamlandı")
            else:
                result = {
                    "Yurt İçi Gider Kontrolü": {
                        "status": "ok",
                        "message": "Yurt içi gider kontrolü yapılamadı"
                    }
                }
                self.check_results_widget.set_check_results(result)
                self.status_label.setText("Yurt içi gider kontrolü tamamlandı")
            
            self.progress_bar.setValue(100)
            self.progress_bar.setVisible(False)
        
        except Exception as e:
            error_msg = f"Yurt içi gider kontrolü sırasında hata: {str(e)}"
            print(error_msg)
            QMessageBox.critical(self, "Hata", error_msg)
            self.status_label.setText("Hata oluştu")
            self.progress_bar.setVisible(False)

    def check_foreign_expense_variation(self):
        """Yurt dışı gider kontrolü"""
        if self.current_df is None:
            QMessageBox.warning(self, "Uyarı", "Veri yüklenmedi")
            return
        
        try:
            # İşlem başladığını göster (soru sormadan)
            self.status_label.setText("Yurt dışı gider analizi çalışıyor...")
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(10)
            QApplication.processEvents()
            
            # Analiz fonksiyonunu çağır
            foreign_check = check_foreign_expense_variation(self.current_df)
            
            # İşlem tamamlandığını göster
            self.progress_bar.setValue(60)
            QApplication.processEvents()
            
            if foreign_check is not None:
            result = {
                    "Yurt Dışı Gider Kontrolü": foreign_check
            }
            
            # Sonuçları widget'a aktar
            self.check_results_widget.set_check_results(result)
            
            # HTML raporunu göster
                if "html_report" in foreign_check:
                    self.check_results_widget.set_html_report(foreign_check["html_report"])
                    self.check_results_widget.tabs.setCurrentIndex(3)
                
                self.status_label.setText("Yurt dışı gider kontrolü tamamlandı")
            else:
                result = {
                    "Yurt Dışı Gider Kontrolü": {
                        "status": "ok",
                        "message": "Yurt dışı gider kontrolü yapılamadı"
                    }
                }
                self.check_results_widget.set_check_results(result)
                self.status_label.setText("Yurt dışı gider kontrolü tamamlandı")
            
            self.progress_bar.setValue(100)
            self.progress_bar.setVisible(False)
        
        except Exception as e:
            error_msg = f"Yurt dışı gider kontrolü sırasında hata: {str(e)}"
            print(error_msg)
            QMessageBox.critical(self, "Hata", error_msg)
            self.status_label.setText("Hata oluştu")
            self.progress_bar.setVisible(False)

    def check_supalan_storage(self):
        """Supalan-depolama kontrolü"""
        if self.current_df is None:
            QMessageBox.warning(self, "Uyarı", "Veri yüklenmedi")
            return
        
        try:
            # İşlem başladığını göster (soru sormadan)
            self.status_label.setText("Supalan-depolama analizi çalışıyor...")
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(10)
            QApplication.processEvents()
            
            # Analiz fonksiyonunu çağır
            storage_check = check_supalan_storage(self.current_df)
            
            # İşlem tamamlandığını göster
            self.progress_bar.setValue(60)
            QApplication.processEvents()
            
            if storage_check is not None:
            result = {
                    "Supalan-Depolama Kontrolü": storage_check
            }
            
            # Sonuçları widget'a aktar
            self.check_results_widget.set_check_results(result)
            
            # HTML raporunu göster
                if "html_report" in storage_check:
                    self.check_results_widget.set_html_report(storage_check["html_report"])
                    self.check_results_widget.tabs.setCurrentIndex(3)
                
                self.status_label.setText("Supalan-depolama kontrolü tamamlandı")
            else:
                result = {
                    "Supalan-Depolama Kontrolü": {
                        "status": "ok",
                        "message": "Supalan-depolama kontrolü yapılamadı"
                    }
                }
                self.check_results_widget.set_check_results(result)
                self.status_label.setText("Supalan-depolama kontrolü tamamlandı")
            
            self.progress_bar.setValue(100)
            self.progress_bar.setVisible(False)
        
        except Exception as e:
            error_msg = f"Supalan-depolama kontrolü sırasında hata: {str(e)}"
            print(error_msg)
            QMessageBox.critical(self, "Hata", error_msg)
            self.status_label.setText("Hata oluştu")
            self.progress_bar.setVisible(False)

    def check_gtip_tanim_detail(self):
        """GTİP-Tanım detay kontrolü"""
        if self.current_df is None:
            QMessageBox.warning(self, "Uyarı", "Veri yüklenmedi")
            return
        
        try:
            # İşlem başladığını göster (soru sormadan)
            self.status_label.setText("GTİP-Tanım detay analizi çalışıyor...")
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(10)
            QApplication.processEvents()
            
            # Analiz fonksiyonunu çağır
            from analysis_modules.gtip_analysis import check_gtip_tanim_detail
            gtip_detail_check = check_gtip_tanim_detail(self.current_df)
            
            # İşlem tamamlandığını göster
            self.progress_bar.setValue(60)
            QApplication.processEvents()
            
            if gtip_detail_check is not None:
                result = {
                    "GTİP-Tanım Detay Kontrolü": gtip_detail_check
                }
                
                # Sonuçları widget'a aktar
                self.check_results_widget.set_check_results(result)
                
                # HTML raporunu göster
                if "html_report" in gtip_detail_check:
                    self.check_results_widget.set_html_report(gtip_detail_check["html_report"])
                    self.check_results_widget.tabs.setCurrentIndex(3)
                
                self.status_label.setText("GTİP-Tanım detay kontrolü tamamlandı")
            else:
                result = {
                    "GTİP-Tanım Detay Kontrolü": {
                        "status": "ok",
                        "message": "GTİP-Tanım detay kontrolü yapılamadı"
                    }
                }
                self.check_results_widget.set_check_results(result)
                self.status_label.setText("GTİP-Tanım detay kontrolü tamamlandı")
            
            self.progress_bar.setValue(100)
            self.progress_bar.setVisible(False)
            
        except Exception as e:
            error_msg = f"GTİP-Tanım detay kontrolü sırasında hata: {str(e)}"
            print(error_msg)
            QMessageBox.critical(self, "Hata", error_msg)
            self.status_label.setText("Hata oluştu")
            self.progress_bar.setVisible(False)

    # Tüm kontrolleri otomatik çalıştır
    def run_all_checks_auto(self):
        """Tüm kontrolleri otomatik olarak çalıştır"""
        if self.current_df is None:
            QMessageBox.warning(self, "Uyarı", "Veri yüklenmedi")
            return
        
        # İlerleme çubuğunu göster
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("Tüm kontroller otomatik olarak çalıştırılıyor...")
        QApplication.processEvents()
        
        # Tüm kontrol sonuçlarını saklamak için
        self.all_check_results = {}
        
        # Kontrol listesi (fonksiyon adı, görünen ad, ilerleme değeri)
        checks = [
            (self.check_islem_niteligi_consistency, "İşlem Niteliği Kontrolü", 10),
            (self.check_gtip_tanim_detail, "GTİP-Tanım Detay Analizi", 20),
            (self.check_gtip_urun_kodu_consistency, "GTİP-Ürün Kodu Kontrolü", 30),
            (self.check_alici_satici_relationship, "Alıcı-Satıcı İlişki Kontrolü", 40),
            (self.check_rarely_used_currency, "Nadir Döviz Kontrolü", 50),
            (self.check_rarely_used_origin_country, "Nadir Menşe Ülke Kontrolü", 60),
            (self.check_rarely_used_origin_country_by_sender_gtip, "Gönderici-GTİP Nadir Menşe Kontrolü", 65),
            (self.check_rarely_used_payment_method, "Nadir Ödeme Şekli Kontrolü", 70),
            (self.check_unit_price_increase, "Birim Fiyat Artışı Kontrolü", 80),
            (self.check_kdv_consistency, "KDV Tutarlılık Kontrolü", 85),
            (self.check_domestic_expense_variation, "Yurt İçi Gider Kontrolü", 90),
            (self.check_foreign_expense_variation, "Yurt Dışı Gider Kontrolü", 95),
            (self.check_supalan_storage, "Supalan-Depolama Kontrolü", 100)
        ]
        
        successful_checks = 0
        total_checks = len(checks)
        
        for check_func, check_name, progress_value in checks:
            try:
                self.status_label.setText(f"{check_name} çalıştırılıyor...")
                self.progress_bar.setValue(progress_value)
                QApplication.processEvents()
                
                # Kontrolü çalıştır
                check_func()
                successful_checks += 1
                
                # Kısa bekleme
                QApplication.processEvents()
                time.sleep(0.1)
                
            except Exception as e:
                print(f"{check_name} hatası: {str(e)}")
                continue
        
        # Tamamlandı
        self.progress_bar.setValue(100)
        self.status_label.setText(f"Tüm kontroller tamamlandı! ({successful_checks}/{total_checks} başarılı)")
        
        # 2 saniye sonra progress bar'ı gizle
        QTimer.singleShot(2000, lambda: self.progress_bar.setVisible(False))
        
        # Sonuçları göster
        QMessageBox.information(self, "Tamamlandı", 
                              f"Tüm kontroller tamamlandı!\n\n"
                              f"Başarılı: {successful_checks}/{total_checks}\n"
                              f"Sonuçları Excel'e aktarmak için 'Tüm Sonuçları Excel'e Aktar' butonunu kullanın.")

    def export_all_results_to_excel(self):
        """Tüm kontrol sonuçlarını tek bir Excel dosyasına aktar"""
        if not hasattr(self, 'check_results_widget'):
            QMessageBox.warning(self, "Uyarı", "Kontrol sonuçları widget'ı bulunamadı.")
            return
            
        # Check results widget'ın check_results özelliğini kontrol et
        if not hasattr(self.check_results_widget, 'check_results') or not self.check_results_widget.check_results:
            QMessageBox.warning(self, "Uyarı", "Henüz kontrol sonucu yok. Önce kontrolleri çalıştırın.")
            return
        
        # Dosya kaydetme dialogu
        file_path, _ = QFileDialog.getSaveFileName(
            self, 
            "Tüm Kontrol Sonuçlarını Kaydet", 
            f"tum_kontrol_sonuclari_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            "Excel Files (*.xlsx)"
        )
        
        if not file_path:
                return
            
        try:
            # İlerleme çubuğunu göster
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(0)
            self.status_label.setText("Excel dosyası oluşturuluyor...")
            QApplication.processEvents()
            
            # Excel writer oluştur
            with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                
                # Özet sayfa oluştur
                self.progress_bar.setValue(10)
                self.status_label.setText("Özet sayfa oluşturuluyor...")
            QApplication.processEvents()
            
                summary_data = []
                all_findings = []  # Tüm tespitleri toplamak için
                
                # Her kontrol sonucunu işle
                for i, (check_name, result) in enumerate(self.check_results_widget.check_results.items()):
                    progress = 10 + (i * 80 / len(self.check_results_widget.check_results))
                    self.progress_bar.setValue(int(progress))
                    self.status_label.setText(f"İşleniyor: {check_name}")
            QApplication.processEvents()
            
                    # Özet bilgiler
                    status = result.get('status', 'unknown')
                    message = result.get('message', 'Mesaj yok')
                    
                    summary_data.append({
                        'Kontrol_Adi': check_name,
                        'Durum': status,
                        'Sonuc': message,
                        'Tespit_Sayisi': len(result.get('data', [])) if 'data' in result and hasattr(result['data'], '__len__') else 0
                    })
                    
                    # Eğer veri varsa, ayrı sayfa oluştur
                    if 'data' in result and hasattr(result['data'], 'to_excel'):
                        try:
                            # Sayfa adını temizle (Excel için geçersiz karakterleri kaldır)
                            sheet_name = check_name.replace('/', '_').replace('\\', '_').replace('?', '_').replace('*', '_').replace('[', '_').replace(']', '_')[:31]
                            
                            # Veriyi sayfaya yaz
                            result['data'].to_excel(writer, sheet_name=sheet_name, index=False)
                            
                            # Tüm tespitlere ekle (beyanname numarası ile)
                            if 'Beyanname_no' in result['data'].columns:
                                for _, row in result['data'].iterrows():
                                    finding = {
                                        'Beyanname_No': row.get('Beyanname_no', ''),
                                        'Kontrol_Turu': check_name,
                                        'Tespit': message,
                                        'Detay': str(row.to_dict())[:500] + '...' if len(str(row.to_dict())) > 500 else str(row.to_dict())
                                    }
                                    all_findings.append(finding)
                                    
                        except Exception as e:
                            print(f"{check_name} sayfası oluşturulurken hata: {str(e)}")
                            continue
                
                # Özet sayfayı yaz
                summary_df = pd.DataFrame(summary_data)
                summary_df.to_excel(writer, sheet_name='OZET', index=False)
                
                # Tüm tespitler sayfası
                if all_findings:
                    findings_df = pd.DataFrame(all_findings)
                    findings_df.to_excel(writer, sheet_name='TUM_TESPITLER', index=False)
                
                # Genel bilgiler sayfası
                self.progress_bar.setValue(95)
                self.status_label.setText("Genel bilgiler ekleniyor...")
            QApplication.processEvents()
            
                info_data = [
                    ['Rapor Tarihi', pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')],
                    ['Toplam Kayit Sayisi', len(self.current_df) if self.current_df is not None else 0],
                    ['Toplam Kontrol Sayisi', len(self.check_results_widget.check_results)],
                    ['Toplam Tespit Sayisi', len(all_findings)],
                    ['Dosya Adi', getattr(self, 'current_file_name', 'Bilinmiyor')]
                ]
                
                info_df = pd.DataFrame(info_data, columns=['Bilgi', 'Deger'])
                info_df.to_excel(writer, sheet_name='GENEL_BILGILER', index=False)
            
            # Tamamlandı
            self.progress_bar.setValue(100)
            self.status_label.setText("Excel dosyası başarıyla oluşturuldu!")
            
            # 2 saniye sonra progress bar'ı gizle
            QTimer.singleShot(2000, lambda: self.progress_bar.setVisible(False))
            
            # Başarı mesajı
            QMessageBox.information(self, "Başarılı", 
                                  f"Tüm kontrol sonuçları başarıyla Excel'e aktarıldı!\n\n"
                                  f"Dosya: {file_path}\n"
                                  f"Toplam tespit: {len(all_findings)} adet\n"
                                  f"Toplam sayfa: {len(self.check_results_widget.check_results) + 3}")
            
        except Exception as e:
            self.progress_bar.setVisible(False)
            QMessageBox.critical(self, "Hata", f"Excel dosyası oluşturulurken hata:\n{str(e)}")

    def on_tab_changed(self, index):
        """Tab değiştiğinde çağrılır"""
        try:
            # Dashboard sekmesine geçildiğinde güncelle
            if index == 3:  # Dashboard tab index
                self.update_dashboard()
        except Exception as e:
            print(f"Tab değişim hatası: {str(e)}")

    def setup_shortcuts(self):
        """Kısayol tuşlarını ayarla"""
        try:
            from PyQt5.QtWidgets import QShortcut
            from PyQt5.QtGui import QKeySequence
            
            # Ctrl+O: XML dosyası aç
            open_shortcut = QShortcut(QKeySequence("Ctrl+O"), self)
            open_shortcut.activated.connect(self.import_xml)
            
            # Ctrl+Shift+O: XML klasörü aç
            open_folder_shortcut = QShortcut(QKeySequence("Ctrl+Shift+O"), self)
            open_folder_shortcut.activated.connect(self.import_xml_folder)
            
            # F5: Tüm kontrolleri çalıştır
            run_all_shortcut = QShortcut(QKeySequence("F5"), self)
            run_all_shortcut.activated.connect(self.run_all_checks_auto)
            
        except Exception as e:
            print(f"Kısayol ayarlama hatası: {str(e)}")

    def _run_alici_satici_check(self):
        """Alıcı-Satıcı ilişki kontrolü çalıştır"""
        from analysis_modules.relationship_analysis import check_alici_satici_relationship
        return check_alici_satici_relationship(self.current_df)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CustomsCheckApp()
    window.show()
    sys.exit(app.exec_()) 