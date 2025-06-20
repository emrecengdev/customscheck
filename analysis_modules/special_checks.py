import pandas as pd
import numpy as np
import traceback

def check_supalan_storage_declaration(df):
    """
    Supalan işlemlerde (BS3 kodu) depolama beyanı kontrolü yapar
    
    Args:
        df (pandas.DataFrame): Beyanname verileri içeren DataFrame
    
    Returns:
        dict: Analiz sonuçları
    """
    try:
        print("Supalan-depolama analizi başlatılıyor...")
        
        # BS3 sütununu bul
        bs3_columns = ['BS3', 'bs3', 'Bs3', 'Bulundugu_yer', 'Esyanin_bulundugu_yer']
        bs3_column = None
        
        for col in bs3_columns:
            if col in df.columns:
                bs3_column = col
                break
        
        if bs3_column is None:
            return {
                "status": "error",
                "message": f"BS3 (eşyanın bulunduğu yer) sütunu bulunamadı. Mevcut sütunlar: {', '.join(df.columns.tolist())}"
            }
        
        # Depolama gider sütunlarını bul
        storage_columns = ['Depolama', 'Ardiye', 'Ardiye_ucreti', 'Storage', 'Warehouse_fee']
        storage_column = None
        
        for col in storage_columns:
            if col in df.columns:
                storage_column = col
                break
        
        if storage_column is None:
            return {
                "status": "error",
                "message": f"Depolama gider sütunu bulunamadı. Mevcut sütunlar: {', '.join(df.columns.tolist())}"
            }
        
        # Firma sütununu bul
        firma_columns = ['Adi_unvani', 'Firma', 'Gonderen']
        firma_column = None
        for col in firma_columns:
            if col in df.columns:
                firma_column = col
                break
        
        # Boş değerleri filtrele
        filtered_df = df[
            (df[bs3_column].notna()) & 
            (df[storage_column].notna()) &
            (df[bs3_column] != '') 
        ].copy()
        
        if len(filtered_df) == 0:
            return {
                "status": "ok",
                "message": "Analiz için uygun veri bulunamadı.",
                "html_report": "<p>Analiz için uygun veri bulunamadı.</p>"
            }
        
        # Depolama değerlerini sayısal hale getir
        filtered_df[storage_column] = pd.to_numeric(filtered_df[storage_column], errors='coerce')
        
        # Supalan (taşıtüstü) kodlarını tanımla - yaygın kodlar
        supalan_codes = ['03', '3', 'SUPALAN', 'TASITÜSTÜ', 'TAŞITÜSTÜ', 'TRANSIT', 'VEHICLE']
        
        # Supalan işlemlerini filtrele
        supalan_filter = filtered_df[bs3_column].astype(str).str.upper().isin([code.upper() for code in supalan_codes])
        supalan_data = filtered_df[supalan_filter].copy()
        
        print(f"Toplam {len(supalan_data)} supalan işlemi bulundu.")
        
        if len(supalan_data) == 0:
            return {
                "status": "ok",
                "message": "Supalan işlemi bulunamadı.",
                "html_report": _create_supalan_storage_html([], {})
            }
        
        # Depolama gideri olan supalan işlemlerini bul
        storage_with_supalan = supalan_data[
            (supalan_data[storage_column].notna()) & 
            (supalan_data[storage_column] > 0)
        ]
        
        print(f"Depolama gideri bulunan supalan işlemi sayısı: {len(storage_with_supalan)}")
        
        if len(storage_with_supalan) == 0:
            return {
                "status": "ok",
                "message": "Supalan işlemlerinde depolama gideri tespit edilmedi. Kontrol başarılı.",
                "html_report": _create_supalan_storage_html([], {})
            }
        
        # Problemli kayıtları analiz et
        problematic_records = []
        
        for _, row in storage_with_supalan.iterrows():
            record = {
                'Beyanname_no': row.get('Beyanname_no', 'N/A'),
                'BS3_Kodu': row[bs3_column],
                'Depolama_Gideri': row[storage_column],
                'GTİP': row.get('Gtip', 'N/A'),
                'Ticari_Tanım': row.get('Ticari_tanimi', 'N/A'),
                'Beyanname_Tarihi': row.get('Beyanname_tarihi', 'N/A')
            }
            
            if firma_column:
                record['Firma'] = row.get(firma_column, 'N/A')
            
            problematic_records.append(record)
        
        # Sonuçları DataFrame'e dönüştür
        result_df = pd.DataFrame(problematic_records)
        
        # Özet istatistikleri hesapla
        summary_stats = {
            'total_supalan_records': len(supalan_data),
            'problematic_records': len(storage_with_supalan),
            'total_storage_amount': storage_with_supalan[storage_column].sum(),
            'avg_storage_amount': storage_with_supalan[storage_column].mean(),
            'unique_firms_affected': len(storage_with_supalan[firma_column].unique()) if firma_column else 0
        }
        
        # Özet DataFrame
        summary_df = pd.DataFrame([summary_stats])
        
        # HTML raporu oluştur
        html_content = _create_supalan_storage_html(problematic_records, summary_stats)
        
        return {
            "status": "warning",
            "message": f"{len(storage_with_supalan)} supalan işleminde hatalı depolama gideri beyanı tespit edildi.",
            "data": result_df,
            "summary": summary_df,
            "stats": summary_stats,
            "html_report": html_content
        }
        
    except Exception as e:
        error_msg = f"Supalan-depolama analizi sırasında hata: {str(e)}"
        print(error_msg)
        print(traceback.format_exc())
        return {
            "status": "error",
            "message": error_msg,
            "html_report": f"<p>Hata: {str(e)}</p>"
        }

def _create_supalan_storage_html(problematic_records, summary_stats):
    """
    Supalan-depolama analizi için gelişmiş HTML raporu oluşturur
    """
    if not problematic_records:
        return """
        <div style="padding: 20px; text-align: center;">
            <h3>✅ Supalan-Depolama Kontrolü Başarılı</h3>
            <p>Supalan işlemlerinde hatalı depolama gideri beyanı tespit edilmedi.</p>
            <div style="background-color: #d4edda; border: 1px solid #c3e6cb; border-radius: 5px; padding: 15px; margin: 20px 0;">
                <p><strong>Kontrol Sonucu:</strong> Tüm supalan işlemlerde depolama gideri beyanı doğru şekilde yapılmış (sıfır veya boş).</p>
                <p><strong>Açıklama:</strong> Supalan, eşyanın taşıt üstünde bulunduğu durumu ifade eder ve bu durumda depolama gideri olmaması beklenir.</p>
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
                background: linear-gradient(135deg, #e91e63 0%, #9c27b0 100%);
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
                background: linear-gradient(135deg, #ffebee 0%, #fce4ec 100%);
                border: 1px solid #f8bbd9;
                border-radius: 8px;
                padding: 20px;
                margin-bottom: 25px;
                border-left: 5px solid #e91e63;
            }}
            .alert-title {{
                font-size: 18px;
                font-weight: bold;
                color: #c2185b;
                margin-bottom: 15px;
                display: flex;
                align-items: center;
            }}
            .alert-title::before {{
                content: "🚨";
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
                background: linear-gradient(135deg, #e91e63 0%, #9c27b0 100%);
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
                background: linear-gradient(135deg, #e91e63 0%, #9c27b0 100%);
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
                background-color: #fce4ec;
                transition: background-color 0.3s ease;
            }}
            .storage-amount {{
                background-color: #ffebee;
                color: #c62828;
                font-weight: bold;
                padding: 4px 8px;
                border-radius: 4px;
            }}
            .bs3-code {{
                display: inline-block;
                padding: 4px 8px;
                background-color: #e3f2fd;
                color: #1976d2;
                border-radius: 4px;
                font-size: 11px;
                font-weight: bold;
            }}
            .info-box {{
                background: linear-gradient(135deg, #e8eaf6 0%, #f3e5f5 100%);
                border: 1px solid #c5cae9;
                border-radius: 8px;
                padding: 20px;
                margin-bottom: 25px;
                border-left: 5px solid #3f51b5;
            }}
            .info-title {{
                color: #3f51b5;
                font-size: 16px;
                font-weight: bold;
                margin-bottom: 10px;
                display: flex;
                align-items: center;
            }}
            .info-title::before {{
                content: "ℹ️";
                margin-right: 10px;
                font-size: 18px;
            }}
            .evaluation-box {{
                background: linear-gradient(135deg, #ffebee 0%, #fce4ec 100%);
                border: 1px solid #f8bbd9;
                border-radius: 8px;
                padding: 25px;
                margin-top: 30px;
                border-left: 5px solid #e91e63;
            }}
            .evaluation-title {{
                color: #c2185b;
                font-size: 20px;
                font-weight: bold;
                margin-bottom: 15px;
                display: flex;
                align-items: center;
            }}
            .evaluation-title::before {{
                content: "⚖️";
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
                <h1>Supalan-Depolama Kontrolü</h1>
                <p>BS3 Kodu ile Depolama Gideri Tutarsızlık Analizi</p>
            </div>
            
            <div class="content">
                <div class="info-box">
                    <div class="info-title">Supalan Nedir?</div>
                    <p><strong>Supalan:</strong> Eşyanın taşıt üstünde (kamyon, gemi, tren vb.) bulunduğu durumdur. BS3 kodu "03" veya benzeri kodlarla belirtilir.</p>
                    <p><strong>Kontrol Mantığı:</strong> Supalan işlemlerde eşya depolanmadığı için depolama/ardiye gideri olmaması beklenir.</p>
                </div>
                
                <div class="alert-box">
                    <div class="alert-title">Supalan İşlemlerinde Depolama Gideri Tespit Edildi</div>
                    <p>Bu rapor, BS3 kodu supalan olan işlemlerde hatalı depolama gideri beyanı yapılan kayıtları gösterir.</p>
                    <p><strong>Toplam {summary_stats['problematic_records']}</strong> kayıtta tutarsızlık tespit edilmiştir.</p>
                </div>
    """
    
    # İstatistik kartları
    html += f"""
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-number">{summary_stats['total_supalan_records']}</div>
                        <div class="stat-label">Toplam Supalan İşlemi</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">{summary_stats['problematic_records']}</div>
                        <div class="stat-label">Hatalı Kayıt</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">{summary_stats['total_storage_amount']:,.2f}</div>
                        <div class="stat-label">Toplam Hatalı Depolama</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">{summary_stats['unique_firms_affected']}</div>
                        <div class="stat-label">Etkilenen Firma</div>
                    </div>
                </div>
    """
    
    # Detaylı tablo
    html += """
                <h3>Hatalı Supalan-Depolama Kayıtları</h3>
                <table>
                    <thead>
                        <tr>
                            <th>Beyanname No</th>
                            <th>BS3 Kodu</th>
                            <th>Depolama Gideri</th>
                            <th>GTİP Kodu</th>
                            <th>Ticari Tanım</th>
                            <th>Firma</th>
                            <th>Tarih</th>
                        </tr>
                    </thead>
                    <tbody>
    """
    
    # En fazla 25 sonucu göster
    for i, record in enumerate(sorted(problematic_records, key=lambda x: x['Depolama_Gideri'], reverse=True)[:25]):
        html += f"""
                        <tr>
                            <td><strong>{record['Beyanname_no']}</strong></td>
                            <td><span class="bs3-code">{record['BS3_Kodu']}</span></td>
                            <td><span class="storage-amount">{record['Depolama_Gideri']:,.2f}</span></td>
                            <td>{record['GTİP']}</td>
                            <td>{record['Ticari_Tanım'][:50]}{'...' if len(str(record['Ticari_Tanım'])) > 50 else ''}</td>
                            <td>{record.get('Firma', 'N/A')[:40]}{'...' if len(str(record.get('Firma', ''))) > 40 else ''}</td>
                            <td>{record['Beyanname_Tarihi']}</td>
                        </tr>
        """
    
    html += """
                    </tbody>
                </table>
    """
    
    if len(problematic_records) > 25:
        html += f"<p><em>Not: Toplam {len(problematic_records)} sonuçtan ilk 25 tanesi gösterilmektedir.</em></p>"
    
    # Değerlendirme bölümü
    html += f"""
                <div class="evaluation-box">
                    <div class="evaluation-title">Hukuki Değerlendirme ve Risk Analizi</div>
                    <p>Supalan işlemlerde depolama gideri beyanı aşağıdaki durumları gösterebilir:</p>
                    <ul>
                        <li><strong>Beyan Hatası:</strong> BS3 kodu yanlış veya depolama gideri yanlış beyan edilmiş</li>
                        <li><strong>Gümrük Değeri Manipülasyonu:</strong> Depolama gideri ekleyerek değer artırma</li>
                        <li><strong>Prosedür Karışıklığı:</strong> Farklı işlemlerden kaynaklanan karışıklık</li>
                        <li><strong>Sistem Hatası:</strong> Otomatik hesaplama veya aktarım hatası</li>
                        <li><strong>Belge Uyumsuzluğu:</strong> Ek beyanname ile asıl beyanname arasında fark</li>
                    </ul>
                    <p><strong>Yasal Çerçeve:</strong></p>
                    <ul>
                        <li>4458 Sayılı Gümrük Kanunu madde 21-24 (Gümrük değeri)</li>
                        <li>Gümrük Yönetmeliği Ek-2 (Beyan formları)</li>
                        <li>BS3 kodu supalan durumda depolama gideri olmamalı</li>
                        <li>Gümrük değerine dahil edilecek giderler belirli kurallara tabidir</li>
                    </ul>
                    <p><strong>Öneriler:</strong></p>
                    <ul>
                        <li>Her kayıt için BS3 kodu ile gider beyanının tutarlılığı kontrol edilmeli</li>
                        <li>Sistematik hatalar için beyan sistemi gözden geçirilmeli</li>
                        <li>Firmalar bu konuda eğitilmeli ve bilgilendirilmeli</li>
                        <li>Yüksek tutarlı hatalar öncelikli olarak incelenmeli</li>
                        <li>Tekrarlanan hatalar için ek kontrol mekanizmaları geliştirilmeli</li>
                    </ul>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html 