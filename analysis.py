import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from io import BytesIO
import base64
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton, QTableView
from PyQt5.QtCore import Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

# ----------------------
# Temel Analiz Fonksiyonları
# ----------------------

def calculate_basic_stats(df):
    """
    Veri seti hakkında temel istatistikler hesaplar
    """
    numeric_columns = df.select_dtypes(include=['number']).columns.tolist()
    
    if not numeric_columns:
        return {
            "row_count": len(df),
            "column_count": len(df.columns),
            "numeric_stats": None
        }
    
    # Sayısal değerler için istatistikler
    numeric_stats = df[numeric_columns].describe()
    
    return {
        "row_count": len(df),
        "column_count": len(df.columns),
        "numeric_stats": numeric_stats
    }

def check_missing_values(df):
    """
    Eksik değerlerin kontrolünü yapar
    """
    # Her sütun için eksik değer sayısı
    missing_values = df.isnull().sum()
    
    # Eksik değer içeren sütunları filtrele
    missing_values = missing_values[missing_values > 0]
    
    # Eksik değerlerin yüzdesini hesapla
    missing_percentage = (missing_values / len(df)) * 100
    
    # Sonuçları bir DataFrame olarak döndür
    if len(missing_values) > 0:
        result = pd.DataFrame({
            'Eksik Değer Sayısı': missing_values,
            'Eksik Değer Yüzdesi': missing_percentage
        })
        return result
    else:
        return None

def check_duplicate_rows(df):
    """
    Tekrarlanan satırları kontrol eder
    """
    # Tüm satırlar arasında tekrarlananları bul
    duplicates_all = df.duplicated().sum()
    
    # Belirli sütunlara göre tekrarlanan satırları bul
    key_columns = []
    for col in df.columns:
        if "Kalem_No" in col or "Gtip" in col:
            key_columns.append(col)
    
    duplicates_by_key = 0
    if key_columns:
        duplicates_by_key = df.duplicated(subset=key_columns).sum()
    
    return {
        "duplicate_rows_all": duplicates_all,
        "duplicate_rows_by_key": duplicates_by_key,
        "key_columns": key_columns
    }

def check_value_consistency(df, column, expected_values=None):
    """
    Bir sütundaki değerlerin belirli bir değer kümesi içinde olup olmadığını kontrol eder
    """
    if column not in df.columns:
        return {
            "status": "error",
            "message": f"Sütun '{column}' veride bulunamadı."
        }
    
    unique_values = df[column].unique()
    
    if expected_values:
        # Beklenen değerler kümesi
        unexpected_values = [val for val in unique_values if val not in expected_values and pd.notna(val)]
        
        return {
            "status": "ok" if not unexpected_values else "warning",
            "unique_values": unique_values.tolist(),
            "unexpected_values": unexpected_values,
            "expected_values": expected_values
        }
    else:
        # Beklenen değerler belirtilmediyse, sadece benzersiz değerleri döndür
        return {
            "status": "ok",
            "unique_values": unique_values.tolist(),
        }

def check_numeric_range(df, column, min_value=None, max_value=None):
    """
    Sayısal bir sütundaki değerlerin belirli bir aralıkta olup olmadığını kontrol eder
    """
    if column not in df.columns:
        return {
            "status": "error",
            "message": f"Sütun '{column}' veride bulunamadı."
        }
    
    # Sütun sayısal mı kontrol et
    if not pd.api.types.is_numeric_dtype(df[column]):
        try:
            # Sayısal değere dönüştürmeyi dene
            numeric_values = pd.to_numeric(df[column], errors='coerce')
        except:
            return {
                "status": "error",
                "message": f"Sütun '{column}' sayısal değere dönüştürülemiyor."
            }
    else:
        numeric_values = df[column]
    
    # Sonuçları hesapla
    result = {
        "status": "ok",
        "min": numeric_values.min(),
        "max": numeric_values.max(),
        "mean": numeric_values.mean(),
        "median": numeric_values.median(),
        "outliers": []
    }
    
    # Min değer kontrolü
    if min_value is not None:
        below_min = df[numeric_values < min_value]
        if not below_min.empty:
            result["status"] = "warning"
            result["below_min_count"] = len(below_min)
            result["below_min_percentage"] = (len(below_min) / len(df)) * 100
    
    # Max değer kontrolü
    if max_value is not None:
        above_max = df[numeric_values > max_value]
        if not above_max.empty:
            result["status"] = "warning"
            result["above_max_count"] = len(above_max)
            result["above_max_percentage"] = (len(above_max) / len(df)) * 100
    
    # Aykırı değerleri tespit et (IQR yöntemi)
    q1 = numeric_values.quantile(0.25)
    q3 = numeric_values.quantile(0.75)
    iqr = q3 - q1
    
    lower_bound = q1 - (1.5 * iqr)
    upper_bound = q3 + (1.5 * iqr)
    
    outliers = df[(numeric_values < lower_bound) | (numeric_values > upper_bound)]
    
    if not outliers.empty:
        result["outliers_count"] = len(outliers)
        result["outliers_percentage"] = (len(outliers) / len(df)) * 100
    
    return result

# ----------------------
# Pivot Tablo Fonksiyonları
# ----------------------

def create_gtip_summary(df):
    """
    GTIP kodlarına göre özet pivot tablo oluşturur
    """
    if "Gtip" not in df.columns:
        return None
    
    numeric_columns = []
    for col in ['Fatura_miktari', 'Net_agirlik', 'Brut_agirlik']:
        if col in df.columns:
            numeric_columns.append(col)
    
    if not numeric_columns:
        return None
    
    # Multi-index oluştur - Gtip, Beyanname_no ve Adi_unvani
    multi_index = ["Gtip"]
    
    # İstenen sütunların varlığını kontrol et
    if "Beyanname_no" in df.columns:
        multi_index.append("Beyanname_no")
    
    if "Adi_unvani" in df.columns:
        multi_index.append("Adi_unvani")
    
    pivot = pd.pivot_table(
        df,
        index=multi_index,
        values=numeric_columns,
        aggfunc={'Fatura_miktari': 'sum', 'Net_agirlik': 'sum', 'Brut_agirlik': 'sum'},
        margins=True,
        margins_name="Toplam"
    )
    
    return pivot

def create_country_summary(df):
    """
    Menşei ülkelere göre özet pivot tablo oluşturur
    """
    if "Mensei_ulke" not in df.columns:
        return None
    
    numeric_columns = []
    for col in ['Fatura_miktari', 'Net_agirlik', 'Brut_agirlik']:
        if col in df.columns:
            numeric_columns.append(col)
    
    if not numeric_columns:
        return None
    
    # Multi-index oluştur - Mensei_ulke, Beyanname_no ve Adi_unvani
    multi_index = ["Mensei_ulke"]
    
    # İstenen sütunların varlığını kontrol et
    if "Beyanname_no" in df.columns:
        multi_index.append("Beyanname_no")
    
    if "Adi_unvani" in df.columns:
        multi_index.append("Adi_unvani")
    
    pivot = pd.pivot_table(
        df,
        index=multi_index,
        values=numeric_columns,
        aggfunc='sum',
        margins=True,
        margins_name="Toplam"
    )
    
    return pivot

def create_rejim_summary(df):
    """
    Rejim kodlarına göre özet pivot tablo oluşturur
    """
    if "Rejim" not in df.columns:
        return None
    
    # Multi-index oluştur - Rejim, Beyanname_no ve Adi_unvani
    multi_index = ["Rejim"]
    
    # İstenen sütunların varlığını kontrol et
    if "Beyanname_no" in df.columns:
        multi_index.append("Beyanname_no")
    
    if "Adi_unvani" in df.columns:
        multi_index.append("Adi_unvani")
    
    pivot = pd.pivot_table(
        df,
        index=multi_index,
        values=["Kalem_No"],
        aggfunc='count',
        margins=True,
        margins_name="Toplam"
    )
    
    # Sütun adını anlamlı hale getir
    pivot.columns = ["Kalem Sayısı"]
    
    return pivot

def create_gtip_country_cross(df):
    """
    GTIP ve menşei ülke çapraz pivot tablo oluşturur
    """
    if "Gtip" not in df.columns or "Mensei_ulke" not in df.columns:
        return None
    
    if "Fatura_miktari" not in df.columns:
        return None
    
    # Multi-index oluştur - Gtip, Beyanname_no ve Adi_unvani
    multi_index = ["Gtip"]
    
    # İstenen sütunların varlığını kontrol et
    if "Beyanname_no" in df.columns:
        multi_index.append("Beyanname_no")
    
    if "Adi_unvani" in df.columns:
        multi_index.append("Adi_unvani")
    
    pivot = pd.pivot_table(
        df,
        index=multi_index,
        columns="Mensei_ulke",
        values="Fatura_miktari",
        aggfunc='sum',
        margins=True,
        margins_name="Toplam"
    )
    
    return pivot

def create_custom_pivot(df, index, values, columns=None, aggfunc='sum'):
    """
    Özel bir pivot tablo oluşturur
    """
    if index not in df.columns:
        return None
    
    if isinstance(values, list):
        missing_values = [val for val in values if val not in df.columns]
        if missing_values:
            return None
    elif values not in df.columns:
        return None
    
    if columns is not None and columns not in df.columns:
        return None
    
    try:
        # Kaynak veriyi hazırla
        pivot_data = df.copy()
        
        # Eğer "Beyanname_no" ve "Adi_unvani" sütunları var ise, bunları çoklu indeks olarak ekle
        multi_index = [index]
        
        # İstenen sütunların varlığını kontrol et
        if "Beyanname_no" in df.columns and index != "Beyanname_no":
            multi_index.append("Beyanname_no")
        
        if "Adi_unvani" in df.columns and index != "Adi_unvani":
            multi_index.append("Adi_unvani")
        
        # Pivot tabloyu oluştur
        pivot = pd.pivot_table(
            pivot_data,
            index=multi_index,
            values=values,
            columns=columns,
            aggfunc=aggfunc,
            margins=True,
            margins_name="Toplam"
        )
        
        # Eğer tek sütunlu pivot tablosu oluştuysa ve yalnızca "Toplam" var ise
        if isinstance(pivot.columns, pd.Index) and len(pivot.columns) == 1 and pivot.columns[0] == "Toplam":
            # Sütun adını değiştir
            pivot.columns = [values if isinstance(values, str) else values[0]]
        
        return pivot
    except Exception as e:
        print(f"Pivot tablo oluşturulurken hata: {str(e)}")
        return None

# ----------------------
# Görselleştirme Fonksiyonları
# ----------------------

def plot_to_base64(fig):
    """
    Matplotlib figürünü base64 formatına dönüştürür
    """
    buf = BytesIO()
    fig.savefig(buf, format='png', dpi=100, bbox_inches='tight')
    buf.seek(0)
    img_str = base64.b64encode(buf.read()).decode('utf-8')
    buf.close()
    return img_str

def create_bar_chart(df, column, title=None, limit=10):
    """
    Bir sütun için çubuk grafik oluşturur
    """
    if column not in df.columns:
        return None
    
    # Değer sayılarını hesapla
    value_counts = df[column].value_counts().nlargest(limit)
    
    fig, ax = plt.subplots(figsize=(10, 6))
    value_counts.plot(kind='bar', ax=ax)
    
    if title:
        ax.set_title(title)
    else:
        ax.set_title(f'{column} Dağılımı')
    
    ax.set_xlabel(column)
    ax.set_ylabel('Sayı')
    
    plt.tight_layout()
    
    return fig

def create_pie_chart(df, column, title=None, limit=5):
    """
    Bir sütun için pasta grafik oluşturur
    """
    if column not in df.columns:
        return None
    
    # Değer sayılarını hesapla
    value_counts = df[column].value_counts().nlargest(limit)
    
    # Kalan değerleri "Diğer" olarak grupla
    total = df[column].count()
    if total > value_counts.sum():
        value_counts["Diğer"] = total - value_counts.sum()
    
    fig, ax = plt.subplots(figsize=(10, 6))
    value_counts.plot(kind='pie', ax=ax, autopct='%1.1f%%')
    
    if title:
        ax.set_title(title)
    else:
        ax.set_title(f'{column} Dağılımı')
    
    ax.set_ylabel('')
    
    plt.tight_layout()
    
    return fig

def create_scatter_plot(df, x_column, y_column, title=None):
    """
    İki sayısal sütun için saçılım grafiği oluşturur
    """
    if x_column not in df.columns or y_column not in df.columns:
        return None
    
    # Sütunların sayısal olduğundan emin ol
    try:
        x_data = pd.to_numeric(df[x_column], errors='coerce')
        y_data = pd.to_numeric(df[y_column], errors='coerce')
    except:
        return None
    
    # NaN değerleri filtrele
    mask = ~(x_data.isnull() | y_data.isnull())
    x_data = x_data[mask]
    y_data = y_data[mask]
    
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.scatter(x_data, y_data, alpha=0.5)
    
    if title:
        ax.set_title(title)
    else:
        ax.set_title(f'{x_column} vs {y_column}')
    
    ax.set_xlabel(x_column)
    ax.set_ylabel(y_column)
    
    # En uygun doğru ekle
    if len(x_data) >= 2:  # Regresyon için en az 2 nokta gerekir
        try:
            z = np.polyfit(x_data, y_data, 1)
            p = np.poly1d(z)
            ax.plot(x_data, p(x_data), "r--", alpha=0.8)
        except:
            pass
    
    plt.tight_layout()
    
    return fig

# ----------------------
# Kontrol İşlemleri
# ----------------------

def check_vergi_consistency(df):
    """
    Vergi tutarlılığını kontrol eder
    """
    # Vergi sütunlarını bul
    vergi_miktari_cols = [col for col in df.columns if col.endswith('_Miktar')]
    
    if not vergi_miktari_cols:
        return None
    
    # Her vergi türü için tutarları topla
    vergi_toplamları = {}
    for col in vergi_miktari_cols:
        try:
            vergi_kodu = col.split('_')[1]  # Vergi kodunu al
            tutar = pd.to_numeric(df[col], errors='coerce').sum()
            vergi_toplamları[vergi_kodu] = tutar
        except:
            pass
    
    return pd.Series(vergi_toplamları, name="Vergi Tutarları")

def check_weight_consistency(df):
    """
    Brüt ve net ağırlık tutarlılığını kontrol eder
    """
    if "Brut_agirlik" not in df.columns or "Net_agirlik" not in df.columns:
        return None
    
    try:
        brut = pd.to_numeric(df["Brut_agirlik"], errors='coerce')
        net = pd.to_numeric(df["Net_agirlik"], errors='coerce')
    except:
        return None
    
    # Brüt ağırlık < Net ağırlık olan kalemleri bul
    inconsistent = df[brut < net].copy()
    
    if inconsistent.empty:
        return {"status": "ok", "message": "Ağırlık tutarlılık kontrolü başarılı."}
    else:
        return {
            "status": "warning",
            "message": f"Brüt ağırlık < Net ağırlık olan {len(inconsistent)} kalem bulundu.",
            "inconsistent_rows": inconsistent
        }

def check_currency_values(df):
    """
    Döviz tutarlarının tutarlılığını kontrol eder
    """
    if "Fatura_miktari" not in df.columns or "Fatura_miktarinin_dovizi" not in df.columns:
        return None
    
    # Döviz bazında fatura tutarlarını topla
    try:
        pivot = pd.pivot_table(
            df,
            index="Fatura_miktarinin_dovizi",
            values="Fatura_miktari",
            aggfunc='sum'
        )
        
        return pivot
    except:
        return None

def check_gtip_ticari_tanim_consistency(df):
    """
    Aynı ticari tanımda farklı GTİP kodu kullanılıp kullanılmadığını kontrol eder
    """
    print("GTİP-Ticari Tanım tutarlılık kontrolü başlatılıyor...")
    
    if "Gtip" not in df.columns or "Ticari_tanimi" not in df.columns:
        print("Hata: Gtip veya Ticari_tanimi sütunları bulunamadı.")
        return {
            "status": "error",
            "message": "Gtip veya Ticari_tanimi sütunları bulunamadı."
        }
    
    try:
        # Boş ticari tanımları filtrele
        filtered_df = df[df['Ticari_tanimi'].notna() & (df['Ticari_tanimi'] != '')]
        
        print(f"Filtrelenmiş veri: {len(filtered_df)} satır")
        
        if len(filtered_df) == 0:
            return {
                "status": "ok",
                "message": "İşlenecek veri bulunamadı. Ticari tanımlar boş olabilir.",
                "html_report": "<p>İşlenecek veri bulunamadı. Ticari tanımlar boş olabilir.</p>"
            }
        
        # Her ticari tanım için benzersiz GTİP kodlarını bul
        grouped = filtered_df.groupby('Ticari_tanimi')['Gtip'].unique().reset_index()
        
        # Her ticari tanım için kaç farklı GTİP kodu kullanıldığını hesapla
        grouped['GTİP_Sayısı'] = grouped['Gtip'].apply(len)
        
        print(f"Toplam {len(grouped)} benzersiz ticari tanım bulundu.")
        print(f"Birden fazla GTİP kodu içeren tanım sayısı: {len(grouped[grouped['GTİP_Sayısı'] > 1])}")
        
        # Birden fazla GTİP kodu olan ticari tanımları filtrele
        multiple_gtips = grouped[grouped['GTİP_Sayısı'] > 1].sort_values(by='GTİP_Sayısı', ascending=False)
        
        if multiple_gtips.empty:
            print("Aynı ticari tanımda farklı GTİP kodu kullanımı tespit edilmedi.")
            return {
                "status": "ok",
                "message": "Aynı ticari tanımda farklı GTİP kodu kullanımı tespit edilmedi.",
                "html_report": "<p>Aynı ticari tanımda farklı GTİP kodu kullanımı tespit edilmedi.</p>"
            }
        else:
            print(f"{len(multiple_gtips)} ticari tanımda tutarsızlık bulundu.")
            
            # Ayrıntılı sonuçlar için DataFrame oluştur
            result_rows = []
            
            # Ticari tanımlar için daha basit bir özet listesi oluştur
            simplified_summary = []
            
            # Her bir tutarsız ticari tanım için özet bilgi oluştur
            for _, row in multiple_gtips.iterrows():
                ticari_tanim = row['Ticari_tanimi']
                gtip_codes = row['Gtip']
                gtip_count = row['GTİP_Sayısı']
                
                # İlgili satırları bul
                related_rows = filtered_df[filtered_df['Ticari_tanimi'] == ticari_tanim]
                
                # GTİP detayları için tam bilgileri topla - HTML rapor için
                gtip_details = []
                for gtip in gtip_codes:
                    gtip_rows = related_rows[related_rows['Gtip'] == gtip]
                    
                    beyanname_list = []
                    if "Beyanname_no" in gtip_rows.columns:
                        beyanname_list = gtip_rows['Beyanname_no'].dropna().unique().tolist()
                    
                    unvan_list = []
                    if "Adi_unvani" in gtip_rows.columns:
                        unvan_list = gtip_rows['Adi_unvani'].dropna().unique().tolist()
                    
                    gtip_details.append({
                        'gtip': gtip,
                        'beyannameler': beyanname_list,
                        'unvanlar': unvan_list
                    })
                
                # Basitleştirilmiş özet için satır ekle - karmaşık nesneler yok
                simplified_summary.append({
                    'Ticari_tanimi': ticari_tanim,
                    'Farklı_GTİP_Sayısı': gtip_count,
                    'GTİP_Kodları': ', '.join(gtip_codes),
                    'GTİP_Detayları': gtip_details  # Her satır için GTİP detaylarını ekle
                })
                
                # Detaylı sonuçlar için satırları ekle
                for gtip in gtip_codes:
                    gtip_rows = related_rows[related_rows['Gtip'] == gtip]
                    
                    for _, data_row in gtip_rows.iterrows():
                        result_row = {
                            'Ticari_tanimi': ticari_tanim,
                            'Gtip': gtip
                        }
                        
                        # Diğer önemli sütunları da ekle
                        for col in ['Kalem_No', 'Mensei_ulke', 'Fatura_miktari', 'Fatura_miktarinin_dovizi', 'Beyanname_no', 'Adi_unvani', 'Kaynak_Dosya']:
                            if col in data_row:
                                result_row[col] = data_row[col]
                        
                        result_rows.append(result_row)
            
            # Detaylı dataframe oluştur
            result_df = pd.DataFrame(result_rows)
            print(f"Sonuç DataFrame oluşturuldu: {len(result_df)} satır")
            
            # Özet DataFrame oluştur - basitleştirilmiş veri
            summary_df = pd.DataFrame(simplified_summary)
            if 'GTİP_Detayları' in summary_df.columns:
                summary_df = summary_df.drop(columns=['GTİP_Detayları'])  # JSON serileştirme hatalarını önlemek için kompleks sütunu kaldır
            
            print(f"Özet DataFrame oluşturuldu: {len(summary_df)} satır")
            
            # Görsel sunum için HTML tablosu oluştur
            try:
                html_content = create_gtip_consistency_html(simplified_summary)
                print("HTML raporu başarıyla oluşturuldu.")
            except Exception as e:
                print(f"HTML rapor oluşturma hatası: {str(e)}")
                html_content = f"<p>HTML rapor oluşturulurken hata: {str(e)}</p>"
            
            return {
                "status": "warning",
                "message": f"{len(multiple_gtips)} ticari tanımda farklı GTİP kodları kullanılmış.",
                "inconsistent_rows": result_df,
                "summary": summary_df,
                "detail": multiple_gtips,
                "html_report": html_content
            }
    except Exception as e:
        error_message = f"GTİP-Ticari Tanım tutarlılık kontrolü sırasında hata: {str(e)}"
        print(error_message)
        import traceback
        print(traceback.format_exc())
        return {
            "status": "error",
            "message": error_message,
            "html_report": f"<p>Hata: {str(e)}</p>"
        }

def create_gtip_consistency_html(summary_data):
    """
    GTİP-Ticari Tanım tutarlılık kontrolü için basitleştirilmiş HTML raporu oluşturur
    """
    if not summary_data:
        return "<p>Herhangi bir tutarsızlık bulunamadı.</p>"
    
    # Pivot veri hazırla - GTİP kodlarının dağılımını göstermek için
    gtip_codes = []
    for item in summary_data:
        for detail in item['GTİP_Detayları']:
            gtip = detail['gtip']
            beyannameler = detail['beyannameler']
            count = len(beyannameler) if beyannameler else 1
            gtip_codes.append({
                'GTİP': gtip,
                'Beyanname_Sayısı': count,
                'Ticari_Tanım_Sayısı': 1
            })
    
    # GTİP kodlarına göre gruplama ve toplama
    gtip_pivot = None
    if gtip_codes:
        import pandas as pd
        gtip_df = pd.DataFrame(gtip_codes)
        gtip_pivot = gtip_df.groupby('GTİP').agg({
            'Beyanname_Sayısı': 'sum',
            'Ticari_Tanım_Sayısı': 'count'
        }).sort_values(by='Beyanname_Sayısı', ascending=False).reset_index()
    
    # Minimal HTML ve CSS kullan
    html = """
    <style>
    body {
        font-family: Arial, sans-serif;
        font-size: 12px;
        margin: 0;
        padding: 10px;
    }
    table {
        width: 100%;
        border-collapse: collapse;
        margin-bottom: 20px;
    }
    th {
        background-color: #f2f2f2;
        padding: 6px;
        text-align: left;
        border: 1px solid #ddd;
        position: sticky;
        top: 0;
    }
    td {
        padding: 4px;
        border: 1px solid #ddd;
        vertical-align: top;
    }
    .main-row {
        background-color: #e6f2ff;
        font-weight: bold;
    }
    .gtip-code {
        font-family: monospace;
        color: #0066cc;
    }
    .badge {
        display: inline-block;
        padding: 2px 4px;
        margin: 1px;
        border-radius: 3px;
        background-color: #f8f9fa;
        border: 1px solid #dee2e6;
        font-size: 11px;
    }
    .more-badge {
        display: inline-block;
        padding: 2px 4px;
        margin: 1px;
        border-radius: 3px;
        background-color: #e2e8f0;
        color: #4a5568;
        border: 1px solid #cbd5e0;
        font-size: 11px;
        cursor: pointer;
    }
    .more-badge:hover {
        background-color: #cbd5e0;
    }
    .hidden-items {
        display: none;
    }
    .pivot-table {
        width: 100%;
        border-collapse: collapse;
        margin: 15px 0;
        box-shadow: 0 0 5px rgba(0,0,0,0.1);
    }
    .pivot-table th {
        background-color: #e3f2fd;
        padding: 8px;
        text-align: left;
        border: 1px solid #bbd6f5;
        font-weight: bold;
    }
    .pivot-table td {
        padding: 6px;
        border: 1px solid #bbd6f5;
        text-align: right;
    }
    .pivot-table tr:nth-child(even) {
        background-color: #f5f9ff;
    }
    .pivot-table tr:last-child, .pivot-table td:last-child {
        font-weight: bold;
        background-color: #e3f2fd;
    }
    .summary-box {
        background-color: #f0f7ff;
        border: 1px solid #bbd6f5;
        border-radius: 8px;
        padding: 15px;
        margin-bottom: 20px;
    }
    .summary-title {
        font-size: 14px;
        font-weight: bold;
        color: #2c3e50;
        margin-bottom: 10px;
    }
    </style>
    
    <script>
    function toggleItems(id) {
        var hiddenItems = document.getElementById(id);
        var badge = document.getElementById('badge-' + id);
        
        if (hiddenItems.style.display === 'none' || hiddenItems.style.display === '') {
            hiddenItems.style.display = 'inline';
            badge.style.display = 'none';
        } else {
            hiddenItems.style.display = 'none';
            badge.style.display = 'inline-block';
        }
    }
    </script>
    
    <h2>GTİP - Ticari Tanım Tutarlılık Raporu</h2>
    <p><b>Not:</b> Bu rapor performans nedeniyle basitleştirilmiştir. Her GTİP için en fazla 10 beyanname gösterilmektedir.</p>
    """
    
    # Özet pivot tablosu ekle
    if gtip_pivot is not None and not gtip_pivot.empty:
        html += """
        <div class="summary-box">
            <div class="summary-title">GTİP Kodları Özet Pivot</div>
        """
        
        html += """
            <table class="pivot-table">
                <thead>
                    <tr>
                        <th>GTİP Kodu</th>
                        <th>Beyanname Sayısı</th>
                        <th>Farklı Ticari Tanım Sayısı</th>
                    </tr>
                </thead>
                <tbody>
        """
        
        # Pivot satırlarını ekle - en fazla 15 satır göster
        for _, row in gtip_pivot.head(15).iterrows():
            html += f"""
                <tr>
                    <td class="gtip-code">{row['GTİP']}</td>
                    <td>{row['Beyanname_Sayısı']}</td>
                    <td>{row['Ticari_Tanım_Sayısı']}</td>
                </tr>
            """
        
        # Toplam satırı ekle
        if len(gtip_pivot) > 0:
            html += f"""
                <tr>
                    <td>Toplam</td>
                    <td>{gtip_pivot['Beyanname_Sayısı'].sum()}</td>
                    <td>{gtip_pivot['Ticari_Tanım_Sayısı'].sum()}</td>
                </tr>
            """
            
        # Tablo kapanışı
        html += """
                </tbody>
            </table>
        </div>
        """
    
    # Detaylı tablo başlat
    html += """
    <table>
        <thead>
            <tr>
                <th style="width: 30%">Ticari Tanımı</th>
                <th style="width: 15%">GTİP Kodu</th>
                <th style="width: 40%">Beyanname No</th>
                <th style="width: 15%">Firma</th>
            </tr>
        </thead>
        <tbody>
    """
    
    # Maksimum gösterilecek öğe sayısı
    max_beyanname = 10
    max_firma = 3
    
    # Benzersiz ID üreteci
    unique_id = 1
    
    # Veriyi işle - maksimum 10 ticari tanım (en çok GTİP farklılığı olanlar)
    for i, item in enumerate(summary_data[:10]):
        ticari_tanim = item['Ticari_tanimi']
        
        # Ana satır - Ticari Tanım
        html += f"""
            <tr class="main-row">
                <td colspan="4"><b>{ticari_tanim}</b> - {item['Farklı_GTİP_Sayısı']} farklı GTİP kodu tespit edildi</td>
            </tr>
        """
        
        # Her GTİP için alt satır
        for detail in item['GTİP_Detayları'][:5]:  # Maksimum 5 GTİP göster
            gtip = detail['gtip']
            beyannameler = detail['beyannameler']
            unvanlar = detail['unvanlar']
            
            # Beyanname listesi oluştur
            beyanname_html = ""
            if beyannameler:
                # İlk beyannameyi göster
                for b in beyannameler[:max_beyanname]:
                    beyanname_html += f'<span class="badge">{b}</span> '
                
                # Eğer daha fazla beyanname varsa
                if len(beyannameler) > max_beyanname:
                    remaining_count = len(beyannameler) - max_beyanname
                    hidden_items_id = f"hidden-items-{unique_id}"
                    badge_id = f"badge-{hidden_items_id}"
                    
                    # Gizli beyannameler için span oluştur
                    hidden_html = '<span id="' + hidden_items_id + '" class="hidden-items">'
                    for b in beyannameler[max_beyanname:]:
                        hidden_html += f'<span class="badge">{b}</span> '
                    hidden_html += '</span>'
                    
                    # "Daha fazla" butonu ekle
                    more_badge = f'<span id="{badge_id}" class="more-badge" onclick="toggleItems(\'{hidden_items_id}\')">+{remaining_count} daha</span>'
                    
                    # Her ikisini de ekle
                    beyanname_html += more_badge + hidden_html
                    
                    # ID'yi artır
                    unique_id += 1
            
            # Firma listesi oluştur
            unvan_html = ""
            if unvanlar:
                for u in unvanlar[:max_firma]:
                    unvan_html += f'{u}<br>'
                
                # Eğer daha fazla firma varsa toggle ekle
                if len(unvanlar) > max_firma:
                    remaining_count = len(unvanlar) - max_firma
                    hidden_items_id = f"hidden-items-{unique_id}"
                    badge_id = f"badge-{hidden_items_id}"
                    
                    # Gizli firmalar için div oluştur
                    hidden_html = '<div id="' + hidden_items_id + '" class="hidden-items">'
                    for u in unvanlar[max_firma:]:
                        hidden_html += f'{u}<br>'
                    hidden_html += '</div>'
                    
                    # "Daha fazla" butonu ekle
                    more_badge = f'<span id="{badge_id}" class="more-badge" onclick="toggleItems(\'{hidden_items_id}\')">+{remaining_count} firma daha</span>'
                    
                    # Her ikisini de ekle
                    unvan_html += more_badge + hidden_html
                    
                    # ID'yi artır
                    unique_id += 1
            
            html += f"""
                <tr>
                    <td></td>
                    <td class="gtip-code">{gtip}</td>
                    <td>{beyanname_html}</td>
                    <td>{unvan_html}</td>
                </tr>
            """
    
    # İlave satır sayısı bildirimi
    if len(summary_data) > 10:
        html += f"""
            <tr>
                <td colspan="4" style="text-align:center;font-style:italic">
                    +{len(summary_data) - 10} adet daha ticari tanım tutarsızlığı bulundu. 
                    Performans nedeniyle sadece ilk 10 tanesi gösterilmektedir.
                </td>
            </tr>
        """
    
    # Tabloyu kapat
    html += """
        </tbody>
    </table>
    """
    
    return html

def check_alici_satici_relationship(df, selected_companies=None, progress_callback=None):
    """
    Alıcı-Satıcı ilişki kontrolü
    
    İki kontrol yöntemi:
    1. Seçilen gönderici firmalara ait beyannamelardan ilişki durumu 6 olanları bulur
    2. Seçilen firma yoksa, aynı göndericide hem 6 hem 0 ilişki durumu olan beyannameleri bulur
    
    Args:
        df: Kontrol edilecek DataFrame
        selected_companies: Kullanıcının seçtiği firma listesi (opsiyonel)
        progress_callback: İlerleme bildirimi için callback fonksiyon
        
    Returns:
        dict: Kontrol sonuçları
    """
    if progress_callback:
        progress_callback(10, "Alıcı-satıcı ilişki kontrolü başlatılıyor...")
    
    # Büyük veri setleri için örnekleme yap
    sample_size = 5000  # Maksimum işlenecek satır sayısı
    if len(df) > sample_size:
        print(f"Veri seti çok büyük ({len(df)} satır). Örnekleme yapılıyor: {sample_size} satır")
        if progress_callback:
            progress_callback(15, f"Veri seti çok büyük ({len(df)} satır). Örnekleme yapılıyor...")
        df_sample = df.sample(sample_size, random_state=42)
    else:
        df_sample = df
    
    if "Alici_satici_iliskisi" not in df_sample.columns:
        return {
            "status": "error",
            "message": "Alici_satici_iliskisi sütunu bulunamadı."
        }
    
    if progress_callback:
        progress_callback(20, "Gerekli sütunlar kontrol ediliyor...")
    
    # Gerekli sütunların varlığını kontrol et
    needed_columns = ["Alici_satici_iliskisi", "Beyanname_no"]
    sender_column = None
    
    # Gönderici sütununu belirle - farklı isimler kullanılabilir
    possible_sender_columns = ["Gonderen", "Gonderen_adi", "Gonderen_firma", "Adi_unvani", "Ihracatci"]
    for col in possible_sender_columns:
        if col in df_sample.columns:
            sender_column = col
            break
    
    if not sender_column:
        return {
            "status": "error",
            "message": "Gönderici sütunu bulunamadı."
        }
    
    needed_columns.append(sender_column)
    
    # Tarih sütununu belirle
    date_column = None
    possible_date_columns = ["Beyanname_tarihi", "Tarih", "Tescil_tarihi"]
    for col in possible_date_columns:
        if col in df_sample.columns:
            date_column = col
            break
    
    if date_column:
        needed_columns.append(date_column)
    
    # Sütunların var olup olmadığını kontrol et
    missing_columns = [col for col in needed_columns if col not in df_sample.columns]
    if missing_columns:
        return {
            "status": "error",
            "message": f"Gerekli sütunlar bulunamadı: {', '.join(missing_columns)}"
        }
    
    if progress_callback:
        progress_callback(30, "Veri işleniyor...")
    
    # İşlem 1: Belirli gönderici firmaların ilişki durumu 6 olan beyannamelerini bul
    if selected_companies and len(selected_companies) > 0:
        if progress_callback:
            progress_callback(40, "Seçilen firma kayıtları filtreleniyor...")
        
        # Seçilen firmaların beyannamelerini filtrele
        selected_df = df_sample[df_sample[sender_column].isin(selected_companies)]
        
        # İlişki durumu 6 olan beyannameleri bul
        error_relations = selected_df[selected_df["Alici_satici_iliskisi"] == "6"].copy()
        
        if progress_callback:
            progress_callback(70, "Sonuçlar hazırlanıyor...")
        
        if date_column:
            error_relations = error_relations.sort_values(by=date_column, ascending=False)
        
        if error_relations.empty:
            return {
                "status": "ok",
                "message": "Seçilen firmalarda ilişki durumu 6 olan beyanname bulunamadı.",
                "type": "selected_companies",
                "data": None
            }
        else:
            # Tekrarlı beyannameleri kaldır - aynı beyanname numarasına sahip kayıtları tekil say
            unique_error_relations = error_relations.drop_duplicates(subset=["Beyanname_no"])
            
            # Sonuç DataFrame'ini hazırla
            result_columns = ["Beyanname_no", sender_column, "Alici_satici_iliskisi"]
            if date_column:
                result_columns.insert(1, date_column)
            
            result_df = error_relations[result_columns].copy()
            
            return {
                "status": "warning",
                "message": f"{len(unique_error_relations)} adet ilişki durumu 6 olan beyanname bulundu.",
                "type": "selected_companies",
                "data": result_df
            }
    
    # İşlem 2: Aynı göndericide farklı ilişki durumları olan beyannameleri bul ve hangi kodun hatalı olduğunu belirle
    else:
        if progress_callback:
            progress_callback(40, "Tüm firmalar için ön filtreleme yapılıyor...")
        
        # Sadece 0 ve 6 ilişki durumlarına odaklan - bu önemli performans iyileştirmesi
        filtered_df = df_sample[df_sample["Alici_satici_iliskisi"].isin(["0", "6"])].copy()
        
        if filtered_df.empty:
            return {
                "status": "ok",
                "message": "Veri setinde '0' veya '6' ilişki durumu bulunmuyor.",
                "type": "all_senders",
                "data": None
            }
        
        if progress_callback:
            progress_callback(50, "Firma grupları oluşturuluyor...")
        
        # Daha performanslı bir yaklaşım kullan
        # Önce 0 ve 6 değerlerine sahip firmaları bul
        firms_with_0 = set(filtered_df[filtered_df["Alici_satici_iliskisi"] == "0"][sender_column].unique())
        firms_with_6 = set(filtered_df[filtered_df["Alici_satici_iliskisi"] == "6"][sender_column].unique())
        
        # Kesişim kümesi - hem 0 hem 6 olan firmalar
        inconsistent_with_6_0 = list(firms_with_0.intersection(firms_with_6))
        
        if progress_callback:
            progress_callback(60, f"{len(inconsistent_with_6_0)} adet tutarsız firma bulundu...")
        
        if not inconsistent_with_6_0:
            return {
                "status": "ok",
                "message": "Aynı göndericide hem 6 hem 0 ilişki durumu olan beyanname bulunamadı.",
                "type": "all_senders",
                "data": None
            }
        else:
            if progress_callback:
                progress_callback(70, "İlgili beyannameler filtreleniyor...")
            
            # İlgili beyannameleri filtrele - daha verimli yöntem
            inconsistent_df = filtered_df[filtered_df[sender_column].isin(inconsistent_with_6_0)].copy()
            
            # Hatalı kodları belirle
            if progress_callback:
                progress_callback(75, "Hatalı kodlar belirleniyor...")
            
            # Tüm tutarsız veriyi sakla
            all_inconsistent_rows = []
            
            # Firma bazlı hatalı kod sayıları
            firm_error_stats = {
                "Firma": [],
                "Kod_0_Sayısı": [],
                "Kod_6_Sayısı": [],
                "Hatalı_Kod": [],
                "Hatalı_Beyanname_Sayısı": []
            }
            
            total_error_count = 0
            total_beyanname_error_count = 0  # Tekil beyanname sayısını takip et
            
            # Her firma için hangi kodun hatalı olduğunu belirle
            for firm in inconsistent_with_6_0:
                firm_data = inconsistent_df[inconsistent_df[sender_column] == firm]
                
                # Her firma için benzersiz beyanname numaralarını al
                unique_beyannames_0 = firm_data[firm_data["Alici_satici_iliskisi"] == "0"]["Beyanname_no"].unique()
                unique_beyannames_6 = firm_data[firm_data["Alici_satici_iliskisi"] == "6"]["Beyanname_no"].unique()
                
                # Kod sayılarını beyanname bazında hesapla
                code_0_count = len(unique_beyannames_0)
                code_6_count = len(unique_beyannames_6)
                
                # Hangi kod daha az sayıda ise onu hatalı say
                incorrect_code = "6" if code_6_count < code_0_count else "0"
                error_count = code_6_count if incorrect_code == "6" else code_0_count
                total_error_count += error_count
                
                # Hatalı kodlara sahip beyannameleri işaretle
                incorrect_rows = firm_data[firm_data["Alici_satici_iliskisi"] == incorrect_code].copy()
                incorrect_rows["Dogru_Kod"] = "0" if incorrect_code == "6" else "6"
                incorrect_rows["Hata_Durumu"] = "Hatalı kod"
                
                # Beyanname bazında benzersiz hata sayısını say
                unique_error_beyannames = incorrect_rows["Beyanname_no"].unique()
                total_beyanname_error_count += len(unique_error_beyannames)
                
                # Sonuçları topla
                all_inconsistent_rows.append(incorrect_rows)
                
                # Firma istatistiklerini ekle
                firm_error_stats["Firma"].append(firm)
                firm_error_stats["Kod_0_Sayısı"].append(code_0_count)
                firm_error_stats["Kod_6_Sayısı"].append(code_6_count)
                firm_error_stats["Hatalı_Kod"].append(incorrect_code)
                firm_error_stats["Hatalı_Beyanname_Sayısı"].append(error_count)
            
            # Tüm hatalı satırları birleştir
            result_df = pd.concat(all_inconsistent_rows) if all_inconsistent_rows else pd.DataFrame()
            
            # İstatistik DataFrame'i oluştur
            stats_df = pd.DataFrame(firm_error_stats)
            
            if progress_callback:
                progress_callback(80, "Sonuçlar hazırlanıyor...")
            
            # Sıralama
            if date_column and not result_df.empty:
                result_df = result_df.sort_values(by=[sender_column, date_column], ascending=[True, False])
            elif not result_df.empty:
                result_df = result_df.sort_values(by=sender_column)
            
            # Gösterilecek sütunları belirle
            if not result_df.empty:
                result_columns = ["Beyanname_no", sender_column, "Alici_satici_iliskisi", "Dogru_Kod", "Hata_Durumu"]
                if date_column:
                    result_columns.insert(1, date_column)
                
                # Sadece gerekli sütunları al
                available_columns = [col for col in result_columns if col in result_df.columns]
                result_df = result_df[available_columns].copy()
            
            return {
                "status": "warning",
                "message": f"{len(inconsistent_with_6_0)} gönderici firmada toplam {total_beyanname_error_count} adet hatalı ilişki kodlu beyanname tespit edildi.",
                "type": "all_senders_enhanced",
                "data": result_df,
                "stats": stats_df,
                "total_error_count": total_error_count,
                "total_beyanname_error_count": total_beyanname_error_count,
                "firm_count": len(inconsistent_with_6_0)
            }

def check_rarely_used_currency(df):
    """
    Firmalara göre nadiren kullanılan para birimlerini kontrol eder
    """
    if 'Fatura_miktarinin_dovizi' not in df.columns:
        return {
            "status": "error",
            "message": "Döviz bilgisi sütunu bulunamadı"
        }
    
    # Firma sütunlarını belirle
    firma_columns = [
        'Adi_unvani', 'Gonderen', 'Gonderen_adi', 'Gonderen_firma', 
        'Ihracatci', 'Ithalatci', 'Satici', 'Alici'
    ]
    
    # Mevcut olan firma sütununu bul
    firma_column = None
    for col in firma_columns:
        if col in df.columns:
            firma_column = col
            break
    
    if not firma_column:
        return {
            "status": "error",
            "message": "Firma/ithalatçı/ihracatçı sütunu bulunamadı"
        }
    
    # Boş firma ve döviz değerlerini filtrele
    filtered_df = df[(df[firma_column].notna()) & (df['Fatura_miktarinin_dovizi'].notna())]
    filtered_df = filtered_df[(df[firma_column] != '') & (df['Fatura_miktarinin_dovizi'] != '')]
    
    if len(filtered_df) == 0:
        return {
            "status": "error",
            "message": "Filtreleme sonrası incelenecek veri kalmadı"
        }
    
    # Her firma için döviz kullanımını hesapla
    result_data = []
    
    # Firmaları grupla
    for firma, firma_data in filtered_df.groupby(firma_column):
        # Boş veya geçersiz firma adlarını atla
        if pd.isna(firma) or firma == '':
            continue
            
        # Dövizleri say
        doviz_counts = firma_data['Fatura_miktarinin_dovizi'].value_counts()
        
        # En az 2 farklı döviz birimi kullanan firmaları kontrol et
        if len(doviz_counts) >= 2:
            # Toplam beyanname sayısı
            total_beyanname_count = len(firma_data['Beyanname_no'].unique())
            
            # En çok ve en az kullanılan dövizleri belirle
            most_common_currency = doviz_counts.index[0]
            most_common_count = doviz_counts.iloc[0]
            most_common_percentage = (most_common_count / len(firma_data)) * 100
            
            # Nadiren kullanılan dövizleri bul
            threshold_percentage = 10  # %10'dan az kullanılanlar "nadir" olarak kabul edilecek
            rarely_used_currencies = []
            
            for currency, count in doviz_counts.items():
                if currency == most_common_currency:
                    continue
                    
                percentage = (count / len(firma_data)) * 100
                if percentage < threshold_percentage:
                    # Nadir kullanılan döviz birimi örnek beyannamelerini bul
                    sample_beyannames = firma_data[firma_data['Fatura_miktarinin_dovizi'] == currency]['Beyanname_no'].unique()
                    sample_beyannames = sample_beyannames[:5].tolist()  # En fazla 5 örnek
                    
                    rarely_used_currencies.append({
                        'doviz': currency,
                        'sayi': count,
                        'yuzde': percentage,
                        'ornek_beyannameler': sample_beyannames
                    })
            
            # Nadir kullanılan döviz birimi varsa sonuca ekle
            if rarely_used_currencies:
                result_data.append({
                    'firma': firma,
                    'toplam_beyanname': total_beyanname_count,
                    'en_cok_kullanilan_doviz': most_common_currency,
                    'en_cok_kullanilan_doviz_yuzdesi': most_common_percentage,
                    'nadir_kullanilan_dovizler': rarely_used_currencies
                })
    
    if not result_data:
        return {
            "status": "ok",
            "message": "Nadiren kullanılan döviz birimi tespit edilmedi"
        }
    
    # Sonuç dataframe'i oluştur
    result_rows = []
    
    for item in result_data:
        firma = item['firma']
        
        for currency_info in item['nadir_kullanilan_dovizler']:
            currency = currency_info['doviz']
            count = currency_info['sayi']
            percentage = currency_info['yuzde']
            sample_beyannames = currency_info['ornek_beyannameler']
            
            # Örnek beyannameleri ilgili veriyi al
            sample_data = filtered_df[
                (filtered_df[firma_column] == firma) & 
                (filtered_df['Fatura_miktarinin_dovizi'] == currency) &
                (filtered_df['Beyanname_no'].isin(sample_beyannames))
            ]
            
            for _, row in sample_data.iterrows():
                result_row = {
                    'Firma': firma,
                    'Nadiren_Kullanilan_Doviz': currency,
                    'Kullanim_Sayisi': count,
                    'Kullanim_Yuzdesi': percentage,
                    'En_Cok_Kullanilan_Doviz': item['en_cok_kullanilan_doviz'],
                }
                
                # Beyannameye ilişkin detayları ekle
                for col in ['Beyanname_no', 'Fatura_miktarinin_dovizi', 'Fatura_miktari', 'Gtip', 'Rejim']:
                    if col in row:
                        result_row[col] = row[col]
                
                result_rows.append(result_row)
    
    # Tüm sonuçları içeren DataFrame
    result_df = pd.DataFrame(result_rows)
    
    # Özet DataFrame'i
    summary_data = []
    for item in result_data:
        for currency_info in item['nadir_kullanilan_dovizler']:
            summary_data.append({
                'Firma': item['firma'],
                'En_Cok_Kullanilan_Doviz': item['en_cok_kullanilan_doviz'],
                'En_Cok_Kullanilan_Doviz_Yuzdesi': round(item['en_cok_kullanilan_doviz_yuzdesi'], 2),
                'Nadir_Kullanilan_Doviz': currency_info['doviz'],
                'Nadir_Kullanilan_Doviz_Sayisi': currency_info['sayi'],
                'Nadir_Kullanilan_Doviz_Yuzdesi': round(currency_info['yuzde'], 2)
            })
    
    summary_df = pd.DataFrame(summary_data)
    
    # HTML rapor oluştur
    html_report = _create_rarely_used_html_report(result_data, "döviz birimi", firma_column)
    
    return {
        "status": "warning" if len(result_data) > 0 else "ok",
        "message": f"{len(result_data)} firmada nadiren kullanılan döviz birimi tespit edildi" if result_data else "Nadiren kullanılan döviz birimi tespit edilmedi",
        "data": result_df,
        "summary": summary_df,
        "html_report": html_report
    }

def _create_rarely_used_html_report(result_data, item_type, firma_column):
    """
    Nadiren kullanılan öğelerin (döviz, menşe ülke, ödeme şekli) HTML raporunu oluşturur
    """
    html = """
    <style>
    body {
        font-family: Arial, sans-serif;
        font-size: 12px;
        margin: 0;
        padding: 10px;
    }
    table {
        width: 100%;
        border-collapse: collapse;
        margin-bottom: 20px;
    }
    th {
        background-color: #f2f2f2;
        padding: 6px;
        text-align: left;
        border: 1px solid #ddd;
        position: sticky;
        top: 0;
    }
    td {
        padding: 4px;
        border: 1px solid #ddd;
    }
    tr:nth-child(even) {
        background-color: #f9f9f9;
    }
    .warning {
        color: #e53935;
        font-weight: bold;
    }
    .info {
        color: #2196F3;
    }
    .container {
        margin-bottom: 20px;
    }
    h2 {
        color: #333;
        font-size: 16px;
        margin-top: 20px;
        margin-bottom: 10px;
        padding-bottom: 5px;
        border-bottom: 1px solid #ddd;
    }
    h3 {
        color: #555;
        font-size: 14px;
        margin-top: 15px;
        margin-bottom: 8px;
    }
    .firm-section {
        margin-bottom: 30px;
        padding: 15px;
        background-color: #f5f5f5;
        border-radius: 5px;
    }
    .summary-box {
        background-color: #e3f2fd;
        border-left: 4px solid #2196F3;
        padding: 10px;
        margin-bottom: 20px;
    }
    </style>
    
    <div class="container">
        <h2>Nadiren Kullanılan """ + item_type.title() + """ Analizi</h2>
        
        <div class="summary-box">
            <p><strong>Özet:</strong> Bu rapor, firmaların genelde tercih ettiği """ + item_type + """den farklı olarak nadiren kullandıkları """ + item_type + """leri gösterir.</p>
            <p class="warning">Toplam <strong>""" + str(len(result_data)) + """</strong> firmada nadiren kullanılan """ + item_type + """ tespit edildi.</p>
        </div>
    """
    
    # Her firma için ayrı bölüm oluştur
    for item in result_data:
        firma = item['firma']
        en_cok_kullanilan = item['en_cok_kullanilan_doviz'] if 'en_cok_kullanilan_doviz' in item else (
                           item['en_cok_kullanilan_ulke'] if 'en_cok_kullanilan_ulke' in item else 
                           item['en_cok_kullanilan_odeme'])
        
        en_cok_yuzde = round(item['en_cok_kullanilan_doviz_yuzdesi'], 2) if 'en_cok_kullanilan_doviz_yuzdesi' in item else (
                       round(item['en_cok_kullanilan_ulke_yuzdesi'], 2) if 'en_cok_kullanilan_ulke_yuzdesi' in item else 
                       round(item['en_cok_kullanilan_odeme_yuzdesi'], 2))
        
        nadir_kullanilan_list = item['nadir_kullanilan_dovizler'] if 'nadir_kullanilan_dovizler' in item else (
                               item['nadir_kullanilan_ulkeler'] if 'nadir_kullanilan_ulkeler' in item else 
                               item['nadir_kullanilan_odeme_sekilleri'])
        
        nadir_field_name = 'doviz' if 'nadir_kullanilan_dovizler' in item else (
                          'ulke' if 'nadir_kullanilan_ulkeler' in item else 
                          'odeme')
        
        html += f"""
        <div class="firm-section">
            <h3>Firma: {firma}</h3>
            <p><strong>En çok kullanılan {item_type}:</strong> {en_cok_kullanilan} ({en_cok_yuzde}%)</p>
            <p><strong>Nadiren kullanılan {item_type} sayısı:</strong> {len(nadir_kullanilan_list)}</p>
            
            <table>
                <thead>
                    <tr>
                        <th>Nadiren Kullanılan {item_type.title()}</th>
                        <th>Kullanım Sayısı</th>
                        <th>Yüzde (%)</th>
                        <th>Örnek Beyannameler</th>
                    </tr>
                </thead>
                <tbody>
        """
        
        for nadir_item in nadir_kullanilan_list:
            deger = nadir_item[nadir_field_name]
            sayi = nadir_item['sayi']
            yuzde = round(nadir_item['yuzde'], 2)
            ornek_beyannameler = ", ".join(nadir_item['ornek_beyannameler']) if nadir_item['ornek_beyannameler'] else "-"
            
            html += f"""
                <tr>
                    <td>{deger}</td>
                    <td>{sayi}</td>
                    <td>{yuzde}%</td>
                    <td>{ornek_beyannameler}</td>
                </tr>
            """
        
        html += """
                </tbody>
            </table>
        </div>
        """
    
    # Değerlendirme
    html += """
    <h3>Değerlendirme</h3>
    <p>Firmaların nadiren kullandığı """ + item_type + """ öğeleri, aşağıdaki sebeplerden kaynaklanabilir:</p>
    <ul>
        <li>Genellikle tercih edilen """ + item_type + """den farklı özel bir durumun geçici olarak ortaya çıkması</li>
        <li>Vergi avantajı veya maliyet düşürme amaçlı işlemler</li>
        <li>Sadece belirli bir süre veya belirli işlemler için kullanılan farklı """ + item_type + """</li>
        <li>Veri girişi hataları veya tutarsız kodlamalar</li>
    </ul>
    <p>Bu tip tutarsızlıkların incelenmesi, işlemlerin tutarlılığı ve risk değerlendirmesi açısından önemlidir.</p>
    """
    
    html += "</div>"
    return html

def check_rarely_used_origin_country(df):
    """
    Firmalara göre nadiren kullanılan menşe ülkeleri kontrol eder
    """
    if 'Mensei_ulke' not in df.columns:
        return {
            "status": "error",
            "message": "Menşe ülke bilgisi sütunu bulunamadı"
        }
    
    # Firma sütunlarını belirle
    firma_columns = [
        'Adi_unvani', 'Gonderen', 'Gonderen_adi', 'Gonderen_firma', 
        'Ihracatci', 'Ithalatci', 'Satici', 'Alici'
    ]
    
    # Mevcut olan firma sütununu bul
    firma_column = None
    for col in firma_columns:
        if col in df.columns:
            firma_column = col
            break
    
    if not firma_column:
        return {
            "status": "error",
            "message": "Firma/ithalatçı/ihracatçı sütunu bulunamadı"
        }
    
    # Boş firma ve menşe ülke değerlerini filtrele
    filtered_df = df[(df[firma_column].notna()) & (df['Mensei_ulke'].notna())]
    filtered_df = filtered_df[(df[firma_column] != '') & (df['Mensei_ulke'] != '')]
    
    if len(filtered_df) == 0:
        return {
            "status": "error",
            "message": "Filtreleme sonrası incelenecek veri kalmadı"
        }
    
    # Her firma için menşe ülke kullanımını hesapla
    result_data = []
    
    # Firmaları grupla
    for firma, firma_data in filtered_df.groupby(firma_column):
        # Boş veya geçersiz firma adlarını atla
        if pd.isna(firma) or firma == '':
            continue
            
        # Menşe ülkeleri say
        ulke_counts = firma_data['Mensei_ulke'].value_counts()
        
        # En az 2 farklı menşe ülke kullanan firmaları kontrol et
        if len(ulke_counts) >= 2:
            # Toplam beyanname sayısı
            total_beyanname_count = len(firma_data['Beyanname_no'].unique())
            
            # En çok ve en az kullanılan menşe ülkeleri belirle
            most_common_country = ulke_counts.index[0]
            most_common_count = ulke_counts.iloc[0]
            most_common_percentage = (most_common_count / len(firma_data)) * 100
            
            # Nadiren kullanılan menşe ülkeleri bul
            threshold_percentage = 10  # %10'dan az kullanılanlar "nadir" olarak kabul edilecek
            rarely_used_countries = []
            
            for country, count in ulke_counts.items():
                if country == most_common_country:
                    continue
                    
                percentage = (count / len(firma_data)) * 100
                if percentage < threshold_percentage:
                    # Nadir kullanılan menşe ülke örnek beyannamelerini bul
                    sample_beyannames = firma_data[firma_data['Mensei_ulke'] == country]['Beyanname_no'].unique()
                    sample_beyannames = sample_beyannames[:5].tolist()  # En fazla 5 örnek
                    
                    rarely_used_countries.append({
                        'ulke': country,
                        'sayi': count,
                        'yuzde': percentage,
                        'ornek_beyannameler': sample_beyannames
                    })
            
            # Nadir kullanılan menşe ülke varsa sonuca ekle
            if rarely_used_countries:
                result_data.append({
                    'firma': firma,
                    'toplam_beyanname': total_beyanname_count,
                    'en_cok_kullanilan_ulke': most_common_country,
                    'en_cok_kullanilan_ulke_yuzdesi': most_common_percentage,
                    'nadir_kullanilan_ulkeler': rarely_used_countries
                })
    
    if not result_data:
        return {
            "status": "ok",
            "message": "Nadiren kullanılan menşe ülke tespit edilmedi"
        }
    
    # Sonuç dataframe'i oluştur
    result_rows = []
    
    for item in result_data:
        firma = item['firma']
        
        for country_info in item['nadir_kullanilan_ulkeler']:
            country = country_info['ulke']
            count = country_info['sayi']
            percentage = country_info['yuzde']
            sample_beyannames = country_info['ornek_beyannameler']
            
            # Örnek beyannameleri ilgili veriyi al
            sample_data = filtered_df[
                (filtered_df[firma_column] == firma) & 
                (filtered_df['Mensei_ulke'] == country) &
                (filtered_df['Beyanname_no'].isin(sample_beyannames))
            ]
            
            for _, row in sample_data.iterrows():
                result_row = {
                    'Firma': firma,
                    'Nadiren_Kullanilan_Ulke': country,
                    'Kullanim_Sayisi': count,
                    'Kullanim_Yuzdesi': percentage,
                    'En_Cok_Kullanilan_Ulke': item['en_cok_kullanilan_ulke'],
                }
                
                # Beyannameye ilişkin detayları ekle
                for col in ['Beyanname_no', 'Mensei_ulke', 'Fatura_miktari', 'Gtip', 'Rejim']:
                    if col in row:
                        result_row[col] = row[col]
                
                result_rows.append(result_row)
    
    # Tüm sonuçları içeren DataFrame
    result_df = pd.DataFrame(result_rows)
    
    # Özet DataFrame'i
    summary_data = []
    for item in result_data:
        for country_info in item['nadir_kullanilan_ulkeler']:
            summary_data.append({
                'Firma': item['firma'],
                'En_Cok_Kullanilan_Ulke': item['en_cok_kullanilan_ulke'],
                'En_Cok_Kullanilan_Ulke_Yuzdesi': round(item['en_cok_kullanilan_ulke_yuzdesi'], 2),
                'Nadir_Kullanilan_Ulke': country_info['ulke'],
                'Nadir_Kullanilan_Ulke_Sayisi': country_info['sayi'],
                'Nadir_Kullanilan_Ulke_Yuzdesi': round(country_info['yuzde'], 2)
            })
    
    summary_df = pd.DataFrame(summary_data)
    
    # HTML rapor oluştur
    html_report = _create_rarely_used_html_report(result_data, "menşe ülke", firma_column)
    
    return {
        "status": "warning" if len(result_data) > 0 else "ok",
        "message": f"{len(result_data)} firmada nadiren kullanılan menşe ülke tespit edildi" if result_data else "Nadiren kullanılan menşe ülke tespit edilmedi",
        "data": result_df,
        "summary": summary_df,
        "html_report": html_report
    }

def check_rarely_used_payment_method(df):
    """
    Firmalara göre nadiren kullanılan ödeme şekillerini kontrol eder
    """
    # Check for available payment method columns, prioritize "Odeme" if available
    payment_columns = ['Odeme', 'Odeme_sekli']
    payment_column = None
    
    for col in payment_columns:
        if col in df.columns:
            payment_column = col
            break
    
    if not payment_column:
        return {
            "status": "error",
            "message": "Ödeme şekli bilgisi sütunu bulunamadı"
        }
    
    # Firma sütunlarını belirle
    firma_columns = [
        'Adi_unvani', 'Gonderen', 'Gonderen_adi', 'Gonderen_firma', 
        'Ihracatci', 'Ithalatci', 'Satici', 'Alici'
    ]
    
    # Mevcut olan firma sütununu bul
    firma_column = None
    for col in firma_columns:
        if col in df.columns:
            firma_column = col
            break
    
    if not firma_column:
        return {
            "status": "error",
            "message": "Firma/ithalatçı/ihracatçı sütunu bulunamadı"
        }
    
    # Boş firma ve ödeme şekli değerlerini filtrele
    filtered_df = df[(df[firma_column].notna()) & (df[payment_column].notna())]
    filtered_df = filtered_df[(df[firma_column] != '') & (df[payment_column] != '')]
    
    if len(filtered_df) == 0:
        return {
            "status": "error",
            "message": "Filtreleme sonrası incelenecek veri kalmadı"
        }
    
    # Her firma için ödeme şekli kullanımını hesapla
    result_data = []
    
    # Firmaları grupla
    for firma, firma_data in filtered_df.groupby(firma_column):
        # Boş veya geçersiz firma adlarını atla
        if pd.isna(firma) or firma == '':
            continue
            
        # Ödeme şekillerini say
        odeme_counts = firma_data[payment_column].value_counts()
        
        # En az 2 farklı ödeme şekli kullanan firmaları kontrol et
        if len(odeme_counts) >= 2:
            # Toplam beyanname sayısı
            total_beyanname_count = len(firma_data['Beyanname_no'].unique())
            
            # En çok ve en az kullanılan ödeme şekillerini belirle
            most_common_payment = odeme_counts.index[0]
            most_common_count = odeme_counts.iloc[0]
            most_common_percentage = (most_common_count / len(firma_data)) * 100
            
            # Nadiren kullanılan ödeme şekillerini bul
            threshold_percentage = 10  # %10'dan az kullanılanlar "nadir" olarak kabul edilecek
            rarely_used_payments = []
            
            for payment, count in odeme_counts.items():
                if payment == most_common_payment:
                    continue
                    
                percentage = (count / len(firma_data)) * 100
                if percentage < threshold_percentage:
                    # Nadir kullanılan ödeme şekli örnek beyannamelerini bul
                    sample_beyannames = firma_data[firma_data[payment_column] == payment]['Beyanname_no'].unique()
                    sample_beyannames = sample_beyannames[:5].tolist()  # En fazla 5 örnek
                    
                    # Özellikle peşin ödemeleri işaretle
                    is_pesin = False
                    payment_lower = payment.lower() if isinstance(payment, str) else ""
                    if "peşin" in payment_lower or "pesin" in payment_lower:
                        is_pesin = True
                    
                    rarely_used_payments.append({
                        'odeme': payment,
                        'sayi': count,
                        'yuzde': percentage,
                        'ornek_beyannameler': sample_beyannames,
                        'is_pesin': is_pesin
                    })
            
            # Nadir kullanılan ödeme şekli varsa sonuca ekle
            if rarely_used_payments:
                result_data.append({
                    'firma': firma,
                    'toplam_beyanname': total_beyanname_count,
                    'en_cok_kullanilan_odeme': most_common_payment,
                    'en_cok_kullanilan_odeme_yuzdesi': most_common_percentage,
                    'nadir_kullanilan_odeme_sekilleri': rarely_used_payments
                })
    
    if not result_data:
        return {
            "status": "ok",
            "message": "Nadiren kullanılan ödeme şekli tespit edilmedi"
        }
    
    # Sonuç dataframe'i oluştur
    result_rows = []
    
    for item in result_data:
        firma = item['firma']
        
        for payment_info in item['nadir_kullanilan_odeme_sekilleri']:
            payment = payment_info['odeme']
            count = payment_info['sayi']
            percentage = payment_info['yuzde']
            sample_beyannames = payment_info['ornek_beyannameler']
            is_pesin = payment_info['is_pesin']
            
            # Örnek beyannameleri ilgili veriyi al
            sample_data = filtered_df[
                (filtered_df[firma_column] == firma) & 
                (filtered_df[payment_column] == payment) &
                (filtered_df['Beyanname_no'].isin(sample_beyannames))
            ]
            
            for _, row in sample_data.iterrows():
                result_row = {
                    'Firma': firma,
                    'Nadiren_Kullanilan_Odeme': payment,
                    'Kullanim_Sayisi': count,
                    'Kullanim_Yuzdesi': percentage,
                    'En_Cok_Kullanilan_Odeme': item['en_cok_kullanilan_odeme'],
                    'Pesin_Odeme_Mi': is_pesin
                }
                
                # Beyannameye ilişkin detayları ekle
                for col in ['Beyanname_no', payment_column, 'Fatura_miktari', 'Gtip', 'Rejim']:
                    if col in row:
                        # Use a standard column name for the payment method in the result
                        if col == payment_column:
                            result_row['Odeme_sekli'] = row[col]
                        else:
                            result_row[col] = row[col]
                
                result_rows.append(result_row)
    
    # Tüm sonuçları içeren DataFrame
    result_df = pd.DataFrame(result_rows)
    
    # Özet DataFrame'i
    summary_data = []
    for item in result_data:
        for payment_info in item['nadir_kullanilan_odeme_sekilleri']:
            summary_data.append({
                'Firma': item['firma'],
                'En_Cok_Kullanilan_Odeme': item['en_cok_kullanilan_odeme'],
                'En_Cok_Kullanilan_Odeme_Yuzdesi': round(item['en_cok_kullanilan_odeme_yuzdesi'], 2),
                'Nadir_Kullanilan_Odeme': payment_info['odeme'],
                'Nadir_Kullanilan_Odeme_Sayisi': payment_info['sayi'],
                'Nadir_Kullanilan_Odeme_Yuzdesi': round(payment_info['yuzde'], 2),
                'Pesin_Odeme_Mi': payment_info['is_pesin']
            })
    
    summary_df = pd.DataFrame(summary_data)
    
    # HTML rapor oluştur
    html_report = _create_rarely_used_html_report(result_data, "ödeme şekli", firma_column)
    
    # Peşin ödeme özellikle vurgulanacak
    pesin_count = sum(1 for item in summary_data if item['Pesin_Odeme_Mi'])
    if pesin_count > 0:
        message = f"{len(result_data)} firmada nadiren kullanılan ödeme şekli tespit edildi ({pesin_count} firma için peşin ödeme dikkat çekici)"
    else:
        message = f"{len(result_data)} firmada nadiren kullanılan ödeme şekli tespit edildi"
    
    return {
        "status": "warning" if len(result_data) > 0 else "ok",
        "message": message if result_data else "Nadiren kullanılan ödeme şekli tespit edilmedi",
        "data": result_df,
        "summary": summary_df,
        "html_report": html_report
    }

def check_gtip_urun_kodu_consistency(df):
    """
    Aynı ürün kodunda farklı GTİP kodu kullanılıp kullanılmadığını kontrol eder
    """
    print("GTİP-Ürün Kodu tutarlılık kontrolü başlatılıyor...")
    
    # Ürün kodu sütununu tanımla - yaygın isimlendirmeler
    product_code_columns = ["Urun_kodu", "Urun_Kodu", "Urun_no", "Product_code", "Stok_kodu", "Stok_Kodu"]
    
    # Veri setinde mevcut olan ürün kodu sütununu bul
    product_code_column = None
    for col in product_code_columns:
        if col in df.columns:
            product_code_column = col
            break
    
    if "Gtip" not in df.columns or product_code_column is None:
        print(f"Hata: Gtip veya Ürün Kodu sütunları bulunamadı.")
        return {
            "status": "error",
            "message": f"Gtip veya Ürün Kodu sütunları bulunamadı. Mevcut sütunlar: {', '.join(df.columns.tolist())}"
        }
    
    try:
        # Boş ürün kodlarını filtrele
        filtered_df = df[df[product_code_column].notna() & (df[product_code_column] != '')]
        
        print(f"Filtrelenmiş veri: {len(filtered_df)} satır")
        
        if len(filtered_df) == 0:
            return {
                "status": "ok",
                "message": "İşlenecek veri bulunamadı. Ürün kodları boş olabilir.",
                "html_report": "<p>İşlenecek veri bulunamadı. Ürün kodları boş olabilir.</p>"
            }
        
        # Her ürün kodu için benzersiz GTİP kodlarını bul
        grouped = filtered_df.groupby(product_code_column)['Gtip'].unique().reset_index()
        
        # Her ürün kodu için kaç farklı GTİP kodu kullanıldığını hesapla
        grouped['GTİP_Sayısı'] = grouped['Gtip'].apply(len)
        
        print(f"Toplam {len(grouped)} benzersiz ürün kodu bulundu.")
        print(f"Birden fazla GTİP kodu içeren ürün sayısı: {len(grouped[grouped['GTİP_Sayısı'] > 1])}")
        
        # Birden fazla GTİP kodu olan ürün kodlarını filtrele
        multiple_gtips = grouped[grouped['GTİP_Sayısı'] > 1].sort_values(by='GTİP_Sayısı', ascending=False)
        
        if multiple_gtips.empty:
            print("Aynı ürün kodunda farklı GTİP kodu kullanımı tespit edilmedi.")
            return {
                "status": "ok",
                "message": "Aynı ürün kodunda farklı GTİP kodu kullanımı tespit edilmedi.",
                "html_report": "<p>Aynı ürün kodunda farklı GTİP kodu kullanımı tespit edilmedi.</p>"
            }
        else:
            print(f"{len(multiple_gtips)} ürün kodunda tutarsızlık bulundu.")
            
            # Ayrıntılı sonuçlar için DataFrame oluştur
            result_rows = []
            
            # Ürün kodları için daha basit bir özet listesi oluştur
            simplified_summary = []
            
            # Her bir tutarsız ürün kodu için özet bilgi oluştur
            for _, row in multiple_gtips.iterrows():
                urun_kodu = row[product_code_column]
                gtip_codes = row['Gtip']
                gtip_count = row['GTİP_Sayısı']
                
                # İlgili satırları bul
                related_rows = filtered_df[filtered_df[product_code_column] == urun_kodu]
                
                # GTİP detayları için tam bilgileri topla - HTML rapor için
                gtip_details = []
                for gtip in gtip_codes:
                    gtip_rows = related_rows[related_rows['Gtip'] == gtip]
                    
                    beyanname_list = []
                    if "Beyanname_no" in gtip_rows.columns:
                        beyanname_list = gtip_rows['Beyanname_no'].dropna().unique().tolist()
                    
                    unvan_list = []
                    if "Adi_unvani" in gtip_rows.columns:
                        unvan_list = gtip_rows['Adi_unvani'].dropna().unique().tolist()
                    
                    gtip_details.append({
                        'gtip': gtip,
                        'beyannameler': beyanname_list,
                        'unvanlar': unvan_list
                    })
                
                # Basitleştirilmiş özet için satır ekle - karmaşık nesneler yok
                simplified_summary.append({
                    'Urun_kodu': urun_kodu,
                    'Farklı_GTİP_Sayısı': gtip_count,
                    'GTİP_Kodları': ', '.join(gtip_codes),
                    'GTİP_Detayları': gtip_details  # Her satır için GTİP detaylarını ekle
                })
                
                # Detaylı sonuçlar için satırları ekle
                for gtip in gtip_codes:
                    gtip_rows = related_rows[related_rows['Gtip'] == gtip]
                    
                    for _, data_row in gtip_rows.iterrows():
                        result_row = {
                            product_code_column: urun_kodu,
                            'Gtip': gtip
                        }
                        
                        # Diğer önemli sütunları da ekle
                        for col in ['Kalem_No', 'Ticari_tanimi', 'Mensei_ulke', 'Fatura_miktari', 'Fatura_miktarinin_dovizi', 'Beyanname_no', 'Adi_unvani', 'Kaynak_Dosya']:
                            if col in data_row:
                                result_row[col] = data_row[col]
                        
                        result_rows.append(result_row)
            
            # Detaylı dataframe oluştur
            result_df = pd.DataFrame(result_rows)
            print(f"Sonuç DataFrame oluşturuldu: {len(result_df)} satır")
            
            # Özet DataFrame oluştur - basitleştirilmiş veri
            summary_df = pd.DataFrame(simplified_summary)
            if 'GTİP_Detayları' in summary_df.columns:
                summary_df = summary_df.drop(columns=['GTİP_Detayları'])  # JSON serileştirme hatalarını önlemek için kompleks sütunu kaldır
            
            print(f"Özet DataFrame oluşturuldu: {len(summary_df)} satır")
            
            # Görsel sunum için HTML tablosu oluştur
            try:
                html_content = create_gtip_urun_kodu_html(simplified_summary, product_code_column)
                print("HTML raporu başarıyla oluşturuldu.")
            except Exception as e:
                print(f"HTML rapor oluşturma hatası: {str(e)}")
                html_content = f"<p>HTML rapor oluşturulurken hata: {str(e)}</p>"
            
            return {
                "status": "warning",
                "message": f"{len(multiple_gtips)} ürün kodunda farklı GTİP kodları kullanılmış.",
                "inconsistent_rows": result_df,
                "summary": summary_df,
                "detail": multiple_gtips,
                "html_report": html_content
            }
    except Exception as e:
        error_message = f"GTİP-Ürün Kodu tutarlılık kontrolü sırasında hata: {str(e)}"
        print(error_message)
        import traceback
        print(traceback.format_exc())
        return {
            "status": "error",
            "message": error_message,
            "html_report": f"<p>Hata: {str(e)}</p>"
        }

def create_gtip_urun_kodu_html(summary_data, product_code_column):
    """
    GTİP-Ürün Kodu tutarlılık kontrolü için basitleştirilmiş HTML raporu oluşturur
    """
    if not summary_data:
        return "<p>Herhangi bir tutarsızlık bulunamadı.</p>"
    
    # Pivot veri hazırla - GTİP kodlarının dağılımını göstermek için
    gtip_codes = []
    for item in summary_data:
        for detail in item['GTİP_Detayları']:
            gtip = detail['gtip']
            beyannameler = detail['beyannameler']
            count = len(beyannameler) if beyannameler else 1
            gtip_codes.append({
                'GTİP': gtip,
                'Beyanname_Sayısı': count,
                'Ürün_Kodu_Sayısı': 1
            })
    
    # GTİP kodlarına göre gruplama ve toplama
    gtip_pivot = None
    if gtip_codes:
        import pandas as pd
        gtip_df = pd.DataFrame(gtip_codes)
        gtip_pivot = gtip_df.groupby('GTİP').agg({
            'Beyanname_Sayısı': 'sum',
            'Ürün_Kodu_Sayısı': 'count'
        }).sort_values(by='Beyanname_Sayısı', ascending=False).reset_index()
    
    # Minimal HTML ve CSS kullan
    html = """
    <style>
    body {
        font-family: Arial, sans-serif;
        font-size: 12px;
        margin: 0;
                padding: 10px;
    }
    table {
        width: 100%;
        border-collapse: collapse;
        margin-bottom: 20px;
    }
    th {
        background-color: #f2f2f2;
        padding: 6px;
        text-align: left;
        border: 1px solid #ddd;
        position: sticky;
        top: 0;
    }
    td {
        padding: 4px;
        border: 1px solid #ddd;
    }
    tr:nth-child(even) {
        background-color: #f9f9f9;
    }
    .warning {
        color: #e53935;
        font-weight: bold;
    }
    .info {
        color: #2196F3;
    }
    .container {
        margin-bottom: 20px;
    }
    h2 {
        color: #333;
        font-size: 16px;
        margin-top: 20px;
                margin-bottom: 10px;
        padding-bottom: 5px;
        border-bottom: 1px solid #ddd;
    }
    h3 {
        color: #555;
        font-size: 14px;
        margin-top: 15px;
        margin-bottom: 8px;
    }
    .chart-container {
        margin-top: 20px;
        margin-bottom: 30px;
    }
    .summary-box {
        background-color: #f5f5f5;
        border-left: 4px solid #2196F3;
        padding: 10px;
        margin-bottom: 20px;
    }
    </style>
    
    <div class="container">
        <h2>GTİP - Ürün Kodu Tutarlılık Analizi</h2>
        
        <div class="summary-box">
            <p><strong>Özet:</strong> Bu rapor, aynı ürün koduna farklı GTİP kodları atanmış beyannameleri gösterir.</p>
            <p class="warning">Toplam <strong>""" + str(len(summary_data)) + """</strong> ürün kodunda tutarsızlık tespit edildi.</p>
        </div>
    """
    
    # GTİP dağılımı tablosu
    if gtip_pivot is not None and len(gtip_pivot) > 0:
        html += """
        <h3>GTİP Kodlarının Dağılımı</h3>
        <table>
            <thead>
                <tr>
                    <th>GTİP Kodu</th>
                    <th>Beyanname Sayısı</th>
                    <th>Kullanıldığı Ürün Kodu Sayısı</th>
                </tr>
            </thead>
            <tbody>
        """
        
        # En fazla 20 satır göster
        for _, row in gtip_pivot.head(20).iterrows():
            html += f"""
                <tr>
                    <td>{row['GTİP']}</td>
                    <td>{row['Beyanname_Sayısı']}</td>
                    <td>{row['Ürün_Kodu_Sayısı']}</td>
                </tr>
            """
        
        html += """
            </tbody>
        </table>
        """
        
        if len(gtip_pivot) > 20:
            html += f"<p><em>Not: Toplam {len(gtip_pivot)} GTİP kodundan ilk 20 tanesi gösterilmektedir.</em></p>"
    
    # Tutarsız ürün kodları listesi
    html += """
    <h3>Farklı GTİP Kodları Kullanılan Ürün Kodları</h3>
    <table>
        <thead>
            <tr>
                <th>Ürün Kodu</th>
                <th>Farklı GTİP Sayısı</th>
                <th>GTİP Kodları</th>
            </tr>
        </thead>
        <tbody>
    """
    
    # En fazla 100 tutarsız ürün kodu göster
    for item in summary_data[:100]:
        html += f"""
            <tr>
                <td>{item['Urun_kodu']}</td>
                <td>{item['Farklı_GTİP_Sayısı']}</td>
                <td>{item['GTİP_Kodları']}</td>
            </tr>
        """
    
    html += """
        </tbody>
    </table>
    """
    
    if len(summary_data) > 100:
        html += f"<p><em>Not: Toplam {len(summary_data)} tutarsız ürün kodundan ilk 100 tanesi gösterilmektedir.</em></p>"
    
    # Detaylı açıklama
    html += """
    <h3>Değerlendirme</h3>
    <p>Aynı ürün koduna sahip ürünlerin farklı GTİP kodları ile beyan edilmesi, aşağıdaki sebeplerden kaynaklanabilir:</p>
    <ul>
        <li>Ürünlerin yanlış GTİP kodu ile beyan edilmiş olması</li>
        <li>Aynı ürün kodu altında farklı ürünlerin bulunması</li>
        <li>Zaman içinde ürünün GTİP sınıflandırmasında değişiklik olması</li>
    </ul>
    <p>Bu tip tutarsızlıkların incelenmesi, vergi ve gümrük mevzuatına uyum açısından önemlidir.</p>
    """
    
    html += "</div>"
    return html

def check_unit_price_increase(df):
    """
    Aynı ürünün birim fiyatlarının zaman içinde önemli oranda artıp artmadığını kontrol eder.
    Aylık %3, 3 aylık %10'un üzerinde artış olup olmadığını analiz eder.
    
    Args:
        df (pandas.DataFrame): Beyanname verileri içeren DataFrame
    
    Returns:
        dict: Analiz sonuçları
    """
    # Gerekli sütunların varlığını kontrol et
    required_columns = ['Gtip', 'Ticari_tanimi', 'Adi_unvani', 'Beyanname_no']
    missing_columns = [col for col in required_columns if col not in df.columns]
    
    if missing_columns:
        return {
            "status": "error",
            "message": f"Gerekli sütunlar eksik: {', '.join(missing_columns)}"
        }
    
    # Tarih sütunu kontrolü
    date_column = None
    for col in ['Beyanname_tarihi', 'Tescil_tarihi', 'Tarih']:
        if col in df.columns:
            date_column = col
            break
    
    if not date_column:
        return {
            "status": "error",
            "message": "Tarih bilgisi sütunu bulunamadı"
        }
    
    # Birim kıymet bilgisi kontrolü - Istatistiki_kiymet'i kullan
    if 'Istatistiki_kiymet' not in df.columns:
        return {
            "status": "error",
            "message": "Istatistiki_kiymet sütunu bulunamadı"
        }
    
    unit_price_column = 'Istatistiki_kiymet'
    
    # Tarih sütununu datetime formatına dönüştür
    try:
        df[date_column] = pd.to_datetime(df[date_column], errors='coerce')
    except:
        return {
            "status": "error",
            "message": "Tarih sütunu dönüştürülemedi"
        }
    
    # Tarihi olmayan verileri filtrele
    df = df.dropna(subset=[date_column])
    
    # Sonuç verisini toplamak için liste
    result_data = []
    
    # Gtip, Ticari_tanimi ve Adi_unvani kombinasyonlarına göre grupla
    group_columns = ['Gtip', 'Ticari_tanimi', 'Adi_unvani']
    product_groups = df.groupby(group_columns)
    
    for (gtip, ticari_tanim, firma), group_data in product_groups:
        # Aynı ürün için tarihe göre sırala
        sorted_data = group_data.sort_values(by=date_column)
        
        # En az 2 kayıt yoksa analiz yapılamaz
        if len(sorted_data) < 2:
            continue
        
        # Döviz cinsi kontrolü
        currency_column = None
        for col in ['Doviz_cinsi', 'Fatura_doviz']:
            if col in sorted_data.columns:
                currency_column = col
                break
        
        # Döviz cinsi varsa, aynı döviz cinsine göre filtrele
        if currency_column and currency_column in sorted_data.columns:
            currency_groups = sorted_data.groupby(currency_column)
        else:
            # Döviz cinsi yoksa tüm veriyi tek grup olarak kullan
            currency_groups = [(None, sorted_data)]
        
        for currency, currency_data in currency_groups:
            # Tarihe göre yeniden sırala
            currency_data = currency_data.sort_values(by=date_column)
            
            # Her kayıt için karşılaştırma yap
            for i in range(1, len(currency_data)):
                current_row = currency_data.iloc[i]
                previous_rows = currency_data.iloc[:i]
                
                # Önceki satırı al
                previous_row = currency_data.iloc[i-1]
                
                # Tarih farklarını hesapla (gün olarak)
                days_diff = (current_row[date_column] - previous_row[date_column]).days
                
                # Karşılaştırma için günlük minimum fark (aynı gün olmasın)
                if days_diff < 1:
                    continue
                
                # 3 ay önceki fiyatı bul (yaklaşık 90 gün)
                three_month_price = None
                three_month_row = None
                
                for j in range(i):
                    prev_row = currency_data.iloc[j]
                    days_between = (current_row[date_column] - prev_row[date_column]).days
                    if 80 <= days_between <= 100:  # ~3 ay (80-100 gün arası)
                        three_month_price = prev_row[unit_price_column]
                        three_month_row = prev_row
                        break
                
                # Fiyat artışlarını hesapla
                current_price = current_row[unit_price_column]
                previous_price = previous_row[unit_price_column]
                
                # Fiyatların sayısal olmasını sağla
                try:
                    current_price = float(current_price)
                    previous_price = float(previous_price)
                    
                    if three_month_price is not None:
                        three_month_price = float(three_month_price)
                except (ValueError, TypeError):
                    # Fiyat sayısal değilse atla
                    continue
                
                # İki fiyat arasındaki artış yüzdesi
                if previous_price > 0:
                    monthly_increase_pct = ((current_price - previous_price) / previous_price) * 100
                    
                    # Aylık artış yüzdesi (30 güne normalize et)
                    if days_diff > 0:
                        normalized_monthly_increase = monthly_increase_pct * (30 / days_diff)
                    else:
                        normalized_monthly_increase = 0
                    
                    # 3 aylık artış yüzdesi
                    three_month_increase_pct = None
                    if three_month_price is not None and three_month_price > 0:
                        three_month_increase_pct = ((current_price - three_month_price) / three_month_price) * 100
                    
                    # Eşik değerlerin üzerinde artış varsa sonuçlara ekle
                    if (normalized_monthly_increase > 3) or (three_month_increase_pct is not None and three_month_increase_pct > 10):
                        result_row = {
                            'Gtip': gtip,
                            'Ticari_tanimi': ticari_tanim,
                            'Firma': firma,
                            'Doviz': currency if currency else 'Bilinmiyor',
                            'Onceki_Tarih': previous_row[date_column],
                            'Guncel_Tarih': current_row[date_column],
                            'Gun_Farki': days_diff,
                            'Onceki_Birim_Fiyat': previous_price,
                            'Guncel_Birim_Fiyat': current_price,
                            'Artis_Yuzdesi': monthly_increase_pct,
                            'Aylik_Normalize_Artis': normalized_monthly_increase,
                            'Beyanname_no': current_row['Beyanname_no'],
                            'Onceki_Beyanname_no': previous_row['Beyanname_no']
                        }
                        
                        # 3 aylık artış bilgisini ekle
                        if three_month_increase_pct is not None:
                            result_row['Uc_Aylik_Artis_Yuzdesi'] = three_month_increase_pct
                            result_row['Uc_Ay_Onceki_Beyanname_no'] = three_month_row['Beyanname_no']
                            result_row['Uc_Ay_Onceki_Tarih'] = three_month_row[date_column]
                            result_row['Uc_Ay_Onceki_Birim_Fiyat'] = three_month_price
                        
                        result_data.append(result_row)
    
    if not result_data:
        return {
            "status": "ok",
            "message": "Önemli birim fiyat artışı tespit edilmedi"
        }
    
    # Sonuçları DataFrame'e dönüştür
    result_df = pd.DataFrame(result_data)
    
    # Aylık ve 3 aylık artış durumlarını belirle
    monthly_increases = result_df[result_df['Aylik_Normalize_Artis'] > 3]
    three_month_increases = result_df[result_df.get('Uc_Aylik_Artis_Yuzdesi', 0) > 10]
    
    # Özet tablosu oluştur
    summary_data = {
        'Kontrol Kriteri': ['Aylık %3+ Artış', '3 Aylık %10+ Artış', 'Toplam Artış Tespiti'],
        'Tespit Sayısı': [len(monthly_increases), 
                         len(three_month_increases) if 'Uc_Aylik_Artis_Yuzdesi' in result_df.columns else 0, 
                         len(result_df)],
        'Etkilenen GTİP Sayısı': [monthly_increases['Gtip'].nunique(), 
                                three_month_increases['Gtip'].nunique() if 'Uc_Aylik_Artis_Yuzdesi' in result_df.columns else 0,
                                result_df['Gtip'].nunique()]
    }
    summary_df = pd.DataFrame(summary_data)
    
    # HTML rapor oluştur
    html_report = _generate_price_increase_html_report(result_df, summary_df)
    
    # Sonuç mesajını oluştur
    message = f"{len(result_df)} adet önemli birim fiyat artışı tespit edildi. ({len(monthly_increases)} aylık, {len(three_month_increases) if 'Uc_Aylik_Artis_Yuzdesi' in result_df.columns else 0} üç aylık)"
    
    return {
        "status": "warning",
        "message": message,
        "data": result_df,
        "summary": summary_df,
        "html_report": html_report
    }

def _generate_price_increase_html_report(result_df, summary_df):
    """
    Birim fiyat artışı kontrolü için HTML rapor oluşturur
    """
    # HTML şablonu
    html = """
    <style>
    body {
        font-family: Arial, sans-serif;
        margin: 0;
        padding: 10px;
    }
    h2, h3 {
        color: #2c3e50;
        padding-bottom: 10px;
        border-bottom: 1px solid #eee;
    }
    .summary-box {
        background-color: #f8f9fa;
        border: 1px solid #dee2e6;
        border-radius: 5px;
        padding: 15px;
        margin-bottom: 20px;
    }
    table {
        width: 100%;
        border-collapse: collapse;
        margin-bottom: 20px;
    }
    th {
        background-color: #f2f2f2;
        text-align: left;
        padding: 8px;
        border: 1px solid #ddd;
    }
    td {
        padding: 8px;
        border: 1px solid #ddd;
    }
    tr:nth-child(even) {
        background-color: #f8f9fa;
    }
    .warning {
        color: #e74c3c;
        font-weight: bold;
    }
    .info-card {
        background-color: #e3f2fd;
        border-left: 4px solid #2196f3;
        padding: 12px;
        margin: 15px 0;
                border-radius: 4px;
    }
    .critical {
        background-color: #ffebee;
        border-left: 4px solid #f44336;
    }
    .moderate {
        background-color: #fff8e1;
        border-left: 4px solid #ffc107;
    }
    .gtip-section {
        margin-top: 30px;
        padding-top: 10px;
        border-top: 1px dashed #ccc;
    }
    </style>
    
    <h2>Birim Fiyat Artışı Analiz Raporu</h2>
    
    <div class="summary-box">
        <h3>Kontrol Özeti</h3>
        <p>Bu kontrol, aynı ürünün birim fiyatlarının zaman içinde önemli oranda artıp artmadığını analiz eder.</p>
        <p><strong>Analiz Kriterleri:</strong></p>
        <ul>
            <li>Aylık %3'ün üzerinde fiyat artışı</li>
            <li>3 aylık %10'un üzerinde fiyat artışı</li>
        </ul>
    </div>
    """
    
    # Özet tablosunu ekle
    html += "<h3>Kontrol Sonuçları</h3>"
    html += summary_df.to_html(index=False, classes="table table-striped")
    
    # GTİP bazlı gruplandırma
    if not result_df.empty:
        html += "<h3>GTİP Bazlı Fiyat Artışları</h3>"
        
        gtip_groups = result_df.groupby('Gtip')
        
        for gtip, gtip_data in gtip_groups:
            html += f'<div class="gtip-section"><h4>GTİP: {gtip}</h4>'
            
            # Ticari tanım bilgisini ekle
            if 'Ticari_tanimi' in gtip_data.columns and not gtip_data['Ticari_tanimi'].isna().all():
                product_desc = gtip_data['Ticari_tanimi'].iloc[0]
                html += f'<p><strong>Ticari Tanım:</strong> {product_desc}</p>'
                
            # Firma bilgisini ekle
            if 'Firma' in gtip_data.columns and not gtip_data['Firma'].isna().all():
                firma = gtip_data['Firma'].iloc[0]
                html += f'<p><strong>Firma:</strong> {firma}</p>'
            
            # En yüksek artışları göster (en fazla 5 kayıt)
            html += '<p><strong>En Yüksek Artışlar:</strong></p>'
            
            # Aylık normalize artışa göre sırala
            monthly_sorted = gtip_data.sort_values(by='Aylik_Normalize_Artis', ascending=False).head(5)
            display_columns = ['Beyanname_no', 'Guncel_Tarih', 'Onceki_Tarih', 'Gun_Farki', 
                              'Guncel_Birim_Fiyat', 'Onceki_Birim_Fiyat', 'Aylik_Normalize_Artis']
            
            # Firma ve Ticari_tanimi sütunları varsa ekle
            if 'Firma' in monthly_sorted.columns:
                display_columns.append('Firma')
            
            if 'Ticari_tanimi' in monthly_sorted.columns:
                display_columns.append('Ticari_tanimi')
                
            # Mevcut sütunları kontrol et (bazı sütunlar eksik olabilir)
            existing_columns = [col for col in display_columns if col in monthly_sorted.columns]
            monthly_display = monthly_sorted[existing_columns]
            
            # Sütun adlarını değiştir
            column_mapping = {
                'Beyanname_no': 'Beyanname No', 
                'Guncel_Tarih': 'Güncel Tarih', 
                'Onceki_Tarih': 'Önceki Tarih', 
                'Gun_Farki': 'Gün Farkı', 
                'Guncel_Birim_Fiyat': 'Güncel Birim Fiyat', 
                'Onceki_Birim_Fiyat': 'Önceki Birim Fiyat', 
                'Aylik_Normalize_Artis': 'Aylık Artış (%)',
                'Firma': 'Firma',
                'Ticari_tanimi': 'Ticari Tanım'
            }
            
            # Sadece mevcut sütunlar için eşleştirmeleri kullan
            mapping = {k: v for k, v in column_mapping.items() if k in monthly_display.columns}
            monthly_display.columns = [mapping.get(col, col) for col in monthly_display.columns]
            
            html += monthly_display.to_html(index=False, classes="table table-striped")
            
            # 3 aylık artışları göster
            if 'Uc_Aylik_Artis_Yuzdesi' in gtip_data.columns:
                three_month_data = gtip_data[~gtip_data['Uc_Aylik_Artis_Yuzdesi'].isna()]
                
                if not three_month_data.empty:
                    html += '<p><strong>3 Aylık Artışlar:</strong></p>'
                    
                    three_month_sorted = three_month_data.sort_values(by='Uc_Aylik_Artis_Yuzdesi', ascending=False).head(5)
                    display_columns = ['Beyanname_no', 'Guncel_Tarih', 'Uc_Ay_Onceki_Tarih',
                                      'Guncel_Birim_Fiyat', 'Uc_Ay_Onceki_Birim_Fiyat', 'Uc_Aylik_Artis_Yuzdesi']
                    
                    # Firma ve Ticari_tanimi sütunları varsa ekle
                    if 'Firma' in three_month_sorted.columns:
                        display_columns.append('Firma')
                    
                    if 'Ticari_tanimi' in three_month_sorted.columns:
                        display_columns.append('Ticari_tanimi')
                    
                    # Mevcut sütunları kontrol et (bazı sütunlar eksik olabilir)
                    existing_columns = [col for col in display_columns if col in three_month_sorted.columns]
                    three_month_display = three_month_sorted[existing_columns]
                    
                    # Sütun adlarını değiştir
                    column_mapping = {
                        'Beyanname_no': 'Beyanname No', 
                        'Guncel_Tarih': 'Güncel Tarih', 
                        'Uc_Ay_Onceki_Tarih': '3 Ay Önceki Tarih',
                        'Guncel_Birim_Fiyat': 'Güncel Birim Fiyat', 
                        'Uc_Ay_Onceki_Birim_Fiyat': '3 Ay Önceki Birim Fiyat', 
                        'Uc_Aylik_Artis_Yuzdesi': '3 Aylık Artış (%)',
                        'Firma': 'Firma',
                        'Ticari_tanimi': 'Ticari Tanım'
                    }
                    
                    # Sadece mevcut sütunlar için eşleştirmeleri kullan
                    mapping = {k: v for k, v in column_mapping.items() if k in three_month_display.columns}
                    three_month_display.columns = [mapping.get(col, col) for col in three_month_display.columns]
                    
                    html += three_month_display.to_html(index=False, classes="table table-striped")
            
            html += '</div>'
    
    return html

def check_kdv_consistency(df):
    """
    Aynı GTİP için farklı KDV oranları beyan edilip edilmediğini kontrol eder.
    Özellikle %1, %10 ve %20 gibi farklı KDV oranlarına dikkat edilir.
    
    Args:
        df (pandas.DataFrame): Beyanname verileri içeren DataFrame
    
    Returns:
        dict: Analiz sonuçları
    """
    # KDV sütununu bul
    kdv_columns = ['Kdv_orani', 'Kdv', 'Vergi_orani_kdv']
    kdv_column = None
    
    for col in kdv_columns:
        if col in df.columns:
            kdv_column = col
            break
    
    if not kdv_column:
        return {
            "status": "error",
            "message": "KDV oranı sütunu bulunamadı"
        }
    
    # GTIP sütununu kontrol et
    if 'Gtip' not in df.columns:
        return {
            "status": "error",
            "message": "GTIP sütunu bulunamadı"
        }
    
    # Firma sütununu bul
    firma_columns = ['Adi_unvani', 'Gonderen', 'Gonderen_adi', 'Gonderen_firma', 'Ihracatci', 'Ithalatci']
    firma_column = None
    
    for col in firma_columns:
        if col in df.columns:
            firma_column = col
            break
    
    # KDV değerlerini normalize et
    df['Normalized_KDV'] = df[kdv_column].astype(str).str.replace(',', '.').str.replace('%', '')
    df['Normalized_KDV'] = pd.to_numeric(df['Normalized_KDV'], errors='coerce')
    
    # Aynı GTIP kodları için farklı KDV oranlarını bul
    gtip_kdv_counts = df.groupby('Gtip')['Normalized_KDV'].nunique()
    gtips_with_multiple_kdv = gtip_kdv_counts[gtip_kdv_counts > 1].index.tolist()
    
    if not gtips_with_multiple_kdv:
        return {
            "status": "ok",
            "message": "Aynı GTIP için farklı KDV oranı beyanı tespit edilmedi"
        }
    
    # Sonuç verisini oluştur
    result_data = []
    
    for gtip in gtips_with_multiple_kdv:
        gtip_data = df[df['Gtip'] == gtip]
        
        # Bu GTIP için KDV oranlarını ve sayılarını hesapla
        kdv_counts = gtip_data['Normalized_KDV'].value_counts().reset_index()
        kdv_counts.columns = ['KDV_Orani', 'Sayi']
        kdv_counts = kdv_counts.sort_values('Sayi', ascending=False)
        
        # En çok kullanılan KDV oranı
        most_common_kdv = kdv_counts.iloc[0]['KDV_Orani'] if not kdv_counts.empty else None
        
        # Bu GTIP için her bir KDV oranından örnek beyanname seç
        for kdv_rate in gtip_data['Normalized_KDV'].unique():
            sample_data = gtip_data[gtip_data['Normalized_KDV'] == kdv_rate].head(5)
            
            for _, row in sample_data.iterrows():
                result_row = {
                    'Gtip': gtip,
                    'KDV_Orani': kdv_rate,
                    'En_Cok_Kullanilan_KDV': most_common_kdv,
                    'Beyanname_no': row['Beyanname_no']
                }
                
                # Firma bilgisi ekle
                if firma_column:
                    result_row['Firma'] = row[firma_column] if firma_column in row else ''
                
                # Ürün tanımı ekle
                for desc_col in ['Ticari_tanimi', 'Esya_tanimi', 'Aciklama']:
                    if desc_col in row:
                        result_row['Urun_Tanimi'] = row[desc_col]
                        break
                
                # Tarih bilgisi ekle
                for date_col in ['Tescil_tarihi', 'Beyanname_tarihi', 'Tarih']:
                    if date_col in row:
                        result_row['Tarih'] = row[date_col]
                        break
                
                result_data.append(result_row)
    
    # Sonuçları DataFrame'e dönüştür
    result_df = pd.DataFrame(result_data)
    
    # Özel dikkat gerektiren KDV oranları
    special_rates = [1, 10, 20]
    special_rate_gtips = []
    
    for gtip in gtips_with_multiple_kdv:
        gtip_data = df[df['Gtip'] == gtip]
        kdv_rates = gtip_data['Normalized_KDV'].unique()
        
        # Bu GTIP için özel oranlar kullanılmış mı kontrol et
        special_rates_used = [rate for rate in kdv_rates if rate in special_rates]
        
        if len(special_rates_used) > 0:
            special_rate_gtips.append(gtip)
    
    # Özet tablosu oluştur
    summary_data = {
        'Analiz': [
            'Farklı KDV Oranları Bulunan GTIP Sayısı',
            'Özel KDV Oranları (%1, %10, %20) Bulunan GTIP Sayısı',
            'Toplam Farklı KDV Beyanı Sayısı'
        ],
        'Değer': [
            len(gtips_with_multiple_kdv),
            len(special_rate_gtips),
            len(result_df)
        ]
    }
    
    summary_df = pd.DataFrame(summary_data)
    
    # HTML rapor oluştur
    html_report = _generate_kdv_consistency_html_report(result_df, summary_df, df)
    
    # Sonuç mesajını oluştur
    message = f"{len(gtips_with_multiple_kdv)} GTIP için farklı KDV oranları beyan edilmiş. " + \
             f"{len(special_rate_gtips)} GTIP'te özel oranlar (%1, %10, %20) bulunuyor."
    
    return {
        "status": "warning",
        "message": message,
        "data": result_df,
        "summary": summary_df,
        "html_report": html_report
    }

def _generate_kdv_consistency_html_report(result_df, summary_df, original_df):
    """
    KDV tutarlılık kontrolü için HTML rapor oluşturur
    """
    # HTML şablonu
    html = """
    <style>
    body {
        font-family: Arial, sans-serif;
        margin: 0;
        padding: 10px;
    }
    h2, h3 {
        color: #2c3e50;
        padding-bottom: 10px;
        border-bottom: 1px solid #eee;
    }
    .summary-box {
        background-color: #f8f9fa;
        border: 1px solid #dee2e6;
        border-radius: 5px;
        padding: 15px;
        margin-bottom: 20px;
    }
    table {
        width: 100%;
        border-collapse: collapse;
        margin-bottom: 20px;
    }
    th {
        background-color: #f2f2f2;
        text-align: left;
        padding: 8px;
        border: 1px solid #ddd;
    }
    td {
        padding: 8px;
        border: 1px solid #ddd;
    }
    tr:nth-child(even) {
        background-color: #f8f9fa;
    }
    .warning {
        color: #e74c3c;
        font-weight: bold;
    }
    .info-card {
        background-color: #e3f2fd;
        border-left: 4px solid #2196f3;
        padding: 12px;
        margin: 15px 0;
                border-radius: 4px;
    }
    .gtip-section {
        margin-top: 30px;
        padding-top: 10px;
        border-top: 1px dashed #ccc;
    }
    .rate-distribution {
        display: inline-block;
        margin-right: 15px;
                padding: 5px 10px;
        background-color: #f1f1f1;
        border-radius: 4px;
    }
    </style>
    
    <h2>KDV Oranı Tutarlılık Analiz Raporu</h2>
    
    <div class="summary-box">
        <h3>Kontrol Özeti</h3>
        <p>Bu kontrol, aynı GTIP için farklı KDV oranları beyan edilip edilmediğini analiz eder.</p>
        <p><strong>Analiz Kriterleri:</strong></p>
        <ul>
            <li>Aynı GTIP için birden fazla KDV oranı beyan edilmiş mi?</li>
            <li>Özel KDV oranları (%1, %10, %20) kullanılmış mı?</li>
        </ul>
    </div>
    """
    
    # Özet tablosunu ekle
    html += "<h3>Kontrol Sonuçları</h3>"
    html += summary_df.to_html(index=False, classes="table table-striped")
    
    # GTIP bazlı gruplandırma
    if not result_df.empty:
        html += "<h3>GTIP Bazlı KDV Farklılıkları</h3>"
        
        gtip_groups = result_df.groupby('Gtip')
        
        for gtip, gtip_data in gtip_groups:
            html += f'<div class="gtip-section"><h4>GTIP: {gtip}</h4>'
            
            # Ürün tanımı bilgisi varsa ekle
            if 'Urun_Tanimi' in gtip_data.columns and not gtip_data['Urun_Tanimi'].isna().all():
                product_desc = gtip_data['Urun_Tanimi'].iloc[0]
                html += f'<p><strong>Ürün Tanımı:</strong> {product_desc}</p>'
            
            # KDV oranlarının dağılımını göster
            gtip_original_data = original_df[original_df['Gtip'] == gtip]
            
            if 'Normalized_KDV' in gtip_original_data.columns:
                kdv_distribution = gtip_original_data['Normalized_KDV'].value_counts().reset_index()
                kdv_distribution.columns = ['KDV_Orani', 'Beyanname_Sayisi']
                kdv_distribution['Oran'] = (kdv_distribution['Beyanname_Sayisi'] / kdv_distribution['Beyanname_Sayisi'].sum() * 100).round(2)
                kdv_distribution = kdv_distribution.sort_values('Beyanname_Sayisi', ascending=False)
                
                html += '<p><strong>KDV Oranı Dağılımı:</strong></p>'
                html += '<div>'
                
                for _, row in kdv_distribution.iterrows():
                    html += f'<div class="rate-distribution">%{row["KDV_Orani"]}: {row["Beyanname_Sayisi"]} beyanname ({row["Oran"]}%)</div>'
                
                html += '</div>'
            
            # Örnek beyannameleri göster
            html += '<p><strong>Farklı KDV Oranları Kullanılan Beyannameler:</strong></p>'
            
            # KDV oranına göre grupla
            kdv_rate_groups = gtip_data.groupby('KDV_Orani')
            
            for kdv_rate, rate_data in kdv_rate_groups:
                html += f'<p>KDV Oranı: <strong>%{kdv_rate}</strong></p>'
                
                # Beyanname örneklerini göster
                display_data = rate_data.head(3)
                
                # Gösterilecek sütunları seç
                display_cols = ['Beyanname_no', 'Firma'] if 'Firma' in rate_data.columns else ['Beyanname_no']
                
                # Tarih sütunu varsa ekle
                if 'Tarih' in rate_data.columns:
                    display_cols.append('Tarih')
                
                html += display_data[display_cols].to_html(index=False, classes="table table-striped")
            
            html += '</div>'
    
    return html

def check_domestic_expense_variation(df):
    """
    Benzer sevkiyatlarda yurt içi gider (ardiye, liman, demuraj vs) beyan farklarını kontrol eder.
    Aynı firmadan yapılan benzer ithalat işlemlerinde yurt içi gider beyanlarının tutarlılığını analiz eder.
    
    Args:
        df (pandas.DataFrame): Beyanname verileri içeren DataFrame
    
    Returns:
        dict: Analiz sonuçları
    """
    # Yurt içi gider sütunlarını bul
    domestic_expense_columns = []
    possible_columns = ['Yurtici_gider', 'Ardiye', 'Liman', 'Demuraj', 'Ic_nakliye', 'Iclojistik', 
                        'Terminal', 'Gumruk_masrafi', 'Gumrukleme']
    
    for col in df.columns:
        col_lower = col.lower()
        if any(keyword in col_lower for keyword in ['yurtici', 'ardiye', 'liman', 'demuraj', 'iç', 'terminal']):
            domestic_expense_columns.append(col)
        elif col in possible_columns:
            domestic_expense_columns.append(col)
    
    if not domestic_expense_columns:
        return {
            "status": "error",
            "message": "Yurt içi gider sütunları bulunamadı"
        }
    
    # Firma sütununu bul
    firm_columns = ['Adi_unvani', 'Gonderen', 'Gonderen_adi', 'Gonderen_firma', 'Ihracatci', 'Ithalatci', 'Satici']
    firm_column = None
    
    for col in firm_columns:
        if col in df.columns:
            firm_column = col
            break
    
    if not firm_column:
        return {
            "status": "error",
            "message": "Firma/gönderici sütunu bulunamadı"
        }
    
    # GTIP sütununu kontrol et
    if 'Gtip' not in df.columns:
        return {
            "status": "error",
            "message": "GTIP sütunu bulunamadı"
        }
    
    # Miktar sütununu kontrol et
    quantity_column = None
    for col in ['Miktar', 'Net_agirlik', 'Brut_agirlik']:
        if col in df.columns:
            quantity_column = col
            break
    
    if not quantity_column:
        return {
            "status": "error",
            "message": "Miktar/ağırlık sütunu bulunamadı"
        }
    
    # Yurt içi gider toplamını hesapla
    df['Toplam_Yurtici_Gider'] = 0
    
    for col in domestic_expense_columns:
        # Sayısal değerlere dönüştür
        try:
            df[col] = pd.to_numeric(df[col], errors='coerce')
            df['Toplam_Yurtici_Gider'] += df[col].fillna(0)
        except:
            pass  # Sayısal olmayan sütunları atla
    
    # Birim yurt içi gider hesapla (gider/miktar)
    df['Birim_Yurtici_Gider'] = df['Toplam_Yurtici_Gider'] / df[quantity_column]
    df['Birim_Yurtici_Gider'] = df['Birim_Yurtici_Gider'].replace([np.inf, -np.inf], np.nan)
    
    # Firma ve GTIP bazında grupla
    result_data = []
    
    # Her firma için analiz
    firms = df[firm_column].dropna().unique()
    
    for firm in firms:
        firm_data = df[df[firm_column] == firm]
        
        # GTIP bazında grupla
        gtip_groups = firm_data.groupby('Gtip')
        
        for gtip, gtip_data in gtip_groups:
            # En az 3 kayıt yoksa analiz yapmaya değmez
            if len(gtip_data) < 3:
                continue
            
            # Birim gider hesapla ve istatistikleri çıkar
            birim_gider = gtip_data['Birim_Yurtici_Gider'].dropna()
            
            if len(birim_gider) < 3:
                continue
            
            # Temel istatistikler
            mean_expense = birim_gider.mean()
            median_expense = birim_gider.median()
            std_expense = birim_gider.std()
            min_expense = birim_gider.min()
            max_expense = birim_gider.max()
            
            # Değişim katsayısı (CV = std / mean) - değişkenliği gösterir
            cv = std_expense / mean_expense if mean_expense > 0 else 0
            
            # %20'den fazla varyasyon önemli kabul edilsin
            if cv > 0.20 and std_expense > 0:
                # En düşük, ortalama ve en yüksek giderli beyanname örneklerini seç
                min_sample = gtip_data[gtip_data['Birim_Yurtici_Gider'] == min_expense].iloc[0]
                max_sample = gtip_data[gtip_data['Birim_Yurtici_Gider'] == max_expense].iloc[0]
                
                # Ortalamaya en yakın örneği bul
                median_idx = (gtip_data['Birim_Yurtici_Gider'] - median_expense).abs().idxmin()
                median_sample = gtip_data.loc[median_idx]
                
                # Sonuç verisine ekle
                result_row = {
                    'Firma': firm,
                    'Gtip': gtip,
                    'Ortalama_Birim_Yurtici_Gider': mean_expense,
                    'Medyan_Birim_Yurtici_Gider': median_expense,
                    'Standart_Sapma': std_expense,
                    'Minimum_Birim_Gider': min_expense,
                    'Maksimum_Birim_Gider': max_expense,
                    'Degisim_Katsayisi': cv,
                    'Beyanname_Sayisi': len(birim_gider),
                    'Min_Beyanname_No': min_sample['Beyanname_no'],
                    'Median_Beyanname_No': median_sample['Beyanname_no'],
                    'Max_Beyanname_No': max_sample['Beyanname_no']
                }
                
                # Ürün tanımı ekle
                for desc_col in ['Ticari_tanimi', 'Esya_tanimi', 'Aciklama']:
                    if desc_col in gtip_data.columns and not gtip_data[desc_col].isna().all():
                        result_row['Urun_Tanimi'] = gtip_data[desc_col].iloc[0]
                        break
                
                result_data.append(result_row)
    
    if not result_data:
        return {
            "status": "ok",
            "message": "Yurt içi gider beyanlarında önemli farklılık tespit edilmedi"
        }
    
    # Sonuçları DataFrame'e dönüştür
    result_df = pd.DataFrame(result_data)
    
    # Değişim katsayısına göre sırala
    result_df = result_df.sort_values('Degisim_Katsayisi', ascending=False)
    
    # Özet istatistikler
    high_variation_count = len(result_df[result_df['Degisim_Katsayisi'] > 0.5])  # %50'den fazla değişim
    medium_variation_count = len(result_df[(result_df['Degisim_Katsayisi'] > 0.3) & (result_df['Degisim_Katsayisi'] <= 0.5)])
    
    # Özet tablosu oluştur
    summary_data = {
        'Analiz': [
            'Yüksek Değişkenlik Gösteren (CV > 0.5) GTIP Sayısı',
            'Orta Değişkenlik Gösteren (0.3 < CV <= 0.5) GTIP Sayısı',
            'Toplam Değişkenlik Tespit Edilen (CV > 0.2) GTIP Sayısı',
            'Etkilenen Firma Sayısı'
        ],
        'Değer': [
            high_variation_count,
            medium_variation_count,
            len(result_df),
            result_df['Firma'].nunique()
        ]
    }
    
    summary_df = pd.DataFrame(summary_data)
    
    # HTML rapor oluştur
    html_report = _generate_expense_variation_html_report(result_df, summary_df, "Yurt İçi", domestic_expense_columns)
    
    # Sonuç mesajı
    message = f"{len(result_df)} GTIP için yurt içi gider beyanlarında önemli farklılıklar tespit edildi. " + \
             f"{high_variation_count} GTIP'te yüksek değişkenlik (>%50) mevcut."
    
    return {
        "status": "warning",
        "message": message,
        "data": result_df,
        "summary": summary_df,
        "html_report": html_report
    }

def check_foreign_expense_variation(df):
    """
    Benzer sevkiyatlarda yurt dışı gider (navlun, sigorta, komisyon vs) beyan farklarını kontrol eder.
    Aynı firmadan yapılan benzer ithalat işlemlerinde yurt dışı gider beyanlarının tutarlılığını analiz eder.
    
    Args:
        df (pandas.DataFrame): Beyanname verileri içeren DataFrame
    
    Returns:
        dict: Analiz sonuçları
    """
    # Yurt dışı gider sütunlarını bul
    foreign_expense_columns = []
    possible_columns = ['Yurtdisi_gider', 'Navlun', 'Sigorta', 'Komisyon', 'Royalti', 
                        'Dis_nakliye', 'Dislojistik', 'Demuraj_yurtdisi']
    
    for col in df.columns:
        col_lower = col.lower()
        if any(keyword in col_lower for keyword in ['yurtdisi', 'navlun', 'sigorta', 'komisyon', 'royalti']):
            foreign_expense_columns.append(col)
        elif col in possible_columns:
            foreign_expense_columns.append(col)
    
    if not foreign_expense_columns:
        return {
            "status": "error",
            "message": "Yurt dışı gider sütunları bulunamadı"
        }
    
    # Firma sütununu bul
    firm_columns = ['Adi_unvani', 'Gonderen', 'Gonderen_adi', 'Gonderen_firma', 'Ihracatci', 'Ithalatci', 'Satici']
    firm_column = None
    
    for col in firm_columns:
        if col in df.columns:
            firm_column = col
            break
    
    if not firm_column:
        return {
            "status": "error",
            "message": "Firma/gönderici sütunu bulunamadı"
        }
    
    # GTIP sütununu kontrol et
    if 'Gtip' not in df.columns:
        return {
            "status": "error",
            "message": "GTIP sütunu bulunamadı"
        }
    
    # Miktar sütununu kontrol et
    quantity_column = None
    for col in ['Miktar', 'Net_agirlik', 'Brut_agirlik']:
        if col in df.columns:
            quantity_column = col
            break
    
    if not quantity_column:
        return {
            "status": "error",
            "message": "Miktar/ağırlık sütunu bulunamadı"
        }
    
    # Yurt dışı gider toplamını hesapla
    df['Toplam_Yurtdisi_Gider'] = 0
    
    for col in foreign_expense_columns:
        # Sayısal değerlere dönüştür
        try:
            df[col] = pd.to_numeric(df[col], errors='coerce')
            df['Toplam_Yurtdisi_Gider'] += df[col].fillna(0)
        except:
            pass  # Sayısal olmayan sütunları atla
    
    # Birim yurt dışı gider hesapla (gider/miktar)
    df['Birim_Yurtdisi_Gider'] = df['Toplam_Yurtdisi_Gider'] / df[quantity_column]
    df['Birim_Yurtdisi_Gider'] = df['Birim_Yurtdisi_Gider'].replace([np.inf, -np.inf], np.nan)
    
    # Firma ve GTIP bazında grupla
    result_data = []
    
    # Her firma için analiz
    firms = df[firm_column].dropna().unique()
    
    for firm in firms:
        firm_data = df[df[firm_column] == firm]
        
        # GTIP bazında grupla
        gtip_groups = firm_data.groupby('Gtip')
        
        for gtip, gtip_data in gtip_groups:
            # En az 3 kayıt yoksa analiz yapmaya değmez
            if len(gtip_data) < 3:
                continue
            
            # Birim gider hesapla ve istatistikleri çıkar
            birim_gider = gtip_data['Birim_Yurtdisi_Gider'].dropna()
            
            if len(birim_gider) < 3:
                continue
            
            # Temel istatistikler
            mean_expense = birim_gider.mean()
            median_expense = birim_gider.median()
            std_expense = birim_gider.std()
            min_expense = birim_gider.min()
            max_expense = birim_gider.max()
            
            # Değişim katsayısı (CV = std / mean) - değişkenliği gösterir
            cv = std_expense / mean_expense if mean_expense > 0 else 0
            
            # %20'den fazla varyasyon önemli kabul edilsin
            if cv > 0.20 and std_expense > 0:
                # En düşük, ortalama ve en yüksek giderli beyanname örneklerini seç
                min_sample = gtip_data[gtip_data['Birim_Yurtdisi_Gider'] == min_expense].iloc[0]
                max_sample = gtip_data[gtip_data['Birim_Yurtdisi_Gider'] == max_expense].iloc[0]
                
                # Ortalamaya en yakın örneği bul
                median_idx = (gtip_data['Birim_Yurtdisi_Gider'] - median_expense).abs().idxmin()
                median_sample = gtip_data.loc[median_idx]
                
                # Sonuç verisine ekle
                result_row = {
                    'Firma': firm,
                    'Gtip': gtip,
                    'Ortalama_Birim_Yurtdisi_Gider': mean_expense,
                    'Medyan_Birim_Yurtdisi_Gider': median_expense,
                    'Standart_Sapma': std_expense,
                    'Minimum_Birim_Gider': min_expense,
                    'Maksimum_Birim_Gider': max_expense,
                    'Degisim_Katsayisi': cv,
                    'Beyanname_Sayisi': len(birim_gider),
                    'Min_Beyanname_No': min_sample['Beyanname_no'],
                    'Median_Beyanname_No': median_sample['Beyanname_no'],
                    'Max_Beyanname_No': max_sample['Beyanname_no']
                }
                
                # Ürün tanımı ekle
                for desc_col in ['Ticari_tanimi', 'Esya_tanimi', 'Aciklama']:
                    if desc_col in gtip_data.columns and not gtip_data[desc_col].isna().all():
                        result_row['Urun_Tanimi'] = gtip_data[desc_col].iloc[0]
                        break
                
                result_data.append(result_row)
    
    if not result_data:
        return {
            "status": "ok",
            "message": "Yurt dışı gider beyanlarında önemli farklılık tespit edilmedi"
        }
    
    # Sonuçları DataFrame'e dönüştür
    result_df = pd.DataFrame(result_data)
    
    # Değişim katsayısına göre sırala
    result_df = result_df.sort_values('Degisim_Katsayisi', ascending=False)
    
    # Özet istatistikler
    high_variation_count = len(result_df[result_df['Degisim_Katsayisi'] > 0.5])  # %50'den fazla değişim
    medium_variation_count = len(result_df[(result_df['Degisim_Katsayisi'] > 0.3) & (result_df['Degisim_Katsayisi'] <= 0.5)])
    
    # Özet tablosu oluştur
    summary_data = {
        'Analiz': [
            'Yüksek Değişkenlik Gösteren (CV > 0.5) GTIP Sayısı',
            'Orta Değişkenlik Gösteren (0.3 < CV <= 0.5) GTIP Sayısı',
            'Toplam Değişkenlik Tespit Edilen (CV > 0.2) GTIP Sayısı',
            'Etkilenen Firma Sayısı'
        ],
        'Değer': [
            high_variation_count,
            medium_variation_count,
            len(result_df),
            result_df['Firma'].nunique()
        ]
    }
    
    summary_df = pd.DataFrame(summary_data)
    
    # HTML rapor oluştur
    html_report = _generate_expense_variation_html_report(result_df, summary_df, "Yurt Dışı", foreign_expense_columns)
    
    # Sonuç mesajı
    message = f"{len(result_df)} GTIP için yurt dışı gider beyanlarında önemli farklılıklar tespit edildi. " + \
             f"{high_variation_count} GTIP'te yüksek değişkenlik (>%50) mevcut."
    
    return {
        "status": "warning",
        "message": message,
        "data": result_df,
        "summary": summary_df,
        "html_report": html_report
    }

def _generate_expense_variation_html_report(result_df, summary_df, expense_type, expense_columns):
    """
    Gider değişkenlik kontrolü için HTML rapor oluşturur
    
    Args:
        result_df: Analiz sonuçları
        summary_df: Özet sonuçları
        expense_type: Gider tipi (Yurt İçi veya Yurt Dışı)
        expense_columns: İncelenen gider sütunları
    """
    # HTML şablonu
    html = f"""
    <style>
    body {{
        font-family: Arial, sans-serif;
        margin: 0;
        padding: 10px;
    }}
    h2, h3 {{
        color: #2c3e50;
        padding-bottom: 10px;
        border-bottom: 1px solid #eee;
    }}
    .summary-box {{
        background-color: #f8f9fa;
        border: 1px solid #dee2e6;
        border-radius: 5px;
        padding: 15px;
        margin-bottom: 20px;
    }}
    table {{
        width: 100%;
        border-collapse: collapse;
        margin-bottom: 20px;
    }}
    th {{
        background-color: #f2f2f2;
        text-align: left;
                padding: 8px;
        border: 1px solid #ddd;
    }}
    td {{
        padding: 8px;
        border: 1px solid #ddd;
    }}
    tr:nth-child(even) {{
        background-color: #f8f9fa;
    }}
    .warning {{
        color: #e74c3c;
                font-weight: bold;
    }}
    .info-card {{
        background-color: #e3f2fd;
        border-left: 4px solid #2196f3;
        padding: 12px;
        margin: 15px 0;
        border-radius: 4px;
    }}
    .firm-section {{
        margin-top: 30px;
        padding-top: 10px;
        border-top: 1px dashed #ccc;
    }}
    .high-variation {{
        background-color: #ffebee;
    }}
    .medium-variation {{
        background-color: #fff8e1;
    }}
    </style>
    
    <h2>{expense_type} Gider Değişkenlik Analiz Raporu</h2>
    
    <div class="summary-box">
        <h3>Kontrol Özeti</h3>
        <p>Bu kontrol, aynı firmadan yapılan benzer ithalat işlemlerinde (eşya, miktar vs) {expense_type.lower()} gider beyanlarının tutarlılığını analiz eder.</p>
        <p><strong>İncelenen Gider Türleri:</strong> {', '.join(expense_columns)}</p>
        <p><strong>Analiz Kriterleri:</strong></p>
        <ul>
            <li>Aynı firma ve GTIP için birim gider değişkenliği hesaplanır.</li>
            <li>Değişim Katsayısı (CV) = Standart Sapma / Ortalama</li>
            <li>CV > 0.2 (%20) olduğunda önemli değişkenlik olarak kabul edilir.</li>
            <li>CV > 0.5 (%50) olduğunda yüksek değişkenlik olarak kabul edilir.</li>
        </ul>
    </div>
    """
    
    # Özet tablosunu ekle
    html += "<h3>Kontrol Sonuçları</h3>"
    html += summary_df.to_html(index=False, classes="table table-striped")
    
    # Firma bazlı gruplandırma
    if not result_df.empty:
        html += "<h3>Firma Bazlı Gider Değişkenliği</h3>"
        
        firm_groups = result_df.groupby('Firma')
        
        for firm, firm_data in firm_groups:
            html += f'<div class="firm-section"><h4>Firma: {firm}</h4>'
            
            # Değişkenliğe göre sırala
            firm_data = firm_data.sort_values('Degisim_Katsayisi', ascending=False)
            
            # GTIP bazında gösterim
            html += '<table class="table">'
            html += '''
            <tr>
                <th>GTIP</th>
                <th>Ürün Tanımı</th>
                <th>Değişim Katsayısı</th>
                <th>Min Birim Gider</th>
                <th>Ortalama Birim Gider</th>
                <th>Max Birim Gider</th>
                <th>Beyanname Sayısı</th>
            </tr>
            '''
            
            for _, row in firm_data.iterrows():
                # Değişkenlik seviyesine göre satır rengi belirle
                row_class = ""
                if row['Degisim_Katsayisi'] > 0.5:
                    row_class = "high-variation"
                elif row['Degisim_Katsayisi'] > 0.3:
                    row_class = "medium-variation"
                
                html += f'<tr class="{row_class}">'
                html += f'<td>{row["Gtip"]}</td>'
                html += f'<td>{row.get("Urun_Tanimi", "")}</td>'
                html += f'<td>{row["Degisim_Katsayisi"]:.2f}</td>'
                html += f'<td>{row["Minimum_Birim_Gider"]:.2f}</td>'
                html += f'<td>{row["Ortalama_Birim_Yurtici_Gider" if "Ortalama_Birim_Yurtdisi_Gider" in row else "Ortalama_Birim_Yurtici_Gider"]:.2f}</td>'
                html += f'<td>{row["Maksimum_Birim_Gider"]:.2f}</td>'
                html += f'<td>{row["Beyanname_Sayisi"]}</td>'
                html += '</tr>'
            
            html += '</table>'
            
            # En yüksek değişkenliğe sahip 2 GTIP'in örnek beyannamelerini göster
            high_variation_gtips = firm_data.head(2)
            
            if not high_variation_gtips.empty:
                html += '<h5>Örnek Beyannameler (En yüksek değişkenlik gösteren GTIPler için)</h5>'
                
                for _, gtip_row in high_variation_gtips.iterrows():
                    html += f'<p><strong>GTIP: {gtip_row["Gtip"]}</strong></p>'
                    html += '<ul>'
                    html += f'<li>En düşük giderli beyanname: {gtip_row["Min_Beyanname_No"]} (Birim gider: {gtip_row["Minimum_Birim_Gider"]:.2f})</li>'
                    html += f'<li>Ortalama giderli beyanname: {gtip_row["Median_Beyanname_No"]} (Birim gider: {gtip_row["Medyan_Birim_Yurtdisi_Gider" if "Medyan_Birim_Yurtdisi_Gider" in gtip_row else "Medyan_Birim_Yurtici_Gider"]:.2f})</li>'
                    html += f'<li>En yüksek giderli beyanname: {gtip_row["Max_Beyanname_No"]} (Birim gider: {gtip_row["Maksimum_Birim_Gider"]:.2f})</li>'
                    html += '</ul>'
            
            html += '</div>'
    
    return html

def check_supalan_storage_declaration(df):
    """
    Supalan (taşıt üstü) işlemlerde depolama (ardiye) beyanı olup olmadığını kontrol eder.
    BS3 kodu (taşıt üstü işlem) bulunan işlemlerde ardiye/depolama beyanı olmaması beklenir.
    
    Args:
        df (pandas.DataFrame): Beyanname verileri içeren DataFrame
    
    Returns:
        dict: Analiz sonuçları
    """
    # Basitleştirilmiş usul kodunu içeren sütunları bul
    procedure_columns = []
    possible_columns = ['Basitlestirilmis_usul', 'Basitlestirilmis_usul_kodu', 'Islem_kodu', 'Islem_turu']
    
    for col in df.columns:
        col_lower = col.lower()
        if any(keyword in col_lower for keyword in ['basitle', 'usul_kod', 'islem_kod', 'bs']):
            procedure_columns.append(col)
        elif col in possible_columns:
            procedure_columns.append(col)
    
    if not procedure_columns:
        return {
            "status": "error",
            "message": "Basitleştirilmiş usul/işlem kodu sütunu bulunamadı"
        }
    
    # Depolama/ardiye giderlerini içeren sütunları bul
    storage_columns = []
    possible_storage_columns = ['Ardiye', 'Depolama', 'Antrepo', 'Terminal', 'Yurtici_gider_aciklama']
    
    for col in df.columns:
        col_lower = col.lower()
        if any(keyword in col_lower for keyword in ['ardiye', 'depola', 'antrepo']):
            storage_columns.append(col)
        elif col in possible_storage_columns:
            storage_columns.append(col)
    
    if not storage_columns:
        return {
            "status": "error",
            "message": "Depolama/ardiye gideri sütunu bulunamadı"
        }
    
    # BS3 kodu bulunan beyannameleri tespit et
    supalan_beyannames = set()
    
    for col in procedure_columns:
        # Tüm olası BS3 kod formatlarını kontrol et (BS3, 3, bs3, vs.)
        if pd.api.types.is_string_dtype(df[col]):
            bs3_mask = df[col].str.lower().str.contains('bs3|^3$', na=False, regex=True)
            supalan_beyannames.update(df[bs3_mask]['Beyanname_no'].unique())
    
    if not supalan_beyannames:
        return {
            "status": "info",
            "message": "BS3 kodu (taşıt üstü işlem) bulunan beyanname bulunamadı"
        }
    
    # Depolama/ardiye gideri olan beyannameleri tespit et
    result_data = []
    
    for beyanname_no in supalan_beyannames:
        beyanname_df = df[df['Beyanname_no'] == beyanname_no]
        
        has_storage_fee = False
        storage_fee_evidence = []
        
        # Sayısal sütunlarda pozitif depolama gideri kontrolü
        for col in storage_columns:
            if col in beyanname_df.columns:
                try:
                    # Sayısal değerlere dönüştür
                    storage_values = pd.to_numeric(beyanname_df[col], errors='coerce')
                    
                    # Pozitif değer varsa depolama gideri vardır
                    if (storage_values > 0).any():
                        has_storage_fee = True
                        storage_fee_evidence.append(f"{col}: {storage_values.max()}")
                except:
                    # Metin sütunları için depolama/ardiye anahtar kelimelerini ara
                    if pd.api.types.is_string_dtype(beyanname_df[col]):
                        storage_text_mask = beyanname_df[col].str.lower().str.contains('ardiye|depo|antrepo', na=False, regex=True)
                        if storage_text_mask.any():
                            has_storage_fee = True
                            storage_text = beyanname_df.loc[storage_text_mask, col].iloc[0] if not beyanname_df.loc[storage_text_mask, col].empty else "Depolama bilgisi bulundu"
                            storage_fee_evidence.append(f"{col}: {storage_text}")
        
        if has_storage_fee:
            # Beyanname bilgilerini ekle
            result_row = {
                'Beyanname_no': beyanname_no,
                'Depolama_Gideri_Var': True,
                'Depolama_Kaniti': ', '.join(storage_fee_evidence)
            }
            
            # Gönderici firma bilgisini ekle
            for firm_col in ['Adi_unvani', 'Gonderen', 'Gonderen_adi', 'Ihracatci', 'Ithalatci']:
                if firm_col in beyanname_df.columns and not beyanname_df[firm_col].isna().all():
                    result_row['Firma'] = beyanname_df[firm_col].iloc[0]
                    break
            
            # Tarih bilgisini ekle
            for date_col in ['Tescil_tarihi', 'Beyanname_tarihi', 'Tarih']:
                if date_col in beyanname_df.columns and not beyanname_df[date_col].isna().all():
                    result_row['Tarih'] = beyanname_df[date_col].iloc[0]
                    break
    
            # İşlem kodunu ekle
            for proc_col in procedure_columns:
                if proc_col in beyanname_df.columns and not beyanname_df[proc_col].isna().all():
                    result_row['Islem_Kodu'] = beyanname_df[proc_col].iloc[0]
                    break
            
            result_data.append(result_row)
    
    if not result_data:
        return {
            "status": "ok",
            "message": f"BS3 kodlu {len(supalan_beyannames)} beyannamede depolama/ardiye gideri tespit edilmedi"
        }
    
    # Sonuçları DataFrame'e dönüştür
    result_df = pd.DataFrame(result_data)
    
    # Özet tablosu oluştur
    summary_data = {
        'Analiz': [
            'Toplam BS3 Kodlu Beyanname Sayısı',
            'Depolama/Ardiye Gideri Bulunan BS3 Beyanname Sayısı',
            'Depolama/Ardiye Gideri Bulunma Oranı (%)'
        ],
        'Değer': [
            len(supalan_beyannames),
            len(result_df),
            round(len(result_df) / len(supalan_beyannames) * 100, 2)
        ]
    }
    
    summary_df = pd.DataFrame(summary_data)
    
    # HTML rapor oluştur
    html_report = _generate_supalan_storage_html_report(result_df, summary_df)
    
    # Sonuç mesajı
    message = f"{len(result_df)} adet BS3 kodlu (taşıt üstü) beyannamede depolama/ardiye gideri beyanı tespit edildi. " + \
             f"Bu, tüm BS3 kodlu beyannamelerin %{round(len(result_df) / len(supalan_beyannames) * 100, 2)}'ini oluşturuyor."
    
    return {
        "status": "warning",
        "message": message,
        "data": result_df,
        "summary": summary_df,
        "html_report": html_report
    }

def _generate_supalan_storage_html_report(result_df, summary_df):
    """
    Supalan işlemlerde depolama gideri analizi için HTML rapor oluşturur
    """
    # HTML şablonu
    html = """
    <style>
    body {
        font-family: Arial, sans-serif;
        margin: 0;
        padding: 10px;
    }
    h2, h3 {
        color: #2c3e50;
        padding-bottom: 10px;
        border-bottom: 1px solid #eee;
    }
    .summary-box {
        background-color: #f8f9fa;
        border: 1px solid #dee2e6;
        border-radius: 5px;
        padding: 15px;
        margin-bottom: 20px;
    }
    table {
        width: 100%;
        border-collapse: collapse;
        margin-bottom: 20px;
    }
    th {
        background-color: #f2f2f2;
        text-align: left;
        padding: 8px;
        border: 1px solid #ddd;
    }
    td {
        padding: 8px;
        border: 1px solid #ddd;
    }
    tr:nth-child(even) {
        background-color: #f8f9fa;
    }
    .warning {
        color: #e74c3c;
        font-weight: bold;
    }
    .info-card {
        background-color: #e3f2fd;
        border-left: 4px solid #2196f3;
        padding: 12px;
        margin: 15px 0;
        border-radius: 4px;
    }
    </style>
    
    <h2>Supalan İşlemlerde Depolama Gideri Analiz Raporu</h2>
    
    <div class="summary-box">
        <h3>Kontrol Özeti</h3>
        <p>Bu kontrol, BS3 kodu bulunan işlemlerde (supalan - taşıt üstü) depolama/ardiye gideri beyanı olup olmadığını analiz eder.</p>
        <p class="warning">Supalan (taşıt üstü) işlemlerde eşya taşıt üzerinden doğrudan teslim edildiği için depolama/ardiye gideri olmaması beklenir.</p>
    </div>
    """
    
    # Özet tablosunu ekle
    html += "<h3>Kontrol Sonuçları</h3>"
    html += summary_df.to_html(index=False, classes="table table-striped")
    
    # Detaylı sonuçları göster
    if not result_df.empty:
        html += "<h3>Depolama/Ardiye Gideri Bulunan BS3 Kodlu Beyannameler</h3>"
        
        # Tarih sütununa göre sırala (varsa)
        if 'Tarih' in result_df.columns:
            result_df = result_df.sort_values('Tarih', ascending=False)
        
        # Gösterilecek sütunları belirle
        display_cols = ['Beyanname_no']
        
        # Firma sütunu varsa ekle
        if 'Firma' in result_df.columns:
            display_cols.append('Firma')
        
        # Tarih sütunu varsa ekle
        if 'Tarih' in result_df.columns:
            display_cols.append('Tarih')
        
        # İşlem kodu ve depolama kanıtı ekle
        if 'Islem_Kodu' in result_df.columns:
            display_cols.append('Islem_Kodu')
        
        display_cols.append('Depolama_Kaniti')
        
        # Detay tablosunu göster
        html += result_df[display_cols].to_html(index=False, classes="table table-striped")
        
        # Açıklama ekle
        html += """
        <div class="info-card">
            <p>Supalan (taşıt üstü) işlemlerde depolama/ardiye gideri beyanı bulunması, eşyanın taşıt üzerinden doğrudan teslim edilmediğini ve gümrük sahası içerisinde depolandığını gösterir.</p>
            <p>Bu durum, BS3 koduyla yapılan işlemlerin niteliğiyle çelişmektedir. BS3 kodu, eşyanın depolanmadan, doğrudan taşıt üzerinden teslim edildiği durumları ifade eder.</p>
        </div>
        """
    
    return html

# ----------------------
# GUI Widget'ları
# ----------------------

class PivotWidget(QWidget):
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
                if col in ["Fatura_miktari", "Net_agirlik"]:
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
        
        # Figürü temizle
        self.figure.clear()
        
        if chart_type == "Çubuk Grafik":
            create_bar_chart(self.df, x_column, title=f"{x_column} Dağılımı", limit=10)
            
        elif chart_type == "Pasta Grafik":
            create_pie_chart(self.df, x_column, title=f"{x_column} Dağılımı", limit=5)
            
        elif chart_type == "Scatter Plot":
            y_column = self.y_selector.currentText()
            create_scatter_plot(self.df, x_column, y_column, 
                               title=f"{x_column} vs {y_column}")
        
        # Canvası güncelle
        self.canvas.draw() 

def check_rarely_used_origin_country_by_sender_gtip(df):
    """
    Aynı gönderici ve aynı GTİP kodunda nadiren kullanılan menşe ülkeleri kontrol eder
    
    Args:
        df (pandas.DataFrame): Beyanname verileri içeren DataFrame
    
    Returns:
        dict: Analiz sonuçları
    """
    # Gerekli sütunları kontrol et
    required_columns = ['Mensei_ulke', 'Gtip']
    missing_columns = [col for col in required_columns if col not in df.columns]
    
    if missing_columns:
        return {
            "status": "error",
            "message": f"Gerekli sütunlar bulunamadı: {', '.join(missing_columns)}"
        }
    
    # Gönderici sütunlarını belirle (öncelik sırası)
    sender_columns = ['Adi_unvani', 'Gonderen', 'Gonderen_adi', 'Gonderen_firma', 'Satici', 'Ihracatci']
    sender_column = None
    
    for col in sender_columns:
        if col in df.columns:
            sender_column = col
            break
    
    if not sender_column:
        return {
            "status": "error",
            "message": f"Gönderici sütunu bulunamadı. Aranan sütunlar: {', '.join(sender_columns)}"
        }
    
    # Boş değerleri filtrele
    filtered_df = df[
        (df[sender_column].notna()) & 
        (df['Mensei_ulke'].notna()) &
        (df['Gtip'].notna()) &
        (df[sender_column] != '') & 
        (df['Mensei_ulke'] != '') &
        (df['Gtip'] != '')
    ].copy()
    
    if len(filtered_df) == 0:
        return {
            "status": "error",
            "message": "Filtreleme sonrası incelenecek veri kalmadı"
        }
    
    # Gönderici + GTİP kombinasyonları için analiz
    result_data = []
    
    # Gönderici ve GTİP kombinasyonlarını grupla
    for (sender, gtip), group_data in filtered_df.groupby([sender_column, 'Gtip']):
        # Boş veya geçersiz değerleri atla
        if pd.isna(sender) or pd.isna(gtip) or sender == '' or gtip == '':
            continue
        
        # En az 3 beyanname ve 2 farklı menşe ülke olmalı
        if len(group_data) < 3:
            continue
            
        # Menşe ülkeleri say
        ulke_counts = group_data['Mensei_ulke'].value_counts()
        
        if len(ulke_counts) < 2:
            continue
        
        # En çok kullanılan menşe ülke
        most_common_country = ulke_counts.index[0]
        most_common_count = ulke_counts.iloc[0]
        most_common_percentage = (most_common_count / len(group_data)) * 100
        
        # Nadiren kullanılan menşe ülkeleri bul (eşik: %20)
        threshold_percentage = 20  # Daha sıkı kontrol için %20 eşiği
        rarely_used_countries = []
        
        for country, count in ulke_counts.items():
            if country == most_common_country:
                continue
                
            percentage = (count / len(group_data)) * 100
            if percentage < threshold_percentage:
                # Nadir kullanılan menşe ülke örnek beyannamelerini bul
                sample_beyannames = group_data[group_data['Mensei_ulke'] == country]['Beyanname_no'].unique()
                sample_beyannames = sample_beyannames[:3].tolist()  # En fazla 3 örnek
                
                # Fatura miktarları ve tarihleri
                country_data = group_data[group_data['Mensei_ulke'] == country]
                avg_amount = country_data['Fatura_miktari'].mean() if 'Fatura_miktari' in country_data.columns else 0
                
                rarely_used_countries.append({
                    'ulke': country,
                    'sayi': count,
                    'yuzde': percentage,
                    'ortalama_fatura_miktari': avg_amount,
                    'ornek_beyannameler': sample_beyannames
                })
        
        # Nadir kullanılan menşe ülke varsa sonuca ekle
        if rarely_used_countries:
            # GTİP açıklamasını bul
            gtip_description = ""
            if 'Gtip_tanimi' in group_data.columns:
                gtip_description = group_data['Gtip_tanimi'].iloc[0] if not group_data['Gtip_tanimi'].isna().all() else ""
            elif 'GTİP_tanimi' in group_data.columns:
                gtip_description = group_data['GTİP_tanimi'].iloc[0] if not group_data['GTİP_tanimi'].isna().all() else ""
            
            result_data.append({
                'gonderen': sender,
                'gtip': gtip,
                'gtip_tanimi': gtip_description,
                'toplam_beyanname': len(group_data),
                'toplam_mensei_ulke_sayisi': len(ulke_counts),
                'en_cok_kullanilan_ulke': most_common_country,
                'en_cok_kullanilan_ulke_yuzdesi': most_common_percentage,
                'nadir_kullanilan_ulkeler': rarely_used_countries
            })
    
    if not result_data:
        return {
            "status": "ok",
            "message": "Aynı gönderici ve GTİP kodunda nadiren kullanılan menşe ülke tespit edilmedi"
        }
    
    # Sonuç dataframe'i oluştur
    result_rows = []
    
    for item in result_data:
        sender = item['gonderen']
        gtip = item['gtip']
        
        for country_info in item['nadir_kullanilan_ulkeler']:
            country = country_info['ulke']
            count = country_info['sayi']
            percentage = country_info['yuzde']
            avg_amount = country_info['ortalama_fatura_miktari']
            sample_beyannames = country_info['ornek_beyannameler']
            
            # Örnek beyannameleri ilgili veriyi al
            sample_data = filtered_df[
                (filtered_df[sender_column] == sender) & 
                (filtered_df['Gtip'] == gtip) &
                (filtered_df['Mensei_ulke'] == country) &
                (filtered_df['Beyanname_no'].isin(sample_beyannames))
            ]
            
            for _, row in sample_data.iterrows():
                result_row = {
                    'Gonderen': sender,
                    'Gtip': gtip,
                    'Gtip_Tanimi': item['gtip_tanimi'],
                    'Nadiren_Kullanilan_Ulke': country,
                    'Kullanim_Sayisi': count,
                    'Kullanim_Yuzdesi': round(percentage, 2),
                    'Ortalama_Fatura_Miktari': round(avg_amount, 2) if avg_amount > 0 else 0,
                    'En_Cok_Kullanilan_Ulke': item['en_cok_kullanilan_ulke'],
                    'Toplam_Beyanname_Sayisi': item['toplam_beyanname'],
                    'Toplam_Mensei_Ulke_Sayisi': item['toplam_mensei_ulke_sayisi']
                }
                
                # Beyannameye ilişkin detayları ekle
                for col in ['Beyanname_no', 'Mensei_ulke', 'Fatura_miktari', 'Tescil_tarihi', 'Rejim']:
                    if col in row:
                        result_row[col] = row[col]
                
                result_rows.append(result_row)
    
    # Tüm sonuçları içeren DataFrame
    result_df = pd.DataFrame(result_rows)
    
    # Özet DataFrame'i
    summary_data = []
    for item in result_data:
        for country_info in item['nadir_kullanilan_ulkeler']:
            summary_data.append({
                'Gonderen': item['gonderen'],
                'Gtip': item['gtip'],
                'Gtip_Tanimi': item['gtip_tanimi'][:50] + "..." if len(item['gtip_tanimi']) > 50 else item['gtip_tanimi'],
                'En_Cok_Kullanilan_Ulke': item['en_cok_kullanilan_ulke'],
                'Nadir_Kullanilan_Ulke': country_info['ulke'],
                'Nadir_Kullanilan_Ulke_Sayisi': country_info['sayi'],
                'Nadir_Kullanilan_Ulke_Yuzdesi': round(country_info['yuzde'], 2),
                'Ortalama_Fatura_Miktari': round(country_info['ortalama_fatura_miktari'], 2) if country_info['ortalama_fatura_miktari'] > 0 else 0,
                'Toplam_Beyanname': item['toplam_beyanname'],
                'Risk_Skoru': round(country_info['yuzde'] * (country_info['ortalama_fatura_miktari'] / 1000), 2)  # Risk skoru hesaplama
            })
    
    summary_df = pd.DataFrame(summary_data)
    
    # HTML rapor oluştur
    html_report = _create_sender_gtip_origin_html_report(result_data, sender_column)
    
    return {
        "status": "warning" if len(result_data) > 0 else "ok",
        "message": f"{len(result_data)} gönderici-GTİP kombinasyonunda nadiren kullanılan menşe ülke tespit edildi" if result_data else "Aynı gönderici ve GTİP kodunda nadiren kullanılan menşe ülke tespit edilmedi",
        "data": result_df,
        "summary": summary_df,
        "html_report": html_report,
        "detailed_analysis": result_data
    }

def _create_sender_gtip_origin_html_report(result_data, sender_column):
    """
    Gönderici-GTİP bazında nadir menşe ülke analizi için HTML rapor oluşturur
    """
    if not result_data:
        return "<p>Analiz sonucunda herhangi bir risk tespit edilmedi.</p>"
    
    html = """
    <div style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 20px;">
        <h2 style="color: #d32f2f; border-bottom: 2px solid #d32f2f; padding-bottom: 10px;">
            🔍 Gönderici-GTİP Bazında Nadir Menşe Ülke Analizi
        </h2>
        
        <div style="background: linear-gradient(135deg, #fff3e0 0%, #ffe0b2 100%); 
                    padding: 15px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #ff9800;">
            <h3 style="margin: 0; color: #e65100;">📊 Analiz Özeti</h3>
            <p style="margin: 10px 0 0 0; color: #bf360c;">
                <strong>{} gönderici-GTİP kombinasyonu</strong>nda nadiren kullanılan menşe ülke tespit edildi.
                Bu durum, aynı ürün grubu için farklı menşe ülke tercihlerini gösterebilir.
            </p>
        </div>
    """.format(len(result_data))
    
    # Her gönderici-GTİP kombinasyonu için detay
    for i, item in enumerate(result_data, 1):
        html += f"""
        <div style="background: white; border: 1px solid #e0e0e0; border-radius: 8px; 
                    margin: 15px 0; padding: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
            
            <h3 style="color: #1976d2; margin: 0 0 15px 0; border-bottom: 1px solid #e3f2fd; padding-bottom: 8px;">
                {i}. {item['gonderen']} - {item['gtip']}
            </h3>
            
            <div style="background: #f5f5f5; padding: 10px; border-radius: 5px; margin: 10px 0;">
                <strong>GTİP Tanımı:</strong> {item['gtip_tanimi']}<br>
                <strong>Toplam Beyanname:</strong> {item['toplam_beyanname']} adet<br>
                <strong>Kullanılan Menşe Ülke Sayısı:</strong> {item['toplam_mensei_ulke_sayisi']} adet<br>
                <strong>En Çok Kullanılan:</strong> {item['en_cok_kullanilan_ulke']} 
                ({item['en_cok_kullanilan_ulke_yuzdesi']:.1f}%)
            </div>
            
            <h4 style="color: #d32f2f; margin: 15px 0 10px 0;">⚠️ Nadiren Kullanılan Menşe Ülkeler:</h4>
            <div style="margin-left: 20px;">
        """
        
        for country_info in item['nadir_kullanilan_ulkeler']:
            risk_level = "🔴 Yüksek" if country_info['yuzde'] < 10 else "🟡 Orta"
            
            html += f"""
                <div style="background: #ffebee; border-left: 4px solid #f44336; 
                            padding: 10px; margin: 8px 0; border-radius: 0 5px 5px 0;">
                    <strong style="color: #c62828;">{country_info['ulke']}</strong><br>
                    <span style="color: #666;">
                        Kullanım: {country_info['sayi']} kez ({country_info['yuzde']:.1f}%) | 
                        Risk Seviyesi: {risk_level} | 
                        Ort. Fatura: {country_info['ortalama_fatura_miktari']:,.2f}
                    </span><br>
                    <small style="color: #888;">
                        Örnek Beyannameler: {', '.join(map(str, country_info['ornek_beyannameler']))}
                    </small>
                </div>
            """
        
        html += """
            </div>
        </div>
        """
    
    html += """
        <div style="background: linear-gradient(135deg, #e8f5e8 0%, #c8e6c9 100%); 
                    padding: 15px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #4caf50;">
            <h3 style="margin: 0; color: #2e7d32;">💡 Değerlendirme Kriterleri</h3>
            <ul style="margin: 10px 0 0 20px; color: #388e3c;">
                <li><strong>Eşik Değer:</strong> %20'den az kullanılan menşe ülkeler "nadir" kabul edilir</li>
                <li><strong>Minimum Beyanname:</strong> En az 3 beyanname olmalı</li>
                <li><strong>Risk Faktörleri:</strong> Düşük kullanım oranı + Yüksek fatura miktarı</li>
                <li><strong>Kontrol Önerisi:</strong> Aynı ürün için farklı menşe tercihi sebepleri araştırılmalı</li>
            </ul>
        </div>
    </div>
    """
    
    return html