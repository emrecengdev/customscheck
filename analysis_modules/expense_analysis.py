import pandas as pd
import numpy as np
import traceback

def check_domestic_expense_variation(df):
    """
    Yurt içi gider beyanlarındaki değişkenliği analiz eder
    
    Args:
        df (pandas.DataFrame): Beyanname verileri içeren DataFrame
    
    Returns:
        dict: Analiz sonuçları
    """
    try:
        print("Yurt içi gider değişkenlik analizi başlatılıyor...")
        
        # Yurt içi gider sütunlarını bul
        domestic_expense_columns = [
            'Yurticinde_odenecek_giderler', 'Yurt_ici_gider', 'Domestic_expenses',
            'Liman_harci', 'Ardiye_ucreti', 'Gumrukleme_masrafi', 'Boslama_yukleme'
        ]
        
        found_columns = [col for col in domestic_expense_columns if col in df.columns]
        
        if not found_columns or 'Gtip' not in df.columns:
            return {
                "status": "error",
                "message": f"GTİP veya yurt içi gider sütunu bulunamadı. Mevcut sütunlar: {', '.join(df.columns.tolist())}"
            }
        
        # İlk bulunan sütunu kullan
        expense_column = found_columns[0]
        
        # Firma sütununu bul
        firma_columns = ['Adi_unvani', 'Firma', 'Gonderen']
        firma_column = None
        for col in firma_columns:
            if col in df.columns:
                firma_column = col
                break
        
        if not firma_column:
            return {
                "status": "error",
                "message": "Firma bilgisi sütunu bulunamadı."
            }
        
        # Boş değerleri filtrele
        filtered_df = df[
            (df['Gtip'].notna()) & 
            (df[expense_column].notna()) & 
            (df[firma_column].notna()) &
            (df['Gtip'] != '') & 
            (df[firma_column] != '')
        ].copy()
        
        if len(filtered_df) == 0:
            return {
                "status": "ok",
                "message": "Analiz için uygun veri bulunamadı.",
                "html_report": "<p>Analiz için uygun veri bulunamadı.</p>"
            }
        
        # Gider değerlerini sayısal hale getir
        filtered_df[expense_column] = pd.to_numeric(filtered_df[expense_column], errors='coerce')
        filtered_df = filtered_df[filtered_df[expense_column].notna()]
        
        # Firma ve GTİP bazında gruplama yap
        variations = []
        
        # Her firma için ayrı analiz
        for firma in filtered_df[firma_column].unique():
            firma_data = filtered_df[filtered_df[firma_column] == firma]
            
            if len(firma_data) < 2:
                continue
            
            # Her GTİP kodu için analiz
            for gtip in firma_data['Gtip'].unique():
                gtip_data = firma_data[firma_data['Gtip'] == gtip]
                
                if len(gtip_data) < 2:
                    continue
                
                # İstatistik hesapla
                mean_expense = gtip_data[expense_column].mean()
                std_expense = gtip_data[expense_column].std()
                cv = (std_expense / mean_expense) * 100 if mean_expense > 0 else 0  # Coefficient of Variation
                min_expense = gtip_data[expense_column].min()
                max_expense = gtip_data[expense_column].max()
                
                # Yüksek değişkenlik varsa kaydet (CV > %50)
                if cv > 50 and len(gtip_data) >= 3:
                    variations.append({
                        'Firma': firma,
                        'GTİP': gtip,
                        'Beyanname_Sayısı': len(gtip_data),
                        'Ortalama_Gider': mean_expense,
                        'Standart_Sapma': std_expense,
                        'Değişkenlik_Katsayısı': cv,
                        'Min_Gider': min_expense,
                        'Max_Gider': max_expense,
                        'Gider_Farkı': max_expense - min_expense,
                        'İlk_Tarih': gtip_data['Beyanname_tarihi'].min() if 'Beyanname_tarihi' in gtip_data.columns else None,
                        'Son_Tarih': gtip_data['Beyanname_tarihi'].max() if 'Beyanname_tarihi' in gtip_data.columns else None
                    })
        
        if not variations:
            return {
                "status": "ok",
                "message": "Anormal yurt içi gider değişkenliği tespit edilmedi.",
                "html_report": _create_expense_variation_html([], {}, "yurt içi")
            }
        
        # Sonuçları DataFrame'e dönüştür
        result_df = pd.DataFrame(variations)
        
        # Özet istatistikleri hesapla
        summary_stats = {
            'total_firms_affected': result_df['Firma'].nunique(),
            'total_gtip_affected': len(result_df),
            'highest_variation': result_df['Değişkenlik_Katsayısı'].max(),
            'avg_variation': result_df['Değişkenlik_Katsayısı'].mean(),
            'total_beyanname_affected': result_df['Beyanname_Sayısı'].sum()
        }
        
        # Özet DataFrame
        summary_df = pd.DataFrame([summary_stats])
        
        # HTML raporu oluştur
        html_content = _create_expense_variation_html(variations, summary_stats, "yurt içi")
        
        return {
            "status": "warning",
            "message": f"{len(variations)} firma-GTİP kombinasyonunda yüksek yurt içi gider değişkenliği tespit edildi.",
            "data": result_df,
            "summary": summary_df,
            "stats": summary_stats,
            "html_report": html_content
        }
        
    except Exception as e:
        error_msg = f"Yurt içi gider değişkenlik analizi sırasında hata: {str(e)}"
        print(error_msg)
        print(traceback.format_exc())
        return {
            "status": "error",
            "message": error_msg,
            "html_report": f"<p>Hata: {str(e)}</p>"
        }

def check_foreign_expense_variation(df):
    """
    Yurt dışı gider beyanlarındaki değişkenliği analiz eder
    
    Args:
        df (pandas.DataFrame): Beyanname verileri içeren DataFrame
    
    Returns:
        dict: Analiz sonuçları
    """
    try:
        print("Yurt dışı gider değişkenlik analizi başlatılıyor...")
        
        # Yurt dışı gider sütunlarını bul
        foreign_expense_columns = [
            'Yurtdisinda_odenecek_giderler', 'Yurt_disi_gider', 'Foreign_expenses',
            'Navlun', 'Sigorta', 'Komisyon', 'Icerik_ucreti'
        ]
        
        found_columns = [col for col in foreign_expense_columns if col in df.columns]
        
        if not found_columns or 'Gtip' not in df.columns:
            return {
                "status": "error",
                "message": f"GTİP veya yurt dışı gider sütunu bulunamadı. Mevcut sütunlar: {', '.join(df.columns.tolist())}"
            }
        
        # İlk bulunan sütunu kullan
        expense_column = found_columns[0]
        
        # Firma sütununu bul
        firma_columns = ['Adi_unvani', 'Firma', 'Gonderen']
        firma_column = None
        for col in firma_columns:
            if col in df.columns:
                firma_column = col
                break
        
        if not firma_column:
            return {
                "status": "error",
                "message": "Firma bilgisi sütunu bulunamadı."
            }
        
        # Boş değerleri filtrele
        filtered_df = df[
            (df['Gtip'].notna()) & 
            (df[expense_column].notna()) & 
            (df[firma_column].notna()) &
            (df['Gtip'] != '') & 
            (df[firma_column] != '')
        ].copy()
        
        if len(filtered_df) == 0:
            return {
                "status": "ok",
                "message": "Analiz için uygun veri bulunamadı.",
                "html_report": "<p>Analiz için uygun veri bulunamadı.</p>"
            }
        
        # Gider değerlerini sayısal hale getir
        filtered_df[expense_column] = pd.to_numeric(filtered_df[expense_column], errors='coerce')
        filtered_df = filtered_df[filtered_df[expense_column].notna()]
        
        # Firma ve GTİP bazında gruplama yap
        variations = []
        
        # Her firma için ayrı analiz
        for firma in filtered_df[firma_column].unique():
            firma_data = filtered_df[filtered_df[firma_column] == firma]
            
            if len(firma_data) < 2:
                continue
            
            # Her GTİP kodu için analiz
            for gtip in firma_data['Gtip'].unique():
                gtip_data = firma_data[firma_data['Gtip'] == gtip]
                
                if len(gtip_data) < 2:
                    continue
                
                # İstatistik hesapla
                mean_expense = gtip_data[expense_column].mean()
                std_expense = gtip_data[expense_column].std()
                cv = (std_expense / mean_expense) * 100 if mean_expense > 0 else 0  # Coefficient of Variation
                min_expense = gtip_data[expense_column].min()
                max_expense = gtip_data[expense_column].max()
                
                # Yüksek değişkenlik varsa kaydet (CV > %40 yurt dışı için)
                if cv > 40 and len(gtip_data) >= 3:
                    variations.append({
                        'Firma': firma,
                        'GTİP': gtip,
                        'Beyanname_Sayısı': len(gtip_data),
                        'Ortalama_Gider': mean_expense,
                        'Standart_Sapma': std_expense,
                        'Değişkenlik_Katsayısı': cv,
                        'Min_Gider': min_expense,
                        'Max_Gider': max_expense,
                        'Gider_Farkı': max_expense - min_expense,
                        'İlk_Tarih': gtip_data['Beyanname_tarihi'].min() if 'Beyanname_tarihi' in gtip_data.columns else None,
                        'Son_Tarih': gtip_data['Beyanname_tarihi'].max() if 'Beyanname_tarihi' in gtip_data.columns else None
                    })
        
        if not variations:
            return {
                "status": "ok",
                "message": "Anormal yurt dışı gider değişkenliği tespit edilmedi.",
                "html_report": _create_expense_variation_html([], {}, "yurt dışı")
            }
        
        # Sonuçları DataFrame'e dönüştür
        result_df = pd.DataFrame(variations)
        
        # Özet istatistikleri hesapla
        summary_stats = {
            'total_firms_affected': result_df['Firma'].nunique(),
            'total_gtip_affected': len(result_df),
            'highest_variation': result_df['Değişkenlik_Katsayısı'].max(),
            'avg_variation': result_df['Değişkenlik_Katsayısı'].mean(),
            'total_beyanname_affected': result_df['Beyanname_Sayısı'].sum()
        }
        
        # Özet DataFrame
        summary_df = pd.DataFrame([summary_stats])
        
        # HTML raporu oluştur
        html_content = _create_expense_variation_html(variations, summary_stats, "yurt dışı")
        
        return {
            "status": "warning",
            "message": f"{len(variations)} firma-GTİP kombinasyonunda yüksek yurt dışı gider değişkenliği tespit edildi.",
            "data": result_df,
            "summary": summary_df,
            "stats": summary_stats,
            "html_report": html_content
        }
        
    except Exception as e:
        error_msg = f"Yurt dışı gider değişkenlik analizi sırasında hata: {str(e)}"
        print(error_msg)
        print(traceback.format_exc())
        return {
            "status": "error",
            "message": error_msg,
            "html_report": f"<p>Hata: {str(e)}</p>"
        }

def _create_expense_variation_html(variations, summary_stats, expense_type):
    """
    Gider değişkenlik analizi için gelişmiş HTML raporu oluşturur
    """
    if not variations:
        return f"""
        <div style="padding: 20px; text-align: center;">
            <h3>✅ {expense_type.title()} Gider Tutarlılığı Başarılı</h3>
            <p>Tüm firma-GTİP kombinasyonlarında {expense_type} gider beyanları tutarlıdır.</p>
            <div style="background-color: #d4edda; border: 1px solid #c3e6cb; border-radius: 5px; padding: 15px; margin: 20px 0;">
                <p>Anormal {expense_type} gider değişkenliği tespit edilmemiştir.</p>
            </div>
        </div>
        """
    
    color_scheme = "#17a2b8" if expense_type == "yurt dışı" else "#ffc107"
    
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
                background: linear-gradient(135deg, {color_scheme} 0%, #6c757d 100%);
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
            .alert-box {{
                background: linear-gradient(135deg, #fff3cd 0%, #ffeaa7 100%);
                border: 1px solid #ffc107;
                border-radius: 8px;
                padding: 20px;
                margin-bottom: 25px;
                border-left: 5px solid #ffc107;
            }}
            .alert-title {{
                font-size: 18px;
                font-weight: bold;
                color: #856404;
                margin-bottom: 15px;
                display: flex;
                align-items: center;
            }}
            .alert-title::before {{
                content: "📊";
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
                background: linear-gradient(135deg, {color_scheme} 0%, #6c757d 100%);
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
                background: linear-gradient(135deg, {color_scheme} 0%, #6c757d 100%);
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
            .variation-high {{
                background-color: #ffebee;
                color: #c62828;
                font-weight: bold;
                padding: 4px 8px;
                border-radius: 4px;
            }}
            .variation-very-high {{
                background-color: #ffcdd2;
                color: #b71c1c;
                font-weight: bold;
                padding: 4px 8px;
                border-radius: 4px;
            }}
            .evaluation-box {{
                background: linear-gradient(135deg, #e1f5fe 0%, #f3e5f5 100%);
                border: 1px solid #b3e5fc;
                border-radius: 8px;
                padding: 25px;
                margin-top: 30px;
                border-left: 5px solid {color_scheme};
            }}
            .evaluation-title {{
                color: #0277bd;
                font-size: 20px;
                font-weight: bold;
                margin-bottom: 15px;
                display: flex;
                align-items: center;
            }}
            .evaluation-title::before {{
                content: "🔍";
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
                <h1>{expense_type.title()} Gider Değişkenlik Analizi</h1>
                <p>Firma Bazında Anormal Gider Değişkenliği Tespit Raporu</p>
            </div>
            
            <div class="content">
                <div class="alert-box">
                    <div class="alert-title">{expense_type.title()} Gider Değişkenliği Tespit Edildi</div>
                    <p>Bu rapor, aynı firmadan yapılan benzer ithalat işlemlerinde {expense_type} gider beyanlarının tutarsızlığını gösterir.</p>
                    <p><strong>Toplam {summary_stats['total_firms_affected']}</strong> firmada anormal değişkenlik tespit edilmiştir.</p>
                </div>
    """
    
    # İstatistik kartları
    html += f"""
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-number">{summary_stats['total_firms_affected']}</div>
                        <div class="stat-label">Etkilenen Firma</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">{summary_stats['total_gtip_affected']}</div>
                        <div class="stat-label">Tutarsız GTİP-Firma</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">{summary_stats['highest_variation']:.1f}%</div>
                        <div class="stat-label">En Yüksek Değişkenlik</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">{summary_stats['avg_variation']:.1f}%</div>
                        <div class="stat-label">Ortalama Değişkenlik</div>
                    </div>
                </div>
    """
    
    # Detaylı tablo
    html += f"""
                <h3>Detaylı {expense_type.title()} Gider Değişkenlik Analizi</h3>
                <table>
                    <thead>
                        <tr>
                            <th>Firma</th>
                            <th>GTİP Kodu</th>
                            <th>Beyanname Sayısı</th>
                            <th>Değişkenlik (%)</th>
                            <th>Ortalama Gider</th>
                            <th>Min-Max Gider</th>
                            <th>Gider Farkı</th>
                        </tr>
                    </thead>
                    <tbody>
    """
    
    # En fazla 20 sonucu göster
    for i, item in enumerate(sorted(variations, key=lambda x: x['Değişkenlik_Katsayısı'], reverse=True)[:20]):
        # Değişkenlik seviyesine göre stil
        variation_class = "variation-very-high" if item['Değişkenlik_Katsayısı'] > 100 else "variation-high"
        
        html += f"""
                        <tr>
                            <td><strong>{item['Firma'][:50]}{'...' if len(item['Firma']) > 50 else ''}</strong></td>
                            <td>{item['GTİP']}</td>
                            <td>{item['Beyanname_Sayısı']}</td>
                            <td><span class="{variation_class}">{item['Değişkenlik_Katsayısı']:.1f}%</span></td>
                            <td>{item['Ortalama_Gider']:,.2f}</td>
                            <td>{item['Min_Gider']:,.2f} - {item['Max_Gider']:,.2f}</td>
                            <td>{item['Gider_Farkı']:,.2f}</td>
                        </tr>
        """
    
    html += """
                    </tbody>
                </table>
    """
    
    if len(variations) > 20:
        html += f"<p><em>Not: Toplam {len(variations)} sonuçtan ilk 20 tanesi gösterilmektedir.</em></p>"
    
    # Değerlendirme bölümü
    threshold = "40%" if expense_type == "yurt dışı" else "50%"
    
    html += f"""
                <div class="evaluation-box">
                    <div class="evaluation-title">Değerlendirme ve Risk Analizi</div>
                    <p>Aynı firmada benzer ürünler için {expense_type} gider değişkenliği ({threshold}'den fazla) aşağıdaki durumları gösterebilir:</p>
                    <ul>
                        <li><strong>Transfer Fiyatlandırması:</strong> Gümrük değerini manipüle etmek için gider oyunu</li>
                        <li><strong>Vergi Avantajı:</strong> Gümrük vergisi matrahını düşürmek için yüksek gider beyanı</li>
                        <li><strong>Piyasa Değişiklikleri:</strong> {expense_type} ücret tarifelerindeki değişimler</li>
                        <li><strong>Tedarikçi Değişikliği:</strong> Farklı tedarikçilerden farklı koşullarla alım</li>
                        <li><strong>Mevsimsel Faktörler:</strong> Dönemsel navlun, sigorta oranı değişiklikleri</li>
                    </ul>
                    <p><strong>Risk Göstergeleri:</strong></p>
                    <ul>
                        <li>Değişkenlik katsayısı %100'ü aşan durumlar yüksek riskli</li>
                        <li>Aynı döneme ait işlemlerde büyük farklar şüpheli</li>
                        <li>İlişkili kişilerle yapılan işlemlerde yüksek değişkenlik</li>
                        <li>Benzer ürünlerde sistematik farklılık gösteren firmalar</li>
                    </ul>
                    <p><strong>Öneriler:</strong></p>
                    <ul>
                        <li>Yüksek değişkenlik gösteren firmalar detaylı incelemeye alınmalı</li>
                        <li>Gider belgelerinin gerçekliği ve uygunluğu kontrol edilmeli</li>
                        <li>Piyasa fiyatları ile karşılaştırma yapılmalı</li>
                        <li>Transfer fiyatlandırması açısından değerlendirilmeli</li>
                        <li>Sistematik farklılık gösteren durumlar özel incelemeye alınmalı</li>
                    </ul>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html 