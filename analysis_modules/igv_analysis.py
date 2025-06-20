import pandas as pd
import numpy as np
import os

def check_igv_consistency(df):
    """
    IGV (İlave Gümrük Vergisi) tutarlılığını kontrol eder.
    
    1. IGV listesindeki GTIP kodlarını sistemdeki GTIP kodlarıyla karşılaştırır
    2. Eşleşen kayıtlarda menşe ülkeye göre IGV oranını bulur
    3. Sistemin hesapladığı IGV ile karşılaştırır
    """
    
    try:
        # IGV listesini yükle
        igv_file_path = 'VERGİLER/İGV.xlsx'
        if not os.path.exists(igv_file_path):
            return {
                'success': False,
                'message': 'IGV.xlsx dosyası bulunamadı. VERGİLER klasöründe olmalı.',
                'data': pd.DataFrame()
            }
        
        igv_df = pd.read_excel(igv_file_path)
        
        # Sütun isimlerini düzenle
        igv_columns = igv_df.columns.tolist()
        
        # GTIP sütunu (A sütunu)
        gtip_col = igv_columns[0]  # 'GİTP'
        
        # Ülke kodları sütunları (C, D, E, F, G, H)
        country_cols = igv_columns[2:8]  # Index 2-7
        
        # Diğer ülkeler sütunu (I sütunu)
        other_countries_col = igv_columns[8] if len(igv_columns) > 8 else None
        
        # Ülke kodlarını parse et
        country_codes = {}
        for i, col in enumerate(country_cols):
            if pd.notna(col) and str(col) != 'nan':
                # Virgülle ayrılmış kodları parse et
                codes = str(col).replace('\n', ',').split(',')
                codes = [code.strip() for code in codes if code.strip()]
                for code in codes:
                    try:
                        country_codes[int(code)] = i + 2  # Sütun indexi
                    except:
                        pass
        
        print(f"Toplam {len(country_codes)} ülke kodu bulundu")
        
        # Sistemdeki gerekli sütunları kontrol et
        required_cols = ['Gtip', 'Mensei_ulke']
        missing_cols = [col for col in required_cols if col not in df.columns]
        
        if missing_cols:
            return {
                'success': False,
                'message': f'Gerekli sütunlar bulunamadı: {missing_cols}',
                'data': pd.DataFrame()
            }
        
        # Vergi sütunlarını bul
        vergi_kod_cols = [col for col in df.columns if 'Vergi_' in col and '_Kod' in col]
        vergi_miktar_cols = [col for col in df.columns if 'Vergi_' in col and '_Miktar' in col]
        vergi_oran_cols = [col for col in df.columns if 'Vergi_' in col and '_Oran' in col]
        vergi_matrahi_cols = [col for col in df.columns if 'Vergi_' in col and '_Vergi_matrahi' in col]
        
        if not vergi_kod_cols:
            return {
                'success': False,
                'message': 'Vergi kod sütunları bulunamadı',
                'data': pd.DataFrame()
            }
        
        # IGV GTIP kodlarını set'e çevir
        igv_gtips = set(igv_df[gtip_col].dropna().astype(str))
        
        # Sistemdeki GTIP kodlarını string'e çevir
        df_copy = df.copy()
        df_copy['Gtip_str'] = df_copy['Gtip'].astype(str)
        
        # IGV'ye tabi kayıtları filtrele
        igv_records = df_copy[df_copy['Gtip_str'].isin(igv_gtips)].copy()
        
        if igv_records.empty:
            return {
                'success': True,
                'message': 'IGV\'ye tabi kayıt bulunamadı',
                'data': pd.DataFrame()
            }
        
        print(f"IGV'ye tabi {len(igv_records)} kayıt bulundu")
        
        results = []
        
        for idx, row in igv_records.iterrows():
            try:
                gtip_code = str(row['Gtip'])
                mensei_ulke = row['Mensei_ulke']
                
                # IGV oranını bul
                igv_row = igv_df[igv_df[gtip_col].astype(str) == gtip_code]
                if igv_row.empty:
                    continue
                
                igv_row = igv_row.iloc[0]
                
                # Menşe ülke koduna göre IGV oranını belirle
                expected_igv_rate = None
                used_column = None
                
                try:
                    mensei_code = int(mensei_ulke)
                    if mensei_code in country_codes:
                        col_idx = country_codes[mensei_code]
                        expected_igv_rate = igv_row.iloc[col_idx]
                        used_column = igv_columns[col_idx]
                    else:
                        # Diğer ülkeler sütununu kullan
                        if other_countries_col:
                            expected_igv_rate = igv_row[other_countries_col]
                            used_column = other_countries_col
                except:
                    # Diğer ülkeler sütununu kullan
                    if other_countries_col:
                        expected_igv_rate = igv_row[other_countries_col]
                        used_column = other_countries_col
                
                if pd.isna(expected_igv_rate):
                    continue
                
                # Sistemin IGV'sini bul (kod 59)
                system_igv_amount = None
                igv_vergi_column = None
                
                for i, kod_col in enumerate(vergi_kod_cols):
                    if pd.notna(row[kod_col]) and str(row[kod_col]) == '59':
                        # Corresponding miktar sütununu bul
                        miktar_col = kod_col.replace('_Kod', '_Miktar')
                        if miktar_col in df.columns:
                            try:
                                # Güvenli sayısal dönüşüm
                                igv_amount = pd.to_numeric(row[miktar_col], errors='coerce')
                                if pd.notna(igv_amount):
                                    system_igv_amount = igv_amount
                                    igv_vergi_column = miktar_col
                                    break
                            except:
                                continue
                
                # Vergi matrahını bul
                vergi_matrahi = None
                for matrahi_col in vergi_matrahi_cols:
                    if pd.notna(row[matrahi_col]):
                        try:
                            # Güvenli sayısal dönüşüm
                            matrahi_value = pd.to_numeric(row[matrahi_col], errors='coerce')
                            if pd.notna(matrahi_value) and matrahi_value > 0:
                                vergi_matrahi = matrahi_value
                                break
                        except:
                            continue
                
                # Beklenen IGV tutarını hesapla
                expected_igv_amount = None
                if vergi_matrahi and expected_igv_rate:
                    try:
                        # IGV oranını güvenli şekilde sayıya çevir
                        igv_rate = pd.to_numeric(expected_igv_rate, errors='coerce')
                        if pd.notna(igv_rate):
                            expected_igv_amount = (vergi_matrahi * igv_rate) / 100
                    except:
                        pass
                
                # Farkı hesapla
                difference = None
                if system_igv_amount is not None and expected_igv_amount is not None:
                    try:
                        # Güvenli sayısal dönüşüm
                        sys_igv = pd.to_numeric(system_igv_amount, errors='coerce')
                        exp_igv = pd.to_numeric(expected_igv_amount, errors='coerce')
                        if pd.notna(sys_igv) and pd.notna(exp_igv):
                            difference = sys_igv - exp_igv
                    except:
                        pass
                
                # Sistemin IGV oranını hesapla
                system_igv_rate = None
                if system_igv_amount is not None and vergi_matrahi and vergi_matrahi > 0:
                    try:
                        sys_igv = pd.to_numeric(system_igv_amount, errors='coerce')
                        if pd.notna(sys_igv):
                            system_igv_rate = (sys_igv / vergi_matrahi) * 100
                    except:
                        pass
                
                results.append({
                    'Beyanname_no': row.get('Beyanname_no', ''),
                    'Gtip': gtip_code,
                    'Mensei_ulke': mensei_ulke,
                    'Vergi_matrahi': vergi_matrahi,
                    'Excel_IGV_orani': expected_igv_rate,
                    'Sistem_IGV_orani': system_igv_rate,
                    'Kullanilan_sutun': used_column,
                    'Beklenen_IGV_tutari': expected_igv_amount,
                    'Sistem_IGV_tutari': system_igv_amount,
                    'IGV_vergi_sutunu': igv_vergi_column,
                    'Fark': difference,
                    'Fark_yuzdesi': (difference / expected_igv_amount * 100) if expected_igv_amount and expected_igv_amount != 0 else None
                })
                
            except Exception as e:
                print(f"Satır {idx} işlenirken hata: {e}")
                continue
        
        result_df = pd.DataFrame(results)
        
        if result_df.empty:
            return {
                'success': True,
                'message': 'IGV hesaplaması yapılabilecek kayıt bulunamadı',
                'data': pd.DataFrame()
            }
        
        # Sonuçları filtrele ve sırala
        result_df = result_df.dropna(subset=['Fark'])
        
        # Önemli farkları belirle (5% üzeri)
        significant_diff = result_df[abs(result_df['Fark_yuzdesi']) > 5] if 'Fark_yuzdesi' in result_df.columns else pd.DataFrame()
        
        summary_stats = {
            'toplam_igv_kayit': len(result_df),
            'onemli_fark_sayisi': len(significant_diff),
            'ortalama_fark': result_df['Fark'].mean() if not result_df.empty else 0,
            'toplam_fark': result_df['Fark'].sum() if not result_df.empty else 0
        }
        
        return {
            'success': True,
            'message': f'IGV analizi tamamlandı. {len(result_df)} kayıt analiz edildi.',
            'data': result_df,
            'summary': summary_stats,
            'significant_differences': significant_diff
        }
        
    except Exception as e:
        return {
            'success': False,
            'message': f'IGV analizi sırasında hata oluştu: {str(e)}',
            'data': pd.DataFrame()
        } 