import pandas as pd
import numpy as np
import os

def check_tedarikci_beyan_kontrol(df):
    """
    Tedarikçi Beyan Kontrol analizi yapar.
    
    1. AT seçilenleri bulur (Uluslararasi_anlasma = 'AT')
    2. AT ülkeleri dışındaki menşe ülkeleri filtreler
    3. Tedarikçi beyanı GTIP listesi ile karşılaştırır
    4. IGV ödenmeyenleri bulur (kod 59, miktar 0)
    5. Tedarikçi beyanı varlığını kontrol eder (kod 0819)
    """
    
    try:
        # Tedarikçi beyanı listesini yükle
        tedarikci_file_path = 'VERGİLER/tedarikci beyanı.xlsx'
        if not os.path.exists(tedarikci_file_path):
            return {
                'success': False,
                'message': 'tedarikci beyanı.xlsx dosyası bulunamadı. VERGİLER klasöründe olmalı.',
                'data': pd.DataFrame()
            }
        
        tedarikci_df = pd.read_excel(tedarikci_file_path)
        
        # Tedarikçi beyanı GTIP kodlarını al (A sütunu)
        tedarikci_gtips = set(tedarikci_df.iloc[:, 0].dropna().astype(str))
        print(f"Tedarikçi beyanı listesinde {len(tedarikci_gtips)} GTIP kodu bulundu")
        
        # Sistemdeki gerekli sütunları kontrol et
        required_cols = ['Uluslararasi_anlasma', 'Mensei_ulke', 'Gtip']
        missing_cols = [col for col in required_cols if col not in df.columns]
        
        if missing_cols:
            return {
                'success': False,
                'message': f'Gerekli sütunlar bulunamadı: {missing_cols}',
                'data': pd.DataFrame()
            }
        
        # 1. AT seçilenleri bul
        at_records = df[df['Uluslararasi_anlasma'].astype(str).str.upper() == 'AT'].copy()
        
        if at_records.empty:
            return {
                'success': True,
                'message': 'AT seçili kayıt bulunamadı',
                'data': pd.DataFrame()
            }
        
        print(f"AT seçili {len(at_records)} kayıt bulundu")
        
        # 2. AT ülkeleri listesi
        at_countries = {
            '004', '038', '017', '068', '061', '008', '053', '032', '001', '092', 
            '003', '007', '011', '030', '005', '054', '055', '018', '064', '046', 
            '060', '010', '066', '063', '091', '093', '052'
        }
        
        # AT ülkeleri dışındaki menşe ülkeleri filtrele
        at_records['Mensei_ulke_str'] = at_records['Mensei_ulke'].astype(str)
        non_at_countries = at_records[~at_records['Mensei_ulke_str'].isin(at_countries)].copy()
        
        if non_at_countries.empty:
            return {
                'success': True,
                'message': 'AT seçili ama AT dışı menşe ülkeli kayıt bulunamadı',
                'data': pd.DataFrame()
            }
        
        print(f"AT seçili ama AT dışı menşe ülkeli {len(non_at_countries)} kayıt bulundu")
        
        # 3. Tedarikçi beyanı GTIP listesi ile karşılaştır
        non_at_countries['Gtip_str'] = non_at_countries['Gtip'].astype(str)
        tedarikci_gtip_matches = non_at_countries[non_at_countries['Gtip_str'].isin(tedarikci_gtips)].copy()
        
        if tedarikci_gtip_matches.empty:
            return {
                'success': True,
                'message': 'Tedarikçi beyanı GTIP listesinde eşleşen kayıt bulunamadı',
                'data': pd.DataFrame()
            }
        
        print(f"Tedarikçi beyanı GTIP listesinde {len(tedarikci_gtip_matches)} eşleşme bulundu")
        
        # Vergi ve doküman sütunlarını bul
        vergi_kod_cols = [col for col in df.columns if 'Vergi_' in col and '_Kod' in col]
        vergi_miktar_cols = [col for col in df.columns if 'Vergi_' in col and '_Miktar' in col]
        dokuman_kod_cols = [col for col in df.columns if 'Dokuman_' in col and '_Kod' in col]
        dokuman_referans_cols = [col for col in df.columns if 'Dokuman_' in col and '_Referans' in col]
        
        results = []
        
        for idx, row in tedarikci_gtip_matches.iterrows():
            try:
                # 4. IGV ödenmeyenleri bul (kod 59, miktar 0)
                igv_paid = False
                igv_amount = None
                igv_column = None
                
                for i, kod_col in enumerate(vergi_kod_cols):
                    if pd.notna(row[kod_col]) and str(row[kod_col]) == '59':
                        # IGV kodu bulundu, miktar sütununu kontrol et
                        miktar_col = kod_col.replace('_Kod', '_Miktar')
                        if miktar_col in df.columns:
                            try:
                                igv_amount = pd.to_numeric(row[miktar_col], errors='coerce')
                                igv_column = miktar_col
                                if pd.notna(igv_amount) and igv_amount > 0:
                                    igv_paid = True
                                break
                            except:
                                continue
                
                # 5. Tedarikçi beyanı var mı kontrol et (kod 0819)
                tedarikci_beyan_var = False
                tedarikci_beyan_referans = None
                tedarikci_beyan_column = None
                
                for i, dok_kod_col in enumerate(dokuman_kod_cols):
                    if pd.notna(row[dok_kod_col]) and str(row[dok_kod_col]) == '0819':
                        # Tedarikçi beyanı kodu bulundu, referans sütununu kontrol et
                        referans_col = dok_kod_col.replace('_Kod', '_Referans')
                        if referans_col in df.columns:
                            tedarikci_beyan_var = True
                            tedarikci_beyan_referans = row[referans_col]
                            tedarikci_beyan_column = referans_col
                            break
                
                # Sonucu kaydet
                results.append({
                    'Beyanname_no': row.get('Beyanname_no', ''),
                    'Gtip': str(row['Gtip']),
                    'Mensei_ulke': str(row['Mensei_ulke']),
                    'Uluslararasi_anlasma': str(row['Uluslararasi_anlasma']),
                    'IGV_odendi_mi': 'Evet' if igv_paid else 'Hayır',
                    'IGV_miktari': igv_amount if igv_amount is not None else 0,
                    'IGV_sutunu': igv_column,
                    'Tedarikci_beyan_var_mi': 'Evet' if tedarikci_beyan_var else 'Hayır',
                    'Tedarikci_beyan_referans': tedarikci_beyan_referans,
                    'Tedarikci_beyan_sutunu': tedarikci_beyan_column,
                    'Risk_durumu': 'Yüksek Risk' if not igv_paid and not tedarikci_beyan_var else 
                                  'Orta Risk' if not igv_paid or not tedarikci_beyan_var else 'Düşük Risk'
                })
                
            except Exception as e:
                print(f"Satır {idx} işlenirken hata: {e}")
                continue
        
        result_df = pd.DataFrame(results)
        
        if result_df.empty:
            return {
                'success': True,
                'message': 'Analiz edilebilecek kayıt bulunamadı',
                'data': pd.DataFrame()
            }
        
        # Özet istatistikler
        summary_stats = {
            'toplam_kayit': len(result_df),
            'igv_odenmeyenler': len(result_df[result_df['IGV_odendi_mi'] == 'Hayır']),
            'tedarikci_beyan_olmayanlar': len(result_df[result_df['Tedarikci_beyan_var_mi'] == 'Hayır']),
            'yuksek_risk': len(result_df[result_df['Risk_durumu'] == 'Yüksek Risk']),
            'orta_risk': len(result_df[result_df['Risk_durumu'] == 'Orta Risk']),
            'dusuk_risk': len(result_df[result_df['Risk_durumu'] == 'Düşük Risk'])
        }
        
        # Risk durumuna göre sırala
        result_df = result_df.sort_values(['Risk_durumu', 'IGV_miktari'], ascending=[False, True])
        
        return {
            'success': True,
            'message': f'Tedarikçi beyan kontrol analizi tamamlandı. {len(result_df)} kayıt analiz edildi.',
            'data': result_df,
            'summary': summary_stats
        }
        
    except Exception as e:
        return {
            'success': False,
            'message': f'Tedarikçi beyan kontrol analizi sırasında hata oluştu: {str(e)}',
            'data': pd.DataFrame()
        } 