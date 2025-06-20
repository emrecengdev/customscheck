"""
GTİP ve Ürün Kodu tutarlılık analiz modülü.
Aynı ürün koduna sahip ürünlerin farklı GTİP kodları ile beyan edilip edilmediğini kontrol eder.
"""

import pandas as pd
import traceback

def check_gtip_urun_kodu_consistency(df):
    """
    Aynı ürün kodunda farklı GTİP kodu kullanılıp kullanılmadığını kontrol eder
    
    Args:
        df (pandas.DataFrame): Beyanname verileri içeren DataFrame
    
    Returns:
        dict: Analiz sonuçları
    """
    print("GTİP-Ürün Kodu tutarlılık kontrolü başlatılıyor...")
    
    # Ürün kodu sütununu tanımla - yaygın isimlendirmeler
    product_code_columns = ["Urun_kodu", "Urun_Kodu", "Urun_no", "Product_code", "Stok_kodu", "Stok_Kodu"]
    
    # Veri setinde mevcut olan ürün kodu sütununu bul
    product_code_column = None
    for col in product_code_columns:
        if col in df.columns:
            product_code_column = col
            break
    
    if "Gtip" not in df.columns or product_code_column is None:
        print(f"Hata: Gtip veya Ürün Kodu sütunları bulunamadı.")
        return {
            "status": "error",
            "message": f"Gtip veya Ürün Kodu sütunları bulunamadı. Mevcut sütunlar: {', '.join(df.columns.tolist())}"
        }
    
    try:
        # Boş ürün kodlarını filtrele
        filtered_df = df[df[product_code_column].notna() & (df[product_code_column] != '')]
        
        print(f"Filtrelenmiş veri: {len(filtered_df)} satır")
        
        if len(filtered_df) == 0:
            return {
                "status": "ok",
                "message": "İşlenecek veri bulunamadı. Ürün kodları boş olabilir.",
                "html_report": "<p>İşlenecek veri bulunamadı. Ürün kodları boş olabilir.</p>"
            }
        
        # Her ürün kodu için benzersiz GTİP kodlarını bul
        grouped = filtered_df.groupby(product_code_column)['Gtip'].unique().reset_index()
        
        # Her ürün kodu için kaç farklı GTİP kodu kullanıldığını hesapla
        grouped['GTİP_Sayısı'] = grouped['Gtip'].apply(len)
        
        print(f"Toplam {len(grouped)} benzersiz ürün kodu bulundu.")
        print(f"Birden fazla GTİP kodu içeren ürün sayısı: {len(grouped[grouped['GTİP_Sayısı'] > 1])}")
        
        # Birden fazla GTİP kodu olan ürün kodlarını filtrele
        multiple_gtips = grouped[grouped['GTİP_Sayısı'] > 1].sort_values(by='GTİP_Sayısı', ascending=False)
        
        if multiple_gtips.empty:
            print("Aynı ürün kodunda farklı GTİP kodu kullanımı tespit edilmedi.")
            return {
                "status": "ok",
                "message": "Aynı ürün kodunda farklı GTİP kodu kullanımı tespit edilmedi.",
                "html_report": "<p>Aynı ürün kodunda farklı GTİP kodu kullanımı tespit edilmedi.</p>"
            }
        else:
            print(f"{len(multiple_gtips)} ürün kodunda tutarsızlık bulundu.")
            
            # Ayrıntılı sonuçlar için DataFrame oluştur
            result_rows = []
            
            # Ürün kodları için daha basit bir özet listesi oluştur
            simplified_summary = []
            
            # Her bir tutarsız ürün kodu için özet bilgi oluştur
            for _, row in multiple_gtips.iterrows():
                urun_kodu = row[product_code_column]
                gtip_codes = row['Gtip']
                gtip_count = row['GTİP_Sayısı']
                
                # İlgili satırları bul
                related_rows = filtered_df[filtered_df[product_code_column] == urun_kodu]
                
                # GTİP detayları için tam bilgileri topla - HTML rapor için
                gtip_details = []
                for gtip in gtip_codes:
                    gtip_rows = related_rows[related_rows['Gtip'] == gtip]
                    
                    beyanname_list = []
                    if "Beyanname_no" in gtip_rows.columns:
                        beyanname_list = gtip_rows['Beyanname_no'].dropna().unique().tolist()
                    
                    unvan_list = []
                    if "Adi_unvani" in gtip_rows.columns:
                        unvan_list = gtip_rows['Adi_unvani'].dropna().unique().tolist()
                    
                    gtip_details.append({
                        'gtip': gtip,
                        'beyannameler': beyanname_list,
                        'unvanlar': unvan_list
                    })
                
                # Basitleştirilmiş özet için satır ekle - karmaşık nesneler yok
                simplified_summary.append({
                    'Urun_kodu': urun_kodu,
                    'Farklı_GTİP_Sayısı': gtip_count,
                    'GTİP_Kodları': ', '.join(gtip_codes),
                    'GTİP_Detayları': gtip_details  # Her satır için GTİP detaylarını ekle
                })
                
                # Detaylı sonuçlar için satırları ekle
                for gtip in gtip_codes:
                    gtip_rows = related_rows[related_rows['Gtip'] == gtip]
                    
                    for _, data_row in gtip_rows.iterrows():
                        result_row = {
                            product_code_column: urun_kodu,
                            'Gtip': gtip
                        }
                        
                        # Diğer önemli sütunları da ekle
                        for col in ['Kalem_No', 'Ticari_tanimi', 'Mensei_ulke', 'Fatura_miktari', 'Fatura_miktarinin_dovizi', 'Beyanname_no', 'Adi_unvani', 'Kaynak_Dosya']:
                            if col in data_row:
                                result_row[col] = data_row[col]
                        
                        result_rows.append(result_row)
            
            # Detaylı dataframe oluştur
            result_df = pd.DataFrame(result_rows)
            print(f"Sonuç DataFrame oluşturuldu: {len(result_df)} satır")
            
            # Özet DataFrame oluştur - basitleştirilmiş veri
            summary_df = pd.DataFrame(simplified_summary)
            if 'GTİP_Detayları' in summary_df.columns:
                summary_df = summary_df.drop(columns=['GTİP_Detayları'])  # JSON serileştirme hatalarını önlemek için kompleks sütunu kaldır
            
            print(f"Özet DataFrame oluşturuldu: {len(summary_df)} satır")
            
            # Görsel sunum için HTML tablosu oluştur
            try:
                html_content = create_gtip_urun_kodu_html(simplified_summary, product_code_column)
                print("HTML raporu başarıyla oluşturuldu.")
            except Exception as e:
                print(f"HTML rapor oluşturma hatası: {str(e)}")
                html_content = f"<p>HTML rapor oluşturulurken hata: {str(e)}</p>"
            
            return {
                "status": "warning",
                "message": f"{len(multiple_gtips)} ürün kodunda farklı GTİP kodları kullanılmış.",
                "inconsistent_rows": result_df,
                "summary": summary_df,
                "detail": multiple_gtips,
                "html_report": html_content
            }
    except Exception as e:
        error_message = f"GTİP-Ürün Kodu tutarlılık kontrolü sırasında hata: {str(e)}"
        print(error_message)
        print(traceback.format_exc())
        return {
            "status": "error",
            "message": error_message,
            "html_report": f"<p>Hata: {str(e)}</p>"
        }

def create_gtip_urun_kodu_html(summary_data, product_code_column):
    """
    GTİP-Ürün Kodu tutarlılık kontrolü için basitleştirilmiş HTML raporu oluşturur
    """
    if not summary_data:
        return "<p>Herhangi bir tutarsızlık bulunamadı.</p>"
    
    # Pivot veri hazırla - GTİP kodlarının dağılımını göstermek için
    gtip_codes = []
    for item in summary_data:
        for detail in item['GTİP_Detayları']:
            gtip = detail['gtip']
            beyannameler = detail['beyannameler']
            count = len(beyannameler) if beyannameler else 1
            gtip_codes.append({
                'GTİP': gtip,
                'Beyanname_Sayısı': count,
                'Ürün_Kodu_Sayısı': 1
            })
    
    # GTİP kodlarına göre gruplama ve toplama
    gtip_pivot = None
    if gtip_codes:
        gtip_df = pd.DataFrame(gtip_codes)
        gtip_pivot = gtip_df.groupby('GTİP').agg({
            'Beyanname_Sayısı': 'sum',
            'Ürün_Kodu_Sayısı': 'count'
        }).sort_values(by='Beyanname_Sayısı', ascending=False).reset_index()
    
    # Minimal HTML ve CSS kullan
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
    .info {
        color: #2196F3;
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
    .chart-container {
        margin-top: 20px;
        margin-bottom: 30px;
    }
    .summary-box {
        background-color: #f5f5f5;
        border-left: 4px solid #2196F3;
        padding: 10px;
        margin-bottom: 20px;
    }
    </style>
    
    <div class="container">
        <h2>GTİP - Ürün Kodu Tutarlılık Analizi</h2>
        
        <div class="summary-box">
            <p><strong>Özet:</strong> Bu rapor, aynı ürün koduna farklı GTİP kodları atanmış beyannameleri gösterir.</p>
            <p class="warning">Toplam <strong>""" + str(len(summary_data)) + """</strong> ürün kodunda tutarsızlık tespit edildi.</p>
        </div>
    """
    
    # GTİP dağılımı tablosu
    if gtip_pivot is not None and len(gtip_pivot) > 0:
        html += """
        <h3>GTİP Kodlarının Dağılımı</h3>
        <table>
            <thead>
                <tr>
                    <th>GTİP Kodu</th>
                    <th>Beyanname Sayısı</th>
                    <th>Kullanıldığı Ürün Kodu Sayısı</th>
                </tr>
            </thead>
            <tbody>
        """
        
        # En fazla 20 satır göster
        for _, row in gtip_pivot.head(20).iterrows():
            html += f"""
                <tr>
                    <td>{row['GTİP']}</td>
                    <td>{row['Beyanname_Sayısı']}</td>
                    <td>{row['Ürün_Kodu_Sayısı']}</td>
                </tr>
            """
        
        html += """
            </tbody>
        </table>
        """
        
        if len(gtip_pivot) > 20:
            html += f"<p><em>Not: Toplam {len(gtip_pivot)} GTİP kodundan ilk 20 tanesi gösterilmektedir.</em></p>"
    
    # Tutarsız ürün kodları listesi
    html += """
    <h3>Farklı GTİP Kodları Kullanılan Ürün Kodları</h3>
    <table>
        <thead>
            <tr>
                <th>Ürün Kodu</th>
                <th>Farklı GTİP Sayısı</th>
                <th>GTİP Kodları</th>
            </tr>
        </thead>
        <tbody>
    """
    
    # En fazla 100 tutarsız ürün kodu göster
    for item in summary_data[:100]:
        html += f"""
            <tr>
                <td>{item['Urun_kodu']}</td>
                <td>{item['Farklı_GTİP_Sayısı']}</td>
                <td>{item['GTİP_Kodları']}</td>
            </tr>
        """
    
    html += """
        </tbody>
    </table>
    """
    
    if len(summary_data) > 100:
        html += f"<p><em>Not: Toplam {len(summary_data)} tutarsız ürün kodundan ilk 100 tanesi gösterilmektedir.</em></p>"
    
    # Detaylı açıklama
    html += """
    <h3>Değerlendirme</h3>
    <p>Aynı ürün koduna sahip ürünlerin farklı GTİP kodları ile beyan edilmesi, aşağıdaki sebeplerden kaynaklanabilir:</p>
    <ul>
        <li>Ürünlerin yanlış GTİP kodu ile beyan edilmiş olması</li>
        <li>Aynı ürün kodu altında farklı ürünlerin bulunması</li>
        <li>Zaman içinde ürünün GTİP sınıflandırmasında değişiklik olması</li>
    </ul>
    <p>Bu tip tutarsızlıkların incelenmesi, vergi ve gümrük mevzuatına uyum açısından önemlidir.</p>
    """
    
    html += "</div>"
    return html 