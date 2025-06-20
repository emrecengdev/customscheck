import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import traceback

def check_unit_price_increase(df):
    """
    Aynı ürünün birim fiyatlarında anormal artışları kontrol eder
    
    Args:
        df (pandas.DataFrame): Beyanname verileri içeren DataFrame
    
    Returns:
        dict: Analiz sonuçları
    """
    try:
        print("Birim fiyat artış analizi başlatılıyor...")
        
        # Tarih sütununu belirle - farklı sütun isimlerini dene
        date_column = None
        possible_date_columns = [
            'Beyanname_Tarihi', 'Beyanname_tarihi', 'Tescil_tarihi', 
            'Tarih', 'Date', 'beyanname_tarihi'
        ]
        
        for col in possible_date_columns:
            if col in df.columns:
                date_column = col
                break
        
        if not date_column:
            return {
                "status": "error",
                "message": f"Tarih sütunu bulunamadı. Aranan sütunlar: {', '.join(possible_date_columns)}"
            }
        
        # Gerekli sütunları kontrol et
        required_columns = ['Gtip', 'Fatura_miktari', 'Fatura_miktarinin_dovizi', date_column]
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            return {
                "status": "error",
                "message": f"Gerekli sütunlar eksik: {', '.join(missing_columns)}"
            }
        
        # Tarih sütununu datetime'a dönüştür
        df_copy = df.copy()
        df_copy[date_column] = pd.to_datetime(df_copy[date_column], errors='coerce')
        
        # Boş değerleri filtrele
        filtered_df = df_copy[
            (df_copy['Gtip'].notna()) & 
            (df_copy['Fatura_miktari'].notna()) & 
            (df_copy['Fatura_miktarinin_dovizi'].notna()) & 
            (df_copy[date_column].notna()) &
            (df_copy['Fatura_miktari'] > 0)
        ].copy()
        
        if len(filtered_df) == 0:
            return {
                "status": "ok",
                "message": "Analiz için uygun veri bulunamadı.",
                "html_report": "<p>Analiz için uygun veri bulunamadı.</p>"
            }
        
        # Birim fiyat hesapla (eğer miktar sütunu varsa)
        if 'Miktar' in filtered_df.columns and 'Miktar' not in missing_columns:
            filtered_df['Birim_Fiyat'] = filtered_df['Fatura_miktari'] / filtered_df['Miktar'].replace(0, np.nan)
        else:
            # Miktar yoksa fatura miktarını kendisi olarak kullan
            filtered_df['Birim_Fiyat'] = filtered_df['Fatura_miktari']
        
        # Ay-yıl kolonu ekle
        filtered_df['Ay_Yil'] = filtered_df[date_column].dt.to_period('M')
        
        # GTİP kodu ve döviz birimi bazında gruplama
        price_increases = []
        
        # Her GTİP kodu için ayrı analiz yap
        for gtip in filtered_df['Gtip'].unique():
            gtip_data = filtered_df[filtered_df['Gtip'] == gtip]
            
            # Her döviz birimi için ayrı analiz
            for currency in gtip_data['Fatura_miktarinin_dovizi'].unique():
                currency_data = gtip_data[gtip_data['Fatura_miktarinin_dovizi'] == currency]
                
                if len(currency_data) < 2:
                    continue
                
                # Aylık ortalama fiyatları hesapla
                monthly_prices = currency_data.groupby('Ay_Yil')['Birim_Fiyat'].mean().sort_index()
                
                if len(monthly_prices) < 2:
                    continue
                
                # Aylık artış oranlarını hesapla
                monthly_increases = monthly_prices.pct_change().dropna()
                
                # 3 aylık artış oranlarını hesapla
                quarterly_increases = monthly_prices.pct_change(periods=3).dropna()
                
                # Anormal artışları tespit et (%3 aylık, %10 3 aylık)
                high_monthly = monthly_increases[monthly_increases > 0.03]  # %3'ten fazla aylık artış
                high_quarterly = quarterly_increases[quarterly_increases > 0.10]  # %10'dan fazla 3 aylık artış
                
                # Anormal artış varsa kaydet
                if len(high_monthly) > 0 or len(high_quarterly) > 0:
                    price_increases.append({
                        'GTİP': gtip,
                        'Döviz': currency,
                        'Aylık_Yüksek_Artış_Sayısı': len(high_monthly),
                        'Maksimum_Aylık_Artış': monthly_increases.max() if len(monthly_increases) > 0 else 0,
                        'Üç_Aylık_Yüksek_Artış_Sayısı': len(high_quarterly),
                        'Maksimum_Üç_Aylık_Artış': quarterly_increases.max() if len(quarterly_increases) > 0 else 0,
                        'İlk_Tarih': currency_data[date_column].min(),
                        'Son_Tarih': currency_data[date_column].max(),
                        'Beyanname_Sayısı': len(currency_data),
                        'Ortalama_Birim_Fiyat': currency_data['Birim_Fiyat'].mean()
                    })
        
        if not price_increases:
            return {
                "status": "ok",
                "message": "Anormal fiyat artışı tespit edilmedi.",
                "html_report": _create_price_increase_html([], summary_stats={})
            }
        
        # Sonuçları DataFrame'e dönüştür
        result_df = pd.DataFrame(price_increases)
        
        # Özet istatistikleri hesapla
        summary_stats = {
            'total_gtip_affected': len(result_df),
            'total_high_monthly': result_df['Aylık_Yüksek_Artış_Sayısı'].sum(),
            'total_high_quarterly': result_df['Üç_Aylık_Yüksek_Artış_Sayısı'].sum(),
            'max_monthly_increase': result_df['Maksimum_Aylık_Artış'].max(),
            'max_quarterly_increase': result_df['Maksimum_Üç_Aylık_Artış'].max()
        }
        
        # Özet DataFrame oluştur
        summary_df = pd.DataFrame([summary_stats])
        
        # HTML raporu oluştur
        html_content = _create_price_increase_html(price_increases, summary_stats)
        
        return {
            "status": "warning",
            "message": f"{len(price_increases)} GTİP kodunda anormal fiyat artışı tespit edildi.",
            "data": result_df,
            "summary": summary_df,
            "stats": summary_stats,
            "html_report": html_content
        }
        
    except Exception as e:
        error_msg = f"Birim fiyat artış analizi sırasında hata: {str(e)}"
        print(error_msg)
        print(traceback.format_exc())
        return {
            "status": "error",
            "message": error_msg,
            "html_report": f"<p>Hata: {str(e)}</p>"
        }

def _create_price_increase_html(price_increases, summary_stats):
    """
    Birim fiyat artış analizi için gelişmiş HTML raporu oluşturur
    """
    if not price_increases:
        return """
        <div style="padding: 20px; text-align: center;">
            <h3>✅ Anormal Fiyat Artışı Tespit Edilmedi</h3>
            <p>Tüm GTİP kodlarında fiyat artışları normal sınırlar içinde kalmaktadır.</p>
            <div style="background-color: #d4edda; border: 1px solid #c3e6cb; border-radius: 5px; padding: 15px; margin: 20px 0;">
                <p><strong>Değerlendirme Kriterleri:</strong></p>
                <ul style="text-align: left; margin: 0;">
                    <li>Aylık fiyat artışı: %3'ün altında</li>
                    <li>3 aylık fiyat artışı: %10'un altında</li>
                </ul>
            </div>
        </div>
        """
    
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
                background: linear-gradient(135deg, #dc3545 0%, #fd7e14 100%);
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
                content: "⚠️";
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
                background: linear-gradient(135deg, #dc3545 0%, #c82333 100%);
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
                background: linear-gradient(135deg, #dc3545 0%, #fd7e14 100%);
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
                background-color: #fff3cd;
                transition: background-color 0.3s ease;
            }}
            .percentage {{
                font-weight: bold;
                padding: 4px 8px;
                border-radius: 4px;
            }}
            .percentage.high {{
                background-color: #ffebee;
                color: #c62828;
            }}
            .percentage.very-high {{
                background-color: #ffcdd2;
                color: #b71c1c;
            }}
            .currency {{
                display: inline-block;
                padding: 4px 8px;
                background-color: #e3f2fd;
                color: #1976d2;
                border-radius: 4px;
                font-size: 11px;
                font-weight: bold;
            }}
            .evaluation-box {{
                background: linear-gradient(135deg, #ffebee 0%, #fce4ec 100%);
                border: 1px solid #f8bbd9;
                border-radius: 8px;
                padding: 25px;
                margin-top: 30px;
                border-left: 5px solid #dc3545;
            }}
            .evaluation-title {{
                color: #c62828;
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
                <h1>Birim Fiyat Artış Analizi</h1>
                <p>Anormal Fiyat Artışı Tespit Raporu</p>
            </div>
            
            <div class="content">
                <div class="alert-box">
                    <div class="alert-title">Kritik Fiyat Artışı Tespit Edildi</div>
                    <p>Bu rapor, GTİP kodları bazında anormal birim fiyat artışlarını gösterir.</p>
                    <p><strong>Toplam {summary_stats['total_gtip_affected']}</strong> GTİP kodunda limit üstü artış tespit edilmiştir.</p>
                </div>
    """
    
    # İstatistik kartları
    html += f"""
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-number">{summary_stats['total_gtip_affected']}</div>
                        <div class="stat-label">Etkilenen GTİP Kodu</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">{summary_stats['total_high_monthly']}</div>
                        <div class="stat-label">Yüksek Aylık Artış</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">{summary_stats['total_high_quarterly']}</div>
                        <div class="stat-label">Yüksek 3 Aylık Artış</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">{summary_stats['max_monthly_increase']:.1%}</div>
                        <div class="stat-label">En Yüksek Aylık Artış</div>
                    </div>
                </div>
    """
    
    # Detaylı tablo
    html += """
                <h3>Detaylı Fiyat Artış Analizi</h3>
                <table>
                    <thead>
                        <tr>
                            <th>GTİP Kodu</th>
                            <th>Döviz</th>
                            <th>Aylık Yüksek Artış</th>
                            <th>Max Aylık (%)</th>
                            <th>3 Aylık Yüksek Artış</th>
                            <th>Max 3 Aylık (%)</th>
                            <th>Beyanname Sayısı</th>
                            <th>Tarih Aralığı</th>
                        </tr>
                    </thead>
                    <tbody>
    """
    
    # En fazla 20 sonucu göster
    for i, item in enumerate(sorted(price_increases, key=lambda x: x['Maksimum_Aylık_Artış'], reverse=True)[:20]):
        # Yüzde değerleri için stil belirleme
        monthly_class = "very-high" if item['Maksimum_Aylık_Artış'] > 0.10 else "high"
        quarterly_class = "very-high" if item['Maksimum_Üç_Aylık_Artış'] > 0.25 else "high"
        
        html += f"""
                        <tr>
                            <td><strong>{item['GTİP']}</strong></td>
                            <td><span class="currency">{item['Döviz']}</span></td>
                            <td><strong>{item['Aylık_Yüksek_Artış_Sayısı']}</strong></td>
                            <td><span class="percentage {monthly_class}">{item['Maksimum_Aylık_Artış']:.1%}</span></td>
                            <td><strong>{item['Üç_Aylık_Yüksek_Artış_Sayısı']}</strong></td>
                            <td><span class="percentage {quarterly_class}">{item['Maksimum_Üç_Aylık_Artış']:.1%}</span></td>
                            <td>{item['Beyanname_Sayısı']}</td>
                            <td>{item['İlk_Tarih'].strftime('%Y-%m-%d')} - {item['Son_Tarih'].strftime('%Y-%m-%d')}</td>
                        </tr>
        """
    
    html += """
                    </tbody>
                </table>
    """
    
    if len(price_increases) > 20:
        html += f"<p><em>Not: Toplam {len(price_increases)} sonuçtan ilk 20 tanesi gösterilmektedir.</em></p>"
    
    # Değerlendirme bölümü
    html += f"""
                <div class="evaluation-box">
                    <div class="evaluation-title">Değerlendirme ve Risk Analizi</div>
                    <p>Tespit edilen fiyat artışları aşağıdaki durumları gösterebilir:</p>
                    <ul>
                        <li><strong>Piyasa Koşulları:</strong> Hammadde fiyatlarındaki artış, döviz kuru değişimleri</li>
                        <li><strong>Tedarik Zinciri Sorunları:</strong> Kıtlık, lojistik sorunlar</li>
                        <li><strong>Transfer Fiyatlandırması:</strong> İlişkili kişilerle yapılan işlemlerde fiyat manipülasyonu</li>
                        <li><strong>Spekülatif İşlemler:</strong> Yapay fiyat artışları</li>
                        <li><strong>Vergi Avantajı:</strong> Gümrük vergisi, ÖTV değişikliklerinden kaçınma</li>
                    </ul>
                    <p><strong>Öneriler:</strong></p>
                    <ul>
                        <li>Yüksek artış gösteren GTİP kodları için detaylı inceleme yapılmalı</li>
                        <li>Aynı dönemde piyasa fiyatları ile karşılaştırma yapılmalı</li>
                        <li>İlişkili kişiler arası işlemler özellikle dikkatle incelenmeli</li>
                        <li>Aylık %3'ü, 3 aylık %10'u aşan artışlar için ek belge talep edilmeli</li>
                    </ul>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html 