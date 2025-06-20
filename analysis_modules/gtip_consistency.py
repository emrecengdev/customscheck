"""
GTİP ve Ticari Tanım tutarlılık analiz modülü.
Aynı ticari tanıma sahip ürünlerin farklı GTİP kodları ile beyan edilip edilmediğini kontrol eder.
"""

import pandas as pd
import traceback

def check_gtip_ticari_tanim_consistency(df):
    """
    Aynı ticari tanımda farklı GTİP kodu kullanılıp kullanılmadığını kontrol eder.
    
    Args:
        df (pandas.DataFrame): Beyanname verileri içeren DataFrame
    
    Returns:
        dict: Analiz sonuçları
    """
    print("GTİP-Ticari Tanım tutarlılık kontrolü başlatılıyor...")
    
    if "Gtip" not in df.columns or "Ticari_tanimi" not in df.columns:
        print("Hata: Gtip veya Ticari_tanimi sütunları bulunamadı.")
        return {
            "status": "error",
            "message": "Gtip veya Ticari_tanimi sütunları bulunamadı."
        }
    
    try:
        # Boş ticari tanımları filtrele
        filtered_df = df[df['Ticari_tanimi'].notna() & (df['Ticari_tanimi'] != '')]
        
        print(f"Filtrelenmiş veri: {len(filtered_df)} satır")
        
        if len(filtered_df) == 0:
            return {
                "status": "ok",
                "message": "İşlenecek veri bulunamadı. Ticari tanımlar boş olabilir.",
                "html_report": "<p>İşlenecek veri bulunamadı. Ticari tanımlar boş olabilir.</p>"
            }
        
        # Her ticari tanım için benzersiz GTİP kodlarını bul
        grouped = filtered_df.groupby('Ticari_tanimi')['Gtip'].unique().reset_index()
        
        # Her ticari tanım için kaç farklı GTİP kodu kullanıldığını hesapla
        grouped['GTİP_Sayısı'] = grouped['Gtip'].apply(len)
        
        print(f"Toplam {len(grouped)} benzersiz ticari tanım bulundu.")
        print(f"Birden fazla GTİP kodu içeren tanım sayısı: {len(grouped[grouped['GTİP_Sayısı'] > 1])}")
        
        # Birden fazla GTİP kodu olan ticari tanımları filtrele
        multiple_gtips = grouped[grouped['GTİP_Sayısı'] > 1].sort_values(by='GTİP_Sayısı', ascending=False)
        
        if multiple_gtips.empty:
            print("Aynı ticari tanımda farklı GTİP kodu kullanımı tespit edilmedi.")
            return {
                "status": "ok",
                "message": "Aynı ticari tanımda farklı GTİP kodu kullanımı tespit edilmedi.",
                "html_report": "<p>Aynı ticari tanımda farklı GTİP kodu kullanımı tespit edilmedi.</p>"
            }
        else:
            print(f"{len(multiple_gtips)} ticari tanımda tutarsızlık bulundu.")
            
            # Ayrıntılı sonuçlar için DataFrame oluştur
            result_rows = []
            
            # Ticari tanımlar için daha basit bir özet listesi oluştur
            simplified_summary = []
            
            # Her bir tutarsız ticari tanım için özet bilgi oluştur
            for _, row in multiple_gtips.iterrows():
                ticari_tanim = row['Ticari_tanimi']
                gtip_codes = row['Gtip']
                gtip_count = row['GTİP_Sayısı']
                
                # İlgili satırları bul
                related_rows = filtered_df[filtered_df['Ticari_tanimi'] == ticari_tanim]
                
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
                    'Ticari_tanimi': ticari_tanim,
                    'Farklı_GTİP_Sayısı': gtip_count,
                    'GTİP_Kodları': ', '.join(gtip_codes),
                    'GTİP_Detayları': gtip_details  # Her satır için GTİP detaylarını ekle
                })
                
                # Detaylı sonuçlar için satırları ekle
                for gtip in gtip_codes:
                    gtip_rows = related_rows[related_rows['Gtip'] == gtip]
                    
                    for _, data_row in gtip_rows.iterrows():
                        result_row = {
                            'Ticari_tanimi': ticari_tanim,
                            'Gtip': gtip
                        }
                        
                        # Diğer önemli sütunları da ekle
                        for col in ['Kalem_No', 'Mensei_ulke', 'Fatura_miktari', 'Fatura_miktarinin_dovizi', 'Beyanname_no', 'Adi_unvani', 'Kaynak_Dosya']:
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
                html_content = create_gtip_consistency_html(simplified_summary)
                print("HTML raporu başarıyla oluşturuldu.")
            except Exception as e:
                print(f"HTML rapor oluşturma hatası: {str(e)}")
                html_content = f"<p>HTML rapor oluşturulurken hata: {str(e)}</p>"
            
            return {
                "status": "warning",
                "message": f"{len(multiple_gtips)} ticari tanımda farklı GTİP kodları kullanılmış.",
                "inconsistent_rows": result_df,
                "summary": summary_df,
                "detail": multiple_gtips,
                "html_report": html_content
            }
    except Exception as e:
        error_message = f"GTİP-Ticari Tanım tutarlılık kontrolü sırasında hata: {str(e)}"
        print(error_message)
        print(traceback.format_exc())
        return {
            "status": "error",
            "message": error_message,
            "html_report": f"<p>Hata: {str(e)}</p>"
        }

def create_gtip_consistency_html(summary_data):
    """
    GTİP-Ticari Tanım tutarlılık kontrolü için basitleştirilmiş HTML raporu oluşturur
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
                'Ticari_Tanım_Sayısı': 1
            })
    
    # GTİP kodlarına göre gruplama ve toplama
    gtip_pivot = None
    if gtip_codes:
        gtip_df = pd.DataFrame(gtip_codes)
        gtip_pivot = gtip_df.groupby('GTİP').agg({
            'Beyanname_Sayısı': 'sum',
            'Ticari_Tanım_Sayısı': 'count'
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
        vertical-align: top;
    }
    .main-row {
        background-color: #e6f2ff;
        font-weight: bold;
    }
    .gtip-code {
        font-family: monospace;
        color: #0066cc;
    }
    .badge {
        display: inline-block;
        padding: 2px 4px;
        margin: 1px;
        border-radius: 3px;
        background-color: #f8f9fa;
        border: 1px solid #dee2e6;
        font-size: 11px;
    }
    .more-badge {
        display: inline-block;
        padding: 2px 4px;
        margin: 1px;
        border-radius: 3px;
        background-color: #e2e8f0;
        color: #4a5568;
        border: 1px solid #cbd5e0;
        font-size: 11px;
        cursor: pointer;
    }
    .more-badge:hover {
        background-color: #cbd5e0;
    }
    .hidden-items {
        display: none;
    }
    .pivot-table {
        width: 100%;
        border-collapse: collapse;
        margin: 15px 0;
        box-shadow: 0 0 5px rgba(0,0,0,0.1);
    }
    .pivot-table th {
        background-color: #e3f2fd;
        padding: 8px;
        text-align: left;
        border: 1px solid #bbd6f5;
        font-weight: bold;
    }
    .pivot-table td {
        padding: 6px;
        border: 1px solid #bbd6f5;
        text-align: right;
    }
    .pivot-table tr:nth-child(even) {
        background-color: #f5f9ff;
    }
    .pivot-table tr:last-child, .pivot-table td:last-child {
        font-weight: bold;
        background-color: #e3f2fd;
    }
    .summary-box {
        background-color: #f0f7ff;
        border: 1px solid #bbd6f5;
        border-radius: 8px;
        padding: 15px;
        margin-bottom: 20px;
    }
    .summary-title {
        font-size: 14px;
        font-weight: bold;
        color: #2c3e50;
        margin-bottom: 10px;
    }
    </style>
    
    <script>
    function toggleItems(id) {
        var hiddenItems = document.getElementById(id);
        var badge = document.getElementById('badge-' + id);
        
        if (hiddenItems.style.display === 'none' || hiddenItems.style.display === '') {
            hiddenItems.style.display = 'inline';
            badge.style.display = 'none';
        } else {
            hiddenItems.style.display = 'none';
            badge.style.display = 'inline-block';
        }
    }
    </script>
    
    <h2>GTİP - Ticari Tanım Tutarlılık Raporu</h2>
    <p><b>Not:</b> Bu rapor performans nedeniyle basitleştirilmiştir. Her GTİP için en fazla 10 beyanname gösterilmektedir.</p>
    """
    
    # Özet pivot tablosu ekle
    if gtip_pivot is not None and not gtip_pivot.empty:
        html += """
        <div class="summary-box">
            <div class="summary-title">GTİP Kodları Özet Pivot</div>
        """
        
        html += """
            <table class="pivot-table">
                <thead>
                    <tr>
                        <th>GTİP Kodu</th>
                        <th>Beyanname Sayısı</th>
                        <th>Farklı Ticari Tanım Sayısı</th>
                    </tr>
                </thead>
                <tbody>
        """
        
        # Pivot satırlarını ekle - en fazla 15 satır göster
        for _, row in gtip_pivot.head(15).iterrows():
            html += f"""
                <tr>
                    <td class="gtip-code">{row['GTİP']}</td>
                    <td>{row['Beyanname_Sayısı']}</td>
                    <td>{row['Ticari_Tanım_Sayısı']}</td>
                </tr>
            """
        
        # Toplam satırı ekle
        if len(gtip_pivot) > 0:
            html += f"""
                <tr>
                    <td>Toplam</td>
                    <td>{gtip_pivot['Beyanname_Sayısı'].sum()}</td>
                    <td>{gtip_pivot['Ticari_Tanım_Sayısı'].sum()}</td>
                </tr>
            """
            
        # Tablo kapanışı
        html += """
                </tbody>
            </table>
        </div>
        """
    
    # Detaylı tablo başlat
    html += """
    <table>
        <thead>
            <tr>
                <th>Ticari Tanım</th>
                <th>GTİP Kodları</th>
                <th>Beyanname Örnekleri</th>
            </tr>
        </thead>
        <tbody>
    """
    
    # En fazla 15 ticari tanım için sonuçları göster
    for i, item in enumerate(summary_data[:15]):
        ticari_tanim = item['Ticari_tanimi']
        gtip_kodlari = item['GTİP_Kodları']
        
        # Her ticari tanım için bir satır başlat
        html += f"""
        <tr class="main-row">
            <td>{ticari_tanim}</td>
            <td>{gtip_kodlari}</td>
            <td>
        """
        
        # Her GTİP için beyanname örneklerini ekle
        for j, detail in enumerate(item['GTİP_Detayları']):
            gtip = detail['gtip']
            beyannameler = detail.get('beyannameler', [])
            
            html += f"""
                <div>
                    <span class="gtip-code">{gtip}</span>: 
            """
            
            # En fazla 5 beyanname göster
            max_beyanname = 5
            shown_beyanname = min(max_beyanname, len(beyannameler))
            
            for k in range(shown_beyanname):
                html += f'<span class="badge">{beyannameler[k]}</span> '
            
            # Daha fazla beyanname varsa "daha fazla" butonu ekle
            if len(beyannameler) > max_beyanname:
                remaining = len(beyannameler) - max_beyanname
                unique_id = f"gtip-{i}-{j}"
                
                html += f"""
                    <span id="badge-{unique_id}" class="more-badge" onclick="toggleItems('{unique_id}')">+{remaining} daha</span>
                    <span id="{unique_id}" class="hidden-items">
                """
                
                for k in range(max_beyanname, len(beyannameler)):
                    html += f'<span class="badge">{beyannameler[k]}</span> '
                
                html += "</span>"
            
            html += "</div>"
        
        # Satırı kapat
        html += """
            </td>
        </tr>
        """
    
    # Daha fazla ticari tanım varsa belirt
    if len(summary_data) > 15:
        html += f"""
        <tr>
            <td colspan="3" style="text-align: center; font-style: italic;">
                ... ve {len(summary_data) - 15} ticari tanım daha
            </td>
        </tr>
        """
    
    # Tabloyu kapat
    html += """
        </tbody>
    </table>
    """
    
    return html 