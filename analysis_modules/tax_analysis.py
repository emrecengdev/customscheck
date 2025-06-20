import pandas as pd
import numpy as np
import traceback

def check_kdv_consistency(df):
    """
    Aynı GTİP kodu için farklı KDV oranları beyan edilip edilmediğini kontrol eder
    
    Args:
        df (pandas.DataFrame): Beyanname verileri içeren DataFrame
    
    Returns:
        dict: Analiz sonuçları
    """
    try:
        print("KDV tutarlılık analizi başlatılıyor...")
        
        # KDV sütununu bul
        kdv_columns = ['KDV', 'Kdv', 'KDV_orani', 'Kdv_orani', 'KDV_Orani']
        kdv_column = None
        
        for col in kdv_columns:
            if col in df.columns:
                kdv_column = col
                break
        
        if 'Gtip' not in df.columns or kdv_column is None:
            return {
                "status": "error",
                "message": f"GTİP veya KDV sütunu bulunamadı. Mevcut sütunlar: {', '.join(df.columns.tolist())}"
            }
        
        # Boş değerleri filtrele
        filtered_df = df[
            (df['Gtip'].notna()) & 
            (df[kdv_column].notna()) & 
            (df['Gtip'] != '') & 
            (df[kdv_column] != '')
        ].copy()
        
        if len(filtered_df) == 0:
            return {
                "status": "ok",
                "message": "Analiz için uygun veri bulunamadı.",
                "html_report": "<p>Analiz için uygun veri bulunamadı.</p>"
            }
        
        # KDV oranlarını sayısal değere dönüştür
        filtered_df[kdv_column] = pd.to_numeric(filtered_df[kdv_column], errors='coerce')
        filtered_df = filtered_df[filtered_df[kdv_column].notna()]
        
        # Her GTİP kodu için benzersiz KDV oranlarını bul
        gtip_kdv_groups = filtered_df.groupby('Gtip')[kdv_column].unique().reset_index()
        gtip_kdv_groups['KDV_Çeşit_Sayısı'] = gtip_kdv_groups[kdv_column].apply(len)
        
        print(f"Toplam {len(gtip_kdv_groups)} benzersiz GTİP kodu analiz edildi.")
        
        # Birden fazla KDV oranı olan GTİP kodlarını filtrele
        multiple_kdv = gtip_kdv_groups[gtip_kdv_groups['KDV_Çeşit_Sayısı'] > 1].sort_values(
            by='KDV_Çeşit_Sayısı', ascending=False
        )
        
        print(f"Birden fazla KDV oranı içeren GTİP sayısı: {len(multiple_kdv)}")
        
        if multiple_kdv.empty:
            return {
                "status": "ok",
                "message": "Aynı GTİP kodunda farklı KDV oranı kullanımı tespit edilmedi.",
                "html_report": _create_kdv_consistency_html([], {})
            }
        
        # Detaylı sonuçlar için veri hazırla
        result_data = []
        inconsistent_rows = []
        
        for _, row in multiple_kdv.iterrows():
            gtip = row['Gtip']
            kdv_rates = row[kdv_column]
            
            # Bu GTİP kodu için tüm kayıtları al
            gtip_data = filtered_df[filtered_df['Gtip'] == gtip]
            
            # Her KDV oranı için istatistik
            kdv_stats = []
            for kdv_rate in kdv_rates:
                kdv_rows = gtip_data[gtip_data[kdv_column] == kdv_rate]
                beyanname_count = len(kdv_rows['Beyanname_no'].unique()) if 'Beyanname_no' in kdv_rows.columns else len(kdv_rows)
                
                kdv_stats.append({
                    'kdv_oran': kdv_rate,
                    'beyanname_sayisi': beyanname_count,
                    'kayit_sayisi': len(kdv_rows)
                })
            
            # En sık kullanılan KDV oranını bul
            kdv_stats.sort(key=lambda x: x['beyanname_sayisi'], reverse=True)
            most_common_kdv = kdv_stats[0]['kdv_oran']
            
            result_data.append({
                'GTİP': gtip,
                'KDV_Çeşit_Sayısı': len(kdv_rates),
                'KDV_Oranları': ', '.join([f"{k:.1f}%" for k in sorted(kdv_rates)]),
                'En_Sık_KDV': f"{most_common_kdv:.1f}%",
                'Toplam_Beyanname': len(gtip_data['Beyanname_no'].unique()) if 'Beyanname_no' in gtip_data.columns else len(gtip_data),
                'KDV_Detayları': kdv_stats
            })
            
            # Tutarsız satırları da topla
            for _, data_row in gtip_data.iterrows():
                row_dict = {
                    'GTİP': gtip,
                    'KDV_Oranı': data_row[kdv_column],
                    'En_Sık_KDV': most_common_kdv,
                    'Tutarlı_mı': 'Evet' if data_row[kdv_column] == most_common_kdv else 'Hayır'
                }
                
                # Diğer önemli sütunları ekle
                for col in ['Beyanname_no', 'Adi_unvani', 'Ticari_tanimi', 'Mensei_ulke']:
                    if col in data_row:
                        row_dict[col] = data_row[col]
                
                inconsistent_rows.append(row_dict)
        
        # Sonuçları DataFrame'e dönüştür
        result_df = pd.DataFrame(result_data)
        inconsistent_df = pd.DataFrame(inconsistent_rows)
        
        # Özet istatistikleri hesapla
        summary_stats = {
            'total_gtip_affected': len(multiple_kdv),
            'total_beyanname_affected': inconsistent_df['Beyanname_no'].nunique() if 'Beyanname_no' in inconsistent_df.columns else len(inconsistent_df),
            'most_varied_gtip': multiple_kdv.iloc[0]['Gtip'] if not multiple_kdv.empty else None,
            'max_kdv_varieties': multiple_kdv['KDV_Çeşit_Sayısı'].max() if not multiple_kdv.empty else 0
        }
        
        # Özet DataFrame
        summary_df = pd.DataFrame([summary_stats])
        
        # HTML raporu oluştur
        html_content = _create_kdv_consistency_html(result_data, summary_stats)
        
        return {
            "status": "warning",
            "message": f"{len(multiple_kdv)} GTİP kodunda farklı KDV oranları kullanılmış.",
            "data": inconsistent_df,
            "summary": summary_df,
            "stats": summary_stats,
            "html_report": html_content
        }
        
    except Exception as e:
        error_msg = f"KDV tutarlılık analizi sırasında hata: {str(e)}"
        print(error_msg)
        print(traceback.format_exc())
        return {
            "status": "error",
            "message": error_msg,
            "html_report": f"<p>Hata: {str(e)}</p>"
        }

def _create_kdv_consistency_html(result_data, summary_stats):
    """
    KDV tutarlılık analizi için gelişmiş HTML raporu oluşturur
    """
    if not result_data:
        return """
        <div style="padding: 20px; text-align: center;">
            <h3>✅ KDV Tutarlılığı Başarılı</h3>
            <p>Tüm GTİP kodlarında tutarlı KDV oranları kullanılmaktadır.</p>
            <div style="background-color: #d4edda; border: 1px solid #c3e6cb; border-radius: 5px; padding: 15px; margin: 20px 0;">
                <p>Aynı ürün grubu için farklı KDV oranı beyanı tespit edilmemiştir.</p>
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
                background: linear-gradient(135deg, #28a745 0%, #20c997 100%);
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
                background: linear-gradient(135deg, #28a745 0%, #20c997 100%);
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
                background: linear-gradient(135deg, #28a745 0%, #20c997 100%);
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
                background-color: #e8f5e8;
                transition: background-color 0.3s ease;
            }}
            .kdv-rate {{
                display: inline-block;
                padding: 4px 8px;
                background-color: #e3f2fd;
                color: #1976d2;
                border-radius: 4px;
                font-size: 11px;
                font-weight: bold;
                margin: 2px;
            }}
            .most-common {{
                background-color: #c8e6c9 !important;
                color: #2e7d32 !important;
            }}
            .evaluation-box {{
                background: linear-gradient(135deg, #e8f5e8 0%, #f3e5f5 100%);
                border: 1px solid #c8e6c9;
                border-radius: 8px;
                padding: 25px;
                margin-top: 30px;
                border-left: 5px solid #28a745;
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
                content: "📊";
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
            .gtip-details {{
                background-color: #f8f9fa;
                border-radius: 6px;
                padding: 15px;
                margin: 10px 0;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>KDV Tutarlılık Analizi</h1>
                <p>GTİP Kodu Bazında KDV Oranı Tutarsızlık Raporu</p>
            </div>
            
            <div class="content">
                <div class="alert-box">
                    <div class="alert-title">KDV Oranı Tutarsızlığı Tespit Edildi</div>
                    <p>Bu rapor, aynı GTİP koduna sahip ürünlerde farklı KDV oranları beyan edildiği durumları gösterir.</p>
                    <p><strong>Toplam {summary_stats['total_gtip_affected']}</strong> GTİP kodunda tutarsızlık tespit edilmiştir.</p>
                </div>
    """
    
    # İstatistik kartları
    html += f"""
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-number">{summary_stats['total_gtip_affected']}</div>
                        <div class="stat-label">Tutarsız GTİP Kodu</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">{summary_stats['total_beyanname_affected']}</div>
                        <div class="stat-label">Etkilenen Beyanname</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">{summary_stats['max_kdv_varieties']}</div>
                        <div class="stat-label">En Fazla KDV Çeşidi</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">{len(result_data)}</div>
                        <div class="stat-label">Toplam Analiz Edilen</div>
                    </div>
                </div>
    """
    
    # Detaylı analiz
    html += """
                <h3>Detaylı KDV Tutarsızlık Analizi</h3>
    """
    
    # En fazla 15 sonucu göster
    for i, item in enumerate(sorted(result_data, key=lambda x: x['KDV_Çeşit_Sayısı'], reverse=True)[:15]):
        html += f"""
                <div class="gtip-details">
                    <h4>GTİP Kodu: {item['GTİP']}</h4>
                    <p><strong>Kullanılan KDV Oranları:</strong> {item['KDV_Oranları']}</p>
                    <p><strong>En Sık Kullanılan:</strong> <span class="kdv-rate most-common">{item['En_Sık_KDV']}</span></p>
                    <p><strong>Toplam Beyanname:</strong> {item['Toplam_Beyanname']}</p>
                    
                    <table style="margin-top: 15px;">
                        <thead>
                            <tr>
                                <th>KDV Oranı</th>
                                <th>Beyanname Sayısı</th>
                                <th>Kayıt Sayısı</th>
                                <th>Durumu</th>
                            </tr>
                        </thead>
                        <tbody>
        """
        
        # KDV detaylarını göster
        for kdv_detail in item['KDV_Detayları']:
            is_most_common = kdv_detail['kdv_oran'] == float(item['En_Sık_KDV'].replace('%', ''))
            status = "En Sık Kullanılan" if is_most_common else "Nadir Kullanılan"
            status_class = "most-common" if is_most_common else ""
            
            html += f"""
                            <tr>
                                <td><span class="kdv-rate {status_class}">{kdv_detail['kdv_oran']:.1f}%</span></td>
                                <td>{kdv_detail['beyanname_sayisi']}</td>
                                <td>{kdv_detail['kayit_sayisi']}</td>
                                <td>{status}</td>
                            </tr>
            """
        
        html += """
                        </tbody>
                    </table>
                </div>
        """
    
    if len(result_data) > 15:
        html += f"<p><em>Not: Toplam {len(result_data)} sonuçtan ilk 15 tanesi gösterilmektedir.</em></p>"
    
    # Değerlendirme bölümü
    html += f"""
                <div class="evaluation-box">
                    <div class="evaluation-title">Değerlendirme ve Risk Analizi</div>
                    <p>Aynı GTİP kodunda farklı KDV oranları beyan edilmesi aşağıdaki durumları gösterebilir:</p>
                    <ul>
                        <li><strong>Ürün Sınıflandırma Hatası:</strong> Aynı ürünün farklı GTİP altında beyan edilmesi</li>
                        <li><strong>KDV Oranı Değişikliği:</strong> Zaman içinde yasal düzenlemelerle değişen oranlar</li>
                        <li><strong>İstisna ve Muafiyet:</strong> Özel durumlar için uygulanan farklı oranlar</li>
                        <li><strong>Beyan Hatası:</strong> Yanlış KDV oranı beyanı</li>
                        <li><strong>Transfer Fiyatlandırması:</strong> Vergi avantajı sağlamak için manipülasyon</li>
                    </ul>
                    <p><strong>Öneriler:</strong></p>
                    <ul>
                        <li>En sık kullanılan KDV oranının doğruluğu araştırılmalı</li>
                        <li>Nadir kullanılan oranlar için gerekçe talep edilmeli</li>
                        <li>Zaman serisi analizi ile oran değişikliklerinin nedeni incelenmeli</li>
                        <li>İlgili mevzuat ile KDV oranlarının uyumluluğu kontrol edilmeli</li>
                        <li>Sistematik farklılık gösteren firmalar özel incelemeye alınmalı</li>
                    </ul>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html 