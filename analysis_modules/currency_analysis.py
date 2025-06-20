"""
Döviz analiz modülü.
Bu modül, beyannamelerdeki döviz bilgilerinin analizini içerir.
"""

import pandas as pd

def check_currency_values(df):
    """
    Döviz tutarlarının tutarlılığını kontrol eder
    """
    if "Fatura_miktari" not in df.columns or "Fatura_miktarinin_dovizi" not in df.columns:
        return None
    
    # Döviz bazında fatura tutarlarını topla
    try:
        # Boş değerleri filtrele
        filtered_df = df.dropna(subset=["Fatura_miktari", "Fatura_miktarinin_dovizi"])
        if len(filtered_df) == 0:
            return None
            
        # Gruplama yaparak topla
        result = filtered_df.groupby("Fatura_miktarinin_dovizi")["Fatura_miktari"].sum().reset_index()
        return result
    except Exception as e:
        print(f"Döviz değerleri kontrolünde hata: {str(e)}")
        return None

def check_rarely_used_currency(df):
    """
    Firmalara göre nadiren kullanılan para birimlerini kontrol eder
    """
    if 'Fatura_miktarinin_dovizi' not in df.columns:
        return {
            "status": "error",
            "message": "Döviz bilgisi sütunu bulunamadı"
        }
    
    # Firma sütunlarını belirle
    firma_columns = [
        'Adi_unvani', 'Gonderen', 'Gonderen_adi', 'Gonderen_firma', 
        'Ihracatci', 'Ithalatci', 'Satici', 'Alici'
    ]
    
    # Mevcut olan firma sütununu bul
    firma_column = None
    for col in firma_columns:
        if col in df.columns:
            firma_column = col
            break
    
    if not firma_column:
        return {
            "status": "error",
            "message": "Firma/ithalatçı/ihracatçı sütunu bulunamadı"
        }
    
    # Boş firma ve döviz değerlerini filtrele
    filtered_df = df[
        (df[firma_column].notna()) & 
        (df['Fatura_miktarinin_dovizi'].notna()) &
        (df[firma_column] != '') & 
        (df['Fatura_miktarinin_dovizi'] != '')
    ].copy()
    
    if len(filtered_df) == 0:
        return {
            "status": "error",
            "message": "Filtreleme sonrası incelenecek veri kalmadı"
        }
    
    # Her firma için döviz kullanımını hesapla
    result_data = []
    
    # Firmaları grupla
    for firma, firma_data in filtered_df.groupby(firma_column):
        # Boş veya geçersiz firma adlarını atla
        if pd.isna(firma) or firma == '':
            continue
            
        # Dövizleri say
        doviz_counts = firma_data['Fatura_miktarinin_dovizi'].value_counts()
        
        # En az 2 farklı döviz birimi kullanan firmaları kontrol et
        if len(doviz_counts) >= 2:
            # Toplam beyanname sayısı
            total_beyanname_count = len(firma_data['Beyanname_no'].unique()) if 'Beyanname_no' in firma_data.columns else len(firma_data)
            
            # En çok ve en az kullanılan dövizleri belirle
            most_common_currency = doviz_counts.index[0]
            most_common_count = doviz_counts.iloc[0]
            most_common_percentage = (most_common_count / len(firma_data)) * 100
            
            # Nadiren kullanılan dövizleri bul
            threshold_percentage = 10  # %10'dan az kullanılanlar "nadir" olarak kabul edilecek
            rarely_used_currencies = []
            
            for currency, count in doviz_counts.items():
                if currency == most_common_currency:
                    continue
                    
                percentage = (count / len(firma_data)) * 100
                if percentage < threshold_percentage:
                    # Nadir kullanılan döviz birimi beyanname sayısını hesapla
                    if 'Beyanname_no' in firma_data.columns:
                        beyanname_count = len(firma_data[firma_data['Fatura_miktarinin_dovizi'] == currency]['Beyanname_no'].unique())
                        sample_beyannames = firma_data[firma_data['Fatura_miktarinin_dovizi'] == currency]['Beyanname_no'].unique()
                        sample_beyannames = sample_beyannames[:5].tolist()  # En fazla 5 örnek
                    else:
                        beyanname_count = count
                        sample_beyannames = []
                    
                    rarely_used_currencies.append({
                        'doviz': currency,
                        'sayi': count,
                        'beyanname_sayisi': beyanname_count,
                        'yuzde': percentage,
                        'ornek_beyannameler': sample_beyannames
                    })
            
            # Nadir kullanılan döviz birimi varsa sonuca ekle
            if rarely_used_currencies:
                result_data.append({
                    'firma': firma,
                    'toplam_beyanname': total_beyanname_count,
                    'en_cok_kullanilan_doviz': most_common_currency,
                    'en_cok_kullanilan_doviz_yuzdesi': most_common_percentage,
                    'nadir_kullanilan_dovizler': rarely_used_currencies
                })
    
    if not result_data:
        return {
            "status": "ok",
            "message": "Nadiren kullanılan döviz birimi tespit edilmedi"
        }
    
    # Sonuç dataframe'i oluştur
    result_rows = []
    
    for item in result_data:
        firma = item['firma']
        
        for currency_info in item['nadir_kullanilan_dovizler']:
            currency = currency_info['doviz']
            count = currency_info['sayi']
            beyanname_count = currency_info['beyanname_sayisi']
            percentage = currency_info['yuzde']
            sample_beyannames = currency_info['ornek_beyannameler']
            
            # Örnek beyannameleri ilgili veriyi al
            sample_data = filtered_df[
                (filtered_df[firma_column] == firma) & 
                (filtered_df['Fatura_miktarinin_dovizi'] == currency)
            ]
            
            if 'Beyanname_no' in sample_data.columns and sample_beyannames:
                sample_data = sample_data[sample_data['Beyanname_no'].isin(sample_beyannames)]
            
            for _, row in sample_data.head(5).iterrows():  # En fazla 5 örnek
                result_row = {
                    'Firma': firma,
                    'Nadiren_Kullanilan_Doviz': currency,
                    'Kullanim_Sayisi': count,
                    'Beyanname_Sayisi': beyanname_count,
                    'Kullanim_Yuzdesi': round(percentage, 2),
                    'En_Cok_Kullanilan_Doviz': item['en_cok_kullanilan_doviz'],
                    'Toplam_Beyanname': item['toplam_beyanname']
                }
                
                # Beyannameye ilişkin detayları ekle
                for col in ['Beyanname_no', 'Fatura_miktarinin_dovizi', 'Fatura_miktari', 'Gtip', 'Rejim']:
                    if col in row:
                        result_row[col] = row[col]
                
                result_rows.append(result_row)
    
    # Tüm sonuçları içeren DataFrame
    result_df = pd.DataFrame(result_rows)
    
    # Özet DataFrame'i
    summary_data = []
    for item in result_data:
        for currency_info in item['nadir_kullanilan_dovizler']:
            summary_data.append({
                'Firma': item['firma'],
                'Toplam_Beyanname': item['toplam_beyanname'],
                'En_Cok_Kullanilan_Doviz': item['en_cok_kullanilan_doviz'],
                'En_Cok_Kullanilan_Doviz_Yuzdesi': round(item['en_cok_kullanilan_doviz_yuzdesi'], 2),
                'Nadir_Kullanilan_Doviz': currency_info['doviz'],
                'Nadir_Kullanilan_Doviz_Sayisi': currency_info['sayi'],
                'Nadir_Kullanilan_Doviz_Beyanname': currency_info['beyanname_sayisi'],
                'Nadir_Kullanilan_Doviz_Yuzdesi': round(currency_info['yuzde'], 2)
            })
    
    summary_df = pd.DataFrame(summary_data)
    
    # HTML rapor oluştur
    html_report = create_rarely_used_currency_html_report(result_data, firma_column)
    
    return {
        "status": "warning" if len(result_data) > 0 else "ok",
        "message": f"{len(result_data)} firmada nadiren kullanılan döviz birimi tespit edildi" if result_data else "Nadiren kullanılan döviz birimi tespit edilmedi",
        "data": result_df,
        "summary": summary_df,
        "html_report": html_report
    }

def create_rarely_used_currency_html_report(result_data, firma_column):
    """
    Nadiren kullanılan döviz için HTML raporu oluşturur
    """
    if not result_data:
        return "<p>Nadiren kullanılan döviz birimi tespit edilmedi.</p>"
    
    # HTML başlık ve style
    html = """
    <!DOCTYPE html>
    <html lang="tr">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Nadiren Kullanılan Döviz Analizi</title>
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 1400px;
                margin: 0 auto;
                padding: 20px;
                background-color: #f8f9fa;
            }
            .header {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 30px;
                border-radius: 15px;
                text-align: center;
                margin-bottom: 30px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            }
            .header h1 {
                margin: 0;
                font-size: 2.5rem;
                font-weight: 300;
            }
            .header p {
                margin: 10px 0 0 0;
                opacity: 0.9;
                font-size: 1.1rem;
            }
            .summary-stats {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 20px;
                margin-bottom: 30px;
            }
            .stat-card {
                background: white;
                padding: 25px;
                border-radius: 12px;
                text-align: center;
                box-shadow: 0 5px 15px rgba(0,0,0,0.1);
                border-left: 4px solid #667eea;
            }
            .stat-number {
                font-size: 2.5rem;
                font-weight: bold;
                color: #667eea;
                margin: 0;
            }
            .stat-label {
                color: #666;
                font-size: 0.9rem;
                margin: 5px 0 0 0;
                text-transform: uppercase;
                letter-spacing: 1px;
            }
            .firm-section {
                background: white;
                margin-bottom: 30px;
                border-radius: 15px;
                overflow: hidden;
                box-shadow: 0 5px 20px rgba(0,0,0,0.1);
            }
            .firm-header {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 20px 30px;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            .firm-name {
                font-size: 1.3rem;
                font-weight: 600;
            }
            .firm-badge {
                background: rgba(255,255,255,0.2);
                padding: 5px 15px;
                border-radius: 20px;
                font-size: 0.9rem;
            }
            .info-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 20px;
                padding: 30px;
            }
            .info-card {
                background: #f8f9fa;
                padding: 20px;
                border-radius: 10px;
                border-left: 4px solid #667eea;
            }
            .info-card h4 {
                margin: 0 0 10px 0;
                color: #333;
                font-size: 1rem;
            }
            .info-value {
                font-size: 1.4rem;
                font-weight: bold;
                color: #667eea;
                margin-bottom: 5px;
            }
            .percentage {
                color: #666;
                font-size: 0.9rem;
            }
            .currency-table {
                margin-top: 25px;
                overflow-x: auto;
            }
            .currency-table table {
                width: 100%;
                border-collapse: collapse;
                background: white;
                border-radius: 8px;
                overflow: hidden;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            .currency-table th {
                background: #667eea;
                color: white;
                padding: 15px;
                text-align: left;
                font-weight: 600;
            }
            .currency-table td {
                padding: 12px 15px;
                border-bottom: 1px solid #eee;
            }
            .currency-table tr:hover {
                background-color: #f8f9fa;
            }
            .rare-currency {
                background-color: #fff3cd;
                color: #856404;
                padding: 2px 8px;
                border-radius: 4px;
                font-weight: 500;
            }
            .beyanname-info {
                background: #e7f3ff;
                color: #0066cc;
                padding: 2px 8px;
                border-radius: 4px;
                font-weight: 500;
            }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🪙 Nadiren Kullanılan Döviz Analizi</h1>
            <p>Firmaların nadir kullandığı döviz birimlerinin detaylı analizi</p>
        </div>
    """
    
    # Özet istatistikler
    total_firms = len(result_data)
    total_rare_currencies = sum(len(item['nadir_kullanilan_dovizler']) for item in result_data)
    
    html += f"""
        <div class="summary-stats">
            <div class="stat-card">
                <div class="stat-number">{total_firms}</div>
                <div class="stat-label">Firma Sayısı</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{total_rare_currencies}</div>
                <div class="stat-label">Nadir Döviz Türü</div>
            </div>
        </div>
    """
    
    # Her firma için detayları göster
    for item in result_data:
        firma = item['firma']
        toplam_beyanname = item['toplam_beyanname']
        en_cok_kullanilan = item['en_cok_kullanilan_doviz']
        en_cok_yuzde = round(item['en_cok_kullanilan_doviz_yuzdesi'], 1)
        nadir_kullanilan_list = item['nadir_kullanilan_dovizler']
        
        html += f"""
                <div class="firm-section">
                    <div class="firm-header">
                        <div class="firm-name">🏢 {firma}</div>
                        <div class="firm-badge">{len(nadir_kullanilan_list)} nadir döviz</div>
                    </div>
                    
                    <div class="info-grid">
                        <div class="info-card">
                            <h4>En Çok Kullanılan Döviz</h4>
                            <div class="info-value">{en_cok_kullanilan}</div>
                            <div class="percentage">%{en_cok_yuzde}</div>
                        </div>
                        <div class="info-card">
                            <h4>Toplam Beyanname</h4>
                            <div class="info-value">{toplam_beyanname}</div>
                            <div class="percentage">beyanname sayısı</div>
                        </div>
                        <div class="info-card">
                            <h4>Nadir Döviz Türü</h4>
                            <div class="info-value">{len(nadir_kullanilan_list)}</div>
                            <div class="percentage">farklı döviz</div>
                        </div>
                    </div>
                    
                    <div class="currency-table">
                        <table>
                            <thead>
                                <tr>
                                    <th>Nadir Döviz</th>
                                    <th>Kullanım Sayısı</th>
                                    <th>Beyanname Sayısı</th>
                                    <th>Kullanım Oranı</th>
                                    <th>Örnek Beyannameler</th>
                                </tr>
                            </thead>
                            <tbody>
        """
        
        for doviz_info in nadir_kullanilan_list:
            doviz = doviz_info['doviz']
            sayi = doviz_info['sayi']
            beyanname_sayisi = doviz_info['beyanname_sayisi']
            yuzde = round(doviz_info['yuzde'], 1)
            ornekler = doviz_info['ornek_beyannameler']
            
            # Örnek beyannameleri string'e çevir
            ornek_str = ", ".join(ornekler[:3]) + ("..." if len(ornekler) > 3 else "")
            if not ornek_str:
                ornek_str = "-"
            
            html += f"""
                                <tr>
                                    <td><span class="rare-currency">{doviz}</span></td>
                                    <td>{sayi}</td>
                                    <td><span class="beyanname-info">{beyanname_sayisi} beyanname</span></td>
                                    <td>%{yuzde}</td>
                                    <td>{ornek_str}</td>
                                </tr>
            """
        
        html += """
                            </tbody>
                        </table>
                    </div>
                </div>
        """
    
    html += """
    </body>
    </html>
    """
    
    return html 