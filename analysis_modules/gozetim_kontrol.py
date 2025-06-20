"""
Gözetim Kontrol modülü.
GTİP kodlarına göre gözetim eşik değerlerini kontrol eder.
"""

import pandas as pd
import os
import re

def _normalize_gtip(gtip_code):
    """
    GTİP kodunu normalize eder (noktaları kaldırır, boşlukları temizler)
    """
    if pd.isna(gtip_code):
        return ""
    return str(gtip_code).replace(".", "").replace(" ", "").strip()

def check_gozetim_kontrol(df):
    """
    Gözetim kontrol analizi yapar.
    
    Kontrol kriterleri:
    1. Gözetim.xlsx dosyasından GTİP kodlarını ve eşik değerlerini alır
    2. GTİP eşleştirmesi yapar (kısmi eşleştirme dahil)
    3. Birim türüne göre (brüt/ton, kg, adet) minimum değer kontrolü yapar
    4. Eksik beyan edilen kıymetleri tespit eder
    
    Args:
        df (pandas.DataFrame): Beyanname verileri içeren DataFrame
    
    Returns:
        dict: Analiz sonuçları
    """
    
    # Gerekli sütunları kontrol et
    required_columns = ['Gtip', 'Istatistiki_kiymet']
    missing_columns = [col for col in required_columns if col not in df.columns]
    
    if missing_columns:
        return {
            "status": "error",
            "message": f"Gerekli sütunlar bulunamadı: {', '.join(missing_columns)}"
        }
    
    # Gözetim Excel dosyasını yükle
    try:
        gozetim_file_path = os.path.join('VERGİLER', 'Gözetim.xlsx')
        if not os.path.exists(gozetim_file_path):
            return {
                "status": "error",
                "message": "Gözetim.xlsx dosyası bulunamadı (VERGİLER klasöründe olmalı)"
            }
        
        # Excel dosyasını oku (A sütunu: GTİP, D sütunu: Eşik değer)
        gozetim_df = pd.read_excel(gozetim_file_path)
        
        # Sütun isimlerini kontrol et
        if len(gozetim_df.columns) < 4:
            return {
                "status": "error",
                "message": "Gözetim.xlsx dosyasında yeterli sütun bulunamadı (en az 4 sütun gerekli)"
            }
        
        # A ve D sütunlarını al
        gtip_sutunu = gozetim_df.iloc[:, 0]  # A sütunu
        esik_sutunu = gozetim_df.iloc[:, 3]   # D sütunu
        
        # Boş olmayan satırları filtrele
        valid_rows = pd.notna(gtip_sutunu) & pd.notna(esik_sutunu)
        gozetim_gtip = gtip_sutunu[valid_rows].astype(str)
        gozetim_esik = esik_sutunu[valid_rows].astype(str)
        
        # GTİP kodlarını normalize et
        gozetim_gtip_normalized = [_normalize_gtip(gtip) for gtip in gozetim_gtip]
        
        # Boş olmayan normalize edilmiş kodları filtrele
        gozetim_lookup = {}
        for norm_gtip, esik in zip(gozetim_gtip_normalized, gozetim_esik):
            if norm_gtip:  # Boş olmayan kodlar
                gozetim_lookup[norm_gtip] = esik
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Gözetim.xlsx dosyası okunamadı: {str(e)}"
        }
    
    # GTİP eşleştirmesi yap
    eslesme_sonuclari = []
    
    for _, row in df.iterrows():
        beyanname_gtip = _normalize_gtip(str(row['Gtip']).strip())
        eslesen_gozetim_gtip = None
        eslesen_esik_deger = None
        
        # Önce tam eşleştirme dene
        if beyanname_gtip in gozetim_lookup:
            eslesen_gozetim_gtip = beyanname_gtip
            eslesen_esik_deger = gozetim_lookup[beyanname_gtip]
        else:
            # Kısmi eşleştirme - Gözetim GTİP'i beyanname GTİP'inin başlangıcında varsa
            # Hem kısa hem uzun Gözetim kodları için çalışır
            for gozetim_gtip in gozetim_lookup.keys():
                # Gözetim GTİP'i beyanname GTİP'inin başında varsa eşleştir
                if beyanname_gtip.startswith(gozetim_gtip):
                    eslesen_gozetim_gtip = gozetim_gtip
                    eslesen_esik_deger = gozetim_lookup[gozetim_gtip]
                    break
        
        if eslesen_gozetim_gtip:
            eslesme_sonuclari.append({
                'row_index': row.name,
                'beyanname_gtip': beyanname_gtip,
                'gozetim_gtip': eslesen_gozetim_gtip,
                'esik_deger': eslesen_esik_deger,
                'row_data': row
            })
    
    if not eslesme_sonuclari:
        return {
            "status": "ok",
            "message": "Gözetim kapsamında GTİP bulunamadı"
        }
    
    # Eşleşen kayıtları analiz et
    analiz_sonuclari = []
    
    for eslesme in eslesme_sonuclari:
        row = eslesme['row_data']
        esik_deger_str = eslesme['esik_deger']
        
        # Eşik değeri parse et
        esik_analiz = _parse_esik_deger(esik_deger_str)
        if not esik_analiz:
            continue
        
        # Birim türüne göre kontrol yap
        kontrol_sonucu = _birim_kontrolu_yap(row, esik_analiz, df.columns)
        
        if kontrol_sonucu:
            kontrol_sonucu.update({
                'Beyanname_GTİP': eslesme['beyanname_gtip'],
                'Gözetim_GTİP': eslesme['gozetim_gtip'],
                'Eşik_Değer': esik_deger_str,
                'Firma': _get_firma_bilgisi(row),
                'Ürün_Tanımı': _get_urun_tanimi(row),
                'Tarih': _get_tarih_bilgisi(row),
                'Beyanname_No': row.get('Beyanname_no', '')
            })
            analiz_sonuclari.append(kontrol_sonucu)
    
    if not analiz_sonuclari:
        return {
            "status": "ok",
            "message": f"Gözetim kapsamında {len(eslesme_sonuclari)} GTİP eşleşti, ancak problem tespit edilmedi"
        }
    
    # Sonuçları DataFrame'e çevir
    sonuc_df = pd.DataFrame(analiz_sonuclari)
    
    # Sonuçları sırala - problemli kayıtlar en üstte, eksik kıymet büyükten küçüğe
    sonuc_df = sonuc_df.sort_values(['Problem_Var', 'Eksik_Kıymet'], ascending=[False, False])
    
    # Problem sayısını hesapla
    problem_sayisi = len(sonuc_df[sonuc_df['Problem_Var'] == True])
    
    # Özet tablosu oluştur
    ozet_df = _create_summary_table(sonuc_df)
    
    # HTML rapor oluştur
    html_rapor = _html_rapor_olustur(sonuc_df, ozet_df, len(eslesme_sonuclari))
    
    status = "warning" if problem_sayisi > 0 else "ok"
    mesaj = f"Gözetim kontrolü tamamlandı. {len(eslesme_sonuclari)} GTİP eşleşti, {problem_sayisi} problemli kayıt tespit edildi."
    
    return {
        "status": status,
        "message": mesaj,
        "data": sonuc_df,
        "summary": ozet_df,
        "html_report": html_rapor
    }

def _parse_esik_deger(esik_str):
    """
    Eşik değer string'ini parse eder.
    Örnek: "3000 ABD Doları/ton/brüt" -> {'miktar': 3000, 'birim': 'brüt', 'para_birimi': 'ABD Doları'}
    """
    try:
        esik_str = str(esik_str).strip()
        
        # Sayıyı bul
        sayi_match = re.search(r'(\d+(?:\.\d+)?)', esik_str)
        if not sayi_match:
            return None
        
        miktar = float(sayi_match.group(1))
        
        # Birim türünü belirle
        esik_lower = esik_str.lower()
        
        if 'brüt' in esik_lower or 'brut' in esik_lower:
            birim = 'brüt'
        elif '/kg' in esik_lower or ' kg' in esik_lower:
            birim = 'kg'
        elif 'adet' in esik_lower:
            birim = 'adet'
        else:
            return None
        
        # Para birimini bul
        para_birimi = 'USD'  # Varsayılan
        if 'ABD Doları' in esik_str or 'USD' in esik_str:
            para_birimi = 'USD'
        elif 'Euro' in esik_str or 'EUR' in esik_str:
            para_birimi = 'EUR'
        
        return {
            'miktar': miktar,
            'birim': birim,
            'para_birimi': para_birimi,
            'orijinal': esik_str
        }
        
    except Exception:
        return None

def _birim_kontrolu_yap(row, esik_analiz, columns):
    """
    Birim türüne göre kontrol yapar ve eksik kıymet hesaplar.
    """
    try:
        istatistiki_kiymet = float(row['Istatistiki_kiymet'])
        birim = esik_analiz['birim']
        esik_miktar = esik_analiz['miktar']
        
        if birim == 'brüt':
            # Brüt ağırlık kontrolü
            brut_agirlik_sutunu = _find_column(columns, ['brut_agirlik', 'brüt_ağırlık', 'brutağırlık'])
            if not brut_agirlik_sutunu or pd.isna(row[brut_agirlik_sutunu]):
                return None
            
            brut_agirlik = float(row[brut_agirlik_sutunu])  # kg cinsinden
            if brut_agirlik <= 0:
                return None
            
            # Ton'a çevir
            brut_agirlik_ton = brut_agirlik / 1000
            
            # Minimum kıymet hesapla (USD/ton * ton)
            minimum_kiymet = esik_miktar * brut_agirlik_ton
            eksik_kiymet = minimum_kiymet - istatistiki_kiymet
            
            return {
                'Birim_Türü': 'Brüt Ağırlık (ton)',
                'Ağırlık_Miktar': f"{brut_agirlik} kg ({brut_agirlik_ton:.3f} ton)",
                'Eşik_Değer_Birim': f"{esik_miktar} USD/ton",
                'Minimum_Kıymet': round(minimum_kiymet, 2),
                'Beyan_Kıymet': istatistiki_kiymet,
                'Eksik_Kıymet': round(eksik_kiymet, 2) if eksik_kiymet > 0 else 0,
                'Problem_Var': eksik_kiymet > 0,
                'Problem_Açıklama': f"Minimum {minimum_kiymet:.2f} USD olması gerekirken {istatistiki_kiymet} USD beyan edilmiş" if eksik_kiymet > 0 else "Normal"
            }
            
        elif birim == 'kg':
            # Net ağırlık kontrolü
            net_agirlik_sutunu = _find_column(columns, ['net_agirlik', 'net_ağırlık', 'netağırlık'])
            if not net_agirlik_sutunu or pd.isna(row[net_agirlik_sutunu]):
                return None
            
            net_agirlik = float(row[net_agirlik_sutunu])  # kg cinsinden
            if net_agirlik <= 0:
                return None
            
            # Minimum kıymet hesapla (USD/kg * kg)
            minimum_kiymet = esik_miktar * net_agirlik
            eksik_kiymet = minimum_kiymet - istatistiki_kiymet
            
            return {
                'Birim_Türü': 'Net Ağırlık (kg)',
                'Ağırlık_Miktar': f"{net_agirlik} kg",
                'Eşik_Değer_Birim': f"{esik_miktar} USD/kg",
                'Minimum_Kıymet': round(minimum_kiymet, 2),
                'Beyan_Kıymet': istatistiki_kiymet,
                'Eksik_Kıymet': round(eksik_kiymet, 2) if eksik_kiymet > 0 else 0,
                'Problem_Var': eksik_kiymet > 0,
                'Problem_Açıklama': f"Minimum {minimum_kiymet:.2f} USD olması gerekirken {istatistiki_kiymet} USD beyan edilmiş" if eksik_kiymet > 0 else "Normal"
            }
            
        elif birim == 'adet':
            # Miktar kontrolü
            miktar_sutunu = _find_column(columns, ['miktar', 'adet', 'quantity'])
            if not miktar_sutunu or pd.isna(row[miktar_sutunu]):
                return None
            
            miktar = float(row[miktar_sutunu])
            if miktar <= 0:
                return None
            
            # Minimum kıymet hesapla (USD/adet * adet)
            minimum_kiymet = esik_miktar * miktar
            eksik_kiymet = minimum_kiymet - istatistiki_kiymet
            
            return {
                'Birim_Türü': 'Adet',
                'Ağırlık_Miktar': f"{miktar} adet",
                'Eşik_Değer_Birim': f"{esik_miktar} USD/adet",
                'Minimum_Kıymet': round(minimum_kiymet, 2),
                'Beyan_Kıymet': istatistiki_kiymet,
                'Eksik_Kıymet': round(eksik_kiymet, 2) if eksik_kiymet > 0 else 0,
                'Problem_Var': eksik_kiymet > 0,
                'Problem_Açıklama': f"Minimum {minimum_kiymet:.2f} USD olması gerekirken {istatistiki_kiymet} USD beyan edilmiş" if eksik_kiymet > 0 else "Normal"
            }
        
        return None
        
    except (ValueError, TypeError):
        return None

def _find_column(columns, possible_names):
    """
    Sütun listesinde belirtilen isimlerden birini bulur.
    """
    for col in columns:
        col_lower = col.lower().replace(' ', '').replace('_', '')
        for name in possible_names:
            name_lower = name.lower().replace(' ', '').replace('_', '')
            if name_lower in col_lower:
                return col
    return None

def _get_firma_bilgisi(row):
    """Satırdan firma bilgisini çıkarır"""
    firma_sutunlari = ['Adi_unvani', 'Gonderen', 'Gonderen_adi', 'Ithalatci']
    for sutun in firma_sutunlari:
        if sutun in row and pd.notna(row[sutun]):
            return row[sutun]
    return ''

def _get_urun_tanimi(row):
    """Satırdan ürün tanımını çıkarır"""
    urun_sutunlari = ['Ticari_tanimi', 'Esya_tanimi', 'Aciklama']
    for sutun in urun_sutunlari:
        if sutun in row and pd.notna(row[sutun]):
            return row[sutun]
    return ''

def _get_tarih_bilgisi(row):
    """Satırdan tarih bilgisini çıkarır"""
    tarih_sutunlari = ['Tescil_tarihi', 'Beyanname_tarihi', 'Tarih']
    for sutun in tarih_sutunlari:
        if sutun in row and pd.notna(row[sutun]):
            return row[sutun]
    return ''

def _create_summary_table(sonuc_df):
    """Özet tablosu oluşturur"""
    if sonuc_df.empty:
        return pd.DataFrame()
    
    # GTİP bazında özet
    gtip_ozet = sonuc_df.groupby('Gözetim_GTİP').agg({
        'Problem_Var': 'sum',
        'Eksik_Kıymet': 'sum',
        'Beyanname_GTİP': 'count',
        'Birim_Türü': lambda x: ', '.join(x.unique())
    }).reset_index()
    
    gtip_ozet.columns = ['Gözetim_GTİP', 'Problem_Sayısı', 'Toplam_Eksik_Kıymet', 'Toplam_Kayıt', 'Birim_Türleri']
    
    return gtip_ozet

def _html_rapor_olustur(sonuc_df, ozet_df, toplam_eslesme):
    """
    Gözetim kontrol için HTML rapor oluşturur
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
    .istatistik-kutu {
        background-color: #e8f5e8;
        border: 1px solid #c3e6c3;
        border-radius: 5px;
        padding: 15px;
        margin-bottom: 20px;
    }
    .uyari-kutu {
        background-color: #fff3cd;
        border: 1px solid #ffeaa7;
        border-radius: 5px;
        padding: 15px;
        margin-bottom: 20px;
    }
    .hata-kutu {
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
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
    .problem-row {
        background-color: #ffebee !important;
    }
    .normal-row {
        background-color: #e8f5e8 !important;
    }
    .durum-kutu {
        display: inline-block;
        padding: 4px 8px;
        border-radius: 4px;
        font-size: 12px;
        font-weight: bold;
    }
    .problem {
        background-color: #ffcdd2;
        color: #c62828;
    }
    .normal {
        background-color: #c8e6c9;
        color: #2e7d32;
    }
    </style>
    
    <h2>🔍 Gözetim Kontrol Raporu</h2>
    
    <div class="ozet-kutu">
        <h3>📋 Kontrol Açıklaması</h3>
        <p>Bu kontrol, gözetim kapsamındaki GTİP kodları için minimum kıymet eşiklerini kontrol eder.</p>
        <p><strong>🎯 Kontrol Kriterleri:</strong></p>
        <ul>
            <li>Gözetim.xlsx dosyasından GTİP kodları ve eşik değerleri alınır</li>
            <li>Tam ve kısmi GTİP eşleştirmesi yapılır</li>
            <li>Birim türüne göre minimum kıymet hesaplanır:
                <ul>
                    <li><strong>Brüt:</strong> USD/ton × brüt ağırlık (ton)</li>
                    <li><strong>Kg:</strong> USD/kg × net ağırlık (kg)</li>
                    <li><strong>Adet:</strong> USD/adet × miktar (adet)</li>
                </ul>
            </li>
            <li>İstatistiki kıymet ile minimum kıymet karşılaştırılır</li>
        </ul>
        <p><strong>⚠️ Risk:</strong> Gözetim eşiğinin altında kıymet beyanı yapılması.</p>
    </div>
    """
    
    # İstatistikler
    if not sonuc_df.empty:
        problem_sayisi = len(sonuc_df[sonuc_df['Problem_Var'] == True])
        normal_sayisi = len(sonuc_df[sonuc_df['Problem_Var'] == False])
        toplam_eksik = sonuc_df['Eksik_Kıymet'].sum()
        
        if problem_sayisi > 0:
            html += f"""
            <div class="hata-kutu">
                <h3>🚨 Tespit Edilen Problemler</h3>
                <ul>
                    <li><strong>Toplam Eşleşme:</strong> {toplam_eslesme} GTİP</li>
                    <li><strong>Problemli Kayıt:</strong> {problem_sayisi}</li>
                    <li><strong>Normal Kayıt:</strong> {normal_sayisi}</li>
                    <li><strong>Toplam Eksik Kıymet:</strong> {toplam_eksik:.2f} USD</li>
                </ul>
            </div>
            """
        else:
            html += f"""
            <div class="istatistik-kutu">
                <h3>✅ Sonuç</h3>
                <p>Tüm gözetim kontrolleri normal. {toplam_eslesme} GTİP eşleşti, {normal_sayisi} kayıt incelendi.</p>
            </div>
            """
        
        # Özet tablosu
        if not ozet_df.empty:
            html += "<h3>📊 GTİP Bazında Özet</h3>"
            html += ozet_df.to_html(index=False, classes="table table-striped", escape=False)
        
        # Detay tablosu
        html += "<h3>📋 Detaylı Analiz Sonuçları</h3>"
        
        # HTML tablosunu oluştur
        html += '<table class="table table-striped">'
        html += '<thead><tr>'
        for col in sonuc_df.columns:
            html += f'<th>{col}</th>'
        html += '</tr></thead><tbody>'
        
        for _, row in sonuc_df.iterrows():
            css_class = "problem-row" if row['Problem_Var'] else "normal-row"
            
            html += f'<tr class="{css_class}">'
            for col in sonuc_df.columns:
                value = row[col]
                if col == 'Problem_Var':
                    if value:
                        value = '<span class="durum-kutu problem">Problem Var</span>'
                    else:
                        value = '<span class="durum-kutu normal">Normal</span>'
                elif col == 'Eksik_Kıymet' and isinstance(value, (int, float)):
                    if value > 0:
                        value = f'<strong style="color: #c62828;">{value:.2f} USD</strong>'
                    else:
                        value = f"{value:.2f} USD"
                elif col in ['Minimum_Kıymet', 'Beyan_Kıymet'] and isinstance(value, (int, float)):
                    value = f"{value:.2f} USD"
                html += f'<td>{value}</td>'
            html += '</tr>'
        
        html += '</tbody></table>'
    
    else:
        html += """
        <div class="istatistik-kutu">
            <h3>ℹ️ Bilgi</h3>
            <p>Gözetim kapsamında problem tespit edilmedi.</p>
        </div>
        """
    
    return html 