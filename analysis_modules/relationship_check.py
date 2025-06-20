"""
Alıcı-Satıcı ilişki kontrolü modülü.
Beyannamelerde tutarsız alıcı-satıcı ilişki kodlarını tespit eder.
"""

import pandas as pd

def check_alici_satici_relationship(df, selected_companies=None, progress_callback=None):
    """
    Alıcı-Satıcı ilişki kontrolü
    
    İki kontrol yöntemi:
    1. Seçilen gönderici firmalara ait beyannamelardan ilişki durumu 6 olanları bulur
    2. Seçilen firma yoksa, aynı göndericide hem 6 hem 0 ilişki durumu olan beyannameleri bulur
    
    Args:
        df (pandas.DataFrame): Kontrol edilecek DataFrame
        selected_companies (list, optional): Kullanıcının seçtiği firma listesi
        progress_callback (function, optional): İlerleme bildirimi için callback fonksiyon
        
    Returns:
        dict: Kontrol sonuçları
    """
    if progress_callback:
        progress_callback(10, "Alıcı-satıcı ilişki kontrolü başlatılıyor...")
    
    # Büyük veri setleri için örnekleme yap
    sample_size = 5000  # Maksimum işlenecek satır sayısı
    if len(df) > sample_size:
        print(f"Veri seti çok büyük ({len(df)} satır). Örnekleme yapılıyor: {sample_size} satır")
        if progress_callback:
            progress_callback(15, f"Veri seti çok büyük ({len(df)} satır). Örnekleme yapılıyor...")
        df_sample = df.sample(sample_size, random_state=42)
    else:
        df_sample = df
    
    if "Alici_satici_iliskisi" not in df_sample.columns:
        return {
            "status": "error",
            "message": "Alici_satici_iliskisi sütunu bulunamadı."
        }
    
    if progress_callback:
        progress_callback(20, "Gerekli sütunlar kontrol ediliyor...")
    
    # Gerekli sütunların varlığını kontrol et
    needed_columns = ["Alici_satici_iliskisi", "Beyanname_no"]
    sender_column = None
    
    # Gönderici sütununu belirle - farklı isimler kullanılabilir
    possible_sender_columns = ["Gonderen", "Gonderen_adi", "Gonderen_firma", "Adi_unvani", "Ihracatci"]
    for col in possible_sender_columns:
        if col in df_sample.columns:
            sender_column = col
            break
    
    if not sender_column:
        return {
            "status": "error",
            "message": "Gönderici sütunu bulunamadı."
        }
    
    needed_columns.append(sender_column)
    
    # Tarih sütununu belirle
    date_column = None
    possible_date_columns = ["Beyanname_tarihi", "Tarih", "Tescil_tarihi"]
    for col in possible_date_columns:
        if col in df_sample.columns:
            date_column = col
            break
    
    if date_column:
        needed_columns.append(date_column)
    
    # Sütunların var olup olmadığını kontrol et
    missing_columns = [col for col in needed_columns if col not in df_sample.columns]
    if missing_columns:
        return {
            "status": "error",
            "message": f"Gerekli sütunlar bulunamadı: {', '.join(missing_columns)}"
        }
    
    if progress_callback:
        progress_callback(30, "Veri işleniyor...")
    
    # İşlem 1: Belirli gönderici firmaların ilişki durumu 6 olan beyannamelerini bul
    if selected_companies and len(selected_companies) > 0:
        if progress_callback:
            progress_callback(40, "Seçilen firma kayıtları filtreleniyor...")
        
        # Seçilen firmaların beyannamelerini filtrele
        selected_df = df_sample[df_sample[sender_column].isin(selected_companies)]
        
        # İlişki durumu 6 olan beyannameleri bul
        error_relations = selected_df[selected_df["Alici_satici_iliskisi"] == "6"].copy()
        
        if progress_callback:
            progress_callback(70, "Sonuçlar hazırlanıyor...")
        
        if date_column:
            error_relations = error_relations.sort_values(by=date_column, ascending=False)
        
        if error_relations.empty:
            return {
                "status": "ok",
                "message": "Seçilen firmalarda ilişki durumu 6 olan beyanname bulunamadı.",
                "type": "selected_companies",
                "data": None
            }
        else:
            # Tekrarlı beyannameleri kaldır - aynı beyanname numarasına sahip kayıtları tekil say
            unique_error_relations = error_relations.drop_duplicates(subset=["Beyanname_no"])
            
            # Sonuç DataFrame'ini hazırla
            result_columns = ["Beyanname_no", sender_column, "Alici_satici_iliskisi"]
            if date_column:
                result_columns.insert(1, date_column)
            
            result_df = error_relations[result_columns].copy()
            
            return {
                "status": "warning",
                "message": f"{len(unique_error_relations)} adet ilişki durumu 6 olan beyanname bulundu.",
                "type": "selected_companies",
                "data": result_df
            }
    
    # İşlem 2: Aynı göndericide farklı ilişki durumları olan beyannameleri bul ve hangi kodun hatalı olduğunu belirle
    else:
        if progress_callback:
            progress_callback(40, "Tüm firmalar için ön filtreleme yapılıyor...")
        
        # Sadece 0 ve 6 ilişki durumlarına odaklan - bu önemli performans iyileştirmesi
        filtered_df = df_sample[df_sample["Alici_satici_iliskisi"].isin(["0", "6"])].copy()
        
        if filtered_df.empty:
            return {
                "status": "ok",
                "message": "Veri setinde '0' veya '6' ilişki durumu bulunmuyor.",
                "type": "all_senders",
                "data": None
            }
        
        if progress_callback:
            progress_callback(50, "Firma grupları oluşturuluyor...")
        
        # Daha performanslı bir yaklaşım kullan
        # Önce 0 ve 6 değerlerine sahip firmaları bul
        firms_with_0 = set(filtered_df[filtered_df["Alici_satici_iliskisi"] == "0"][sender_column].unique())
        firms_with_6 = set(filtered_df[filtered_df["Alici_satici_iliskisi"] == "6"][sender_column].unique())
        
        # Kesişim kümesi - hem 0 hem 6 olan firmalar
        inconsistent_with_6_0 = list(firms_with_0.intersection(firms_with_6))
        
        if progress_callback:
            progress_callback(60, f"{len(inconsistent_with_6_0)} adet tutarsız firma bulundu...")
        
        if not inconsistent_with_6_0:
            return {
                "status": "ok",
                "message": "Aynı göndericide hem 6 hem 0 ilişki durumu olan beyanname bulunamadı.",
                "type": "all_senders",
                "data": None
            }
        else:
            if progress_callback:
                progress_callback(70, "İlgili beyannameler filtreleniyor...")
            
            # İlgili beyannameleri filtrele - daha verimli yöntem
            inconsistent_df = filtered_df[filtered_df[sender_column].isin(inconsistent_with_6_0)].copy()
            
            # Hatalı kodları belirle
            if progress_callback:
                progress_callback(75, "Hatalı kodlar belirleniyor...")
            
            # Tüm tutarsız veriyi sakla
            all_inconsistent_rows = []
            
            # Firma bazlı hatalı kod sayıları
            firm_error_stats = {
                "Firma": [],
                "Kod_0_Sayısı": [],
                "Kod_6_Sayısı": [],
                "Hatalı_Kod": [],
                "Hatalı_Beyanname_Sayısı": []
            }
            
            total_error_count = 0
            total_beyanname_error_count = 0  # Tekil beyanname sayısını takip et
            
            # Her firma için hangi kodun hatalı olduğunu belirle
            for firm in inconsistent_with_6_0:
                firm_data = inconsistent_df[inconsistent_df[sender_column] == firm]
                
                # Her firma için benzersiz beyanname numaralarını al
                unique_beyannames_0 = firm_data[firm_data["Alici_satici_iliskisi"] == "0"]["Beyanname_no"].unique()
                unique_beyannames_6 = firm_data[firm_data["Alici_satici_iliskisi"] == "6"]["Beyanname_no"].unique()
                
                # Kod sayılarını beyanname bazında hesapla
                code_0_count = len(unique_beyannames_0)
                code_6_count = len(unique_beyannames_6)
                
                # Hangi kod daha az sayıda ise onu hatalı say
                incorrect_code = "6" if code_6_count < code_0_count else "0"
                error_count = code_6_count if incorrect_code == "6" else code_0_count
                total_error_count += error_count
                
                # Hatalı kodlara sahip beyannameleri işaretle
                incorrect_rows = firm_data[firm_data["Alici_satici_iliskisi"] == incorrect_code].copy()
                incorrect_rows["Dogru_Kod"] = "0" if incorrect_code == "6" else "6"
                incorrect_rows["Hata_Durumu"] = "Hatalı kod"
                
                # Beyanname bazında benzersiz hata sayısını say
                unique_error_beyannames = incorrect_rows["Beyanname_no"].unique()
                total_beyanname_error_count += len(unique_error_beyannames)
                
                # Sonuçları topla
                all_inconsistent_rows.append(incorrect_rows)
                
                # Firma istatistiklerini ekle
                firm_error_stats["Firma"].append(firm)
                firm_error_stats["Kod_0_Sayısı"].append(code_0_count)
                firm_error_stats["Kod_6_Sayısı"].append(code_6_count)
                firm_error_stats["Hatalı_Kod"].append(incorrect_code)
                firm_error_stats["Hatalı_Beyanname_Sayısı"].append(error_count)
            
            # Tüm hatalı satırları birleştir
            result_df = pd.concat(all_inconsistent_rows) if all_inconsistent_rows else pd.DataFrame()
            
            # İstatistik DataFrame'i oluştur
            stats_df = pd.DataFrame(firm_error_stats)
            
            if progress_callback:
                progress_callback(80, "Sonuçlar hazırlanıyor...")
            
            # Sıralama
            if date_column and not result_df.empty:
                result_df = result_df.sort_values(by=[sender_column, date_column], ascending=[True, False])
            elif not result_df.empty:
                result_df = result_df.sort_values(by=sender_column)
            
            # Gösterilecek sütunları belirle
            if not result_df.empty:
                result_columns = ["Beyanname_no", sender_column, "Alici_satici_iliskisi", "Dogru_Kod", "Hata_Durumu"]
                if date_column:
                    result_columns.insert(1, date_column)
                
                # Sadece gerekli sütunları al
                available_columns = [col for col in result_columns if col in result_df.columns]
                result_df = result_df[available_columns].copy()
            
            # HTML rapor oluştur
            html_report = _generate_relationship_html_report(result_df, stats_df, sender_column)
            
            return {
                "status": "warning",
                "message": f"{len(inconsistent_with_6_0)} gönderici firmada toplam {total_beyanname_error_count} adet hatalı ilişki kodlu beyanname tespit edildi.",
                "type": "all_senders_enhanced",
                "data": result_df,
                "stats": stats_df,
                "html_report": html_report
            }

def _generate_relationship_html_report(result_df, stats_df, sender_column):
    """
    Alıcı-satıcı ilişki kontrolü sonuçlarını HTML raporuna dönüştürür.
    
    Args:
        result_df (pandas.DataFrame): Analiz sonuç verileri
        stats_df (pandas.DataFrame): Firma bazlı istatistikler
        sender_column (str): Gönderici firma sütun adı
    
    Returns:
        str: HTML rapor içeriği
    """
    if result_df is None or result_df.empty:
        return "<p>Herhangi bir tutarsızlık tespit edilmedi.</p>"
    
    total_firms = len(stats_df)
    total_errors = stats_df["Hatalı_Beyanname_Sayısı"].sum()
    
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
    .firm-section {
        margin-bottom: 30px;
        padding: 15px;
        background-color: #f5f5f5;
        border-radius: 5px;
    }
    .summary-box {
        background-color: #e3f2fd;
        border-left: 4px solid #2196F3;
        padding: 10px;
        margin-bottom: 20px;
    }
    </style>
    
    <div class="container">
        <h2>Alıcı-Satıcı İlişki Kontrolü</h2>
        
        <div class="summary-box">
            <p><strong>Özet:</strong> Bu rapor, aynı gönderici firma için farklı ilişki durumu (0 ve 6) bildirilen beyannameleri gösterir.</p>
            <p class="warning">Toplam <strong>""" + str(total_firms) + """</strong> firmada <strong>""" + str(total_errors) + """</strong> adet tutarsız beyanname tespit edildi.</p>
        </div>
        
        <h3>Firma Bazlı İstatistikler</h3>
        <table>
            <thead>
                <tr>
                    <th>Firma</th>
                    <th>Kod 0 Sayısı</th>
                    <th>Kod 6 Sayısı</th>
                    <th>Hatalı Kod</th>
                    <th>Hatalı Beyanname Sayısı</th>
                </tr>
            </thead>
            <tbody>
    """
    
    # Firma istatistiklerini ekle
    for _, row in stats_df.iterrows():
        html += f"""
            <tr>
                <td>{row['Firma']}</td>
                <td>{row['Kod_0_Sayısı']}</td>
                <td>{row['Kod_6_Sayısı']}</td>
                <td>{row['Hatalı_Kod']}</td>
                <td>{row['Hatalı_Beyanname_Sayısı']}</td>
            </tr>
        """
    
    html += """
            </tbody>
        </table>
    """
    
    # Örnekler bölümü - en fazla 50 satır göster
    if len(result_df) > 0:
        sample_data = result_df.head(50)
        
        html += """
        <h3>Tutarsız Beyanname Örnekleri</h3>
        <p><em>Not: Çok sayıda tutarsızlık olduğunda ilk 50 örnek gösterilir.</em></p>
        <table>
            <thead>
                <tr>
        """
        
        # Tablo başlıkları
        for col in sample_data.columns:
            display_name = col.replace("_", " ").title()
            html += f"<th>{display_name}</th>"
        
        html += """
                </tr>
            </thead>
            <tbody>
        """
        
        # Tablo verileri
        for _, row in sample_data.iterrows():
            html += "<tr>"
            for col in sample_data.columns:
                html += f"<td>{row[col]}</td>"
            html += "</tr>"
        
        html += """
            </tbody>
        </table>
        """
    
    # Değerlendirme
    html += """
    <h3>Değerlendirme</h3>
    <p>Alıcı-satıcı ilişki tutarsızlıkları, aşağıdaki sebeplerden kaynaklanabilir:</p>
    <ul>
        <li>Aynı firma için zaman içinde değişen ilişki durumlarının bildirilmesi</li>
        <li>Beyanname hazırlayıcılarının kodlama hataları</li>
        <li>İlişkili firma durumunun gizlenmesi amacıyla yanlış beyan</li>
        <li>İlişki durumunun yanlış anlaşılması</li>
    </ul>
    <p>Bu tutarsızlıkların incelenmesi, transfer fiyatlaması ve örtülü kazanç aktarımı açısından önemlidir. Aynı firma için sürekli değişen ilişki durumu bildirimleri risk unsuru olarak değerlendirilmelidir.</p>
    """
    
    html += "</div>"
    return html 