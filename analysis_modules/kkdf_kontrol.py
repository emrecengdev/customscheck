"""
KKDF (Kaynak Kullanımını Destekleme Fonu) Kontrol modülü.
Belirtilen ödeme şekli kodu ve rejim kodlarına göre KKDF kontrolü yapar.
"""

import pandas as pd
import os

def check_kkdf_kontrol(df):
    """
    KKDF kontrol analizi yapar.
    
    Kontrol kriterleri:
    1. OdemeSekliKodu sütununda: 2, 3, 12, 7 kodları hariç tutulur
    2. Rejim sütununda: 4000, 4071, 6121, 6123 kodlu olanları filtreler  
    3. KKDF.xlsx dosyasından GTİP bazında KKDF yükümlülüğünü kontrol eder
    4. Vergi kod sütunlarında 991 kodunu arayıp miktar kontrolü yapar
    
    Args:
        df (pandas.DataFrame): Beyanname verileri içeren DataFrame
    
    Returns:
        dict: Analiz sonuçları
    """
    
    # Gerekli sütunları kontrol et
    required_columns = ['Gtip']
    missing_columns = [col for col in required_columns if col not in df.columns]
    
    if missing_columns:
        return {
            "status": "error",
            "message": f"Gerekli sütunlar bulunamadı: {', '.join(missing_columns)}"
        }
    
    # KKDF Excel dosyasını yükle
    try:
        kkdf_file_path = os.path.join('VERGİLER', 'KKDF.xlsx')
        if not os.path.exists(kkdf_file_path):
            return {
                "status": "error",
                "message": "KKDF.xlsx dosyası bulunamadı (VERGİLER klasöründe olmalı)"
            }
        
        kkdf_df = pd.read_excel(kkdf_file_path, skiprows=1)
        kkdf_lookup = dict(zip(kkdf_df['GTİP'].astype(str), kkdf_df['KKDF ORANI']))
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"KKDF.xlsx dosyası okunamadı: {str(e)}"
        }
    
    # 1. Ödeme şekli filtresi - OdemeSekliKodu sütununa göre
    odeme_kodu_sutunu = None
    for col in df.columns:
        if 'odemseklkodu' in col.lower().replace('e', '').replace('i', '') or 'odemeseklikodu' in col.lower():
            odeme_kodu_sutunu = col
            break
    
    if odeme_kodu_sutunu:
        # 2, 3, 12, 7 kodları hariç tutulacak
        haric_kodlar = [2, 3, 12, 7, '2', '3', '12', '7']
        
        # Önce string olarak kontrol et
        odeme_kodu_str = df[odeme_kodu_sutunu].astype(str).str.strip()
        odeme_filtresi_str = ~odeme_kodu_str.isin(['2', '3', '12', '7'])
        
        # Sonra sayısal olarak kontrol et
        try:
            odeme_kodu_num = pd.to_numeric(df[odeme_kodu_sutunu], errors='coerce')
            odeme_filtresi_num = ~odeme_kodu_num.isin([2, 3, 12, 7])
            # Her iki filtreyi birleştir (OR mantığı)
            odeme_filtresi = odeme_filtresi_str & odeme_filtresi_num
        except:
            odeme_filtresi = odeme_filtresi_str
        
        filtered_df = df[odeme_filtresi].copy()
        haric_tutulan = len(df) - len(filtered_df)
        odeme_mesaj = f"Ödeme şekli kodu filtresi uygulandı ({odeme_kodu_sutunu}): {haric_tutulan} kayıt hariç tutuldu (kodlar: 2,3,12,7), {len(filtered_df)} kayıt kaldı"
    else:
        filtered_df = df.copy()
        odeme_mesaj = "OdemeSekliKodu sütunu bulunamadı, tüm kayıtlar dahil edildi"
    
    # 2. Rejim kodu filtresi
    rejim_sutunu = None
    for col in df.columns:
        if 'rejim' in col.lower():
            rejim_sutunu = col
            break
    
    if rejim_sutunu:
        rejim_kodlari = ['4000', '4071', '6121', '6123']
        rejim_filtresi = filtered_df[rejim_sutunu].astype(str).isin(rejim_kodlari)
        filtered_df = filtered_df[rejim_filtresi].copy()
        rejim_mesaj = f"Rejim kodu filtresi uygulandı ({rejim_sutunu}): {len(filtered_df)} kayıt"
    else:
        rejim_mesaj = "Rejim sütunu bulunamadı, rejim filtresi uygulanmadı"
    
    if len(filtered_df) == 0:
        return {
            "status": "ok",
            "message": "Belirtilen kriterlere uyan kayıt bulunamadı"
        }
    
    # 3. GTİP bazında KKDF yükümlülüğü kontrolü
    filtered_df['KKDF_Yukumlulugu'] = filtered_df['Gtip'].astype(str).map(kkdf_lookup)
    filtered_df['KKDF_Yukumlulugu'] = filtered_df['KKDF_Yukumlulugu'].fillna(-1)  # Bulunamayan GTİP'ler için -1
    
    # KKDF'ye tabi olan kayıtları bul
    kkdf_tabi_df = filtered_df[filtered_df['KKDF_Yukumlulugu'] == 6].copy()
    
    if len(kkdf_tabi_df) == 0:
        return {
            "status": "ok",
            "message": f"Filtrelenen {len(filtered_df)} kayıt arasında KKDF'ye tabi GTİP bulunamadı"
        }
    
    # 4. Vergi kod sütunlarında 991 kodunu ara ve miktar kontrolü yap
    vergi_kod_sutunlari = [col for col in df.columns if col.startswith('Vergi_') and col.endswith('_Kod')]
    vergi_miktar_sutunlari = [col for col in df.columns if col.startswith('Vergi_') and col.endswith('_Miktar')]
    
    if not vergi_kod_sutunlari:
        return {
            "status": "error",
            "message": "Vergi kod sütunları bulunamadı (Vergi_X_Kod formatında)"
        }
    
    # KKDF (kod 991) verilerini topla
    kkdf_beyan_verileri = []
    
    for kod_sutun in vergi_kod_sutunlari:
        try:
            vergi_no = kod_sutun.split('_')[1]
            miktar_sutun = f'Vergi_{vergi_no}_Miktar'
            
            if miktar_sutun not in df.columns:
                continue
            
            # KKDF kodu (991) olan satırları bul - iyileştirilmiş arama
            # Önce string olarak ara
            kod_string = kkdf_tabi_df[kod_sutun].astype(str).str.strip()
            kkdf_beyan_satirlari = kkdf_tabi_df[kod_string == '991'].copy()
            
            # Eğer bulunamazsa sayısal değer olarak da ara
            if len(kkdf_beyan_satirlari) == 0:
                try:
                    kod_sayisal = pd.to_numeric(kkdf_tabi_df[kod_sutun], errors='coerce')
                    kkdf_beyan_satirlari = kkdf_tabi_df[kod_sayisal == 991].copy()
                except:
                    pass
            
            # Eğer hala bulunamazsa, boşlukları ve özel karakterleri temizleyerek ara
            if len(kkdf_beyan_satirlari) == 0:
                try:
                    kod_temiz = kkdf_tabi_df[kod_sutun].astype(str).str.replace(r'[^\d]', '', regex=True)
                    kkdf_beyan_satirlari = kkdf_tabi_df[kod_temiz == '991'].copy()
                except:
                    pass
            
            if len(kkdf_beyan_satirlari) > 0:
                # Miktar sütununu temizle ve sayıya çevir - iyileştirilmiş
                miktar_ham = kkdf_beyan_satirlari[miktar_sutun].astype(str)
                
                # Çeşitli temizlik işlemleri
                miktar_temiz = miktar_ham.str.strip()  # Boşlukları temizle
                miktar_temiz = miktar_temiz.str.replace(',', '.')  # Virgülü noktaya çevir
                miktar_temiz = miktar_temiz.str.replace(' ', '')  # Tüm boşlukları kaldır
                miktar_temiz = miktar_temiz.str.replace(r'[^\d\.\-]', '', regex=True)  # Sadece rakam, nokta ve eksi işareti bırak
                
                # Sayıya çevir
                kkdf_beyan_satirlari['Temiz_KKDF_Miktar'] = pd.to_numeric(miktar_temiz, errors='coerce')
                
                # Vergi sütun bilgisini ekle
                kkdf_beyan_satirlari['Vergi_Sutun_No'] = vergi_no
                kkdf_beyan_satirlari['Vergi_Kod_Sutun'] = kod_sutun
                kkdf_beyan_satirlari['Vergi_Miktar_Sutun'] = miktar_sutun
                kkdf_beyan_satirlari['Orijinal_KKDF_Miktar'] = kkdf_beyan_satirlari[miktar_sutun]
                
                kkdf_beyan_verileri.append(kkdf_beyan_satirlari)
        
        except (IndexError, ValueError):
            continue
    
    # Sonuçları analiz et
    if not kkdf_beyan_verileri:
        # KKDF'ye tabi ama beyan edilmemiş
        sonuc_df = kkdf_tabi_df.copy()
        sonuc_df['KKDF_Durumu'] = 'Beyan Edilmemiş'
        sonuc_df['KKDF_Miktar'] = 0
        sonuc_df['Problem'] = 'KKDF beyan edilmesi gerekirken beyan edilmemiş'
        
        problem_sayisi = len(sonuc_df)
        mesaj = f"UYARI: {problem_sayisi} kayıtta KKDF beyan edilmesi gerekirken beyan edilmemiş!"
        
    else:
        # KKDF beyan edilmiş kayıtları birleştir
        tum_kkdf_beyan_df = pd.concat(kkdf_beyan_verileri, ignore_index=True)
        
        # Beyan edilmiş ve edilmemiş kayıtları ayır
        beyan_edilen_gtip_beyanname = set()
        for _, row in tum_kkdf_beyan_df.iterrows():
            key = (row['Gtip'], row.get('Beyanname_no', ''))
            beyan_edilen_gtip_beyanname.add(key)
        
        # Sonuç verilerini hazırla
        sonuc_verileri = []
        
        # Beyan edilmiş kayıtlar
        for _, row in tum_kkdf_beyan_df.iterrows():
            miktar = row['Temiz_KKDF_Miktar']
            if pd.isna(miktar) or miktar == 0:
                durum = 'Beyan Edilmiş - Sıfır Miktar'
                problem = 'KKDF beyan edilmiş ama miktar sıfır'
            else:
                durum = 'Beyan Edilmiş - Pozitif Miktar'
                problem = 'Normal'
            
            sonuc_verileri.append({
                'Gtip': row['Gtip'],
                'Beyanname_no': row.get('Beyanname_no', ''),
                'KKDF_Durumu': durum,
                'KKDF_Miktar': miktar if pd.notna(miktar) else 0,
                'Vergi_Sutun': f"Vergi_{row['Vergi_Sutun_No']}",
                'Orijinal_KKDF_Miktar': row['Orijinal_KKDF_Miktar'],
                'Problem': problem,
                'Firma': _get_firma_bilgisi(row),
                'Urun_Tanimi': _get_urun_tanimi(row),
                'Tarih': _get_tarih_bilgisi(row)
            })
        
        # Beyan edilmemiş kayıtlar
        for _, row in kkdf_tabi_df.iterrows():
            key = (row['Gtip'], row.get('Beyanname_no', ''))
            if key not in beyan_edilen_gtip_beyanname:
                sonuc_verileri.append({
                    'Gtip': row['Gtip'],
                    'Beyanname_no': row.get('Beyanname_no', ''),
                    'KKDF_Durumu': 'Beyan Edilmemiş',
                    'KKDF_Miktar': 0,
                    'Vergi_Sutun': '-',
                    'Orijinal_KKDF_Miktar': '-',
                    'Problem': 'KKDF beyan edilmesi gerekirken beyan edilmemiş',
                    'Firma': _get_firma_bilgisi(row),
                    'Urun_Tanimi': _get_urun_tanimi(row),
                    'Tarih': _get_tarih_bilgisi(row)
                })
        
        sonuc_df = pd.DataFrame(sonuc_verileri)
        
        # Problem sayılarını hesapla
        beyan_edilmemis = len(sonuc_df[sonuc_df['KKDF_Durumu'] == 'Beyan Edilmemiş'])
        sifir_miktar = len(sonuc_df[sonuc_df['KKDF_Durumu'] == 'Beyan Edilmiş - Sıfır Miktar'])
        normal = len(sonuc_df[sonuc_df['KKDF_Durumu'] == 'Beyan Edilmiş - Pozitif Miktar'])
        
        problem_sayisi = beyan_edilmemis + sifir_miktar
        
        if problem_sayisi > 0:
            mesaj = f"UYARI: {problem_sayisi} kayıtta KKDF problemi tespit edildi! "
            mesaj += f"(Beyan edilmemiş: {beyan_edilmemis}, Sıfır miktar: {sifir_miktar}, Normal: {normal})"
        else:
            mesaj = f"Tüm KKDF beyanları normal. Toplam {normal} kayıt incelendi."
    
    # Özet tablosu oluştur
    ozet_df = _create_summary_table(sonuc_df, kkdf_tabi_df)
    
    # HTML rapor oluştur
    html_rapor = _html_rapor_olustur(sonuc_df, ozet_df, odeme_mesaj, rejim_mesaj, len(kkdf_tabi_df))
    
    status = "warning" if problem_sayisi > 0 else "ok"
    
    return {
        "status": status,
        "message": mesaj,
        "data": sonuc_df,
        "summary": ozet_df,
        "html_report": html_rapor
    }

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

def _create_summary_table(sonuc_df, kkdf_tabi_df):
    """Özet tablosu oluşturur"""
    if sonuc_df.empty:
        return pd.DataFrame()
    
    # GTİP bazında özet
    gtip_ozet = sonuc_df.groupby('Gtip').agg({
        'KKDF_Durumu': lambda x: ', '.join(x.unique()),
        'Problem': lambda x: 'Var' if any('problem' in str(p).lower() or 'beyan edilmemiş' in str(p).lower() or 'sıfır' in str(p).lower() for p in x) else 'Yok',
        'Beyanname_no': 'count'
    }).reset_index()
    
    gtip_ozet.columns = ['Gtip', 'KKDF_Durumlari', 'Problem_Var_Mi', 'Toplam_Beyanname']
    
    return gtip_ozet

def _html_rapor_olustur(sonuc_df, ozet_df, odeme_mesaj, rejim_mesaj, kkdf_tabi_sayisi):
    """
    KKDF kontrol için HTML rapor oluşturur
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
    .beyan-edilmemis {
        background-color: #ffcdd2;
        color: #c62828;
    }
    .sifir-miktar {
        background-color: #fff3e0;
        color: #ef6c00;
    }
    .normal {
        background-color: #c8e6c9;
        color: #2e7d32;
    }
    </style>
    
    <h2>💰 KKDF (Kaynak Kullanımını Destekleme Fonu) Kontrol Raporu</h2>
    
    <div class="ozet-kutu">
        <h3>📋 Kontrol Açıklaması</h3>
        <p>Bu kontrol, KKDF yükümlülüğü olan işlemlerde KKDF'nin doğru beyan edilip edilmediğini kontrol eder.</p>
        <p><strong>🎯 Kontrol Kriterleri:</strong></p>
        <ul>
            <li>Ödeme şekli: 2, 3, 12, 7 kodları hariç tutulur</li>
            <li>Rejim kodu: 4000, 4071, 6121, 6123</li>
            <li>KKDF.xlsx dosyasından GTİP bazında KKDF yükümlülüğü (oran=6)</li>
            <li>Vergi kod sütunlarında 991 kodu ve miktar kontrolü</li>
        </ul>
        <p><strong>⚠️ Risk:</strong> KKDF yükümlülüğü olan işlemlerde KKDF beyan edilmemesi veya sıfır miktar beyan edilmesi.</p>
    </div>
    """
    
    # Filtre bilgileri
    html += f"""
    <div class="istatistik-kutu">
        <h3>🔍 Uygulanan Filtreler</h3>
        <ul>
            <li><strong>Ödeme Şekli:</strong> {odeme_mesaj}</li>
            <li><strong>Rejim Kodu:</strong> {rejim_mesaj}</li>
            <li><strong>KKDF'ye Tabi GTİP:</strong> {kkdf_tabi_sayisi} kayıt</li>
        </ul>
    </div>
    """
    
    if not sonuc_df.empty:
        # Problem istatistikleri
        beyan_edilmemis = len(sonuc_df[sonuc_df['KKDF_Durumu'] == 'Beyan Edilmemiş'])
        sifir_miktar = len(sonuc_df[sonuc_df['KKDF_Durumu'] == 'Beyan Edilmiş - Sıfır Miktar'])
        normal = len(sonuc_df[sonuc_df['KKDF_Durumu'] == 'Beyan Edilmiş - Pozitif Miktar'])
        
        if beyan_edilmemis > 0 or sifir_miktar > 0:
            html += f"""
            <div class="hata-kutu">
                <h3>🚨 Tespit Edilen Problemler</h3>
                <ul>
                    <li><strong>Beyan Edilmemiş:</strong> {beyan_edilmemis} kayıt</li>
                    <li><strong>Sıfır Miktar:</strong> {sifir_miktar} kayıt</li>
                    <li><strong>Normal:</strong> {normal} kayıt</li>
                </ul>
            </div>
            """
        else:
            html += f"""
            <div class="istatistik-kutu">
                <h3>✅ Sonuç</h3>
                <p>Tüm KKDF beyanları normal görünmektedir. Toplam {normal} kayıt incelendi.</p>
            </div>
            """
        
        # Özet tablosu
        if not ozet_df.empty:
            html += "<h3>📊 GTİP Bazında Özet</h3>"
            html += ozet_df.to_html(index=False, classes="table table-striped", escape=False)
        
        # Detay tablosu
        html += "<h3>📋 Detaylı Analiz Sonuçları</h3>"
        
        # Tabloyu durum bazında renklendir
        styled_df = sonuc_df.copy()
        
        # HTML tablosunu oluştur
        html += '<table class="table table-striped">'
        html += '<thead><tr>'
        for col in styled_df.columns:
            html += f'<th>{col}</th>'
        html += '</tr></thead><tbody>'
        
        for _, row in styled_df.iterrows():
            css_class = ""
            if 'Beyan Edilmemiş' in str(row['KKDF_Durumu']):
                css_class = "problem-row"
            elif 'Sıfır Miktar' in str(row['KKDF_Durumu']):
                css_class = "problem-row"
            else:
                css_class = "normal-row"
            
            html += f'<tr class="{css_class}">'
            for col in styled_df.columns:
                value = row[col]
                if col == 'KKDF_Durumu':
                    if 'Beyan Edilmemiş' in str(value):
                        value = f'<span class="durum-kutu beyan-edilmemis">{value}</span>'
                    elif 'Sıfır Miktar' in str(value):
                        value = f'<span class="durum-kutu sifir-miktar">{value}</span>'
                    else:
                        value = f'<span class="durum-kutu normal">{value}</span>'
                html += f'<td>{value}</td>'
            html += '</tr>'
        
        html += '</tbody></table>'
    
    else:
        html += """
        <div class="istatistik-kutu">
            <h3>ℹ️ Bilgi</h3>
            <p>Belirtilen kriterlere uyan kayıt bulunamadı.</p>
        </div>
        """
    
    return html 