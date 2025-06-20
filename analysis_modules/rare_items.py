"""
Nadiren kullanılan öğelerin (menşe ülke, ödeme şekli) analizi modülü.
Firmaların alışılmışın dışında kullandıkları menşe ülke ve ödeme şekillerini tespit eder.
"""

import pandas as pd

def _create_rarely_used_html_report(result_data, item_type, firma_column):
    """
    Nadiren kullanılan öğelerin (döviz, menşe ülke, ödeme şekli) gelişmiş HTML raporunu oluşturur
    
    Args:
        result_data (list): Analiz sonuçları listesi
        item_type (str): Öğe tipi ("döviz", "menşe ülke", "ödeme şekli")
        firma_column (str): Firma sütun adı
        
    Returns:
        str: HTML rapor içeriği
    """
    if not result_data:
        return """
        <div style="padding: 20px; text-align: center;">
            <h3>Nadiren kullanılan """ + item_type + """ bulunamadı.</h3>
            <p>Tüm firmalar tutarlı """ + item_type + """ kullanımı göstermektedir.</p>
        </div>
        """
    
    # CSS stilleri
    html = f"""
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                margin: 0;
                padding: 20px;
                background-color: #f8f9fa;
                color: #333;
                line-height: 1.6;
            }}
            .container {{
                max-width: 1400px;
                margin: 0 auto;
                background-color: white;
                border-radius: 10px;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                overflow: hidden;
            }}
            .header {{
                background: linear-gradient(135deg, #6a11cb 0%, #2575fc 100%);
                color: white;
                padding: 30px;
                text-align: center;
            }}
            .header h1 {{
                margin: 0;
                font-size: 28px;
                font-weight: 300;
            }}
            .header p {{
                margin: 10px 0 0 0;
                opacity: 0.9;
            }}
            .content {{
                padding: 30px;
            }}
            .summary-box {{
                background: linear-gradient(135deg, #fff3cd 0%, #ffeaa7 100%);
                border: 1px solid #ffc107;
                border-radius: 8px;
                padding: 20px;
                margin-bottom: 25px;
                border-left: 5px solid #ffc107;
            }}
            .summary-title {{
                font-size: 18px;
                font-weight: bold;
                color: #856404;
                margin-bottom: 15px;
                display: flex;
                align-items: center;
            }}
            .summary-title::before {{
                content: "🔍";
                margin-right: 10px;
                font-size: 20px;
            }}
            .stats-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 20px;
                margin: 25px 0;
            }}
            .stat-card {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border-radius: 10px;
                padding: 20px;
                text-align: center;
                box-shadow: 0 4px 8px rgba(0,0,0,0.1);
            }}
            .stat-number {{
                font-size: 36px;
                font-weight: bold;
                margin-bottom: 5px;
            }}
            .stat-label {{
                font-size: 14px;
                opacity: 0.9;
            }}
            .firm-section {{
                margin: 30px 0;
                padding: 25px;
                background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
                border-radius: 10px;
                border-left: 5px solid #28a745;
                box-shadow: 0 2px 4px rgba(0,0,0,0.05);
            }}
            .firm-header {{
                background: linear-gradient(135deg, #28a745 0%, #20c997 100%);
                color: white;
                padding: 15px 20px;
                border-radius: 8px;
                margin: -25px -25px 20px -25px;
                display: flex;
                align-items: center;
                justify-content: space-between;
            }}
            .firm-name {{
                font-size: 18px;
                font-weight: 600;
            }}
            .firm-badge {{
                background-color: rgba(255,255,255,0.2);
                padding: 5px 12px;
                border-radius: 20px;
                font-size: 12px;
                font-weight: bold;
            }}
            .info-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 20px;
                margin: 20px 0;
            }}
            .info-card {{
                background-color: white;
                padding: 15px;
                border-radius: 8px;
                border: 1px solid #dee2e6;
                box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            }}
            .info-card h4 {{
                color: #495057;
                margin: 0 0 10px 0;
                font-size: 14px;
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }}
            .info-value {{
                font-size: 18px;
                font-weight: bold;
                color: #343a40;
            }}
            .percentage {{
                color: #28a745;
                font-weight: bold;
            }}
            .percentage.low {{
                color: #dc3545;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin: 20px 0;
                background-color: white;
                border-radius: 8px;
                overflow: hidden;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }}
            th {{
                background: linear-gradient(135deg, #3f51b5 0%, #5c6bc0 100%);
                color: white;
                text-align: left;
                padding: 15px;
                font-weight: 600;
                text-transform: uppercase;
                font-size: 12px;
                letter-spacing: 0.5px;
            }}
            td {{
                padding: 12px 15px;
                border-bottom: 1px solid #f0f0f0;
            }}
            tr:nth-child(even) {{
                background-color: #f8f9fa;
            }}
            tr:hover {{
                background-color: #e3f2fd;
                transition: background-color 0.3s ease;
            }}
            .badge {{
                display: inline-block;
                padding: 4px 8px;
                background-color: #e3f2fd;
                color: #1976d2;
                border-radius: 4px;
                font-size: 11px;
                font-weight: bold;
                margin: 1px;
            }}
            .badge.rare {{
                background-color: #ffebee;
                color: #c62828;
            }}
            .evaluation-box {{
                background: linear-gradient(135deg, #e8f5e8 0%, #f0fff0 100%);
                border: 1px solid #c8e6c9;
                border-radius: 8px;
                padding: 25px;
                margin-top: 30px;
                border-left: 5px solid #4caf50;
            }}
            .evaluation-title {{
                color: #2e7d32;
                font-size: 20px;
                font-weight: bold;
                margin-bottom: 15px;
                display: flex;
                align-items: center;
            }}
            .evaluation-title::before {{
                content: "💡";
                margin-right: 10px;
                font-size: 22px;
            }}
            ul {{
                padding-left: 20px;
            }}
            li {{
                margin: 8px 0;
                color: #424242;
            }}
            .beyanname-list {{
                max-height: 100px;
                overflow-y: auto;
                padding: 8px;
                background-color: #f8f9fa;
                border-radius: 4px;
                border: 1px solid #dee2e6;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Nadiren Kullanılan {item_type.title()} Analizi</h1>
                <p>Firma Bazlı {item_type.title()} Kullanım Tutarsızlık Raporu</p>
            </div>
            
            <div class="content">
                <div class="summary-box">
                    <div class="summary-title">Analiz Özeti</div>
                    <p>Bu rapor, firmaların genelde tercih ettiği <strong>{item_type}</strong> seçimlerinden farklı olarak nadiren kullandıkları <strong>{item_type}</strong> öğelerini gösterir.</p>
                    <p>Toplam <strong>{len(result_data)}</strong> firmada nadiren kullanılan {item_type} tespit edilmiştir.</p>
                </div>
    """
    
    # İstatistik kartları
    total_firms = len(result_data)
    total_rare_items = sum([len(item.get('nadir_kullanilan_dovizler', []) or 
                                item.get('nadir_kullanilan_ulkeler', []) or 
                                item.get('nadir_kullanilan_odeme_sekilleri', [])) for item in result_data])
    
    avg_rare_per_firm = round(total_rare_items / total_firms, 1) if total_firms > 0 else 0
    
    html += f"""
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-number">{total_firms}</div>
                        <div class="stat-label">Etkilenen Firma</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">{total_rare_items}</div>
                        <div class="stat-label">Toplam Nadir {item_type.title()}</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">{avg_rare_per_firm}</div>
                        <div class="stat-label">Firma Başına Ortalama</div>
                    </div>
                </div>
    """
    
    # Her firma için ayrı bölüm oluştur
    for i, item in enumerate(result_data):
        firma = item['firma']
        
        # Dinamik alan adları
        if 'en_cok_kullanilan_doviz' in item:
            en_cok_kullanilan = item['en_cok_kullanilan_doviz']
            en_cok_yuzde = round(item['en_cok_kullanilan_doviz_yuzdesi'], 2)
            nadir_kullanilan_list = item['nadir_kullanilan_dovizler']
            nadir_field_name = 'doviz'
        elif 'en_cok_kullanilan_ulke' in item:
            en_cok_kullanilan = item['en_cok_kullanilan_ulke']
            en_cok_yuzde = round(item['en_cok_kullanilan_ulke_yuzdesi'], 2)
            nadir_kullanilan_list = item['nadir_kullanilan_ulkeler']
            nadir_field_name = 'ulke'
        else:
            en_cok_kullanilan = item['en_cok_kullanilan_odeme']
            en_cok_yuzde = round(item['en_cok_kullanilan_odeme_yuzdesi'], 2)
            nadir_kullanilan_list = item['nadir_kullanilan_odeme_sekilleri']
            nadir_field_name = 'odeme'
        
        html += f"""
                <div class="firm-section">
                    <div class="firm-header">
                        <div class="firm-name">🏢 {firma}</div>
                        <div class="firm-badge">{len(nadir_kullanilan_list)} nadir {item_type}</div>
                    </div>
                    
                    <div class="info-grid">
                        <div class="info-card">
                            <h4>En Çok Kullanılan {item_type.title()}</h4>
                            <div class="info-value">{en_cok_kullanilan}</div>
                            <div class="percentage">%{en_cok_yuzde}</div>
                        </div>
                        <div class="info-card">
                            <h4>Nadir Kullanılan {item_type.title()} Sayısı</h4>
                            <div class="info-value">{len(nadir_kullanilan_list)}</div>
                        </div>
                        <div class="info-card">
                            <h4>Toplam Beyanname</h4>
                            <div class="info-value">{item.get('toplam_beyanname', '-')}</div>
                        </div>
                    </div>
                    
                    <table>
                        <thead>
                            <tr>
                                <th>Nadiren Kullanılan {item_type.title()}</th>
                                <th>Kullanım Sayısı</th>
                                <th>Yüzde (%)</th>
                                <th>Örnek Beyannameler</th>
                                <th>O Ülkeye Ait Beyanname Sayısı</th>
                            </tr>
                        </thead>
                        <tbody>
        """
        
        for nadir_item in nadir_kullanilan_list:
            deger = nadir_item[nadir_field_name]
            sayi = nadir_item['sayi']
            yuzde = round(nadir_item['yuzde'], 2)
            ornek_beyannameler = nadir_item.get('ornek_beyannameler', [])
            
            # Beyanname listesini daha güzel göster
            if ornek_beyannameler:
                if len(ornek_beyannameler) <= 5:
                    beyanname_display = ", ".join(ornek_beyannameler)
                else:
                    beyanname_display = f"""
                    <div class="beyanname-list">
                        {", ".join(ornek_beyannameler[:5])}
                        {f" ve {len(ornek_beyannameler)-5} beyanname daha..." if len(ornek_beyannameler) > 5 else ""}
                    </div>
                    """
            else:
                beyanname_display = "-"
            
            percentage_class = "low" if yuzde < 5 else ""
            
            html += f"""
                    <tr>
                        <td><span class="badge rare">{deger}</span></td>
                        <td><strong>{sayi}</strong></td>
                        <td><span class="percentage {percentage_class}">{yuzde}%</span></td>
                        <td>{beyanname_display}</td>
                        <td>{sayi}</td>
                    </tr>
            """
        
        html += """
                        </tbody>
                    </table>
                </div>
        """
    
    # Değerlendirme bölümü
    html += f"""
                <div class="evaluation-box">
                    <div class="evaluation-title">Değerlendirme ve Öneriler</div>
                    <p>Firmaların nadiren kullandığı <strong>{item_type}</strong> öğeleri, aşağıdaki sebeplerden kaynaklanabilir:</p>
                    <ul>
                        <li><strong>Özel Durumlar:</strong> Genellikle tercih edilen {item_type}den farklı özel bir durumun geçici olarak ortaya çıkması</li>
                        <li><strong>Ekonomik Sebepler:</strong> Vergi avantajı veya maliyet düşürme amaçlı işlemler</li>
                        <li><strong>Dönemsel Değişiklikler:</strong> Sadece belirli bir süre veya belirli işlemler için kullanılan farklı {item_type}</li>
                        <li><strong>Operasyonel Hatalar:</strong> Veri girişi hataları veya tutarsız kodlamalar</li>
                        <li><strong>İş Stratejisi Değişiklikleri:</strong> Firmanın iş modelindeki değişikliklere bağlı geçici uygulamalar</li>
                    </ul>
                    <p><strong>Tavsiye:</strong> Bu tip tutarsızlıkların detaylı incelenmesi, işlemlerin tutarlılığı ve risk değerlendirmesi açısından önemlidir. Özellikle düşük yüzdeli kullanımlar dikkatle gözden geçirilmelidir.</p>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html

def check_rarely_used_origin_country(df):
    """
    Firmalara göre nadiren kullanılan menşe ülkeleri kontrol eder
    
    Args:
        df (pandas.DataFrame): Beyanname verileri içeren DataFrame
    
    Returns:
        dict: Analiz sonuçları
    """
    if 'Mensei_ulke' not in df.columns:
        return {
            "status": "error",
            "message": "Menşe ülke bilgisi sütunu bulunamadı"
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
    
    # Boş firma ve menşe ülke değerlerini filtrele
    filtered_df = df[
        (df[firma_column].notna()) & 
        (df['Mensei_ulke'].notna()) &
        (df[firma_column] != '') & 
        (df['Mensei_ulke'] != '')
    ].copy()
    
    if len(filtered_df) == 0:
        return {
            "status": "error",
            "message": "Filtreleme sonrası incelenecek veri kalmadı"
        }
    
    # Her firma için menşe ülke kullanımını hesapla
    result_data = []
    
    # Firmaları grupla
    for firma, firma_data in filtered_df.groupby(firma_column):
        # Boş veya geçersiz firma adlarını atla
        if pd.isna(firma) or firma == '':
            continue
            
        # Menşe ülkeleri say
        ulke_counts = firma_data['Mensei_ulke'].value_counts()
        
        # En az 2 farklı menşe ülke kullanan firmaları kontrol et
        if len(ulke_counts) >= 2:
            # Toplam beyanname sayısı
            total_beyanname_count = len(firma_data['Beyanname_no'].unique())
            
            # En çok ve en az kullanılan menşe ülkeleri belirle
            most_common_country = ulke_counts.index[0]
            most_common_count = ulke_counts.iloc[0]
            most_common_percentage = (most_common_count / len(firma_data)) * 100
            
            # Nadiren kullanılan menşe ülkeleri bul
            threshold_percentage = 10  # %10'dan az kullanılanlar "nadir" olarak kabul edilecek
            rarely_used_countries = []
            
            for country, count in ulke_counts.items():
                if country == most_common_country:
                    continue
                    
                percentage = (count / len(firma_data)) * 100
                if percentage < threshold_percentage:
                    # Nadir kullanılan menşe ülke örnek beyannamelerini bul
                    sample_beyannames = firma_data[firma_data['Mensei_ulke'] == country]['Beyanname_no'].unique()
                    sample_beyannames = sample_beyannames[:5].tolist()  # En fazla 5 örnek
                    
                    rarely_used_countries.append({
                        'ulke': country,
                        'sayi': count,
                        'yuzde': percentage,
                        'ornek_beyannameler': sample_beyannames
                    })
            
            # Nadir kullanılan menşe ülke varsa sonuca ekle
            if rarely_used_countries:
                result_data.append({
                    'firma': firma,
                    'toplam_beyanname': total_beyanname_count,
                    'en_cok_kullanilan_ulke': most_common_country,
                    'en_cok_kullanilan_ulke_yuzdesi': most_common_percentage,
                    'nadir_kullanilan_ulkeler': rarely_used_countries
                })
    
    if not result_data:
        return {
            "status": "ok",
            "message": "Nadiren kullanılan menşe ülke tespit edilmedi"
        }
    
    # Sonuç dataframe'i oluştur
    result_rows = []
    
    for item in result_data:
        firma = item['firma']
        
        for country_info in item['nadir_kullanilan_ulkeler']:
            country = country_info['ulke']
            count = country_info['sayi']
            percentage = country_info['yuzde']
            sample_beyannames = country_info['ornek_beyannameler']
            
            # Örnek beyannameleri ilgili veriyi al
            sample_data = filtered_df[
                (filtered_df[firma_column] == firma) & 
                (filtered_df['Mensei_ulke'] == country) &
                (filtered_df['Beyanname_no'].isin(sample_beyannames))
            ]
            
            for _, row in sample_data.iterrows():
                result_row = {
                    'Firma': firma,
                    'Nadiren_Kullanilan_Ulke': country,
                    'Kullanim_Sayisi': count,
                    'Kullanim_Yuzdesi': percentage,
                    'En_Cok_Kullanilan_Ulke': item['en_cok_kullanilan_ulke'],
                }
                
                # Beyannameye ilişkin detayları ekle
                for col in ['Beyanname_no', 'Mensei_ulke', 'Fatura_miktari', 'Gtip', 'Rejim']:
                    if col in row:
                        result_row[col] = row[col]
                
                result_rows.append(result_row)
    
    # Tüm sonuçları içeren DataFrame
    result_df = pd.DataFrame(result_rows)
    
    # Özet DataFrame'i
    summary_data = []
    for item in result_data:
        for country_info in item['nadir_kullanilan_ulkeler']:
            summary_data.append({
                'Firma': item['firma'],
                'En_Cok_Kullanilan_Ulke': item['en_cok_kullanilan_ulke'],
                'En_Cok_Kullanilan_Ulke_Yuzdesi': round(item['en_cok_kullanilan_ulke_yuzdesi'], 2),
                'Nadir_Kullanilan_Ulke': country_info['ulke'],
                'Nadir_Kullanilan_Ulke_Sayisi': country_info['sayi'],
                'Nadir_Kullanilan_Ulke_Yuzdesi': round(country_info['yuzde'], 2)
            })
    
    summary_df = pd.DataFrame(summary_data)
    
    # HTML rapor oluştur
    html_report = _create_rarely_used_html_report(result_data, "menşe ülke", firma_column)
    
    return {
        "status": "warning" if len(result_data) > 0 else "ok",
        "message": f"{len(result_data)} firmada nadiren kullanılan menşe ülke tespit edildi" if result_data else "Nadiren kullanılan menşe ülke tespit edilmedi",
        "data": result_df,
        "summary": summary_df,
        "html_report": html_report
    }

def check_rarely_used_payment_method(df):
    """
    Firmalara göre nadiren kullanılan ödeme şekillerini kontrol eder
    
    Args:
        df (pandas.DataFrame): Beyanname verileri içeren DataFrame
    
    Returns:
        dict: Analiz sonuçları
    """
    # Ödeme sütunu öncelik sırası: Odeme_sekli, Odeme, Odeme_yontemi
    payment_columns = ['Odeme_sekli', 'Odeme', 'Odeme_yontemi']
    payment_column = None
    
    for col in payment_columns:
        if col in df.columns:
            payment_column = col
            break
    
    if not payment_column:
        return {
            "status": "error",
            "message": f"Ödeme şekli bilgisi sütunu bulunamadı. Aranan sütunlar: {', '.join(payment_columns)}"
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
    
    # Boş firma ve ödeme şekli değerlerini filtrele
    filtered_df = df[
        (df[firma_column].notna()) & 
        (df[payment_column].notna()) &
        (df[firma_column] != '') & 
        (df[payment_column] != '')
    ].copy()
    
    if len(filtered_df) == 0:
        return {
            "status": "error",
            "message": "Filtreleme sonrası incelenecek veri kalmadı"
        }
    
    # Her firma için ödeme şekli kullanımını hesapla
    result_data = []
    
    # Firmaları grupla
    for firma, firma_data in filtered_df.groupby(firma_column):
        # Boş veya geçersiz firma adlarını atla
        if pd.isna(firma) or firma == '':
            continue
            
        # Ödeme şekillerini say
        odeme_counts = firma_data[payment_column].value_counts()
        
        # En az 2 farklı ödeme şekli kullanan firmaları kontrol et
        if len(odeme_counts) >= 2:
            # Toplam beyanname sayısı
            total_beyanname_count = len(firma_data['Beyanname_no'].unique())
            
            # En çok ve en az kullanılan ödeme şekillerini belirle
            most_common_payment = odeme_counts.index[0]
            most_common_count = odeme_counts.iloc[0]
            most_common_percentage = (most_common_count / len(firma_data)) * 100
            
            # Nadiren kullanılan ödeme şekillerini bul
            threshold_percentage = 10  # %10'dan az kullanılanlar "nadir" olarak kabul edilecek
            rarely_used_payments = []
            
            for payment, count in odeme_counts.items():
                if payment == most_common_payment:
                    continue
                    
                percentage = (count / len(firma_data)) * 100
                if percentage < threshold_percentage:
                    # Nadir kullanılan ödeme şekli örnek beyannamelerini bul
                    sample_beyannames = firma_data[firma_data[payment_column] == payment]['Beyanname_no'].unique()
                    sample_beyannames = sample_beyannames[:5].tolist()  # En fazla 5 örnek
                    
                    rarely_used_payments.append({
                        'odeme': payment,
                        'sayi': count,
                        'yuzde': percentage,
                        'ornek_beyannameler': sample_beyannames
                    })
            
            # Özel ilgi: "peşin" veya "cash" içeren ödeme şekilleri
            special_keywords = ["peşin", "pesin", "cash", "advance", "nakit"]
            
            for payment, count in odeme_counts.items():
                if payment == most_common_payment:
                    continue
                
                payment_lower = payment.lower()
                is_special = any(keyword in payment_lower for keyword in special_keywords)
                percentage = (count / len(firma_data)) * 100
                
                # Özel anahtar kelime içeren ve %20'nin altında kullanılan ödemeler
                if is_special and percentage < 20:
                    # Eğer bu ödeme şekli zaten nadir kullanılanlar listesinde yoksa ekle
                    if not any(item['odeme'] == payment for item in rarely_used_payments):
                        sample_beyannames = firma_data[firma_data[payment_column] == payment]['Beyanname_no'].unique()
                        sample_beyannames = sample_beyannames[:5].tolist()  # En fazla 5 örnek
                        
                        rarely_used_payments.append({
                            'odeme': payment,
                            'sayi': count,
                            'yuzde': percentage,
                            'ornek_beyannameler': sample_beyannames,
                            'ozel': True  # Özel ilgi gerektiren bir ödeme şekli
                        })
            
            # Nadir kullanılan ödeme şekli varsa sonuca ekle
            if rarely_used_payments:
                result_data.append({
                    'firma': firma,
                    'toplam_beyanname': total_beyanname_count,
                    'en_cok_kullanilan_odeme': most_common_payment,
                    'en_cok_kullanilan_odeme_yuzdesi': most_common_percentage,
                    'nadir_kullanilan_odeme_sekilleri': rarely_used_payments
                })
    
    if not result_data:
        return {
            "status": "ok",
            "message": "Nadiren kullanılan ödeme şekli tespit edilmedi"
        }
    
    # Sonuç dataframe'i oluştur
    result_rows = []
    
    for item in result_data:
        firma = item['firma']
        
        for payment_info in item['nadir_kullanilan_odeme_sekilleri']:
            payment = payment_info['odeme']
            count = payment_info['sayi']
            percentage = payment_info['yuzde']
            sample_beyannames = payment_info['ornek_beyannameler']
            is_special = payment_info.get('ozel', False)
            
            # Örnek beyannameleri ilgili veriyi al
            sample_data = filtered_df[
                (filtered_df[firma_column] == firma) & 
                (filtered_df[payment_column] == payment) &
                (filtered_df['Beyanname_no'].isin(sample_beyannames))
            ]
            
            for _, row in sample_data.iterrows():
                result_row = {
                    'Firma': firma,
                    'Nadiren_Kullanilan_Odeme': payment,
                    'Kullanim_Sayisi': count,
                    'Kullanim_Yuzdesi': percentage,
                    'En_Cok_Kullanilan_Odeme': item['en_cok_kullanilan_odeme'],
                    'Ozel_Ilgi': is_special
                }
                
                # Beyannameye ilişkin detayları ekle
                for col in ['Beyanname_no', payment_column, 'Fatura_miktari', 'GTİP', 'Rejim']:
                    if col in row:
                        result_row[col] = row[col]
                
                result_rows.append(result_row)
    
    # Tüm sonuçları içeren DataFrame
    result_df = pd.DataFrame(result_rows)
    
    # Özet DataFrame'i
    summary_data = []
    for item in result_data:
        for payment_info in item['nadir_kullanilan_odeme_sekilleri']:
            summary_data.append({
                'Firma': item['firma'],
                'En_Cok_Kullanilan_Odeme': item['en_cok_kullanilan_odeme'],
                'En_Cok_Kullanilan_Odeme_Yuzdesi': round(item['en_cok_kullanilan_odeme_yuzdesi'], 2),
                'Nadir_Kullanilan_Odeme': payment_info['odeme'],
                'Nadir_Kullanilan_Odeme_Sayisi': payment_info['sayi'],
                'Nadir_Kullanilan_Odeme_Yuzdesi': round(payment_info['yuzde'], 2),
                'Ozel_Ilgi': payment_info.get('ozel', False)
            })
    
    summary_df = pd.DataFrame(summary_data)
    
    # HTML rapor oluştur
    html_report = _create_rarely_used_html_report(result_data, "ödeme şekli", firma_column)
    
    return {
        "status": "warning" if len(result_data) > 0 else "ok",
        "message": f"{len(result_data)} firmada nadiren kullanılan ödeme şekli tespit edildi" if result_data else "Nadiren kullanılan ödeme şekli tespit edilmedi",
        "data": result_df,
        "summary": summary_df,
        "html_report": html_report
    } 

def check_rarely_used_origin_country_by_sender_gtip(df):
    """
    Aynı gönderici ve aynı GTİP kodunda nadiren kullanılan menşe ülkeleri kontrol eder
    
    Args:
        df (pandas.DataFrame): Beyanname verileri içeren DataFrame
    
    Returns:
        dict: Analiz sonuçları
    """
    # Gerekli sütunları kontrol et
    required_columns = ['Adi_unvani', 'Gtip', 'Mensei_ulke']
    missing_columns = [col for col in required_columns if col not in df.columns]
    
    if missing_columns:
        return {
            "status": "error",
            "message": f"Gerekli sütunlar bulunamadı: {', '.join(missing_columns)}"
        }
    
    # Boş değerleri filtrele
    filtered_df = df[
        (df['Adi_unvani'].notna()) & 
        (df['Gtip'].notna()) &
        (df['Mensei_ulke'].notna()) &
        (df['Adi_unvani'] != '') & 
        (df['Gtip'] != '') &
        (df['Mensei_ulke'] != '')
    ].copy()
    
    if len(filtered_df) == 0:
        return {
            "status": "error",
            "message": "Filtreleme sonrası incelenecek veri kalmadı"
        }
    
    # Gönderici + GTİP kombinasyonları için analiz
    result_data = []
    
    # Gönderici ve GTİP kombinasyonlarını grupla
    for (sender, gtip), group_data in filtered_df.groupby(['Adi_unvani', 'Gtip']):
        # Boş veya geçersiz değerleri atla
        if pd.isna(sender) or pd.isna(gtip) or sender == '' or gtip == '':
            continue
        
        # En az 3 beyanname ve 2 farklı menşe ülke olmalı
        if len(group_data) < 3:
            continue
            
        # Menşe ülkeleri say
        ulke_counts = group_data['Mensei_ulke'].value_counts()
        
        if len(ulke_counts) < 2:
            continue
        
        # En çok kullanılan menşe ülke
        most_common_country = ulke_counts.index[0]
        most_common_count = ulke_counts.iloc[0]
        most_common_percentage = (most_common_count / len(group_data)) * 100
        
        # Nadiren kullanılan menşe ülkeleri bul (eşik: %20)
        threshold_percentage = 20  # Daha sıkı kontrol için %20 eşiği
        rarely_used_countries = []
        
        for country, count in ulke_counts.items():
            if country == most_common_country:
                continue
                
            percentage = (count / len(group_data)) * 100
            if percentage < threshold_percentage:
                # Örnek beyanname numaraları
                sample_beyannames = []
                if 'Beyanname_no' in group_data.columns:
                    country_data = group_data[group_data['Mensei_ulke'] == country]
                    sample_beyannames = country_data['Beyanname_no'].unique()[:5].tolist()
                
                rarely_used_countries.append({
                    'ulke': country,
                    'sayi': count,
                    'yuzde': percentage,
                    'ornek_beyannameler': sample_beyannames
                })
        
        # Nadir kullanılan menşe ülke varsa sonuca ekle
        if rarely_used_countries:
            result_data.append({
                'gonderen': sender,
                'gtip': gtip,
                'toplam_beyanname': len(group_data),
                'toplam_mensei_ulke_sayisi': len(ulke_counts),
                'en_cok_kullanilan_ulke': most_common_country,
                'en_cok_kullanilan_ulke_yuzdesi': most_common_percentage,
                'nadir_kullanilan_ulkeler': rarely_used_countries
            })
    
    if not result_data:
        return {
            "status": "ok",
            "message": "Aynı gönderici ve GTİP kodunda nadiren kullanılan menşe ülke tespit edilmedi"
        }
    
    # Sonuç dataframe'i oluştur
    result_rows = []
    
    for item in result_data:
        sender = item['gonderen']
        gtip = item['gtip']
        
        for country_info in item['nadir_kullanilan_ulkeler']:
            country = country_info['ulke']
            count = country_info['sayi']
            percentage = country_info['yuzde']
            sample_beyannames = country_info['ornek_beyannameler']
            
            # Örnek beyannameleri ilgili veriyi al
            sample_data = filtered_df[
                (filtered_df['Adi_unvani'] == sender) & 
                (filtered_df['Gtip'] == gtip) &
                (filtered_df['Mensei_ulke'] == country)
            ]
            
            if 'Beyanname_no' in sample_data.columns and sample_beyannames:
                sample_data = sample_data[sample_data['Beyanname_no'].isin(sample_beyannames)]
            
            for _, row in sample_data.iterrows():
                result_row = {
                    'Gonderen': sender,
                    'Gtip': gtip,
                    'Nadiren_Kullanilan_Ulke': country,
                    'Kullanim_Sayisi': count,
                    'Kullanim_Yuzdesi': round(percentage, 2),
                    'En_Cok_Kullanilan_Ulke': item['en_cok_kullanilan_ulke'],
                    'Toplam_Beyanname_Sayisi': item['toplam_beyanname'],
                    'Toplam_Mensei_Ulke_Sayisi': item['toplam_mensei_ulke_sayisi']
                }
                
                # Temel sütunları ekle
                result_row['Adi_unvani'] = row['Adi_unvani']
                result_row['Mensei_ulke'] = row['Mensei_ulke']
                
                # Beyanname numarası varsa ekle
                if 'Beyanname_no' in row:
                    result_row['Beyanname_no'] = row['Beyanname_no']
                
                result_rows.append(result_row)
    
    # Tüm sonuçları içeren DataFrame
    result_df = pd.DataFrame(result_rows)
    
    # Özet DataFrame'i
    summary_data = []
    for item in result_data:
        for country_info in item['nadir_kullanilan_ulkeler']:
            summary_data.append({
                'Gonderen': item['gonderen'],
                'Gtip': item['gtip'],
                'En_Cok_Kullanilan_Ulke': item['en_cok_kullanilan_ulke'],
                'Nadir_Kullanilan_Ulke': country_info['ulke'],
                'Nadir_Kullanilan_Ulke_Sayisi': country_info['sayi'],
                'Nadir_Kullanilan_Ulke_Yuzdesi': round(country_info['yuzde'], 2),
                'Toplam_Beyanname': item['toplam_beyanname']
            })
    
    summary_df = pd.DataFrame(summary_data)
    
    # HTML rapor oluştur
    html_report = _create_sender_gtip_origin_html_report(result_data, 'Adi_unvani')
    
    return {
        "status": "warning" if len(result_data) > 0 else "ok",
        "message": f"{len(result_data)} gönderici-GTİP kombinasyonunda nadiren kullanılan menşe ülke tespit edildi" if result_data else "Aynı gönderici ve GTİP kodunda nadiren kullanılan menşe ülke tespit edilmedi",
        "data": result_df,
        "summary": summary_df,
        "html_report": html_report,
        "detailed_analysis": result_data
    }

def _create_sender_gtip_origin_html_report(result_data, sender_column):
    """
    Gönderici-GTİP bazında nadir menşe ülke analizi için HTML rapor oluşturur
    """
    if not result_data:
        return "<p>Analiz sonucunda herhangi bir risk tespit edilmedi.</p>"
    
    html = """
    <div style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 20px;">
        <h2 style="color: #d32f2f; border-bottom: 2px solid #d32f2f; padding-bottom: 10px;">
            🔍 Gönderici-GTİP Bazında Nadir Menşe Ülke Analizi
        </h2>
        
        <div style="background: linear-gradient(135deg, #fff3e0 0%, #ffe0b2 100%); 
                    padding: 15px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #ff9800;">
            <h3 style="margin: 0; color: #e65100;">📊 Analiz Özeti</h3>
            <p style="margin: 10px 0 0 0; color: #bf360c;">
                <strong>{} gönderici-GTİP kombinasyonu</strong>nda nadiren kullanılan menşe ülke tespit edildi.
                Bu durum, aynı ürün grubu için farklı menşe ülke tercihlerini gösterebilir.
            </p>
        </div>
    """.format(len(result_data))
    
    # Her gönderici-GTİP kombinasyonu için detay
    for i, item in enumerate(result_data, 1):
        html += f"""
        <div style="background: white; border: 1px solid #e0e0e0; border-radius: 8px; 
                    margin: 15px 0; padding: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
            
            <h3 style="color: #1976d2; margin: 0 0 15px 0; border-bottom: 1px solid #e3f2fd; padding-bottom: 8px;">
                {i}. {item['gonderen']} - {item['gtip']}
            </h3>
            
            <div style="background: #f5f5f5; padding: 10px; border-radius: 5px; margin: 10px 0;">
                <strong>Toplam Beyanname:</strong> {item['toplam_beyanname']} adet<br>
                <strong>Kullanılan Menşe Ülke Sayısı:</strong> {item['toplam_mensei_ulke_sayisi']} adet<br>
                <strong>En Çok Kullanılan:</strong> {item['en_cok_kullanilan_ulke']} 
                ({item['en_cok_kullanilan_ulke_yuzdesi']:.1f}%)
            </div>
            
            <h4 style="color: #d32f2f; margin: 15px 0 10px 0;">⚠️ Nadiren Kullanılan Menşe Ülkeler:</h4>
            <div style="margin-left: 20px;">
        """
        
        for country_info in item['nadir_kullanilan_ulkeler']:
            html += f"""
                <div style="background: #ffebee; border-left: 3px solid #f44336; padding: 10px; margin: 8px 0;">
                    <strong style="color: #c62828;">{country_info['ulke']}</strong><br>
                    <span style="color: #666;">
                        Kullanım: {country_info['sayi']} adet ({country_info['yuzde']:.1f}%)
                    </span>
            """
            
            if country_info['ornek_beyannameler']:
                html += f"""<br><span style="color: #666; font-size: 0.9em;">
                    Örnek Beyannameler: {', '.join(map(str, country_info['ornek_beyannameler'][:3]))}
                    {'...' if len(country_info['ornek_beyannameler']) > 3 else ''}
                </span>"""
            
            html += "</div>"
        
        html += """
            </div>
        </div>
        """
    
    html += """
        <div style="background: #e8f5e8; border: 1px solid #4caf50; border-radius: 8px; 
                    padding: 15px; margin: 20px 0;">
            <h4 style="color: #2e7d32; margin: 0 0 10px 0;">💡 Analiz Kriterleri</h4>
            <ul style="margin: 0; color: #388e3c;">
                <li>Aynı gönderici ve GTİP kombinasyonu için en az 3 beyanname</li>
                <li>En az 2 farklı menşe ülke kullanımı</li>
                <li>%20'nin altında kullanılan menşe ülkeler "nadir" olarak değerlendirilir</li>
            </ul>
        </div>
    </div>
    """
    
    return html 