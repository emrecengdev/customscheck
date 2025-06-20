"""
Rapor oluşturma utility fonksiyonları modülü.
Bu modül, analiz raporları için ortak HTML ve rapor oluşturma fonksiyonlarını içerir.
"""

import pandas as pd

def create_rarely_used_html_report(result_data, item_type, firma_column):
    """
    Nadiren kullanılan öğeler için genel HTML raporu oluşturur
    
    Args:
        result_data (list): Analiz sonuç verileri
        item_type (str): Analiz edilen öğe türü (döviz, ülke, ödeme şekli)
        firma_column (str): Firma sütunu adı
    
    Returns:
        str: HTML rapor içeriği
    """
    if not result_data:
        return f"<p>Nadiren kullanılan {item_type} tespit edilmedi.</p>"
    
    # HTML başlık ve style
    html = f"""
    <!DOCTYPE html>
    <html lang="tr">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Nadiren Kullanılan {item_type.title()} Analizi</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 1200px;
                margin: 0 auto;
                padding: 20px;
                background-color: #f8f9fa;
            }}
            .container {{
                background: white;
                border-radius: 12px;
                box-shadow: 0 2px 12px rgba(0,0,0,0.1);
                overflow: hidden;
            }}
            .header {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 30px;
                text-align: center;
            }}
            .header h1 {{
                margin: 0;
                font-size: 2.2em;
                font-weight: 300;
            }}
            .header p {{
                margin: 10px 0 0 0;
                opacity: 0.9;
                font-size: 1.1em;
            }}
            .content {{
                padding: 30px;
            }}
            .summary-box {{
                background: linear-gradient(135deg, #e3f2fd 0%, #f3e5f5 100%);
                border: 1px solid #b3d7ff;
                border-radius: 8px;
                padding: 20px;
                margin-bottom: 30px;
                border-left: 5px solid #2196f3;
            }}
            .summary-title {{
                color: #1565c0;
                font-size: 1.3em;
                font-weight: bold;
                margin-bottom: 10px;
            }}
            .stats-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 20px;
                margin: 30px 0;
            }}
            .stat-card {{
                background: linear-gradient(135deg, #fff 0%, #f8f9fa 100%);
                border: 1px solid #dee2e6;
                border-radius: 8px;
                padding: 20px;
                text-align: center;
                box-shadow: 0 2px 4px rgba(0,0,0,0.05);
            }}
            .stat-number {{
                font-size: 2.5em;
                font-weight: bold;
                color: #495057;
                margin-bottom: 5px;
            }}
            .stat-label {{
                color: #6c757d;
                font-size: 0.9em;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }}
            .firm-section {{
                background: #fff;
                border: 1px solid #e9ecef;
                border-radius: 8px;
                margin-bottom: 25px;
                overflow: hidden;
                box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            }}
            .firm-header {{
                background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
                padding: 15px 20px;
                border-bottom: 1px solid #dee2e6;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }}
            .firm-name {{
                font-weight: bold;
                font-size: 1.1em;
                color: #495057;
            }}
            .firm-badge {{
                background: #007bff;
                color: white;
                padding: 4px 12px;
                border-radius: 15px;
                font-size: 0.8em;
                font-weight: bold;
            }}
            .info-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 15px;
                padding: 20px;
                background: #f8f9fa;
            }}
            .info-card {{
                background: white;
                border: 1px solid #dee2e6;
                border-radius: 6px;
                padding: 15px;
                text-align: center;
            }}
            .info-card h4 {{
                margin: 0 0 10px 0;
                color: #6c757d;
                font-size: 0.9em;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }}
            .info-value {{
                font-size: 1.4em;
                font-weight: bold;
                color: #495057;
                margin-bottom: 5px;
            }}
            .percentage {{
                color: #28a745;
                font-weight: bold;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin: 0 20px 20px 20px;
                width: calc(100% - 40px);
                background: white;
            }}
            th {{
                background: linear-gradient(135deg, #495057 0%, #6c757d 100%);
                color: white;
                padding: 12px;
                text-align: left;
                font-weight: 600;
                border: none;
            }}
            td {{
                padding: 10px 12px;
                border-bottom: 1px solid #dee2e6;
                vertical-align: top;
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
            .badge.special {{
                background-color: #fff3e0;
                color: #ef6c00;
            }}
            .percentage.low {{
                color: #dc3545;
                font-weight: bold;
            }}
            .beyanname-list {{
                max-height: 100px;
                overflow-y: auto;
                padding: 8px;
                background-color: #f8f9fa;
                border-radius: 4px;
                border: 1px solid #dee2e6;
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
    
    # Dinamik alan seçimi
    if 'nadir_kullanilan_dovizler' in result_data[0]:
        rare_field = 'nadir_kullanilan_dovizler'
    elif 'nadir_kullanilan_ulkeler' in result_data[0]:
        rare_field = 'nadir_kullanilan_ulkeler'
    else:
        rare_field = 'nadir_kullanilan_odeme_sekilleri'
    
    total_rare_items = sum([len(item[rare_field]) for item in result_data])
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
        rare_items = item[rare_field]
        
        # Dinamik alan adları
        if rare_field == 'nadir_kullanilan_dovizler':
            en_cok_kullanilan = item['en_cok_kullanilan_doviz']
            en_cok_yuzde = round(item['en_cok_kullanilan_doviz_yuzdesi'], 2)
            field_name = 'doviz'
        elif rare_field == 'nadir_kullanilan_ulkeler':
            en_cok_kullanilan = item['en_cok_kullanilan_ulke']
            en_cok_yuzde = round(item['en_cok_kullanilan_ulke_yuzdesi'], 2)
            field_name = 'ulke'
        else:
            en_cok_kullanilan = item['en_cok_kullanilan_odeme']
            en_cok_yuzde = round(item['en_cok_kullanilan_odeme_yuzdesi'], 2)
            field_name = 'odeme'
        
        html += f"""
                <div class="firm-section">
                    <div class="firm-header">
                        <div class="firm-name">🏢 {firma}</div>
                        <div class="firm-badge">{len(rare_items)} nadir {item_type}</div>
                    </div>
                    
                    <div class="info-grid">
                        <div class="info-card">
                            <h4>En Çok Kullanılan {item_type.title()}</h4>
                            <div class="info-value">{en_cok_kullanilan}</div>
                            <div class="percentage">%{en_cok_yuzde}</div>
                        </div>
                        <div class="info-card">
                            <h4>Nadir Kullanılan {item_type.title()} Sayısı</h4>
                            <div class="info-value">{len(rare_items)}</div>
                        </div>
                    </div>
                    
                    <table>
                        <thead>
                            <tr>
                                <th>Nadiren Kullanılan {item_type.title()}</th>
                                <th>Kullanım Sayısı</th>
                                <th>Yüzde (%)</th>
                                <th>Örnek Beyannameler</th>
                            </tr>
                        </thead>
                        <tbody>
        """
        
        for rare_item in rare_items:
            deger = rare_item[field_name]
            sayi = rare_item['sayi']
            yuzde = round(rare_item['yuzde'], 2)
            ornek_beyannameler = rare_item.get('ornek_beyannameler', [])
            is_special = rare_item.get('ozel', False)
            
            # Beyanname listesini daha güzel göster
            if ornek_beyannameler:
                if len(ornek_beyannameler) <= 5:
                    beyanname_display = ", ".join(map(str, ornek_beyannameler))
                else:
                    beyanname_display = f"""
                    <div class="beyanname-list">
                        {", ".join(map(str, ornek_beyannameler[:5]))}
                        {f" ve {len(ornek_beyannameler)-5} beyanname daha..." if len(ornek_beyannameler) > 5 else ""}
                    </div>
                    """
            else:
                beyanname_display = "-"
            
            percentage_class = "low" if yuzde < 5 else ""
            badge_class = "special" if is_special else "rare"
            
            html += f"""
                    <tr>
                        <td><span class="badge {badge_class}">{deger}</span></td>
                        <td><strong>{sayi}</strong></td>
                        <td><span class="percentage {percentage_class}">{yuzde}%</span></td>
                        <td>{beyanname_display}</td>
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

def create_basic_html_template(title, content, color_theme="blue"):
    """
    Temel HTML şablonu oluşturur
    
    Args:
        title (str): Rapor başlığı
        content (str): HTML içeriği
        color_theme (str): Renk teması (blue, green, red, purple)
    
    Returns:
        str: Tamamlanmış HTML içeriği
    """
    
    # Renk temalarını tanımla
    themes = {
        "blue": {
            "primary": "#2196f3",
            "secondary": "#e3f2fd",
            "accent": "#1976d2"
        },
        "green": {
            "primary": "#4caf50",
            "secondary": "#e8f5e8",
            "accent": "#2e7d32"
        },
        "red": {
            "primary": "#f44336",
            "secondary": "#ffebee",
            "accent": "#c62828"
        },
        "purple": {
            "primary": "#9c27b0",
            "secondary": "#f3e5f5",
            "accent": "#7b1fa2"
        }
    }
    
    theme = themes.get(color_theme, themes["blue"])
    
    html = f"""
    <!DOCTYPE html>
    <html lang="tr">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{title}</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 1200px;
                margin: 0 auto;
                padding: 20px;
                background-color: #f8f9fa;
            }}
            .container {{
                background: white;
                border-radius: 12px;
                box-shadow: 0 2px 12px rgba(0,0,0,0.1);
                overflow: hidden;
            }}
            .header {{
                background: {theme["primary"]};
                color: white;
                padding: 30px;
                text-align: center;
            }}
            .header h1 {{
                margin: 0;
                font-size: 2.2em;
                font-weight: 300;
            }}
            .content {{
                padding: 30px;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin: 20px 0;
            }}
            th {{
                background: {theme["primary"]};
                color: white;
                padding: 12px;
                text-align: left;
            }}
            td {{
                padding: 10px 12px;
                border-bottom: 1px solid #dee2e6;
            }}
            tr:hover {{
                background-color: {theme["secondary"]};
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>{title}</h1>
            </div>
            <div class="content">
                {content}
            </div>
        </div>
    </body>
    </html>
    """
    
    return html

def generate_price_increase_html_report(result_df, summary_df):
    """
    Birim fiyat artışı için HTML rapor oluşturur
    """
    html = """
    <style>
    body {
        font-family: Arial, sans-serif;
        font-size: 12px;
        margin: 0;
        padding: 10px;
    }
    table {
        width: 100%;
        border-collapse: collapse;
        margin-bottom: 20px;
    }
    th {
        background-color: #f2f2f2;
        padding: 6px;
        text-align: left;
        border: 1px solid #ddd;
        position: sticky;
        top: 0;
    }
    td {
        padding: 4px;
        border: 1px solid #ddd;
    }
    tr:nth-child(even) {
        background-color: #f9f9f9;
    }
    .warning {
        color: #e53935;
        font-weight: bold;
    }
    .high-increase {
        background-color: #ffebee;
    }
    .container {
        margin-bottom: 20px;
    }
    h2 {
        color: #333;
        font-size: 16px;
        margin-top: 20px;
        margin-bottom: 10px;
        padding-bottom: 5px;
        border-bottom: 1px solid #ddd;
    }
    h3 {
        color: #555;
        font-size: 14px;
        margin-top: 15px;
        margin-bottom: 8px;
    }
    .summary-box {
        background-color: #e3f2fd;
        border-left: 4px solid #2196F3;
        padding: 10px;
        margin-bottom: 20px;
    }
    </style>
    
    <div class="container">
        <h2>Birim Fiyat Artışı Analizi</h2>
        
        <div class="summary-box">
            <p><strong>Özet:</strong> Bu rapor, aynı GTİP, ticari tanım ve firmaya sahip ürünlerin zaman içinde birim fiyat artışlarını analiz eder.</p>
    """
    
    # Özet verileri
    monthly_issues = summary_df[summary_df['Aylik_Normalize_Artis'] > 3].shape[0]
    three_month_issues = summary_df[summary_df['Uc_Aylik_Artis_Yuzdesi'] > 10].shape[0]
    
    html += f"""
            <p class="warning">
                <strong>Aylık %3'ün üzerinde artış gösteren: {monthly_issues} GTİP-Firma kombinasyonu</strong><br>
                <strong>3 Aylık %10'un üzerinde artış gösteren: {three_month_issues} GTİP-Firma kombinasyonu</strong>
            </p>
        </div>
    """
    
    # GTİP bazında özet tablo
    html += """
        <h3>GTİP Bazında Artış Özeti</h3>
        <table>
            <thead>
                <tr>
                    <th>GTİP</th>
                    <th>Ticari Tanım</th>
                    <th>Firma</th>
                    <th>Aylık Artış (%)</th>
                    <th>3 Aylık Artış (%)</th>
                </tr>
            </thead>
            <tbody>
    """
    
    # Her satır için işlem yap
    for _, row in summary_df.iterrows():
        monthly_class = 'high-increase' if row.get('Aylik_Normalize_Artis', 0) > 3 else ''
        three_month_class = 'high-increase' if row.get('Uc_Aylik_Artis_Yuzdesi', 0) > 10 else ''
        
        html += f"""
                <tr>
                    <td>{row.get('Gtip', '-')}</td>
                    <td>{row.get('Ticari_tanimi', '-')}</td>
                    <td>{row.get('Firma', '-')}</td>
                    <td class="{monthly_class}">{row.get('Aylik_Normalize_Artis', '-'):.2f}%</td>
                    <td class="{three_month_class}">{row.get('Uc_Aylik_Artis_Yuzdesi', '-'):.2f}%</td>
                </tr>
        """
    
    html += """
            </tbody>
        </table>
    """
    
    # Aylık artışlar
    monthly_over_limit = summary_df[summary_df['Aylik_Normalize_Artis'] > 3].sort_values(by='Aylik_Normalize_Artis', ascending=False)
    
    if not monthly_over_limit.empty:
        html += """
            <h3>Aylık %3'ün Üzerinde Artış Gösteren Ürünler</h3>
            <table>
                <thead>
                    <tr>
                        <th>GTİP</th>
                        <th>Ticari Tanım</th>
                        <th>Firma</th>
                        <th>Güncel Tarih</th>
                        <th>Önceki Tarih</th>
                        <th>Güncel Birim Fiyat</th>
                        <th>Önceki Birim Fiyat</th>
                        <th>Aylık Artış (%)</th>
                    </tr>
                </thead>
                <tbody>
        """
        
        for _, row in monthly_over_limit.iterrows():
            html += f"""
                    <tr>
                        <td>{row.get('Gtip', '-')}</td>
                        <td>{row.get('Ticari_tanimi', '-')}</td>
                        <td>{row.get('Firma', '-')}</td>
                        <td>{row.get('Guncel_Tarih', '-')}</td>
                        <td>{row.get('Onceki_Tarih', '-')}</td>
                        <td>{row.get('Guncel_Birim_Fiyat', '-'):.2f}</td>
                        <td>{row.get('Onceki_Birim_Fiyat', '-'):.2f}</td>
                        <td class="high-increase">{row.get('Aylik_Normalize_Artis', '-'):.2f}%</td>
                    </tr>
            """
        
        html += """
                </tbody>
            </table>
        """
    
    # 3 Aylık artışlar
    three_month_over_limit = summary_df[summary_df['Uc_Aylik_Artis_Yuzdesi'] > 10].sort_values(by='Uc_Aylik_Artis_Yuzdesi', ascending=False)
    
    if not three_month_over_limit.empty:
        html += """
            <h3>3 Aylık %10'un Üzerinde Artış Gösteren Ürünler</h3>
            <table>
                <thead>
                    <tr>
                        <th>GTİP</th>
                        <th>Ticari Tanım</th>
                        <th>Firma</th>
                        <th>Güncel Tarih</th>
                        <th>3 Ay Önceki Tarih</th>
                        <th>Güncel Birim Fiyat</th>
                        <th>3 Ay Önceki Birim Fiyat</th>
                        <th>3 Aylık Artış (%)</th>
                    </tr>
                </thead>
                <tbody>
        """
        
        for _, row in three_month_over_limit.iterrows():
            html += f"""
                    <tr>
                        <td>{row.get('Gtip', '-')}</td>
                        <td>{row.get('Ticari_tanimi', '-')}</td>
                        <td>{row.get('Firma', '-')}</td>
                        <td>{row.get('Guncel_Tarih', '-')}</td>
                        <td>{row.get('Uc_Ay_Onceki_Tarih', '-')}</td>
                        <td>{row.get('Guncel_Birim_Fiyat', '-'):.2f}</td>
                        <td>{row.get('Uc_Ay_Onceki_Birim_Fiyat', '-'):.2f}</td>
                        <td class="high-increase">{row.get('Uc_Aylik_Artis_Yuzdesi', '-'):.2f}%</td>
                    </tr>
            """
        
        html += """
                </tbody>
            </table>
        """
    
    # Değerlendirme
    html += """
        <h3>Değerlendirme</h3>
        <p>Birim fiyat artışlarının olası nedenleri:</p>
        <ul>
            <li>Hammadde veya üretim maliyetlerindeki artışlar</li>
            <li>Döviz kurlarındaki dalgalanmalar</li>
            <li>Piyasa koşullarındaki değişiklikler</li>
            <li>Tedarikçi fiyat politikasındaki değişiklikler</li>
            <li>Ürün kalitesindeki değişiklikler</li>
            <li>Gümrük değerlerinin doğru beyan edilmemesi</li>
        </ul>
        <p>Dikkat edilmesi gereken hususlar:</p>
        <ul>
            <li>Aynı ürün için kısa sürede yüksek fiyat artışları, piyasa gerçekleriyle uyumsuz olabilir</li>
            <li>Vergiye tabi değerin düşük gösterilmesi amacıyla fiyat manipülasyonu olasılığı incelenmelidir</li>
            <li>Kısa süre içinde istikrarsız birim fiyat değişimleri, risk göstergesi olabilir</li>
        </ul>
    </div>
    """
    
    return html 