"""
Özet ve pivot tablo fonksiyonları modülü.
Bu modül, veri setinden özet ve pivot tablolar oluşturmak için kullanılan fonksiyonları içerir.
"""

import pandas as pd

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