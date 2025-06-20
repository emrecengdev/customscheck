"""
Yurt İçi Gider Kontrol modülü.
Beyanname bazında yurt içi gider ve brüt ağırlık analizi yapar.
Aynı eşyanın bulunduğu yerde yakın kg'lardaki beyannameleri karşılaştırır.
"""

import pandas as pd
import numpy as np

def check_yurt_ici_gider_kontrol(df):
    """
    Yurt içi gider kontrolü yapar:
    1. Beyanname bazında toplam yurt içi gider alır (bir kere)
    2. Beyanname bazında toplam brüt ağırlık hesaplar
    3. Aynı eşyanın bulunduğu yerde yakın kg'lardaki beyannameleri karşılaştırır
    
    Args:
        df (pandas.DataFrame): Beyanname verileri içeren DataFrame
    
    Returns:
        dict: Analiz sonuçları
    """
    
    # Gerekli sütunları kontrol et
    required_columns = ['Toplam_yurt_ici_harcamalar', 'Brut_agirlik', 'Esyanin_bulundugu_yer', 'Beyanname_no']
    missing_columns = [col for col in required_columns if col not in df.columns]
    
    if missing_columns:
        return {
            "status": "error",
            "message": f"Gerekli sütunlar bulunamadı: {', '.join(missing_columns)}"
        }
    
    # Boş olmayan verileri filtrele
    valid_data = df.dropna(subset=required_columns).copy()
    
    if len(valid_data) == 0:
        return {
            "status": "error",
            "message": "Geçerli veri bulunamadı"
        }
    
    # Sadece "IM" içeren beyannameleri filtrele
    valid_data = valid_data[valid_data['Beyanname_no'].astype(str).str.contains('IM', case=False, na=False)]
    
    if len(valid_data) == 0:
        return {
            "status": "ok",
            "message": "IM içeren beyanname bulunamadı"
        }
    
    # Sayısal değerlere çevir
    valid_data['Toplam_yurt_ici_harcamalar'] = pd.to_numeric(valid_data['Toplam_yurt_ici_harcamalar'], errors='coerce')
    valid_data['Brut_agirlik'] = pd.to_numeric(valid_data['Brut_agirlik'], errors='coerce')
    
    # Sayısal olmayan değerleri çıkar
    valid_data = valid_data.dropna(subset=['Toplam_yurt_ici_harcamalar', 'Brut_agirlik'])
    
    if len(valid_data) == 0:
        return {
            "status": "error",
            "message": "Geçerli sayısal veri bulunamadı"
        }
    
    # 1. Beyanname bazında toplam yurt içi gider (bir kere al)
    # Her beyannamede birden fazla kalem olabilir, ama toplam gider aynı yazılır
    beyanname_gider = valid_data.groupby('Beyanname_no')['Toplam_yurt_ici_harcamalar'].first().reset_index()
    
    # 2. Beyanname bazında toplam brüt ağırlık hesapla
    beyanname_agirlik = valid_data.groupby('Beyanname_no')['Brut_agirlik'].sum().reset_index()
    
    # Beyanname bazında veriyi birleştir
    beyanname_data = pd.merge(beyanname_gider, beyanname_agirlik, on='Beyanname_no')
    
    # Eşyanın bulunduğu yer bilgisini ekle (ilk kaydı al)
    beyanname_yer = valid_data.groupby('Beyanname_no')['Esyanin_bulundugu_yer'].first().reset_index()
    beyanname_data = pd.merge(beyanname_data, beyanname_yer, on='Beyanname_no')
    
    # Firma bilgisini ekle
    firma_sutunlari = ['Adi_unvani', 'Gonderen', 'Gonderen_adi', 'Ithalatci']
    for firma_sutun in firma_sutunlari:
        if firma_sutun in valid_data.columns:
            beyanname_firma = valid_data.groupby('Beyanname_no')[firma_sutun].first().reset_index()
            beyanname_data = pd.merge(beyanname_data, beyanname_firma, on='Beyanname_no')
            break
    
    # Tarih bilgisini ekle
    tarih_sutunlari = ['Tescil_tarihi', 'Beyanname_tarihi', 'Tarih']
    for tarih_sutun in tarih_sutunlari:
        if tarih_sutun in valid_data.columns:
            beyanname_tarih = valid_data.groupby('Beyanname_no')[tarih_sutun].first().reset_index()
            beyanname_data = pd.merge(beyanname_data, beyanname_tarih, on='Beyanname_no')
            break
    
    # Birim gider hesapla (gider/kg)
    beyanname_data['Birim_Gider'] = beyanname_data['Toplam_yurt_ici_harcamalar'] / beyanname_data['Brut_agirlik']
    beyanname_data['Birim_Gider'] = beyanname_data['Birim_Gider'].replace([np.inf, -np.inf], np.nan)
    beyanname_data = beyanname_data.dropna(subset=['Birim_Gider'])
    
    if len(beyanname_data) == 0:
        return {
            "status": "error",
            "message": "Birim gider hesaplanamadı"
        }
    
    # 3. Aynı eşyanın bulunduğu yerde yakın kg'lardaki beyannameleri karşılaştır
    sonuc_verileri = []
    
    # Her eşyanın bulunduğu yer için analiz
    for yer in beyanname_data['Esyanin_bulundugu_yer'].unique():
        yer_data = beyanname_data[beyanname_data['Esyanin_bulundugu_yer'] == yer].copy()
        
        if len(yer_data) < 2:
            continue
        
        # Ağırlığa göre sırala
        yer_data = yer_data.sort_values('Brut_agirlik')
        
        # Her beyanname için yakın ağırlıktaki diğer beyannameleri bul
        for i, row in yer_data.iterrows():
            current_kg = row['Brut_agirlik']
            current_gider = row['Birim_Gider']
            current_beyanname = row['Beyanname_no']
            
            # Yakın ağırlıktaki beyannameleri bul (±%30 tolerans)
            tolerance = 0.30
            min_kg = current_kg * (1 - tolerance)
            max_kg = current_kg * (1 + tolerance)
            
            yakin_beyannameler = yer_data[
                (yer_data['Brut_agirlik'] >= min_kg) & 
                (yer_data['Brut_agirlik'] <= max_kg) &
                (yer_data['Beyanname_no'] != current_beyanname)
            ]
            
            if len(yakin_beyannameler) == 0:
                continue
            
            # Yakın beyannamelerin birim giderlerini karşılaştır
            for j, yakin_row in yakin_beyannameler.iterrows():
                yakin_gider = yakin_row['Birim_Gider']
                yakin_beyanname = yakin_row['Beyanname_no']
                yakin_kg = yakin_row['Brut_agirlik']
                
                # Gider farkını hesapla
                if current_gider > 0:
                    fark_yuzdesi = abs(current_gider - yakin_gider) / current_gider * 100
                else:
                    continue
                
                # %50'den fazla fark varsa kaydet
                if fark_yuzdesi > 50:
                    sonuc_satiri = {
                        'Esyanin_Bulundugu_Yer': yer,
                        'Beyanname_1': current_beyanname,
                        'Brut_Agirlik_1': current_kg,
                        'Toplam_Gider_1': row['Toplam_yurt_ici_harcamalar'],
                        'Birim_Gider_1': current_gider,
                        'Beyanname_2': yakin_beyanname,
                        'Brut_Agirlik_2': yakin_kg,
                        'Toplam_Gider_2': yakin_row['Toplam_yurt_ici_harcamalar'],
                        'Birim_Gider_2': yakin_gider,
                        'Fark_Yuzdesi': fark_yuzdesi,
                        'Agirlik_Farki': abs(current_kg - yakin_kg),
                        'Gider_Farki': abs(row['Toplam_yurt_ici_harcamalar'] - yakin_row['Toplam_yurt_ici_harcamalar'])
                    }
                    
                    # Firma bilgisi varsa ekle
                    for firma_sutun in firma_sutunlari:
                        if firma_sutun in row:
                            sonuc_satiri['Firma_1'] = row[firma_sutun]
                            sonuc_satiri['Firma_2'] = yakin_row[firma_sutun]
                            break
                    
                    # Tarih bilgisi varsa ekle
                    for tarih_sutun in tarih_sutunlari:
                        if tarih_sutun in row:
                            sonuc_satiri['Tarih_1'] = row[tarih_sutun]
                            sonuc_satiri['Tarih_2'] = yakin_row[tarih_sutun]
                            break
                    
                    sonuc_verileri.append(sonuc_satiri)
    
    if len(sonuc_verileri) == 0:
        return {
            "status": "ok",
            "message": "Aynı eşyanın bulunduğu yerde yakın ağırlıklardaki beyannamelerde %50'den fazla gider farkı bulunamadı"
        }
    
    # Sonuçları DataFrame'e çevir
    sonuc_df = pd.DataFrame(sonuc_verileri)
    
    # Fark yüzdesine göre sırala
    sonuc_df = sonuc_df.sort_values('Fark_Yuzdesi', ascending=False)
    
    # Özet tablosu oluştur
    ozet_verileri = []
    
    # Eşyanın bulunduğu yer bazında özet
    for yer in sonuc_df['Esyanin_Bulundugu_Yer'].unique():
        yer_sonuclari = sonuc_df[sonuc_df['Esyanin_Bulundugu_Yer'] == yer]
        
        ozet_verileri.append({
            'Esyanin_Bulundugu_Yer': yer,
            'Farkli_Gider_Sayisi': len(yer_sonuclari),
            'Ortalama_Fark_Yuzdesi': yer_sonuclari['Fark_Yuzdesi'].mean(),
            'Maksimum_Fark_Yuzdesi': yer_sonuclari['Fark_Yuzdesi'].max(),
            'Etkilenen_Beyanname_Sayisi': len(set(yer_sonuclari['Beyanname_1'].tolist() + yer_sonuclari['Beyanname_2'].tolist()))
        })
    
    ozet_df = pd.DataFrame(ozet_verileri)
    
    # HTML rapor oluştur
    html_rapor = _html_rapor_olustur(sonuc_df, ozet_df, beyanname_data)
    
    # Sonuç mesajı
    mesaj = f"{len(sonuc_verileri)} beyanname çiftinde %50'den fazla yurt içi gider farkı tespit edildi. "
    mesaj += f"{len(ozet_df)} farklı eşya bulunduğu yerde sorun var."
    
    return {
        "status": "warning",
        "message": mesaj,
        "data": sonuc_df,
        "summary": ozet_df,
        "html_report": html_rapor
    }

def _html_rapor_olustur(sonuc_df, ozet_df, beyanname_data):
    """
    Yurt içi gider kontrol için HTML rapor oluşturur
    """
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
    .ozet-kutu {
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
    .yuksek-fark {
        background-color: #ffebee;
        color: #c62828;
        font-weight: bold;
    }
    .orta-fark {
        background-color: #fff8e1;
        color: #f57c00;
        font-weight: bold;
    }
    .yer-bolum {
        margin-top: 30px;
        padding-top: 10px;
        border-top: 1px dashed #ccc;
    }
    .istatistik-kutu {
        display: inline-block;
        margin-right: 15px;
        padding: 10px 15px;
        background-color: #e3f2fd;
        border-radius: 4px;
        border-left: 4px solid #2196f3;
    }
    .karsilastirma-kutu {
        background-color: #f5f5f5;
        border: 1px solid #ddd;
        border-radius: 4px;
        padding: 10px;
        margin: 10px 0;
    }
    </style>
    
    <h2>Yurt İçi Gider Kontrol Analiz Raporu</h2>
    
    <div class="ozet-kutu">
        <h3>Kontrol Özeti</h3>
        <p>Bu kontrol, aynı <strong>eşyanın bulunduğu yerde</strong> yakın ağırlıklardaki <strong>IM içeren beyannamelerin</strong> yurt içi gider farklarını analiz eder.</p>
        <p><strong>Kontrol Kriterleri:</strong></p>
        <ul>
            <li>Sadece beyanname numarasında "IM" içeren beyannameler analiz edilir</li>
            <li>Beyanname bazında toplam yurt içi gider alınır (bir kere)</li>
            <li>Beyanname bazında toplam brüt ağırlık hesaplanır</li>
            <li>Aynı eşyanın bulunduğu yerde ±%30 ağırlık toleransındaki beyannameler karşılaştırılır</li>
            <li>%50'den fazla birim gider farkı olan durumlar tespit edilir</li>
        </ul>
    </div>
    """
    
    # Genel istatistikler
    html += f"""
    <h3>Genel İstatistikler</h3>
    <div>
        <div class="istatistik-kutu">
            <strong>Toplam Beyanname:</strong> {len(beyanname_data)}
        </div>
        <div class="istatistik-kutu">
            <strong>Farklı Eşya Yeri:</strong> {beyanname_data['Esyanin_bulundugu_yer'].nunique()}
        </div>
        <div class="istatistik-kutu">
            <strong>Sorunlu Karşılaştırma:</strong> {len(sonuc_df)}
        </div>
        <div class="istatistik-kutu">
            <strong>Ortalama Fark:</strong> {sonuc_df['Fark_Yuzdesi'].mean():.1f}%
        </div>
    </div>
    """
    
    # Özet tablosunu ekle
    html += "<h3>Eşya Yeri Bazında Özet</h3>"
    html += ozet_df.to_html(index=False, classes="table table-striped", escape=False)
    
    # Detaylı sonuçlar
    if not sonuc_df.empty:
        html += "<h3>Detaylı Gider Farkları</h3>"
        
        # Eşya yeri bazında grupla
        yer_gruplari = sonuc_df.groupby('Esyanin_Bulundugu_Yer')
        
        for yer, yer_verileri in yer_gruplari:
            html += f'<div class="yer-bolum"><h4>Eşyanın Bulunduğu Yer: {yer}</h4>'
            
            # En yüksek farkları göster (ilk 10)
            en_yuksek_farklar = yer_verileri.head(10)
            
            for _, row in en_yuksek_farklar.iterrows():
                fark_class = "yuksek-fark" if row['Fark_Yuzdesi'] > 100 else "orta-fark"
                
                html += f"""
                <div class="karsilastirma-kutu">
                    <h5>Beyanname Karşılaştırması - <span class="{fark_class}">%{row['Fark_Yuzdesi']:.1f} Fark</span></h5>
                    <table style="margin-bottom: 10px;">
                        <tr>
                            <th>Özellik</th>
                            <th>Beyanname 1</th>
                            <th>Beyanname 2</th>
                            <th>Fark</th>
                        </tr>
                        <tr>
                            <td><strong>Beyanname No</strong></td>
                            <td>{row['Beyanname_1']}</td>
                            <td>{row['Beyanname_2']}</td>
                            <td>-</td>
                        </tr>
                        <tr>
                            <td><strong>Brüt Ağırlık (kg)</strong></td>
                            <td>{row['Brut_Agirlik_1']:,.2f}</td>
                            <td>{row['Brut_Agirlik_2']:,.2f}</td>
                            <td>{row['Agirlik_Farki']:,.2f} kg</td>
                        </tr>
                        <tr>
                            <td><strong>Toplam Gider</strong></td>
                            <td>{row['Toplam_Gider_1']:,.2f}</td>
                            <td>{row['Toplam_Gider_2']:,.2f}</td>
                            <td>{row['Gider_Farki']:,.2f}</td>
                        </tr>
                        <tr>
                            <td><strong>Birim Gider (TL/kg)</strong></td>
                            <td>{row['Birim_Gider_1']:,.2f}</td>
                            <td>{row['Birim_Gider_2']:,.2f}</td>
                            <td class="{fark_class}">%{row['Fark_Yuzdesi']:.1f}</td>
                        </tr>
                """
                
                # Firma bilgisi varsa ekle
                if 'Firma_1' in row and pd.notna(row['Firma_1']):
                    html += f"""
                        <tr>
                            <td><strong>Firma</strong></td>
                            <td>{row['Firma_1']}</td>
                            <td>{row['Firma_2']}</td>
                            <td>-</td>
                        </tr>
                    """
                
                # Tarih bilgisi varsa ekle
                if 'Tarih_1' in row and pd.notna(row['Tarih_1']):
                    html += f"""
                        <tr>
                            <td><strong>Tarih</strong></td>
                            <td>{row['Tarih_1']}</td>
                            <td>{row['Tarih_2']}</td>
                            <td>-</td>
                        </tr>
                    """
                
                html += """
                    </table>
                </div>
                """
            
            html += '</div>'
    
    return html 