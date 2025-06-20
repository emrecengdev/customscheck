"""
UI bileşenleri modülü.
Bu modül, uygulamada kullanılan özel UI bileşenlerini içerir.
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                            QComboBox, QPushButton, QTableView)
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

# Diğer modüllerden içe aktarmalar
from .summary_functions import create_custom_pivot
from .chart_functions import create_bar_chart, create_pie_chart, create_scatter_plot

class PivotWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.df = None
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Kontrol alanı
        control_layout = QHBoxLayout()
        
        # Pivot tablo parametreleri
        self.index_label = QLabel("Satırlar:")
        self.index_selector = QComboBox()
        
        self.values_label = QLabel("Değerler:")
        self.values_selector = QComboBox()
        
        self.columns_label = QLabel("Sütunlar:")
        self.columns_selector = QComboBox()
        
        self.aggfunc_label = QLabel("İşlev:")
        self.aggfunc_selector = QComboBox()
        self.aggfunc_selector.addItems(["sum", "count", "mean", "min", "max"])
        
        # Oluştur butonu
        self.create_btn = QPushButton("Pivot Tablo Oluştur")
        self.create_btn.clicked.connect(self.create_pivot)
        
        # Kontrol alanını düzenle
        control_layout.addWidget(self.index_label)
        control_layout.addWidget(self.index_selector)
        control_layout.addWidget(self.values_label)
        control_layout.addWidget(self.values_selector)
        control_layout.addWidget(self.columns_label)
        control_layout.addWidget(self.columns_selector)
        control_layout.addWidget(self.aggfunc_label)
        control_layout.addWidget(self.aggfunc_selector)
        control_layout.addWidget(self.create_btn)
        
        layout.addLayout(control_layout)
        
        # Tablo görünümü
        self.table_view = QTableView()
        layout.addWidget(self.table_view)
    
    def set_dataframe(self, df):
        """
        DataFrame'i ayarlar ve UI'yı günceller
        """
        self.df = df
        
        if df is not None:
            # Sütun seçicileri güncelle
            self.index_selector.clear()
            self.values_selector.clear()
            self.columns_selector.clear()
            
            # Tüm sütunları ekle
            self.index_selector.addItems(df.columns)
            self.values_selector.addItems(df.columns)
            self.columns_selector.addItem("(Yok)")
            self.columns_selector.addItems(df.columns)
    
    def create_pivot(self):
        """
        Seçilen parametrelerle pivot tablo oluşturur
        """
        if self.df is None:
            return
        
        index = self.index_selector.currentText()
        values = self.values_selector.currentText()
        
        columns_text = self.columns_selector.currentText()
        columns = None if columns_text == "(Yok)" else columns_text
        
        aggfunc = self.aggfunc_selector.currentText()
        
        # Pivot tabloyu oluştur
        pivot = create_custom_pivot(self.df, index, values, columns, aggfunc)
        
        if pivot is not None:
            # Tabloyu göster
            from custom_widgets import PandasModel
            model = PandasModel(pivot)
            self.table_view.setModel(model)
            
            # Sütunları yeniden boyutlandır
            self.table_view.resizeColumnsToContents()

class ChartWidget(QWidget):
    """
    Grafikler oluşturmak ve görüntülemek için özel widget
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.df = None
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Kontrol paneli
        control_panel = QWidget()
        control_panel.setObjectName("chartControlPanel")
        control_panel.setStyleSheet("""
            #chartControlPanel {
                background-color: white;
                border-radius: 6px;
                padding: 10px;
                margin-bottom: 10px;
            }
        """)
        control_layout = QHBoxLayout(control_panel)
        control_layout.setContentsMargins(10, 10, 10, 10)
        control_layout.setSpacing(10)
        
        # Grafik türü seçici
        chart_type_label = QLabel("Grafik Türü:")
        chart_type_label.setStyleSheet("font-weight: bold; color: #424242;")
        self.chart_type_selector = QComboBox()
        self.chart_type_selector.addItems(["Çubuk Grafik", "Pasta Grafik", "Scatter Plot"])
        self.chart_type_selector.setMinimumWidth(150)
        self.chart_type_selector.setStyleSheet("""
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
        control_layout.addWidget(chart_type_label)
        control_layout.addWidget(self.chart_type_selector)
        
        # X ekseni seçici
        x_label = QLabel("X Ekseni:")
        x_label.setStyleSheet("font-weight: bold; color: #424242;")
        self.x_selector = QComboBox()
        self.x_selector.setMinimumWidth(150)
        self.x_selector.setStyleSheet("""
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
        control_layout.addWidget(x_label)
        control_layout.addWidget(self.x_selector)
        
        # Y ekseni seçici (scatter plot için)
        y_label = QLabel("Y Ekseni:")
        y_label.setStyleSheet("font-weight: bold; color: #424242;")
        self.y_selector = QComboBox()
        self.y_selector.setMinimumWidth(150)
        self.y_selector.setStyleSheet("""
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
        control_layout.addWidget(y_label)
        control_layout.addWidget(self.y_selector)
        
        # Oluştur butonu
        self.create_btn = QPushButton("Grafik Oluştur")
        self.create_btn.setStyleSheet("""
            QPushButton {
                background-color: #5c6bc0;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #3f51b5;
            }
            QPushButton:pressed {
                background-color: #303f9f;
            }
        """)
        self.create_btn.clicked.connect(self.create_chart)
        control_layout.addWidget(self.create_btn)
        
        layout.addWidget(control_panel)
        
        # Chart container with styling
        chart_container = QWidget()
        chart_container.setObjectName("chartContainer")
        chart_container.setStyleSheet("""
            #chartContainer {
                background-color: white;
                border-radius: 6px;
                border: 1px solid #e0e0e0;
            }
        """)
        chart_layout = QVBoxLayout(chart_container)
        
        # Grafik alanı
        self.figure = Figure(figsize=(10, 6))
        # Set modern style for matplotlib
        plt.style.use('seaborn-v0_8-whitegrid')
        self.figure.patch.set_facecolor('white')
        self.canvas = FigureCanvas(self.figure)
        chart_layout.addWidget(self.canvas)
        
        layout.addWidget(chart_container)
    
    def set_dataframe(self, df):
        """
        DataFrame'i ayarlar ve UI'yı günceller
        """
        self.df = df
        
        # Sütun seçicileri güncelle
        self.x_selector.clear()
        self.y_selector.clear()
        
        if df is not None:
            # Tüm sütunları ekle
            for column in df.columns:
                self.x_selector.addItem(column)
                self.y_selector.addItem(column)
            
            # Varsayılan seçimleri ayarla
            # X ekseni için kategorik bir sütun seç
            for i, col in enumerate(df.columns):
                if col in ["Gtip", "Mensei_ulke", "Rejim"]:
                    self.x_selector.setCurrentIndex(i)
                    break
            
            # Y ekseni için sayısal bir sütun seç
            for i, col in enumerate(df.columns):
                if col in ["Fatura_miktari", "Net_agirlik", "Brut_agirlik"]:
                    self.y_selector.setCurrentIndex(i)
                    break
    
    def create_chart(self):
        """
        Seçilen parametrelerle grafik oluşturur
        """
        if self.df is None:
            return
        
        chart_type = self.chart_type_selector.currentText()
        x_column = self.x_selector.currentText()
        
        # Grafik türüne göre işlem yap
        if chart_type == "Çubuk Grafik":
            fig = create_bar_chart(self.df, x_column)
        elif chart_type == "Pasta Grafik":
            fig = create_pie_chart(self.df, x_column)
        elif chart_type == "Scatter Plot":
            y_column = self.y_selector.currentText()
            fig = create_scatter_plot(self.df, x_column, y_column)
        
        if fig:
            # Mevcut figürü temizle
            self.figure.clear()
            
            # Yeni figürü kopyala
            for ax in fig.get_axes():
                new_ax = self.figure.add_subplot(111)
                for line in ax.get_lines():
                    new_ax.plot(line.get_xdata(), line.get_ydata(), 
                              color=line.get_color(), 
                              linestyle=line.get_linestyle(), 
                              marker=line.get_marker(),
                              alpha=line.get_alpha())
                
                # Barlar varsa kopyala
                for patch in ax.patches:
                    new_patch = plt.Rectangle((patch.get_x(), patch.get_y()),
                                           patch.get_width(), patch.get_height(),
                                           color=patch.get_facecolor(),
                                           alpha=patch.get_alpha())
                    new_ax.add_patch(new_patch)
                
                # Pasta dilimlerini kopyala
                for wedge in ax.findobj(plt.matplotlib.patches.Wedge):
                    new_wedge = plt.Wedge((0, 0), wedge.r, wedge.theta1, wedge.theta2,
                                      color=wedge.get_facecolor(),
                                      alpha=wedge.get_alpha())
                    new_ax.add_patch(new_wedge)
                
                # Scatter noktalarını kopyala
                for collection in ax.collections:
                    if isinstance(collection, plt.matplotlib.collections.PathCollection):
                        new_ax.scatter(collection.get_offsets()[:, 0], 
                                    collection.get_offsets()[:, 1],
                                    color=collection.get_facecolor()[0],
                                    alpha=collection.get_alpha())
                
                # Eksenleri, etiketleri ve başlığı kopyala
                new_ax.set_xlabel(ax.get_xlabel())
                new_ax.set_ylabel(ax.get_ylabel())
                new_ax.set_title(ax.get_title())
                
                # Ticks ve labels
                new_ax.set_xticks(ax.get_xticks())
                new_ax.set_xticklabels(ax.get_xticklabels())
                new_ax.set_yticks(ax.get_yticks())
                new_ax.set_yticklabels(ax.get_yticklabels())
                
                # Legend'ı kopyala
                if ax.get_legend():
                    new_ax.legend(ax.get_legend().get_texts())
            
            plt.tight_layout()
            self.canvas.draw() 