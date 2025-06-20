"""
Ağırlık tutarlılık analiz modülü.
Net ağırlık ve brüt ağırlık tutarlılığını kontrol eder (Brut_agirlik >= Net_agirlik).
"""

import pandas as pd

def kontrol_agirlik_tutarlilik(df):
    """
    Net ağırlık ve brüt ağırlık tutarlılığını kontrol eder.
    Her zaman brüt ağırlık >= net ağırlık olmalıdır.
    
    Args:
        df (pandas.DataFrame): Beyanname verileri içeren DataFrame
    
    Returns:
        dict: Analiz sonuçları
    """
    # Gerekli sütunların varlığını kontrol et
    required_columns = ['Net_agirlik', 'Brut_agirlik']
    missing_columns = [col for col in required_columns if col not in df.columns]
    
    if missing_columns:
        return {
            "status": "error",
            "message": f"Gerekli sütunlar eksik: {', '.join(missing_columns)}"
        }
    
    # Net_agirlik ve Brut_agirlik sütunlarını sayısal değere dönüştür
    df['Net_agirlik_numeric'] = pd.to_numeric(df['Net_agirlik'], errors='coerce')
    df['Brut_agirlik_numeric'] = pd.to_numeric(df['Brut_agirlik'], errors='coerce')
    
    # Sayısal değere dönüştürülemeyen değerleri filtrele
    valid_data = df.dropna(subset=['Net_agirlik_numeric', 'Brut_agirlik_numeric'])
    
    # Tutarsız kayıtları bul (Brut_agirlik < Net_agirlik)
    inconsistent_rows = valid_data[valid_data['Brut_agirlik_numeric'] < valid_data['Net_agirlik_numeric']]
    
    # Sonuç nesnesini oluştur
    if len(inconsistent_rows) > 0:
        return {
            "status": "warning",
            "message": f"{len(inconsistent_rows)} adet kayıtta brüt ağırlık net ağırlıktan küçük",
            "inconsistent_rows": inconsistent_rows
        }
    else:
        return {
            "status": "ok",
            "message": "Tüm kayıtlarda brüt ağırlık >= net ağırlık"
        }

# İngilizce fonksiyon ismini Türkçe isimle uyumlu hale getirmek için takma ad (alias)
check_weight_consistency = kontrol_agirlik_tutarlilik 