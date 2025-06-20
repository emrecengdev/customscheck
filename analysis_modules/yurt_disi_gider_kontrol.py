"""
Yurt Dışı Gider Kontrol modülü.
İki farklı kontrol yapar:
1. Aynı gönderici farklı toplam yurt dışı gider kontrolü
2. Aynı gönderici-GTIP farklı gider türleri kontrolü
"""

import pandas as pd
import numpy as np

def check_yurt_disi_gider_kontrol(df):
    """
    Yurt dışı gider kontrolü yapar:
    1. Aynı gönderici farklı toplam yurt dışı gider kontrolü
    2. Aynı gönderici-GTIP farklı gider türleri kontrolü
    
    Args:
        df (pandas.DataFrame): Beyanname verileri içeren DataFrame
    
    Returns:
        dict: Analiz sonuçları
    """
    
    # Gerekli sütunları kontrol et
    required_columns = ['Toplam_yurt_disi_harcamalar', 'Adi_unvani']
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
    
    # Sayısal değerlere çevir
    valid_data['Toplam_yurt_disi_harcamalar'] = pd.to_numeric(valid_data['Toplam_yurt_disi_harcamalar'], errors='coerce')
    valid_data = valid_data.dropna(subset=['Toplam_yurt_disi_harcamalar'])
    
    if len(valid_data) == 0:
        return {
            "status": "error",
            "message": "Geçerli sayısal veri bulunamadı"
        }
    
    # 1. Kontrol: Aynı gönderici farklı toplam yurt dışı gider
    kontrol1_sonuc = _kontrol1_ayni_gonderici_farkli_toplam_gider(valid_data)
    
    # 2. Kontrol: Aynı gönderici-GTIP farklı gider türleri
    kontrol2_sonuc = _kontrol2_ayni_gonderici_gtip_farkli_gider_turleri(valid_data)
    
    # Sonuçları birleştir
    toplam_sorun = 0
    if kontrol1_sonuc['data'] is not None:
        toplam_sorun += len(kontrol1_sonuc['data'])
    if kontrol2_sonuc['data'] is not None:
        toplam_sorun += len(kontrol2_sonuc['data'])
    
    if toplam_sorun == 0:
        return {
            "status": "ok",
            "message": "Yurt dışı gider kontrollerinde sorun tespit edilmedi"
        }
    
    # HTML rapor oluştur
    html_rapor = _html_rapor_olustur(kontrol1_sonuc, kontrol2_sonuc)
    
    # Sonuç mesajı
    mesaj = f"Yurt dışı gider kontrollerinde toplam {toplam_sorun} sorun tespit edildi. "
    if kontrol1_sonuc['data'] is not None:
        mesaj += f"Kontrol 1: {len(kontrol1_sonuc['data'])} sorun. "
    if kontrol2_sonuc['data'] is not None:
        mesaj += f"Kontrol 2: {len(kontrol2_sonuc['data'])} sorun."
    
    return {
        "status": "warning",
        "message": mesaj,
        "kontrol1": kontrol1_sonuc,
        "kontrol2": kontrol2_sonuc,
        "html_report": html_rapor
    }

def _kontrol1_ayni_gonderici_farkli_toplam_gider(df):
    """
    Kontrol 1: Aynı gönderici farklı toplam yurt dışı gider
    Birinde 0, diğerinde var olan durumları tespit eder
    """
    
    sonuc_verileri = []
    
    # Gönderici bazında grupla
    for gonderici in df['Adi_unvani'].unique():
        gonderici_data = df[df['Adi_unvani'] == gonderici]
        
        if len(gonderici_data) < 2:
            continue
        
        # Farklı toplam gider değerlerini bul
        farkli_giderler = gonderici_data['Toplam_yurt_disi_harcamalar'].unique()
        
        # En az bir tanesi 0 ve diğerleri 0'dan farklı mı?
        sifir_var = 0 in farkli_giderler
        sifir_olmayan_var = any(gider > 0 for gider in farkli_giderler)
        
        if sifir_var and sifir_olmayan_var:
            # 0 olan ve 0 olmayan örnekleri bul
            sifir_olanlar = gonderici_data[gonderici_data['Toplam_yurt_disi_harcamalar'] == 0]
            sifir_olmayanlar = gonderici_data[gonderici_data['Toplam_yurt_disi_harcamalar'] > 0]
            
            # Beyanname bilgilerini ekle
            for _, sifir_row in sifir_olanlar.head(3).iterrows():
                for _, pozitif_row in sifir_olmayanlar.head(3).iterrows():
                    sonuc_satiri = {
                        'Gonderici': gonderici,
                        'Beyanname_Sifir': sifir_row.get('Beyanname_no', ''),
                        'Gider_Sifir': 0,
                        'Beyanname_Pozitif': pozitif_row.get('Beyanname_no', ''),
                        'Gider_Pozitif': pozitif_row['Toplam_yurt_disi_harcamalar'],
                        'Fark': pozitif_row['Toplam_yurt_disi_harcamalar']
                    }
                    
                    # Tarih bilgisi varsa ekle
                    tarih_sutunlari = ['Tescil_tarihi', 'Beyanname_tarihi', 'Tarih']
                    for tarih_sutun in tarih_sutunlari:
                        if tarih_sutun in sifir_row:
                            sonuc_satiri['Tarih_Sifir'] = sifir_row[tarih_sutun]
                            sonuc_satiri['Tarih_Pozitif'] = pozitif_row[tarih_sutun]
                            break
                    
                    sonuc_verileri.append(sonuc_satiri)
    
    if len(sonuc_verileri) == 0:
        return {
            "data": None,
            "summary": None,
            "message": "Aynı gönderici farklı toplam gider sorunu bulunamadı"
        }
    
    # DataFrame'e çevir
    sonuc_df = pd.DataFrame(sonuc_verileri)
    
    # Özet tablosu oluştur
    ozet_verileri = []
    for gonderici in sonuc_df['Gonderici'].unique():
        gonderici_sonuclari = sonuc_df[sonuc_df['Gonderici'] == gonderici]
        
        ozet_verileri.append({
            'Gonderici': gonderici,
            'Sorunlu_Karsilastirma_Sayisi': len(gonderici_sonuclari),
            'Maksimum_Gider_Farki': gonderici_sonuclari['Gider_Pozitif'].max(),
            'Ortalama_Gider_Farki': gonderici_sonuclari['Gider_Pozitif'].mean()
        })
    
    ozet_df = pd.DataFrame(ozet_verileri)
    
    return {
        "data": sonuc_df,
        "summary": ozet_df,
        "message": f"{len(sonuc_df)} aynı gönderici farklı toplam gider sorunu tespit edildi"
    }

def _kontrol2_ayni_gonderici_gtip_farkli_gider_turleri(df):
    """
    Kontrol 2: Aynı gönderici-GTIP farklı gider türleri
    """
    
    # GTIP sütunu var mı kontrol et
    if 'Gtip' not in df.columns:
        return {
            "data": None,
            "summary": None,
            "message": "GTIP sütunu bulunamadı"
        }
    
    # Gider türü sütunlarını kontrol et
    gider_turleri = ['YurtDisi_Demuraj', 'YurtDisi_Diger', 'YurtDisi_Faiz', 'YurtDisi_Komisyon', 'YurtDisi_Royalti']
    mevcut_gider_turleri = [col for col in gider_turleri if col in df.columns]
    
    if len(mevcut_gider_turleri) == 0:
        return {
            "data": None,
            "summary": None,
            "message": "Yurt dışı gider türü sütunları bulunamadı"
        }
    
    # Gider türlerini sayısal hale getir
    for gider_turu in mevcut_gider_turleri:
        df[gider_turu] = pd.to_numeric(df[gider_turu], errors='coerce').fillna(0)
    
    sonuc_verileri = []
    
    # Gönderici-GTIP bazında grupla
    for (gonderici, gtip), grup_data in df.groupby(['Adi_unvani', 'Gtip']):
        if len(grup_data) < 2:
            continue
        
        # Her gider türü için kontrol et
        for gider_turu in mevcut_gider_turleri:
            gider_degerleri = grup_data[gider_turu].unique()
            
            # Hem 0 hem de 0'dan farklı değerler var mı?
            sifir_var = 0 in gider_degerleri
            sifir_olmayan_var = any(deger > 0 for deger in gider_degerleri)
            
            if sifir_var and sifir_olmayan_var:
                # 0 olan ve 0 olmayan örnekleri bul
                sifir_olanlar = grup_data[grup_data[gider_turu] == 0]
                sifir_olmayanlar = grup_data[grup_data[gider_turu] > 0]
                
                # Örnek kayıtları al
                for _, sifir_row in sifir_olanlar.head(2).iterrows():
                    for _, pozitif_row in sifir_olmayanlar.head(2).iterrows():
                        sonuc_satiri = {
                            'Gonderici': gonderici,
                            'Gtip': gtip,
                            'Gider_Turu': gider_turu,
                            'Beyanname_Sifir': sifir_row.get('Beyanname_no', ''),
                            'Deger_Sifir': 0,
                            'Beyanname_Pozitif': pozitif_row.get('Beyanname_no', ''),
                            'Deger_Pozitif': pozitif_row[gider_turu],
                            'Fark': pozitif_row[gider_turu]
                        }
                        
                        # Tarih bilgisi varsa ekle
                        tarih_sutunlari = ['Tescil_tarihi', 'Beyanname_tarihi', 'Tarih']
                        for tarih_sutun in tarih_sutunlari:
                            if tarih_sutun in sifir_row:
                                sonuc_satiri['Tarih_Sifir'] = sifir_row[tarih_sutun]
                                sonuc_satiri['Tarih_Pozitif'] = pozitif_row[tarih_sutun]
                                break
                        
                        sonuc_verileri.append(sonuc_satiri)
    
    if len(sonuc_verileri) == 0:
        return {
            "data": None,
            "summary": None,
            "message": "Aynı gönderici-GTIP farklı gider türü sorunu bulunamadı"
        }
    
    # DataFrame'e çevir
    sonuc_df = pd.DataFrame(sonuc_verileri)
    
    # Özet tablosu oluştur
    ozet_verileri = []
    for (gonderici, gtip), grup in sonuc_df.groupby(['Gonderici', 'Gtip']):
        ozet_verileri.append({
            'Gonderici': gonderici,
            'Gtip': gtip,
            'Farkli_Gider_Turu_Sayisi': grup['Gider_Turu'].nunique(),
            'Toplam_Sorun_Sayisi': len(grup),
            'Gider_Turleri': ', '.join(grup['Gider_Turu'].unique())
        })
    
    ozet_df = pd.DataFrame(ozet_verileri)
    
    return {
        "data": sonuc_df,
        "summary": ozet_df,
        "message": f"{len(sonuc_df)} aynı gönderici-GTIP farklı gider türü sorunu tespit edildi"
    }

def _html_rapor_olustur(kontrol1_sonuc, kontrol2_sonuc):
    """
    Yurt dışı gider kontrol için HTML rapor oluşturur
    """
    html = """
    <style>
    body {
        font-family: Arial, sans-serif;
        margin: 0;
        padding: 10px;
    }
    h2, h3, h4 {
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
    .kontrol-bolum {
        background-color: #fff;
        border: 1px solid #ddd;
        border-radius: 8px;
        padding: 20px;
        margin-bottom: 30px;
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
    .sorun-var {
        background-color: #ffebee;
        color: #c62828;
        font-weight: bold;
    }
    .istatistik-kutu {
        display: inline-block;
        margin-right: 15px;
        padding: 10px 15px;
        background-color: #e3f2fd;
        border-radius: 4px;
        border-left: 4px solid #2196f3;
    }
    .basarili {
        background-color: #e8f5e8;
        border-left: 4px solid #4caf50;
        padding: 15px;
        margin: 15px 0;
        border-radius: 4px;
    }
    </style>
    
    <h2>Yurt Dışı Gider Kontrol Analiz Raporu</h2>
    
    <div class="ozet-kutu">
        <h3>Kontrol Özeti</h3>
        <p>Bu kontrol, yurt dışı gider beyanlarında iki farklı tutarsızlık türünü analiz eder:</p>
        <ul>
            <li><strong>Kontrol 1:</strong> Aynı gönderici farklı toplam yurt dışı gider (birinde 0, diğerinde var)</li>
            <li><strong>Kontrol 2:</strong> Aynı gönderici-GTIP farklı gider türleri (birinde var, diğerinde yok)</li>
        </ul>
    </div>
    """
    
    # Kontrol 1 sonuçları
    html += '<div class="kontrol-bolum">'
    html += '<h3>Kontrol 1: Aynı Gönderici Farklı Toplam Yurt Dışı Gider</h3>'
    
    if kontrol1_sonuc['data'] is not None:
        html += f'<p class="sorun-var">⚠️ {len(kontrol1_sonuc["data"])} sorun tespit edildi</p>'
        
        # Özet tablosu
        html += '<h4>Gönderici Bazında Özet</h4>'
        html += kontrol1_sonuc['summary'].to_html(index=False, classes="table table-striped", escape=False)
        
        # Detaylı sonuçlar (ilk 20)
        html += '<h4>Detaylı Sonuçlar (İlk 20)</h4>'
        html += kontrol1_sonuc['data'].head(20).to_html(index=False, classes="table table-striped", escape=False)
        
        if len(kontrol1_sonuc['data']) > 20:
            html += f'<p><em>Not: Toplam {len(kontrol1_sonuc["data"])} sonuçtan ilk 20 tanesi gösterilmektedir.</em></p>'
    else:
        html += '<div class="basarili">✅ Bu kontrolde sorun tespit edilmedi</div>'
    
    html += '</div>'
    
    # Kontrol 2 sonuçları
    html += '<div class="kontrol-bolum">'
    html += '<h3>Kontrol 2: Aynı Gönderici-GTIP Farklı Gider Türleri</h3>'
    
    if kontrol2_sonuc['data'] is not None:
        html += f'<p class="sorun-var">⚠️ {len(kontrol2_sonuc["data"])} sorun tespit edildi</p>'
        
        # Özet tablosu
        html += '<h4>Gönderici-GTIP Bazında Özet</h4>'
        html += kontrol2_sonuc['summary'].to_html(index=False, classes="table table-striped", escape=False)
        
        # Detaylı sonuçlar (ilk 20)
        html += '<h4>Detaylı Sonuçlar (İlk 20)</h4>'
        html += kontrol2_sonuc['data'].head(20).to_html(index=False, classes="table table-striped", escape=False)
        
        if len(kontrol2_sonuc['data']) > 20:
            html += f'<p><em>Not: Toplam {len(kontrol2_sonuc["data"])} sonuçtan ilk 20 tanesi gösterilmektedir.</em></p>'
    else:
        html += '<div class="basarili">✅ Bu kontrolde sorun tespit edilmedi</div>'
    
    html += '</div>'
    
    return html 