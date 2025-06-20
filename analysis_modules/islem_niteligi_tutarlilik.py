import pandas as pd
import traceback


def kontrol_islem_niteligi_tutarlilik(df):
    """
    İşlem niteliği kodlarının ödeme şekli ve rejim kodu ile tutarlılığını kontrol eder
    
    Args:
        df (pandas.DataFrame): Beyanname verileri içeren DataFrame
    
    Returns:
        dict: Analiz sonuçları
    """
    try:
        print("İşlem Niteliği tutarlılık kontrolü başlatılıyor...")
        
        # Kontrol edilecek sütunların varlığını doğrula
        required_columns = ['Kalem_Islem_Niteligi', 'Odeme_sekli', 'Rejim', 'Beyanname_no']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            missing_cols_str = ", ".join(missing_columns)
            return {
                "status": "error",
                "message": f"Kontrol için gerekli sütunlar eksik: {missing_cols_str}",
                "html_report": f"<p>Hata: Gerekli sütunlar eksik: {missing_cols_str}</p>"
            }
        
        # Veri filtreleme
        filtered_df = df.dropna(subset=required_columns)
        print(f"Filtrelenmiş veri: {len(filtered_df)} satır")
        
        if len(filtered_df) == 0:
            return {
                "status": "error",
                "message": "Analiz için gerekli verilerde çok fazla eksik değer var",
                "html_report": "<p>Hata: Analiz için gerekli verilerde çok fazla eksik değer var</p>"
            }
        
        # 1. Kontrol: Ödeme şekli "bedelsiz" ise işlem niteliği kodu "99" olmalı
        bedelsiz_payment_filter = filtered_df['Odeme_sekli'].str.lower().str.contains('bedelsiz', na=False)
        incorrect_payment_code = filtered_df[bedelsiz_payment_filter & (filtered_df['Kalem_Islem_Niteligi'] != '99')].copy()
        if not incorrect_payment_code.empty:
            incorrect_payment_code['Beklenen Kod'] = '99'
            incorrect_payment_code['Girilen Kod'] = incorrect_payment_code['Kalem_Islem_Niteligi']

        # 2. Kontrol: Rejim kodu "6123" ise işlem niteliği kodu "61" olmalı
        rejim_filter = filtered_df['Rejim'] == '6123'
        incorrect_rejim_code = filtered_df[rejim_filter & (filtered_df['Kalem_Islem_Niteligi'] != '61')].copy()
        if not incorrect_rejim_code.empty:
            incorrect_rejim_code['Beklenen Kod'] = '61'
            incorrect_rejim_code['Girilen Kod'] = incorrect_rejim_code['Kalem_Islem_Niteligi']

        # Tüm tutarsızlıkları birleştir
        all_inconsistencies = pd.concat([incorrect_payment_code, incorrect_rejim_code]).drop_duplicates()
        
        print(f"Toplam tutarsızlık: {len(all_inconsistencies)} kayıt")
        
        # Veri görünümü için sadece gerekli sütunları seç
        if not all_inconsistencies.empty:
            # Beyan edilen ve beyan edilmesi gereken işlem niteliği kodlarını oluştur
            display_data = all_inconsistencies.copy()
            
            # Beyan edilen işlem niteliği kodu
            display_data['Beyan_Edilen_Islem_Niteligi'] = display_data['Kalem_Islem_Niteligi']
            
            # Beyan edilmesi gereken işlem niteliği kodunu hesapla
            def get_expected_code(row):
                # Bedelsiz ödeme ise 99 olmalı
                if 'bedelsiz' in str(row['Odeme_sekli']).lower():
                    return '99'
                # Rejim 6123 ise 61 olmalı
                elif str(row['Rejim']) == '6123':
                    return '61'
                else:
                    return row['Kalem_Islem_Niteligi']  # Mevcut kod doğru
            
            display_data['Beyan_Edilmesi_Gereken_Islem_Niteligi'] = display_data.apply(get_expected_code, axis=1)
            
            # Sadece istenen sütunları seç
            display_columns = ['Beyanname_no', 'Beyan_Edilen_Islem_Niteligi', 'Beyan_Edilmesi_Gereken_Islem_Niteligi']
            final_display_data = display_data[display_columns].drop_duplicates()
        else:
            final_display_data = pd.DataFrame()
        
        # Beyanname numarasına göre tekil kayıtları al
        if 'Beyanname_no' in all_inconsistencies.columns:
            unique_inconsistencies = all_inconsistencies.drop_duplicates(subset=['Beyanname_no'])
            unique_beyanname_count = len(unique_inconsistencies)
        else:
            unique_inconsistencies = all_inconsistencies
            unique_beyanname_count = len(unique_inconsistencies)
        
        # Özet tablosu oluştur
        summary_df = _olustur_islem_niteligi_ozet_tablo(
            filtered_df, incorrect_payment_code, incorrect_rejim_code
        )
        
        if len(all_inconsistencies) > 0:
            # HTML raporu oluştur
            try:
                html_content = olustur_islem_niteligi_tutarlilik_html(
                    all_inconsistencies, summary_df, incorrect_payment_code, incorrect_rejim_code
                )
                print("HTML raporu başarıyla oluşturuldu.")
            except Exception as e:
                print(f"HTML rapor oluşturma hatası: {str(e)}")
                print(f"Hata detayı: {traceback.format_exc()}")
                html_content = f"""
                <html>
                <body style="font-family: Arial; padding: 20px;">
                    <h2>HTML Rapor Oluşturma Hatası</h2>
                    <p><strong>Hata Mesajı:</strong> {str(e)}</p>
                    <p><strong>Durum:</strong> İşlem Niteliği analizi tamamlandı ancak HTML raporu oluşturulamadı.</p>
                    <p><strong>Sonuç:</strong> {unique_beyanname_count} beyannamede tutarsızlık bulundu.</p>
                </body>
                </html>
                """
            
            return {
                "status": "warning",
                "message": f"{unique_beyanname_count} adet beyannamede tutarsız işlem niteliği kodu bulundu.",
                "data": final_display_data,
                "summary": summary_df,
                "detail": {
                    "bedelsiz_payment_errors": len(incorrect_payment_code.drop_duplicates(subset=['Beyanname_no'])),
                    "rejim_6123_errors": len(incorrect_rejim_code.drop_duplicates(subset=['Beyanname_no'])),
                    "total_inconsistencies": unique_beyanname_count
                },
                "html_report": html_content
            }
        else:
            # Başarılı kontrol
            html_content = """
            <html>
            <head>
                <style>
                    body { font-family: Arial, sans-serif; margin: 20px; }
                    .success { color: #28a745; background-color: #d4edda; padding: 15px; border-radius: 5px; }
                    .info { background-color: #e3f2fd; padding: 15px; border-radius: 5px; margin: 15px 0; }
                </style>
            </head>
            <body>
                <h2>İşlem Niteliği Tutarlılık Raporu</h2>
                <div class="success">
                    <h3>✅ Kontrol Başarılı</h3>
                    <p>Tüm işlem niteliği kodları ödeme şekli ve rejim kodu ile tutarlı bulunmuştur.</p>
                </div>
                <div class="info">
                    <h4>Kontrol Kriterleri:</h4>
                    <ul>
                        <li>Ödeme şekli "bedelsiz" ise işlem niteliği kodu "99" olmalı</li>
                        <li>Rejim kodu "6123" ise işlem niteliği kodu "61" olmalı</li>
                    </ul>
                </div>
            </body>
            </html>
            """
            
            return {
                "status": "ok",
                "message": "Tüm işlem niteliği kodları ödeme şekli ve rejim kodu ile tutarlı.",
                "summary": summary_df,
                "html_report": html_content
            }
    
    except Exception as e:
        error_msg = f"İşlem niteliği kontrolü sırasında hata: {str(e)}"
        print(error_msg)
        print(f"Hata detayı: {traceback.format_exc()}")
        
        return {
            "status": "error",
            "message": error_msg,
            "html_report": f"<p>Hata: {error_msg}</p>"
        }


def _olustur_islem_niteligi_ozet_tablo(filtered_df, incorrect_payment_code, incorrect_rejim_code):
    """İşlem niteliği kontrolü için özet tablo oluştur"""
    # Toplam ve hatalı kayıt sayılarını hesapla
    total_bedelsiz = filtered_df['Odeme_sekli'].str.lower().str.contains('bedelsiz', na=False).sum()
    total_rejim_6123 = (filtered_df['Rejim'] == '6123').sum()
    
    # Benzersiz beyanname sayısını hesapla
    if 'Beyanname_no' in incorrect_payment_code.columns:
        incorrect_bedelsiz = len(incorrect_payment_code.drop_duplicates(subset=['Beyanname_no']))
    else:
        incorrect_bedelsiz = len(incorrect_payment_code)
        
    if 'Beyanname_no' in incorrect_rejim_code.columns:
        incorrect_rejim = len(incorrect_rejim_code.drop_duplicates(subset=['Beyanname_no']))
    else:
        incorrect_rejim = len(incorrect_rejim_code)
    
    # Uygunluk oranlarını hesapla
    compliance_bedelsiz = 100 if total_bedelsiz == 0 else (1 - incorrect_bedelsiz/total_bedelsiz) * 100
    compliance_rejim = 100 if total_rejim_6123 == 0 else (1 - incorrect_rejim/total_rejim_6123) * 100
    
    # Özet tabloyu oluştur
    summary_df = pd.DataFrame({
        'Kontrol Türü': ['Bedelsiz Ödeme-Kod 99', 'Rejim 6123-Kod 61'],
        'Toplam Kayıt': [total_bedelsiz, total_rejim_6123],
        'Hatalı Beyanname': [incorrect_bedelsiz, incorrect_rejim],
        'Uygunluk Oranı (%)': [round(compliance_bedelsiz, 2), round(compliance_rejim, 2)]
    })
    
    return summary_df


def olustur_islem_niteligi_tutarlilik_html(all_inconsistencies, summary_df, incorrect_payment_code, incorrect_rejim_code):
    """
    İşlem niteliği tutarlılık kontrolü için gelişmiş HTML raporu oluşturur
    """
    if all_inconsistencies.empty:
        return "<p>Herhangi bir tutarsızlık bulunamadı.</p>"
    
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
                max-width: 1200px;
                margin: 0 auto;
                background-color: white;
                border-radius: 10px;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
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
                font-size: 28px;
                font-weight: 300;
            }}
            .content {{
                padding: 30px;
            }}
            .summary-box {{
                background-color: #fff3cd;
                border: 1px solid #ffeaa7;
                border-radius: 8px;
                padding: 20px;
                margin-bottom: 25px;
                border-left: 5px solid #fdcb6e;
            }}
            .summary-title {{
                font-size: 18px;
                font-weight: bold;
                color: #b8860b;
                margin-bottom: 15px;
                display: flex;
                align-items: center;
            }}
            .summary-title::before {{
                content: "⚠️";
                margin-right: 10px;
                font-size: 20px;
            }}
            .info-card {{
                background-color: #e3f2fd;
                border: 1px solid #bbdefb;
                border-radius: 8px;
                padding: 20px;
                margin: 20px 0;
                border-left: 5px solid #2196f3;
            }}
            .info-card h3 {{
                color: #1976d2;
                margin-top: 0;
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
            .error-section {{
                margin: 25px 0;
                padding: 20px;
                border-radius: 8px;
                border: 1px solid #ffcdd2;
                background-color: #ffebee;
            }}
            .error-title {{
                color: #c62828;
                font-size: 18px;
                font-weight: bold;
                margin-bottom: 15px;
                display: flex;
                align-items: center;
            }}
            .error-title::before {{
                content: "❌";
                margin-right: 10px;
                font-size: 20px;
            }}
            .badge {{
                display: inline-block;
                padding: 4px 8px;
                background-color: #e3f2fd;
                color: #1976d2;
                border-radius: 4px;
                font-size: 12px;
                font-weight: bold;
                margin: 2px;
            }}
            .stat-card {{
                display: inline-block;
                background: white;
                border-radius: 8px;
                padding: 20px;
                margin: 10px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                text-align: center;
                min-width: 150px;
            }}
            .stat-number {{
                font-size: 32px;
                font-weight: bold;
                color: #e74c3c;
            }}
            .stat-label {{
                color: #6c757d;
                font-size: 14px;
                margin-top: 5px;
            }}
            .rules-box {{
                background-color: #f0f8ff;
                border: 1px solid #b3d9ff;
                border-radius: 8px;
                padding: 20px;
                margin: 20px 0;
            }}
            .rule-item {{
                display: flex;
                align-items: center;
                margin: 10px 0;
                padding: 10px;
                background-color: white;
                border-radius: 6px;
                border-left: 4px solid #2196f3;
            }}
            .rule-icon {{
                font-size: 18px;
                margin-right: 12px;
                color: #2196f3;
            }}
            .code-comparison {{
                display: flex;
                align-items: center;
                gap: 10px;
            }}
            .code-wrong {{
                background-color: #ffebee;
                color: #c62828;
                padding: 4px 8px;
                border-radius: 4px;
                font-weight: bold;
                border: 1px solid #ffcdd2;
            }}
            .code-correct {{
                background-color: #e8f5e8;
                color: #2e7d32;
                padding: 4px 8px;
                border-radius: 4px;
                font-weight: bold;
                border: 1px solid #c8e6c9;
            }}
            .arrow {{
                color: #666;
                font-weight: bold;
            }}
            th.code-column {{
                text-align: center;
            }}
            td.code-cell {{
                text-align: center;
                font-weight: bold;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>İşlem Niteliği Tutarlılık Raporu</h1>
                <p>Ödeme Şekli ve Rejim Kodu Uyumluluk Analizi</p>
            </div>
            
            <div class="content">
    """
    
    # Ana özet bilgileri
    total_errors = len(all_inconsistencies.drop_duplicates(subset=['Beyanname_no']))
    bedelsiz_errors = len(incorrect_payment_code.drop_duplicates(subset=['Beyanname_no']))
    rejim_errors = len(incorrect_rejim_code.drop_duplicates(subset=['Beyanname_no']))
    
    html += f"""
                <div class="summary-box">
                    <div class="summary-title">Tutarsızlık Tespit Edildi</div>
                    <p>Toplam <strong>{total_errors}</strong> beyannamede işlem niteliği kodu ile ödeme şekli/rejim kodu arasında tutarsızlık bulunmuştur.</p>
                    <p><small>📍 <strong>Kod Karşılaştırma:</strong> Kırmızı kutu = Girilen (Hatalı) kod, Yeşil kutu = Beklenen (Doğru) kod</small></p>
                </div>
                
                <div style="text-align: center; margin: 30px 0;">
                    <div class="stat-card">
                        <div class="stat-number">{bedelsiz_errors}</div>
                        <div class="stat-label">Bedelsiz Ödeme<br>Hataları</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">{rejim_errors}</div>
                        <div class="stat-label">Rejim 6123<br>Hataları</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">{total_errors}</div>
                        <div class="stat-label">Toplam Hatalı<br>Beyanname</div>
                    </div>
                </div>
                
                <div class="rules-box">
                    <h3 style="color: #1976d2; margin-top: 0;">Kontrol Kuralları</h3>
                    <div class="rule-item">
                        <span class="rule-icon">💰</span>
                        <div>
                            <strong>Bedelsiz Ödeme Kuralı:</strong><br>
                            Ödeme şekli "bedelsiz" olan işlemler için işlem niteliği kodu "99" olmalıdır.
                        </div>
                    </div>
                    <div class="rule-item">
                        <span class="rule-icon">📋</span>
                        <div>
                            <strong>Rejim 6123 Kuralı:</strong><br>
                            Rejim kodu "6123" olan işlemler için işlem niteliği kodu "61" olmalıdır.
                        </div>
                    </div>
                </div>
    """
    
    # Özet tablosunu ekle
    html += f"""
                <div class="info-card">
                    <h3>Kontrol Sonuçları Özeti</h3>
                    {summary_df.to_html(index=False, classes="table", table_id="summary-table")}
                </div>
    """
    
    # Bedelsiz ödeme hatalarını listele
    if len(incorrect_payment_code) > 0:
        html += f"""
                <div class="error-section">
                    <div class="error-title">Bedelsiz Ödeme - Hatalı İşlem Niteliği Kodları</div>
                    <p>Aşağıdaki beyannamelerde ödeme şekli "bedelsiz" olmasına rağmen işlem niteliği kodu "99" değildir:</p>
        """
        
        # Beyanname-bazlı gruplama ile tek seferde gösterim
        payment_grouped = incorrect_payment_code.groupby('Beyanname_no').agg({
            'Girilen Kod': 'first',
            'Beklenen Kod': 'first',
            'Odeme_sekli': 'first',
            'Rejim': 'first'
        }).reset_index()
        
        payment_grouped.columns = ['Beyanname No', 'Girilen Kod', 'Beklenen Kod', 'Ödeme Şekli', 'Rejim']
        
        # Kod karşılaştırması için HTML formatı
        payment_grouped['Kod Karşılaştırma'] = payment_grouped.apply(lambda row: 
            f'<div class="code-comparison">'
            f'<span class="code-wrong">{row["Girilen Kod"]}</span>'
            f'<span class="arrow">→</span>'
            f'<span class="code-correct">{row["Beklenen Kod"]}</span>'
            f'</div>', axis=1)
        
        # Sadece gerekli sütunları göster
        display_columns = ['Beyanname No', 'Kod Karşılaştırma', 'Ödeme Şekli', 'Rejim']
        
        # En fazla 20 beyanname göster
        display_payment = payment_grouped[display_columns].head(20)
        
        html += display_payment.to_html(index=False, classes="table", escape=False)
        
        if len(payment_grouped) > 20:
            html += f"<p><em>📋 Not: Toplam {len(payment_grouped)} hatalı beyannameden ilk 20 tanesi gösterilmektedir.</em></p>"
        
        html += "</div>"
    
    # Rejim kodu hatalarını listele
    if len(incorrect_rejim_code) > 0:
        html += f"""
                <div class="error-section">
                    <div class="error-title">Rejim 6123 - Hatalı İşlem Niteliği Kodları</div>
                    <p>Aşağıdaki beyannamelerde rejim kodu "6123" olmasına rağmen işlem niteliği kodu "61" değildir:</p>
        """
        
        # Beyanname-bazlı gruplama ile tek seferde gösterim
        rejim_grouped = incorrect_rejim_code.groupby('Beyanname_no').agg({
            'Girilen Kod': 'first',
            'Beklenen Kod': 'first',
            'Odeme_sekli': 'first',
            'Rejim': 'first'
        }).reset_index()
        
        rejim_grouped.columns = ['Beyanname No', 'Girilen Kod', 'Beklenen Kod', 'Ödeme Şekli', 'Rejim']
        
        # Kod karşılaştırması için HTML formatı
        rejim_grouped['Kod Karşılaştırma'] = rejim_grouped.apply(lambda row: 
            f'<div class="code-comparison">'
            f'<span class="code-wrong">{row["Girilen Kod"]}</span>'
            f'<span class="arrow">→</span>'
            f'<span class="code-correct">{row["Beklenen Kod"]}</span>'
            f'</div>', axis=1)
        
        # Sadece gerekli sütunları göster
        display_columns = ['Beyanname No', 'Kod Karşılaştırma', 'Ödeme Şekli', 'Rejim']
        
        # En fazla 20 beyanname göster
        display_rejim = rejim_grouped[display_columns].head(20)
        
        html += display_rejim.to_html(index=False, classes="table", escape=False)
        
        if len(rejim_grouped) > 20:
            html += f"<p><em>📋 Not: Toplam {len(rejim_grouped)} hatalı beyannameden ilk 20 tanesi gösterilmektedir.</em></p>"
        
        html += "</div>"
    
    # Footer
    html += """
            </div>
        </div>
    </body>
    </html>
    """
    
    return html 