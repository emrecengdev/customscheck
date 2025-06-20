import csv
import os
import re
import html
import glob
import pandas as pd

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
    
    # DataFrame oluştur
    df = pd.DataFrame(data_rows)
    
    # Sütun sıralamasını ayarla
    available_cols = [col for col in ordered_columns if col in df.columns]
    df = df[available_cols]
    
    # XML dosyası işleme sonucunu döndür, ancak Excel ve TXT dosyalarını oluşturma
    # Dosya oluşturma kodları kaldırıldı - gereksiz dosya oluşumu önlendi
    return {
        "xml_file": xml_file,
        "txt_file": None,  # TXT dosyası oluşturulmadı
        "excel_file": None,  # Excel dosyası oluşturulmadı
        "dokuman_count": len(dokuman_list),
        "soru_cevap_count": len(soru_cevap_list),
        "vergi_count": len(vergi_list),
        "kalem_count": len(kalem_data_list),
        "dataframe": df  # Dataframe'i döndür
    }

def process_all_xml_files(xml_dir):
    """
    Belirtilen klasördeki tüm XML dosyalarını işler ve Excel formatına dönüştürür.
    
    xml_dir: XML dosyalarının bulunduğu klasör
    """
    # Klasördeki tüm XML dosyalarını bul
    xml_files = glob.glob(os.path.join(xml_dir, "*.xml"))
    
    if not xml_files:
        print(f"Hata: {xml_dir} klasöründe XML dosyası bulunamadı.")
        return []
    
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
        except Exception as e:
            print(f"Hata ({os.path.basename(xml_file)}): {str(e)}")
    
    return results

def get_common_columns(dataframes):
    """
    Birden fazla DataFramein ortak sütunlarını bulur.
    """
    if not dataframes:
        return []
    
    # İlk DataFrame'in tüm sütunlarıyla başla
    common_cols = set(dataframes[0].columns)
    
    # Diğer DataFrame'lerle kesişimi al
    for df in dataframes[1:]:
        common_cols = common_cols.intersection(set(df.columns))
    
    return sorted(list(common_cols))

def create_pivot_table(df, index, values, aggfunc='sum', columns=None, margins=False):
    """
    Veri çerçevesinden pivot tablo oluşturur.
    
    df: Pandas DataFrame
    index: Satırları oluşturacak sütun(lar)
    values: Hesaplanacak değerlerin bulunduğu sütun(lar)
    aggfunc: Toplama fonksiyonu ('sum', 'mean', 'count' vb.)
    columns: Sütunları oluşturacak sütun (isteğe bağlı)
    margins: Toplam satırı/sütunu eklenip eklenmeyeceği
    """
    try:
        pivot = pd.pivot_table(
            df, 
            index=index, 
            values=values, 
            aggfunc=aggfunc,
            columns=columns,
            margins=margins,
            margins_name='Toplam'
        )
        return pivot
    except Exception as e:
        print(f"Pivot tablo oluşturulurken hata: {str(e)}")
        return None

def process_multiple_xml_files(xml_dir, max_files=None, progress_callback=None):
    """
    Birden fazla XML dosyasını daha verimli şekilde işler.
    Başlık bilgilerini tekrar tekrar işlemez.
    
    xml_dir: XML dosyalarının bulunduğu klasör
    max_files: İşlenecek maksimum dosya sayısı (None: tümü)
    progress_callback: İlerleme durumunu bildirmek için callback fonksiyonu
    """
    # Klasördeki tüm XML dosyalarını bul
    xml_files = glob.glob(os.path.join(xml_dir, "*.xml"))
    
    if not xml_files:
        return [], "Klasörde XML dosyası bulunamadı."
    
    # Maksimum dosya sayısını kontrol et
    if max_files is not None and max_files > 0:
        xml_files = xml_files[:max_files]
    
    # Sonuçları tutacak liste
    all_dataframes = {}
    error_messages = []
    
    # Her XML dosyasını işle
    total_files = len(xml_files)
    for i, xml_file in enumerate(xml_files):
        try:
            # İlerleme durumunu bildir
            if progress_callback:
                progress = (i+1) / total_files
                msg = f"{i+1}/{total_files} dosya işleniyor: {os.path.basename(xml_file)}"
                progress_callback(progress, msg)
            
            # XML dosyasını işle
            result = extract_beyanname_fixed(xml_file)
            
            if 'dataframe' in result and result['dataframe'] is not None:
                file_name = os.path.basename(xml_file)
                all_dataframes[file_name] = result['dataframe']
            else:
                error_messages.append(f"Hata: {os.path.basename(xml_file)} için DataFrame oluşturulamadı.")
                
        except Exception as e:
            error_messages.append(f"Hata ({os.path.basename(xml_file)}): {str(e)}")
    
    # Son ilerleme durumunu bildir
    if progress_callback:
        progress_callback(1.0, f"Tüm dosyalar işlendi.")
    
    # Sonuçları döndür
    return all_dataframes, error_messages

def merge_dataframes(dataframes_dict):
    """
    Birden çok DataFrame'i tek bir DataFrame'de birleştirir.
    
    dataframes_dict: DataFrame nesnelerini içeren sözlük (dosya adı: DataFrame)
    
    Tüm DataFrame'lerin sütunları aynı olmalıdır, farklı ise eksik sütunlar NaN ile doldurulur.
    
    return: Birleştirilmiş tek bir DataFrame
    """
    if not dataframes_dict:
        return None
    
    # Boş bir liste oluştur
    df_list = []
    
    # Sözlükteki tüm DataFrame'leri listeye ekle
    for filename, df in dataframes_dict.items():
        # Hangi dosyadan geldiğini belirtmek için kaynak sütunu ekle
        df = df.copy()  # Orjinal DataFrame'i değiştirmemek için
        df['Kaynak_Dosya'] = filename
        df_list.append(df)
    
    # Tüm DataFrame'leri birleştir
    if len(df_list) == 1:
        return df_list[0]
    else:
        # ignore_index=True ile indeksleri sıfırdan başlayacak şekilde yeniden numaralandır
        merged_df = pd.concat(df_list, ignore_index=True)
        return merged_df 