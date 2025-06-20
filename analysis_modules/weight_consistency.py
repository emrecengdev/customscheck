"""
Ağırlık tutarlılık analiz modülü.
Bu modül, ağırlık verilerinin tutarlılığını kontrol eder.
"""

import pandas as pd

def check_weight_consistency(df):
    """
    Brüt ağırlık >= Net ağırlık kontrolü yapar
    
    Args:
        df (pandas.DataFrame): Kontrol edilecek DataFrame
    
    Returns:
        dict: Kontrol sonuçları
    """
    # Ağırlık sütunlarını belirle
    weight_columns = {
        'brut': None,
        'net': None
    }
    
    # Brüt ağırlık sütununu bul
    brut_weight_options = ['Brut_agirlik', 'Brut_Agirlik', 'Brut_Weight', 'brut_agirlik', 'Brüt_Ağırlık']
    for col in brut_weight_options:
        if col in df.columns:
            weight_columns['brut'] = col
            break
    
    # Net ağırlık sütununu bul
    net_weight_options = ['Net_agirlik', 'Net_Agirlik', 'Net_Weight', 'net_agirlik', 'Net_Ağırlık']
    for col in net_weight_options:
        if col in df.columns:
            weight_columns['net'] = col
            break
    
    # Her iki sütun da yoksa hata döndür
    if not weight_columns['brut'] or not weight_columns['net']:
        missing_columns = []
        if not weight_columns['brut']:
            missing_columns.append('Brüt ağırlık')
        if not weight_columns['net']:
            missing_columns.append('Net ağırlık')
        
        return {
            "status": "error",
            "message": f"Gerekli ağırlık sütunları bulunamadı: {', '.join(missing_columns)}"
        }
    
    brut_col = weight_columns['brut']
    net_col = weight_columns['net']
    
    try:
        # Sayısal değere dönüştür
        df_copy = df.copy()
        df_copy[brut_col] = pd.to_numeric(df_copy[brut_col], errors='coerce')
        df_copy[net_col] = pd.to_numeric(df_copy[net_col], errors='coerce')
        
        # Boş olmayan değerleri filtrele
        valid_data = df_copy[(df_copy[brut_col].notna()) & (df_copy[net_col].notna())]
        
        if len(valid_data) == 0:
            return {
                "status": "error",
                "message": "Geçerli ağırlık verisi bulunamadı"
            }
        
        # Tutarsız kayıtları bul (Brüt < Net)
        inconsistent = valid_data[valid_data[brut_col] < valid_data[net_col]]
        
        if len(inconsistent) == 0:
            return {
                "status": "ok",
                "message": "Tüm ağırlık verileri tutarlı"
            }
        else:
            # Tutarsız kayıtları detaylandır
            inconsistent_details = inconsistent[[brut_col, net_col]].copy()
            inconsistent_details['Fark'] = inconsistent_details[net_col] - inconsistent_details[brut_col]
            
            # Diğer önemli sütunları da ekle
            for col in ['Beyanname_no', 'Kalem_No', 'Gtip', 'Ticari_tanimi']:
                if col in inconsistent.columns:
                    inconsistent_details[col] = inconsistent[col]
            
            return {
                "status": "warning",
                "message": f"{len(inconsistent)} kayıtta ağırlık tutarsızlığı bulundu",
                "inconsistent_rows": inconsistent_details,
                "total_rows": len(valid_data),
                "inconsistent_percentage": round((len(inconsistent) / len(valid_data)) * 100, 2)
            }
    
    except Exception as e:
        return {
            "status": "error",
            "message": f"Ağırlık kontrolü sırasında hata: {str(e)}"
        } 