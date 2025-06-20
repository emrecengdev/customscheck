import csv
import os
import re
import html
import glob

def extract_beyanname_fixed(xml_file, output_dir=None):
    """
    XML verilerini Excel'de düzgün görüntülenmesi için düzenli formatta çıkarır.
    Tab karakteri ayraç olarak kullanır ve Türkçe karakter sorunlarını çözer.
    
    xml_file: İşlenecek XML dosyasının yolu
    output_dir: Çıktı dosyalarının kaydedileceği klasör. None ise, XML dosyasının bulunduğu klasör kullanılır.
    """
    # Çıktı klasörünü ayarla
    if output_dir is None:
        output_dir = os.path.dirname(xml_file)
    
    # XML dosya adını al (uzantısız)
    xml_filename = os.path.basename(xml_file)
    xml_name_without_ext = os.path.splitext(xml_filename)[0]
    
    # XML dosyasını oku
    with open(xml_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Beyanname bilgilerini çıkar
    beyanname_bilgi_pattern = r'<BeyannameBilgi[^>]*>(.*?)</BeyannameBilgi>'
    beyanname_match = re.search(beyanname_bilgi_pattern, content, re.DOTALL)
    
    beyanname_data = {}
    if beyanname_match:
        beyanname_xml = beyanname_match.group(1)
        # Tüm etiketleri bul
        tag_pattern = r'<([^/\s>]+)>([^<]+)</\1>'
        tag_matches = re.findall(tag_pattern, beyanname_xml)
        
        # Beyanname bilgilerini ayıklama
        for tag, value in tag_matches:
            if tag != 'kalem' and tag != 'firma' and tag != 'Ozetbeyan':
                # Metni temizle - Excel'de sorun çıkarabilecek karakterleri düzelt
                value = value.strip().replace('"', '""')
                beyanname_data[tag] = value
    
    # Kalem bilgilerini çıkar
    kalem_pattern = r'<kalem>(.*?)</kalem>'
    kalem_matches = re.findall(kalem_pattern, content, re.DOTALL)
    
    # Dokumanlar bilgilerini çıkar - yeni format için doğrudan dokuman listesi olarak saklayalım
    dokuman_list = []
    dokuman_pattern = r'<Dokumanlar>(.*?)</Dokumanlar>'
    dokumanlar_match = re.search(dokuman_pattern, content, re.DOTALL)
    
    if dokumanlar_match:
        dokumanlar_xml = dokumanlar_match.group(1)
        # Her bir Dokuman etiketini bul
        dokuman_pattern = r'<Dokuman>(.*?)</Dokuman>'
        dokuman_matches = re.findall(dokuman_pattern, dokumanlar_xml, re.DOTALL)
        
        for dokuman_xml in dokuman_matches:
            # Dokuman içindeki tüm etiketleri bul
            tag_pattern = r'<([^/\s>]+)>([^<]+)</\1>'
            tag_matches = re.findall(tag_pattern, dokuman_xml)
            
            dokuman = {}
            # Temel değerleri çıkart
            for tag, value in tag_matches:
                value = value.strip().replace('"', '""')
                dokuman[tag] = value
            
            dokuman_list.append(dokuman)
    
    # Soru_Cevap bilgilerini çıkar - yeni format için doğrudan soru-cevap listesi olarak saklayalım
    soru_cevap_list = []
    soru_cevap_pattern = r'<Sorular_cevaplar>(.*?)</Sorular_cevaplar>'
    sorular_match = re.search(soru_cevap_pattern, content, re.DOTALL)
    
    if sorular_match:
        sorular_xml = sorular_match.group(1)
        # Her bir Soru_Cevap etiketini bul
        soru_cevap_pattern = r'<Soru_Cevap>(.*?)</Soru_Cevap>'
        soru_cevap_matches = re.findall(soru_cevap_pattern, sorular_xml, re.DOTALL)
        
        for soru_cevap_xml in soru_cevap_matches:
            # Soru_Cevap içindeki tüm etiketleri bul
            tag_pattern = r'<([^/\s>]+)>([^<]+)</\1>'
            tag_matches = re.findall(tag_pattern, soru_cevap_xml)
            
            soru_cevap = {}
            # Değerleri çıkart
            for tag, value in tag_matches:
                value = value.strip().replace('"', '""')
                soru_cevap[tag] = value
            
            soru_cevap_list.append(soru_cevap)
    
    # Vergiler bilgilerini çıkar - yeni format için doğrudan vergi listesi olarak saklayalım
    vergi_list = []
    vergi_pattern = r'<Vergiler>(.*?)</Vergiler>'
    vergiler_match = re.search(vergi_pattern, content, re.DOTALL)
    
    if vergiler_match:
        vergiler_xml = vergiler_match.group(1)
        # Her bir Vergi etiketini bul
        vergi_pattern = r'<Vergi>(.*?)</Vergi>'
        vergi_matches = re.findall(vergi_pattern, vergiler_xml, re.DOTALL)
        
        for vergi_xml in vergi_matches:
            # Vergi içindeki tüm etiketleri bul
            tag_pattern = r'<([^/\s>]+)>([^<]+)</\1>'
            tag_matches = re.findall(tag_pattern, vergi_xml)
            
            vergi = {}
            # Değerleri çıkart
            for tag, value in tag_matches:
                value = value.strip().replace('"', '""')
                vergi[tag] = value
            
            vergi_list.append(vergi)
    
    # Kalem bilgilerini hazırla
    kalem_data_list = []
    for i, kalem_xml in enumerate(kalem_matches, 1):
        kalem = {"Kalem_No": str(i)}
        
        # Kalem içindeki tüm etiketleri bul
        tag_pattern = r'<([^/\s>]+)>([^<]+)</\1>'
        tag_matches = re.findall(tag_pattern, kalem_xml)
        
        # Kalem bilgilerini ayıklama
        for tag, value in tag_matches:
            # Metni temizle - Excel'de sorun çıkarabilecek karakterleri düzelt
            value = value.strip().replace('"', '""')
            kalem[tag] = value
        
        # Beyanname verisinden üst bilgileri her kaleme ekle
        for tag, value in beyanname_data.items():
            # Kalem içinde aynı isimde etiket yoksa ekle
            if tag not in kalem:
                kalem[tag] = value
        
        kalem_data_list.append(kalem)
    
    # Tablo formatındaki Excel için veri hazırlama
    # Maksimum doküman, soru-cevap ve vergi sayılarını belirle
    max_dokuman = len(dokuman_list)
    max_soru_cevap = len(soru_cevap_list)
    max_vergi = len(vergi_list)
    
    # Excel için sütun başlıklarını hazırla
    columns = []
    
    # Kalem alanları (örneğin: Kalem_No, GTIP, vb)
    if kalem_data_list:
        for key in kalem_data_list[0].keys():
            columns.append(key)
    
    # Dokuman alan başlıklarını ekle (her dokuman için setleri)
    dokuman_columns = ["Kod", "Dogrulama", "Belge_tarihi", "Referans"]
    
    # Soru cevap alan başlıklarını ekle
    soru_cevap_columns = ["Soru_no", "Cevap"]
    
    # Vergi alan başlıklarını ekle
    vergi_columns = ["Kod", "Miktar", "Oran", "Odeme_sekli", "Vergi_matrahi"]
    
    # Pandas DataFrame için veri listesi
    data_rows = []
    
    # Her kalemi işle
    for kalem in kalem_data_list:
        kalem_no = kalem["Kalem_No"]
        
        # Bu kalem için satır hazırla
        row = dict(kalem)  # Kalem verilerini kopyala
        
        # Bu kaleme ait dokümanları bul ve ekle
        my_dokumans = [d for d in dokuman_list if d.get("Kalem_no") == kalem_no]
        for i, dok in enumerate(my_dokumans):
            for col in dokuman_columns:
                if col in dok:
                    row[f"Dokuman_{i+1}_{col}"] = dok[col]
        
        # Bu kaleme ait soru-cevapları bul ve ekle
        my_soru_cevaps = [sc for sc in soru_cevap_list if sc.get("Kalem_no") == kalem_no or sc.get("Kalem_no") == "0"]
        for i, sc in enumerate(my_soru_cevaps):
            for col in soru_cevap_columns:
                if col in sc:
                    row[f"SoruCevap_{i+1}_{col}"] = sc[col]
        
        # Bu kaleme ait vergileri bul ve ekle  
        my_vergis = [v for v in vergi_list if v.get("Kalem_no") == kalem_no]
        for i, vergi in enumerate(my_vergis):
            for col in vergi_columns:
                if col in vergi:
                    row[f"Vergi_{i+1}_{col}"] = vergi[col]
        
        data_rows.append(row)
    
    # Pandas DataFrame oluştur
    try:
        import pandas as pd
        
        # Tüm sütunları belirle
        all_columns = set()
        for row in data_rows:
            all_columns.update(row.keys())
        
        # Önemli etiketleri belirle - bunlar sütun başında gelecek
        important_columns = [
            "Kalem_No", "Gtip", "Ticari_tanimi", "Mensei_ulke", 
            "Brut_agirlik", "Net_agirlik", "Miktar", "Rejim",
            "Kap_adedi", "Fatura_miktari", "Fatura_miktarinin_dovizi"
        ]
        
        # Sütun sıralaması
        ordered_columns = []
        
        # Önce önemli sütunları ekle
        for col in important_columns:
            if col in all_columns:
                ordered_columns.append(col)
                all_columns.remove(col)
        
        # Dokuman sütunlarını ekle - sıralı olarak
        dokuman_cols = sorted([c for c in all_columns if c.startswith("Dokuman_")])
        ordered_columns.extend(dokuman_cols)
        for col in dokuman_cols:
            all_columns.remove(col)
        
        # SoruCevap sütunlarını ekle - sıralı olarak
        soru_cevap_cols = sorted([c for c in all_columns if c.startswith("SoruCevap_")])
        ordered_columns.extend(soru_cevap_cols)
        for col in soru_cevap_cols:
            all_columns.remove(col)
        
        # Vergi sütunlarını ekle - sıralı olarak
        vergi_cols = sorted([c for c in all_columns if c.startswith("Vergi_")])
        ordered_columns.extend(vergi_cols)
        for col in vergi_cols:
            all_columns.remove(col)
        
        # Kalan sütunları ekle
        ordered_columns.extend(sorted(all_columns))
        
        # DataFrame oluştur - her satırda eksik sütunlar olabilir, bunları None olarak doldur
        df = pd.DataFrame(data_rows)
        
        # Sütun sıralamasını ayarla
        available_cols = [col for col in ordered_columns if col in df.columns]
        df = df[available_cols]
        
        # Formatlı excel dosyası oluştur
        excel_output_file = os.path.join(output_dir, f"{xml_name_without_ext}.xlsx")
        
        # Dosya zaten açıksa veya izin sorunu varsa daha açıklayıcı hata mesajı ver
        try:
            df.to_excel(excel_output_file, index=False)
        except PermissionError:
            print(f"Uyarı: '{excel_output_file}' dosyası başka bir program tarafından kullanılıyor veya yazma izni yok.")
            print("Excel dosyası oluşturulamadı, ancak TXT dosyası başarıyla oluşturuldu.")
            excel_output_file = None
        except Exception as e:
            print(f"Uyarı: Excel dosyası oluşturulurken hata: {str(e)}")
            excel_output_file = None
    except ImportError:
        print("Uyarı: pandas kütüphanesi yüklü değil, Excel dosyası oluşturulamadı.")
        excel_output_file = None
    
    # Ayrıca TAB karakteri ile ayrılmış dosya olarak kaydet (Alternatif görüntüleme için)
    txt_output_file = os.path.join(output_dir, f"{xml_name_without_ext}.txt")
    try:
        with open(txt_output_file, 'w', newline='', encoding='utf-8-sig') as f:  # utf-8-sig BOM ekler, Excel için faydalı
            if 'df' in locals() and 'ordered_columns' in locals():
                writer = csv.writer(f, delimiter='\t', quoting=csv.QUOTE_MINIMAL)
                writer.writerow(available_cols)  # Başlık satırı
                
                # Her satır için değerleri yaz
                for _, row in df.iterrows():
                    values = []
                    for col in available_cols:
                        val = row.get(col, '')
                        values.append(str(val) if pd.notna(val) else '')
                    writer.writerow(values)
            else:
                # pandas yoksa veya DataFrame oluşturulmadıysa, basit text çıktısı yap
                writer = csv.writer(f, delimiter='\t', quoting=csv.QUOTE_MINIMAL)
                # Kalem başlıklarını yaz
                if data_rows:
                    all_keys = set()
                    for row in data_rows:
                        all_keys.update(row.keys())
                    writer.writerow(sorted(all_keys))
                    
                    # Her kalem için verileri yaz
                    for row in data_rows:
                        writer.writerow([row.get(k, '') for k in sorted(all_keys)])
    except Exception as e:
        print(f"Uyarı: TXT dosyası oluşturulurken hata: {str(e)}")
        txt_output_file = None
    
    return {
        "xml_file": xml_file,
        "txt_file": txt_output_file,
        "excel_file": excel_output_file,
        "dokuman_count": len(dokuman_list),
        "soru_cevap_count": len(soru_cevap_list),
        "vergi_count": len(vergi_list),
        "kalem_count": len(kalem_data_list)
    }

def show_excel_content(excel_file, rows=3):
    """
    Excel dosyasının içeriğini gösterir
    """
    try:
        import pandas as pd
        print(f"\nExcel dosyası içeriği: {os.path.basename(excel_file)}")
        print("-" * 80)
        df = pd.read_excel(excel_file)
        
        # Önemli sütunları göster
        important_cols = ['Kalem_No']
        for col in df.columns:
            if ('SoruCevap' in col or 'Dokuman' in col or 'Vergi' in col) and col not in important_cols:
                important_cols.append(col)
        
        # İlk birkaç satırı göster
        if len(important_cols) > 1:
            print(df[important_cols].head(rows))
        else:
            print(df.head(rows))
        
        print("-" * 80)
        
        # SoruCevap sütunlarının listesini göster
        soru_cols = [col for col in df.columns if 'SoruCevap' in col]
        if soru_cols:
            print("\nSoruCevap sütunları:")
            for col in soru_cols:
                print(f"  - {col}")
        else:
            print("\nSoruCevap sütunu bulunamadı!")
            
        # Dokuman sütunlarının listesini göster
        dokuman_cols = [col for col in df.columns if 'Dokuman' in col]
        if dokuman_cols:
            print("\nDokuman sütunları:")
            for col in dokuman_cols:
                print(f"  - {col}")
        else:
            print("\nDokuman sütunu bulunamadı!")
            
        # Vergi sütunlarının listesini göster
        vergi_cols = [col for col in df.columns if 'Vergi' in col]
        if vergi_cols:
            print("\nVergi sütunları:")
            for col in vergi_cols:
                print(f"  - {col}")
        else:
            print("\nVergi sütunu bulunamadı!")
            
    except ImportError:
        print("pandas kütüphanesi yüklü değil, Excel dosyası içeriği görüntülenemiyor.")
    except Exception as e:
        print(f"Excel içeriği görüntülenirken hata: {str(e)}")

def process_all_xml_files(xml_dir):
    """
    Belirtilen klasördeki tüm XML dosyalarını işler ve Excel formatına dönüştürür.
    
    xml_dir: XML dosyalarının bulunduğu klasör
    """
    # Klasördeki tüm XML dosyalarını bul
    xml_files = glob.glob(os.path.join(xml_dir, "*.xml"))
    
    if not xml_files:
        print(f"Hata: {xml_dir} klasöründe XML dosyası bulunamadı.")
        return
    
    # Sonuçları tutacak liste
    results = []
    
    # Her XML dosyasını işle
    for xml_file in xml_files:
        try:
            result = extract_beyanname_fixed(xml_file)
            results.append(result)
            print(f"İşlendi: {os.path.basename(xml_file)} -> {os.path.basename(result['txt_file'])}")
            if result['excel_file']:
                print(f"        Excel: {os.path.basename(result['excel_file'])}")
                
                # İşlem sonrasında Excel dosyasının içeriğini göster
                show_excel_content(result['excel_file'])
        except Exception as e:
            print(f"Hata ({os.path.basename(xml_file)}): {str(e)}")
    
    # Özet bilgileri göster
    print("\nİşlem tamamlandı!")
    print(f"Toplam {len(results)} XML dosyası işlendi.")
    print(f"TXT dosyaları oluşturuldu: {len(results)}")
    excel_count = sum(1 for r in results if r['excel_file'])
    if excel_count > 0:
        print(f"Excel dosyaları oluşturuldu: {excel_count}")
    
    print("\nExcel'de doğru görüntüleme için:")
    print("1. Excel'i açın")
    print("2. Veri > Dış Veri Al > Metin Dosyasından")
    print("3. TXT dosyasını seçin")
    print("4. Veri Sihirbazında 'Sınırlandırılmış' seçin ve 'Ayırıcı' olarak 'Tab' işaretleyin")

def analyze_xml(xml_file):
    with open(xml_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Tüm etiketleri bul (navlun içeren)
    all_tags = re.findall(r'<([^/\s>]+)>([^<]*navlun[^<]*)</\1>', content, re.IGNORECASE)
    
    print(f"Dosya: {os.path.basename(xml_file)}")
    print(f"Navlun içeren etiketler:")
    for tag, value in all_tags:
        print(f"  <{tag}>{value}</{tag}>")
    
    # Genel etiket istatistikleri
    all_simple_tags = re.findall(r'<([^/\s>]+)>([^<]+)</\1>', content)
    unique_tags = set(tag for tag, _ in all_simple_tags)
    
    print(f"\nToplam basit etiket sayısı: {len(all_simple_tags)}")
    print(f"Benzersiz etiket sayısı: {len(unique_tags)}")
    
    return unique_tags

if __name__ == "__main__":
    xml_directory = r"C:\Users\hyazgan\Desktop\kopya oto\xml"
    if os.path.exists(xml_directory):
        process_all_xml_files(xml_directory)
        print("\nİşlem tamamlandı. Sadece XML klasöründeki dosyalar işlendi.")
    else:
        print(f"Hata: {xml_directory} klasörü bulunamadı.") 