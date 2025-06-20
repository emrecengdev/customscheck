"""
Gümrük beyanname analiz modülleri paketi.
Bu paket, beyanname analizleri için kullanılan çeşitli modülleri içerir.
"""

import pandas as pd

# Temel kontrol fonksiyonları
from .basic_checks import (
    calculate_basic_stats,
    check_missing_values,
    check_duplicate_rows,
    check_value_consistency,
    check_numeric_range
)

# Ağırlık tutarlılık analizi
from .weight_consistency import check_weight_consistency

# Döviz analizi
from .currency_analysis import check_currency_values, check_rarely_used_currency

# İşlem Niteliği tutarlılık analizi
from .islem_niteligi_tutarlilik import kontrol_islem_niteligi_tutarlilik as check_islem_niteligi_consistency

# GTİP tutarlılık analizleri
from .gtip_urun_kodu import check_gtip_urun_kodu_consistency

# Nadiren kullanılan öğelerin analizi
from .rare_items import check_rarely_used_origin_country, check_rarely_used_payment_method, check_rarely_used_origin_country_by_sender_gtip

# IGV analizi
from .igv_analysis import check_igv_consistency

# Tedarikçi beyan kontrol analizi
from .tedarikci_beyan_kontrol import check_tedarikci_beyan_kontrol

# Yeni oluşturulan modüller
from .unit_price_analysis import check_unit_price_increase
from .tax_analysis import check_kdv_consistency
from .expense_analysis import check_domestic_expense_variation, check_foreign_expense_variation
from .supalan_depolama_kontrol import check_supalan_depolama_kontrol

# Alıcı-satıcı ilişki analizi (mevcut modülden)
try:
    from analysis import check_alici_satici_relationship, check_vergi_consistency
except ImportError:
    # Eğer analysis modülü yoksa placeholder fonksiyonları tanımla
    def check_alici_satici_relationship(df, selected_companies=None, progress_callback=None):
        return {
            "status": "error",
            "message": "Alıcı-satıcı ilişki analizi modülü bulunamadı.",
            "data": None
        }
    
    def check_vergi_consistency(df):
        return {
            "status": "error", 
            "message": "Vergi tutarlılık analizi modülü bulunamadı.",
            "data": None
        }

# Özet fonksiyonları
try:
    from .summary_functions import (
        create_gtip_summary,
        create_country_summary,
        create_rejim_summary,
        create_gtip_country_cross
    )
except ImportError:
    # Placeholder fonksiyonlar
    def create_gtip_summary(df):
        return df.groupby('Gtip').size() if 'Gtip' in df.columns else None
    
    def create_country_summary(df):
        return df.groupby('Mensei_ulke').size() if 'Mensei_ulke' in df.columns else None
    
    def create_rejim_summary(df):
        return df.groupby('Rejim').size() if 'Rejim' in df.columns else None
    
    def create_gtip_country_cross(df):
        return pd.crosstab(df['Gtip'], df['Mensei_ulke']) if all(col in df.columns for col in ['Gtip', 'Mensei_ulke']) else None

# Grafik fonksiyonları
try:
    from .chart_functions import (
        plot_to_base64,
        create_bar_chart,
        create_pie_chart,
        create_scatter_plot
    )
except ImportError:
    # Placeholder fonksiyonlar
    def plot_to_base64(fig):
        return ""
    
    def create_bar_chart(df, x_col, y_col):
        return None
    
    def create_pie_chart(df, col):
        return None
    
    def create_scatter_plot(df, x_col, y_col):
        return None

# Tüm fonksiyonları listele (kolay erişim için)
__all__ = [
    # Temel kontroller
    'calculate_basic_stats', 'check_missing_values', 'check_duplicate_rows',
    'check_value_consistency', 'check_numeric_range',
    
    # Tutarlılık kontrolleri
    'check_weight_consistency', 'check_islem_niteligi_consistency',
    'check_gtip_urun_kodu_consistency',
    
    # Döviz ve değer analizleri
    'check_currency_values', 'check_rarely_used_currency',
    'check_unit_price_increase', 'check_kdv_consistency',
    
    # Nadir kullanım analizleri
    'check_rarely_used_origin_country', 'check_rarely_used_payment_method',
    'check_rarely_used_origin_country_by_sender_gtip',
    
    # Gider analizleri
    'check_domestic_expense_variation', 'check_foreign_expense_variation',
    
    # Özel kontroller
    'check_supalan_depolama_kontrol', 'check_alici_satici_relationship',
    'check_vergi_consistency',
    
    # Özet ve grafik fonksiyonları
    'create_gtip_summary', 'create_country_summary', 'create_rejim_summary',
    'create_gtip_country_cross',
    'plot_to_base64', 'create_bar_chart', 'create_pie_chart', 'create_scatter_plot',
    
    # IGV analizi
    'check_igv_consistency',
    
    # Tedarikçi beyan kontrol analizi
    'check_tedarikci_beyan_kontrol'
] 