"""
Supalan Depolama Kontrol modülü.
Eşyanın bulunduğu yer "TAŞIT ÜSTÜ - SUPALAN SAHASI" olan kayıtlarda
Yurtici_Depolama gideri beyan edilip edilmediğini kontrol edecek.
"""

import pandas as pd
import numpy as np

def check_supalan_depolama_kontrol(df):
    """
    Supalan depolama kontrolü yapar:
    Eşyanın bulunduğu yer "TAŞIT ÜSTÜ - SUPALAN SAHASI" olan kayıtlarda
    Yurtici_Depolama gideri beyan edilip edilmediğini kontrol eder.
    
    Args:
        df (pandas.DataFrame): Beyanname verileri içeren DataFrame
    
    Returns:
        dict: Analiz sonuçları
    """
    
    # Gerekli sütunları kontrol et
    required_columns = ['Esyanin_bulundugu_yer']
    missing_columns = [col for col in required_columns if col not in df.columns]
    
    if missing_columns:
        return {
            "status": "error",
            "message": f"Gerekli sütunlar bulunamadı: {', '.join(missing_columns)}"
        }
    
    # Yurtici_Depolama sütunu var mı kontrol et
    if 'Yurtici_Depolama' not in df.columns:
        return {
            "status": "error",
            "message": "Yurtici_Depolama sütunu bulunamadı"
        }
    
    # Boş olmayan verileri filtrele
    valid_data = df.dropna(subset=required_columns).copy()
    
    if len(valid_data) == 0:
        return {
            "status": "error",
            "message": "Geçerli veri bulunamadı"
        }
    
    # TAŞIT ÜSTÜ - SUPALAN SAHASI olan kayıtları filtrele
    supalan_kayitlari = valid_data[
        valid_data['Esyanin_bulundugu_yer'].astype(str).str.contains(
            'TAŞIT ÜSTÜ - SUPALAN SAHASI', case=False, na=False
        )
    ].copy()
    
    if len(supalan_kayitlari) == 0:
        return {
            "status": "ok",
            "message": "TAŞIT ÜSTÜ - SUPALAN SAHASI olan kayıt bulunamadı"
        }
    
    # Yurtici_Depolama sütununu sayısal hale getir
    supalan_kayitlari['Yurtici_Depolama'] = pd.to_numeric(
        supalan_kayitlari['Yurtici_Depolama'], errors='coerce'
    ).fillna(0)
    
    # Depolama gideri beyan edilenler ve edilmeyenler
    depolama_var = supalan_kayitlari[supalan_kayitlari['Yurtici_Depolama'] > 0]
    depolama_yok = supalan_kayitlari[supalan_kayitlari['Yurtici_Depolama'] == 0]
    
    # Sonuç verilerini hazırla
    sonuc_verileri = []
    
    # Depolama gideri beyan edilenler
    for _, row in depolama_var.iterrows():
        sonuc_satiri = {
            'Beyanname_no': row.get('Beyanname_no', ''),
            'Esyanin_Bulundugu_Yer': row['Esyanin_bulundugu_yer'],
            'Yurtici_Depolama': row['Yurtici_Depolama'],
            'Durum': 'Depolama Gideri Beyan Edilmiş',
            'Sorun_Durumu': 'Normal'
        }
        
        # Firma bilgisi varsa ekle
        firma_sutunlari = ['Adi_unvani', 'Gonderen', 'Gonderen_adi', 'Ithalatci']
        for firma_sutun in firma_sutunlari:
            if firma_sutun in row and pd.notna(row[firma_sutun]):
                sonuc_satiri['Firma'] = row[firma_sutun]
                break
        
        # Tarih bilgisi varsa ekle
        tarih_sutunlari = ['Tescil_tarihi', 'Beyanname_tarihi', 'Tarih']
        for tarih_sutun in tarih_sutunlari:
            if tarih_sutun in row and pd.notna(row[tarih_sutun]):
                sonuc_satiri['Tarih'] = row[tarih_sutun]
                break
        
        # GTIP bilgisi varsa ekle
        if 'Gtip' in row and pd.notna(row['Gtip']):
            sonuc_satiri['Gtip'] = row['Gtip']
        
        sonuc_verileri.append(sonuc_satiri)
    
    # Depolama gideri beyan edilmeyenler
    for _, row in depolama_yok.iterrows():
        sonuc_satiri = {
            'Beyanname_no': row.get('Beyanname_no', ''),
            'Esyanin_Bulundugu_Yer': row['Esyanin_bulundugu_yer'],
            'Yurtici_Depolama': 0,
            'Durum': 'Depolama Gideri Beyan Edilmemiş',
            'Sorun_Durumu': 'Dikkat Edilmeli'
        }
        
        # Firma bilgisi varsa ekle
        firma_sutunlari = ['Adi_unvani', 'Gonderen', 'Gonderen_adi', 'Ithalatci']
        for firma_sutun in firma_sutunlari:
            if firma_sutun in row and pd.notna(row[firma_sutun]):
                sonuc_satiri['Firma'] = row[firma_sutun]
                break
        
        # Tarih bilgisi varsa ekle
        tarih_sutunlari = ['Tescil_tarihi', 'Beyanname_tarihi', 'Tarih']
        for tarih_sutun in tarih_sutunlari:
            if tarih_sutun in row and pd.notna(row[tarih_sutun]):
                sonuc_satiri['Tarih'] = row[tarih_sutun]
                break
        
        # GTIP bilgisi varsa ekle
        if 'Gtip' in row and pd.notna(row['Gtip']):
            sonuc_satiri['Gtip'] = row['Gtip']
        
        sonuc_verileri.append(sonuc_satiri)
    
    if len(sonuc_verileri) == 0:
        return {
            "status": "ok",
            "message": "TAŞIT ÜSTÜ - SUPALAN SAHASI kayıtları bulunamadı"
        }
    
    # DataFrame'e çevir
    sonuc_df = pd.DataFrame(sonuc_verileri)
    
    # Özet tablosu oluştur
    ozet_verileri = []
    
    # Genel özet
    toplam_supalan = len(supalan_kayitlari)
    depolama_beyan_edilen = len(depolama_var)
    depolama_beyan_edilmeyen = len(depolama_yok)
    
    ozet_verileri.append({
        'Kategori': 'Toplam SUPALAN SAHASI Kayıtları',
        'Sayı': toplam_supalan,
        'Yüzde': 100.0
    })
    
    ozet_verileri.append({
        'Kategori': 'Depolama Gideri Beyan Edilmiş',
        'Sayı': depolama_beyan_edilen,
        'Yüzde': (depolama_beyan_edilen / toplam_supalan * 100) if toplam_supalan > 0 else 0
    })
    
    ozet_verileri.append({
        'Kategori': 'Depolama Gideri Beyan Edilmemiş',
        'Sayı': depolama_beyan_edilmeyen,
        'Yüzde': (depolama_beyan_edilmeyen / toplam_supalan * 100) if toplam_supalan > 0 else 0
    })
    
    # Firma bazında özet
    if 'Firma' in sonuc_df.columns:
        firma_ozet = sonuc_df.groupby(['Firma', 'Durum']).size().unstack(fill_value=0)
        for firma in firma_ozet.index:
            beyan_edilen = firma_ozet.loc[firma].get('Depolama Gideri Beyan Edilmiş', 0)
            beyan_edilmeyen = firma_ozet.loc[firma].get('Depolama Gideri Beyan Edilmemiş', 0)
            toplam_firma = beyan_edilen + beyan_edilmeyen
            
            ozet_verileri.append({
                'Kategori': f'Firma: {firma}',
                'Sayı': toplam_firma,
                'Yüzde': f'Beyan: {beyan_edilen}, Beyan Yok: {beyan_edilmeyen}'
            })
    
    ozet_df = pd.DataFrame(ozet_verileri)
    
    # HTML rapor oluştur
    html_rapor = _html_rapor_olustur(sonuc_df, ozet_df, toplam_supalan, depolama_beyan_edilen, depolama_beyan_edilmeyen)
    
    # Sonuç mesajı
    if depolama_beyan_edilmeyen > 0:
        status = "warning"
        mesaj = f"TAŞIT ÜSTÜ - SUPALAN SAHASI'nda {toplam_supalan} kayıt bulundu. "
        mesaj += f"{depolama_beyan_edilen} tanesinde depolama gideri beyan edilmiş, "
        mesaj += f"{depolama_beyan_edilmeyen} tanesinde beyan edilmemiş."
    else:
        status = "ok"
        mesaj = f"TAŞIT ÜSTÜ - SUPALAN SAHASI'nda {toplam_supalan} kayıt bulundu. "
        mesaj += "Tümünde depolama gideri beyan edilmiş."
    
    return {
        "status": status,
        "message": mesaj,
        "data": sonuc_df,
        "summary": ozet_df,
        "html_report": html_rapor
    }

def _html_rapor_olustur(sonuc_df, ozet_df, toplam_supalan, depolama_beyan_edilen, depolama_beyan_edilmeyen):
    """
    Supalan depolama kontrol için HTML rapor oluşturur
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
    .normal {
        background-color: #e8f5e8;
        color: #2e7d32;
        font-weight: bold;
    }
    .dikkat {
        background-color: #fff3e0;
        color: #f57c00;
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
    .durum-bolum {
        margin-top: 30px;
        padding-top: 10px;
        border-top: 1px dashed #ccc;
    }
    </style>
    
    <h2>Supalan Depolama Kontrol Analiz Raporu</h2>
    
    <div class="ozet-kutu">
        <h3>Kontrol Özeti</h3>
        <p>Bu kontrol, eşyanın bulunduğu yer <strong>"TAŞIT ÜSTÜ - SUPALAN SAHASI"</strong> olan kayıtlarda <strong>Yurtici_Depolama</strong> gideri beyan edilip edilmediğini analiz eder.</p>
        <p><strong>Kontrol Kriteri:</strong> Supalan sahasında bulunan eşyalar için depolama gideri beyan edilmeli mi?</p>
    </div>
    """
    
    # Genel istatistikler
    html += f"""
    <h3>Genel İstatistikler</h3>
    <div>
        <div class="istatistik-kutu">
            <strong>Toplam SUPALAN SAHASI:</strong> {toplam_supalan}
        </div>
        <div class="istatistik-kutu">
            <strong>Depolama Gideri Var:</strong> {depolama_beyan_edilen}
        </div>
        <div class="istatistik-kutu">
            <strong>Depolama Gideri Yok:</strong> {depolama_beyan_edilmeyen}
        </div>
        <div class="istatistik-kutu">
            <strong>Beyan Oranı:</strong> {(depolama_beyan_edilen/toplam_supalan*100):.1f}%
        </div>
    </div>
    """
    
    # Özet tablosunu ekle
    html += "<h3>Kategori Bazında Özet</h3>"
    html += ozet_df.to_html(index=False, classes="table table-striped", escape=False)
    
    # Detaylı sonuçlar
    if not sonuc_df.empty:
        # Depolama gideri beyan edilenler
        beyan_edilenler = sonuc_df[sonuc_df['Durum'] == 'Depolama Gideri Beyan Edilmiş']
        if not beyan_edilenler.empty:
            html += '<div class="durum-bolum">'
            html += '<h3>✅ Depolama Gideri Beyan Edilmiş Kayıtlar</h3>'
            html += beyan_edilenler.head(20).to_html(index=False, classes="table table-striped", escape=False)
            if len(beyan_edilenler) > 20:
                html += f'<p><em>Not: Toplam {len(beyan_edilenler)} kayıttan ilk 20 tanesi gösterilmektedir.</em></p>'
            html += '</div>'
        
        # Depolama gideri beyan edilmeyenler
        beyan_edilmeyenler = sonuc_df[sonuc_df['Durum'] == 'Depolama Gideri Beyan Edilmemiş']
        if not beyan_edilmeyenler.empty:
            html += '<div class="durum-bolum">'
            html += '<h3>⚠️ Depolama Gideri Beyan Edilmemiş Kayıtlar</h3>'
            html += '<p class="dikkat">Bu kayıtlarda SUPALAN SAHASI\'nda olmasına rağmen depolama gideri beyan edilmemiştir.</p>'
            html += beyan_edilmeyenler.head(20).to_html(index=False, classes="table table-striped", escape=False)
            if len(beyan_edilmeyenler) > 20:
                html += f'<p><em>Not: Toplam {len(beyan_edilmeyenler)} kayıttan ilk 20 tanesi gösterilmektedir.</em></p>'
            html += '</div>'
    
    return html 