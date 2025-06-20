"""
Birim fiyat artışı analiz modülü.
Aynı gönderici, aynı GTIP ve aynı ticari tanıma sahip eşyaların birim fiyatlarının 
zaman içinde önemli oranda artıp artmadığını kontrol eder.
"""

import pandas as pd
import numpy as np

def check_unit_price_increase(df):
    """
    Aynı gönderici, aynı GTIP kodu ve aynı ticari tanıma sahip eşyaların birim fiyatlarının
    beyanname tarihleri itibariyle %10'un üzerinde artıp artmadığını kontrol eder.
    
    Birim fiyat = İstatistiki_kiymet / Miktar olarak hesaplanır.
    
    Args:
        df (pandas.DataFrame): Beyanname verileri içeren DataFrame
    
    Returns:
        dict: Analiz sonuçları
    """
    # Gerekli sütunların varlığını kontrol et
    required_columns = ['Gtip', 'Ticari_tanimi', 'Adi_unvani', 'Beyanname_no']
    missing_columns = [col for col in required_columns if col not in df.columns]
    
    if missing_columns:
        return {
            "status": "error",
            "message": f"Gerekli sütunlar eksik: {', '.join(missing_columns)}"
        }
    
    # Birim fiyat hesaplaması için gerekli sütunlar
    if 'Istatistiki_kiymet' not in df.columns:
        return {
            "status": "error",
            "message": "Istatistiki_kiymet sütunu bulunamadı"
        }
    
    if 'Miktar' not in df.columns:
        return {
            "status": "error",
            "message": "Miktar sütunu bulunamadı"
        }
    
    # Tarih sütunu kontrolü - hem büyük hem küçük harfli sürümleri kontrol et
    date_column = None
    for col in ['Beyanname_Tarihi', 'Beyanname_tarihi', 'Tescil_tarihi', 'Tescil_Tarihi', 'Tarih']:
        if col in df.columns:
            date_column = col
            break
    
    if not date_column:
        return {
            "status": "error",
            "message": "Tarih bilgisi sütunu bulunamadı"
        }
    
    # Temiz bir çalışma kopyası oluştur
    work_df = df.copy()
    
    # Sadece IM geçen beyanname numaralarını filtrele
    work_df = work_df[work_df['Beyanname_no'].str.contains('IM', case=False, na=False)]
    
    # Filtreleme sonrası veri kalmadıysa hata ver
    if len(work_df) == 0:
        return {
            "status": "error",
            "message": "IM içeren beyanname bulunamadı"
        }
    
    # Tarih sütununu datetime formatına dönüştür
    try:
        # Türkiye'de kullanılan gün.ay.yıl formatı için dayfirst=True parametresini ekledik
        work_df[date_column] = pd.to_datetime(work_df[date_column], dayfirst=True, errors='coerce')
    except Exception as e:
        return {
            "status": "error",
            "message": f"Tarih sütunu dönüştürülemedi: {str(e)}"
        }
    
    # Tarihi olmayan verileri filtrele
    work_df = work_df.dropna(subset=[date_column])
    
    # Sayısal sütunları düzelt
    work_df['Istatistiki_kiymet'] = pd.to_numeric(work_df['Istatistiki_kiymet'], errors='coerce')
    work_df['Miktar'] = pd.to_numeric(work_df['Miktar'], errors='coerce')
    
    # Geçersiz değerleri filtrele
    work_df = work_df.dropna(subset=['Istatistiki_kiymet', 'Miktar'])
    work_df = work_df[work_df['Miktar'] > 0]  # Miktar sıfırdan büyük olmalı
    
    # Birim fiyat hesapla ve 2 ondalık basamağa yuvarla
    work_df['Birim_Fiyat'] = (work_df['Istatistiki_kiymet'] / work_df['Miktar']).round(2)
    
    # Döviz cinsi kontrolü - opsiyonel
    currency_column = None
    for col in ['Doviz_cinsi', 'Fatura_doviz']:
        if col in work_df.columns:
            currency_column = col
            break
    
    # Sonuç verisini toplamak için liste
    result_data = []
    
    # Aynı gönderici, GTIP ve ticari tanıma göre grupla
    group_columns = ['Adi_unvani', 'Gtip', 'Ticari_tanimi']
    
    # Eğer döviz sütunu varsa, bunu da gruplama kriterlerine ekle
    if currency_column:
        group_columns.append(currency_column)
    
    # Her bir grup için hesaplama yap
    for group_key, group_data in work_df.groupby(group_columns):
        # En az 2 kayıt yoksa analiz yapılamaz
        if len(group_data) < 2:
            continue
        
        # Tarihe göre sırala
        sorted_data = group_data.sort_values(by=date_column)
        
        # Her kayıt için karşılaştırma yap
        for i in range(1, len(sorted_data)):
            current_row = sorted_data.iloc[i]
            previous_row = sorted_data.iloc[i-1]
            
            # Birim fiyatları al
            current_price = current_row['Birim_Fiyat']
            previous_price = previous_row['Birim_Fiyat']
            
            # Fiyat artış yüzdesi hesapla ve 2 ondalık basamağa yuvarla
            if previous_price > 0:
                price_increase_pct = ((current_price - previous_price) / previous_price) * 100
                price_increase_pct = round(price_increase_pct, 2)
                
                # %10'dan fazla artış varsa sonuçlara ekle
                if price_increase_pct > 10:
                    # Grup verilerini ayır
                    if currency_column:
                        gonderici, gtip, ticari_tanim, doviz = group_key
                    else:
                        gonderici, gtip, ticari_tanim = group_key
                        doviz = "Bilinmiyor"
                    
                    # Birim fiyatları 2 ondalık basamağa yuvarla
                    result_row = {
                        'Gonderici': gonderici,
                        'Gtip': gtip,
                        'Ticari_Tanim': ticari_tanim,
                        'Doviz': doviz,
                        'Onceki_Beyanname_No': previous_row['Beyanname_no'],
                        'Yeni_Beyanname_No': current_row['Beyanname_no'],
                        'Onceki_Tarih': previous_row[date_column],
                        'Yeni_Tarih': current_row[date_column],
                        'Gun_Farki': (current_row[date_column] - previous_row[date_column]).days,
                        'Onceki_Toplam_Kiymet': round(previous_row['Istatistiki_kiymet'], 2),
                        'Yeni_Toplam_Kiymet': round(current_row['Istatistiki_kiymet'], 2),
                        'Onceki_Miktar': round(previous_row['Miktar'], 2),
                        'Yeni_Miktar': round(current_row['Miktar'], 2),
                        'Onceki_Birim_Fiyat': round(previous_price, 2),
                        'Yeni_Birim_Fiyat': round(current_price, 2),
                        'Artis_Yuzdesi': price_increase_pct
                    }
                    
                    result_data.append(result_row)
    
    if not result_data:
        return {
            "status": "ok",
            "message": "Birim fiyatlarda %10'dan fazla artış tespit edilmedi"
        }
    
    # Sonuçları DataFrame'e dönüştür
    result_df = pd.DataFrame(result_data)
    
    # Özet tablosu oluştur
    total_cases = len(result_df)
    affected_gtips = result_df['Gtip'].nunique()
    affected_suppliers = result_df['Gonderici'].nunique()
    avg_increase = round(result_df['Artis_Yuzdesi'].mean(), 2)
    max_increase = round(result_df['Artis_Yuzdesi'].max(), 2)
    
    # Artış yüzdesine göre sırala
    result_df = result_df.sort_values('Artis_Yuzdesi', ascending=False)
    
    # Özet tablosu
    summary_data = {
        'Metrik': [
            'Tespit Edilen Toplam Birim Fiyat Artışı',
            'Etkilenen GTIP Sayısı',
            'Etkilenen Gönderici Sayısı',
            'Ortalama Artış Yüzdesi',
            'En Yüksek Artış Yüzdesi'
        ],
        'Değer': [
            total_cases,
            affected_gtips,
            affected_suppliers,
            f"%{avg_increase}",
            f"%{max_increase}"
        ]
    }
    summary_df = pd.DataFrame(summary_data)
    
    # HTML rapor oluştur
    html_report = _generate_price_increase_html_report(result_df, summary_df)
    
    # Sonuç mesajını oluştur
    message = f"{total_cases} adet önemli birim fiyat artışı tespit edildi. " + \
             f"{affected_gtips} GTIP ve {affected_suppliers} göndericiden etkilenmiştir. " + \
             f"Ortalama artış: %{avg_increase}"
    
    return {
        "status": "warning",
        "message": message,
        "data": result_df,
        "summary": summary_df,
        "html_report": html_report
    }

def _generate_price_increase_html_report(result_df, summary_df):
    """
    Birim fiyat artışı kontrolü için HTML rapor oluşturur
    """
    # HTML şablonu
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
    .summary-box {
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
    .warning {
        color: #e74c3c;
        font-weight: bold;
    }
    .info-card {
        background-color: #e3f2fd;
        border-left: 4px solid #2196f3;
        padding: 12px;
        margin: 15px 0;
        border-radius: 4px;
    }
    .critical {
        background-color: #ffebee;
        border-left: 4px solid #f44336;
    }
    .moderate {
        background-color: #fff8e1;
        border-left: 4px solid #ffc107;
    }
    .supplier-section {
        margin-top: 30px;
        padding-top: 10px;
        border-top: 1px dashed #ccc;
    }
    .increase-high {
        color: #d32f2f;
        font-weight: bold;
    }
    .increase-medium {
        color: #f57c00;
        font-weight: bold;
    }
    .increase-low {
        color: #388e3c;
        font-weight: bold;
    }
    </style>
    
    <h2>Birim Fiyat Artışı Analiz Raporu</h2>
    
    <div class="summary-box">
        <h3>Kontrol Özeti</h3>
        <p>Bu kontrol, aynı gönderici, aynı GTIP kodu ve aynı ticari tanıma sahip eşyaların birim fiyatlarının, 
        beyanname tarihleri itibariyle %10'un üzerinde artıp artmadığını kontrol eder.</p>
        <p><strong>Analiz Kriterleri:</strong></p>
        <ul>
            <li>Sadece 'IM' içeren beyanname numaraları dikkate alınır</li>
            <li>Birim fiyat = İstatistiki kıymet / Miktar olarak hesaplanır</li>
            <li>Aynı gönderici, aynı GTIP ve aynı ticari tanım gruplandırılır</li>
            <li>Tarihe göre sıralama yapılır</li>
            <li>Ardışık beyannameler arasında %10'dan fazla birim fiyat artışı tespit edilir</li>
        </ul>
    </div>
    """
    
    # Özet tablosunu ekle
    html += "<h3>Kontrol Sonuçları</h3>"
    html += summary_df.to_html(index=False, classes="table table-striped")
    
    # Gönderici bazlı gruplandırma
    if not result_df.empty:
        html += "<h3>En Yüksek Birim Fiyat Artışları</h3>"
        
        # En yüksek 10 artışı göster
        top_increases = result_df.head(10)
        
        # Gösterilecek sütunları seç
        display_cols = [
            'Gonderici', 'Gtip', 'Ticari_Tanim', 'Doviz',
            'Onceki_Birim_Fiyat', 'Yeni_Birim_Fiyat', 'Artis_Yuzdesi',
            'Onceki_Tarih', 'Yeni_Tarih', 'Gun_Farki'
        ]
        
        # Mevcut sütunları kontrol et
        existing_cols = [col for col in display_cols if col in top_increases.columns]
        display_df = top_increases[existing_cols].copy()
        
        # Sütun isimlerini Türkçe yap
        column_mapping = {
            'Gonderici': 'Gönderici',
            'Gtip': 'GTİP',
            'Ticari_Tanim': 'Ticari Tanım', 
            'Doviz': 'Döviz',
            'Onceki_Birim_Fiyat': 'Önceki Birim Fiyat', 
            'Yeni_Birim_Fiyat': 'Yeni Birim Fiyat', 
            'Artis_Yuzdesi': 'Artış (%)',
            'Onceki_Tarih': 'Önceki Tarih', 
            'Yeni_Tarih': 'Yeni Tarih', 
            'Gun_Farki': 'Gün Farkı'
        }
        
        # Sadece mevcut sütunlar için eşleştirmeleri kullan
        mapping = {k: v for k, v in column_mapping.items() if k in display_df.columns}
        display_df.columns = [mapping.get(col, col) for col in display_df.columns]
        
        # Artış yüzdesini formatlı göster
        if 'Artış (%)' in display_df.columns:
            display_df['Artış (%)'] = display_df['Artış (%)'].apply(lambda x: f"%{x}")
        
        html += display_df.to_html(index=False, classes="table table-striped")
        
        # Gönderici bazlı gruplandırma
        html += "<h3>Gönderici Bazlı Birim Fiyat Artışları</h3>"
        
        # Veriyi gönderici ve GTIP'e göre grupla
        supplier_groups = result_df.groupby(['Gonderici', 'Gtip'])
        
        for (supplier, gtip), group_data in supplier_groups:
            html += f'<div class="supplier-section"><h4>Gönderici: {supplier} - GTİP: {gtip}</h4>'
            
            # Ticari tanım bilgisini ekle
            if 'Ticari_Tanim' in group_data.columns and not group_data['Ticari_Tanim'].isna().all():
                product_desc = group_data['Ticari_Tanim'].iloc[0]
                html += f'<p><strong>Ticari Tanım:</strong> {product_desc}</p>'
            
            # Artışların özeti
            avg_increase = round(group_data['Artis_Yuzdesi'].mean(), 2)
            max_increase = round(group_data['Artis_Yuzdesi'].max(), 2)
            
            html += f'<p><strong>Ortalama Artış:</strong> %{avg_increase} | <strong>En Yüksek Artış:</strong> %{max_increase}</p>'
            
            # Beyannameleri göster
            # Tarihe göre sırala
            sorted_group = group_data.sort_values('Yeni_Tarih')
            
            display_cols = [
                'Onceki_Beyanname_No', 'Yeni_Beyanname_No', 
                'Onceki_Tarih', 'Yeni_Tarih', 
                'Onceki_Birim_Fiyat', 'Yeni_Birim_Fiyat', 'Artis_Yuzdesi'
            ]
            
            # Mevcut sütunları kontrol et
            existing_cols = [col for col in display_cols if col in sorted_group.columns]
            display_df = sorted_group[existing_cols].copy()
            
            # Sütun isimlerini Türkçe yap
            column_mapping = {
                'Onceki_Beyanname_No': 'Önceki Beyanname No',
                'Yeni_Beyanname_No': 'Yeni Beyanname No', 
                'Onceki_Tarih': 'Önceki Tarih', 
                'Yeni_Tarih': 'Yeni Tarih',
                'Onceki_Birim_Fiyat': 'Önceki Birim Fiyat', 
                'Yeni_Birim_Fiyat': 'Yeni Birim Fiyat', 
                'Artis_Yuzdesi': 'Artış (%)'
            }
            
            # Sadece mevcut sütunlar için eşleştirmeleri kullan
            mapping = {k: v for k, v in column_mapping.items() if k in display_df.columns}
            display_df.columns = [mapping.get(col, col) for col in display_df.columns]
            
            # Artış yüzdesini formatlı göster
            if 'Artış (%)' in display_df.columns:
                display_df['Artış (%)'] = display_df['Artış (%)'].apply(lambda x: f"%{x}")
            
            html += display_df.to_html(index=False, classes="table table-striped")
            
            html += '</div>'
    
    # Değerlendirme bölümü
    html += """
    <h3>Değerlendirme</h3>
    <p>Aynı gönderici, GTIP ve ticari tanıma sahip eşyalarda birim fiyat artışları şu nedenlere bağlı olabilir:</p>
    <ul>
        <li>Hammadde veya üretim maliyetlerindeki artışlar</li>
        <li>Döviz kurlarındaki dalgalanmalar</li>
        <li>Tedarik zincirindeki aksaklıklar</li>
        <li>Mevsimsel etkiler veya küresel fiyat değişimleri</li>
        <li>Transfer fiyatlandırması uygulamaları</li>
        <li>Gümrük kıymet beyanında eksik veya hatalı bildirimler</li>
    </ul>
    <p>Özellikle kısa süre içinde yüksek oranda gerçekleşen fiyat artışları daha detaylı inceleme gerektirebilir.</p>
    """
    
    return html 