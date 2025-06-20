"""
Temel veri kontrol fonksiyonları modülü.
Bu modül, veri kalitesi ve temel kontroller için kullanılan fonksiyonları içerir.
"""

import pandas as pd
import numpy as np

def calculate_basic_stats(df):
    """
    DataFrame için temel istatistikleri hesaplar
    
    Args:
        df (pandas.DataFrame): Analiz edilecek DataFrame
    
    Returns:
        dict: Temel istatistikler
    """
    if df is None or df.empty:
        return {"error": "Boş veya geçersiz DataFrame"}
    
    stats = {
        "toplam_satir": len(df),
        "toplam_sutun": len(df.columns),
        "bellek_kullanimi_mb": round(df.memory_usage(deep=True).sum() / 1024**2, 2)
    }
    
    # Sayısal sütunlar için istatistikler
    numeric_columns = df.select_dtypes(include=[np.number]).columns
    if len(numeric_columns) > 0:
        stats["sayisal_sutunlar"] = len(numeric_columns)
        stats["sayisal_istatistikler"] = df[numeric_columns].describe().to_dict()
    
    # Kategorik sütunlar için istatistikler
    categorical_columns = df.select_dtypes(include=['object', 'category']).columns
    if len(categorical_columns) > 0:
        stats["kategorik_sutunlar"] = len(categorical_columns)
        stats["kategorik_istatistikler"] = {}
        
        for col in categorical_columns:
            try:
                unique_count = df[col].nunique()
                most_common = df[col].value_counts().head(1)
                stats["kategorik_istatistikler"][col] = {
                    "benzersiz_deger_sayisi": unique_count,
                    "en_sik_deger": most_common.index[0] if len(most_common) > 0 else None,
                    "en_sik_deger_frekansi": most_common.iloc[0] if len(most_common) > 0 else 0
                }
            except Exception as e:
                stats["kategorik_istatistikler"][col] = {"hata": str(e)}
    
    return stats

def check_missing_values(df):
    """
    DataFrame'deki eksik değerleri kontrol eder
    
    Args:
        df (pandas.DataFrame): Kontrol edilecek DataFrame
    
    Returns:
        pandas.DataFrame: Eksik değer istatistikleri
    """
    if df is None or df.empty:
        return pd.DataFrame()
    
    missing_stats = []
    
    for column in df.columns:
        missing_count = df[column].isnull().sum()
        missing_percentage = (missing_count / len(df)) * 100
        
        if missing_count > 0:
            missing_stats.append({
                'Sütun': column,
                'Eksik_Değer_Sayısı': missing_count,
                'Eksik_Değer_Yüzdesi': round(missing_percentage, 2),
                'Veri_Tipi': str(df[column].dtype)
            })
    
    return pd.DataFrame(missing_stats).sort_values('Eksik_Değer_Sayısı', ascending=False)

def check_duplicate_rows(df):
    """
    DataFrame'deki tekrarlanan satırları kontrol eder
    
    Args:
        df (pandas.DataFrame): Kontrol edilecek DataFrame
    
    Returns:
        dict: Tekrarlanan satır istatistikleri
    """
    if df is None or df.empty:
        return {"duplicate_rows_all": 0, "duplicate_rows_subset": 0}
    
    # Tüm sütunlar için tekrarlanan satırlar
    duplicate_all = df.duplicated().sum()
    
    # Önemli sütunlar için tekrarlanan satırlar (varsa)
    important_columns = []
    
    # Beyanname numarası gibi önemli sütunları bul
    for col in ['Beyanname_no', 'Beyanname_No', 'beyanname_no']:
        if col in df.columns:
            important_columns.append(col)
            break
    
    # Kalem numarası ekle
    for col in ['Kalem_No', 'Kalem_no', 'kalem_no']:
        if col in df.columns:
            important_columns.append(col)
            break
    
    duplicate_subset = 0
    if important_columns:
        duplicate_subset = df.duplicated(subset=important_columns).sum()
    
    return {
        "duplicate_rows_all": duplicate_all,
        "duplicate_rows_subset": duplicate_subset,
        "important_columns": important_columns
    }

def check_value_consistency(df, column_name):
    """
    Belirli bir sütundaki değerlerin tutarlılığını kontrol eder
    
    Args:
        df (pandas.DataFrame): Kontrol edilecek DataFrame
        column_name (str): Kontrol edilecek sütun adı
    
    Returns:
        dict: Tutarlılık istatistikleri
    """
    if df is None or df.empty or column_name not in df.columns:
        return {"error": f"Sütun '{column_name}' bulunamadı"}
    
    column_data = df[column_name]
    
    # Boş olmayan değerleri al
    non_null_data = column_data.dropna()
    
    if len(non_null_data) == 0:
        return {"error": "Sütunda geçerli veri yok"}
    
    result = {
        "toplam_deger": len(column_data),
        "gecerli_deger": len(non_null_data),
        "benzersiz_deger": non_null_data.nunique(),
        "en_sik_degerler": non_null_data.value_counts().head(10).to_dict()
    }
    
    # Sayısal sütunlar için ek istatistikler
    if pd.api.types.is_numeric_dtype(non_null_data):
        result.update({
            "minimum": non_null_data.min(),
            "maksimum": non_null_data.max(),
            "ortalama": round(non_null_data.mean(), 2),
            "standart_sapma": round(non_null_data.std(), 2)
        })
        
        # Aykırı değerleri tespit et (IQR yöntemi)
        Q1 = non_null_data.quantile(0.25)
        Q3 = non_null_data.quantile(0.75)
        IQR = Q3 - Q1
        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR
        
        outliers = non_null_data[(non_null_data < lower_bound) | (non_null_data > upper_bound)]
        result["aykiri_deger_sayisi"] = len(outliers)
        
        if len(outliers) > 0:
            result["aykiri_degerler_ornegi"] = outliers.head(10).tolist()
    
    return result

def check_numeric_range(df, column_name, min_value=None, max_value=None):
    """
    Sayısal sütun değerlerinin belirli aralıkta olup olmadığını kontrol eder
    
    Args:
        df (pandas.DataFrame): Kontrol edilecek DataFrame
        column_name (str): Kontrol edilecek sütun adı
        min_value (float, optional): Minimum değer
        max_value (float, optional): Maksimum değer
    
    Returns:
        dict: Aralık kontrol sonuçları
    """
    if df is None or df.empty or column_name not in df.columns:
        return {"error": f"Sütun '{column_name}' bulunamadı"}
    
    column_data = df[column_name].dropna()
    
    if not pd.api.types.is_numeric_dtype(column_data):
        return {"error": f"Sütun '{column_name}' sayısal değil"}
    
    if len(column_data) == 0:
        return {"error": "Sütunda geçerli sayısal veri yok"}
    
    result = {
        "toplam_deger": len(column_data),
        "gecerli_araliktaki_deger": len(column_data)
    }
    
    # Minimum değer kontrolü
    if min_value is not None:
        below_min = column_data < min_value
        result["minimum_altindaki_deger"] = below_min.sum()
        result["gecerli_araliktaki_deger"] -= below_min.sum()
        
        if below_min.any():
            result["minimum_altindaki_ornekler"] = column_data[below_min].head(10).tolist()
    
    # Maksimum değer kontrolü
    if max_value is not None:
        above_max = column_data > max_value
        result["maksimum_ustundeki_deger"] = above_max.sum()
        result["gecerli_araliktaki_deger"] -= above_max.sum()
        
        if above_max.any():
            result["maksimum_ustundeki_ornekler"] = column_data[above_max].head(10).tolist()
    
    # Yüzde hesapla
    result["gecerli_araliktaki_yuzde"] = round(
        (result["gecerli_araliktaki_deger"] / result["toplam_deger"]) * 100, 2
    )
    
    return result

def check_data_types(df):
    """
    DataFrame'deki veri tiplerini kontrol eder ve önerilerde bulunur
    
    Args:
        df (pandas.DataFrame): Kontrol edilecek DataFrame
    
    Returns:
        dict: Veri tipi analizi
    """
    if df is None or df.empty:
        return {"error": "Boş veya geçersiz DataFrame"}
    
    type_analysis = {
        "sutun_sayisi": len(df.columns),
        "veri_tipleri": {},
        "oneriler": []
    }
    
    for column in df.columns:
        col_dtype = str(df[column].dtype)
        non_null_count = df[column].count()
        unique_count = df[column].nunique()
        
        type_analysis["veri_tipleri"][column] = {
            "mevcut_tip": col_dtype,
            "gecerli_deger_sayisi": non_null_count,
            "benzersiz_deger_sayisi": unique_count
        }
        
        # Veri tipi önerileri
        if col_dtype == 'object':
            # String sütunun sayısal olup olmadığını kontrol et
            try:
                pd.to_numeric(df[column].dropna(), errors='raise')
                type_analysis["oneriler"].append({
                    "sutun": column,
                    "oneri": "Bu sütun sayısal veriye dönüştürülebilir",
                    "onerilen_tip": "numeric"
                })
            except (ValueError, TypeError):
                pass
            
            # Tarih formatında olup olmadığını kontrol et
            if any(keyword in column.lower() for keyword in ['tarih', 'date', 'time']):
                try:
                    pd.to_datetime(df[column].dropna().iloc[:100], errors='raise')
                    type_analysis["oneriler"].append({
                        "sutun": column,
                        "oneri": "Bu sütun tarih tipine dönüştürülebilir",
                        "onerilen_tip": "datetime"
                    })
                except (ValueError, TypeError):
                    pass
            
            # Kategori tipine dönüştürülüp dönüştürülemeyeceğini kontrol et
            if unique_count < len(df) * 0.5:  # Benzersiz değer sayısı toplam satır sayısının %50'sinden azsa
                type_analysis["oneriler"].append({
                    "sutun": column,
                    "oneri": f"Bu sütun kategori tipine dönüştürülebilir (bellek tasarrufu sağlar)",
                    "onerilen_tip": "category",
                    "benzersiz_oran": round((unique_count / len(df)) * 100, 2)
                })
    
    return type_analysis

def check_column_name_consistency(df):
    """
    Sütun adlarının tutarlılığını kontrol eder
    
    Args:
        df (pandas.DataFrame): Kontrol edilecek DataFrame
    
    Returns:
        dict: Sütun adı analizi
    """
    if df is None or df.empty:
        return {"error": "Boş veya geçersiz DataFrame"}
    
    columns = df.columns.tolist()
    
    analysis = {
        "toplam_sutun": len(columns),
        "sorunlu_sutunlar": [],
        "oneriler": []
    }
    
    for col in columns:
        issues = []
        
        # Boşluk kontrolü
        if ' ' in col:
            issues.append("Sütun adında boşluk var")
        
        # Büyük harf kontrolü
        if col != col.lower():
            issues.append("Sütun adında büyük harf var")
        
        # Özel karakter kontrolü
        special_chars = set(col) - set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_')
        if special_chars:
            issues.append(f"Özel karakterler: {', '.join(special_chars)}")
        
        # Sayı ile başlama kontrolü
        if col[0].isdigit():
            issues.append("Sütun adı sayı ile başlıyor")
        
        if issues:
            analysis["sorunlu_sutunlar"].append({
                "sutun": col,
                "sorunlar": issues,
                "onerilen_ad": col.lower().replace(' ', '_').replace('-', '_')
            })
    
    # Genel öneriler
    if analysis["sorunlu_sutunlar"]:
        analysis["oneriler"] = [
            "Sütun adlarını küçük harfe dönüştürün",
            "Boşlukları alt çizgi (_) ile değiştirin",
            "Özel karakterleri kaldırın veya değiştirin",
            "Sütun adlarının harf ile başlamasını sağlayın"
        ]
    
    return analysis 