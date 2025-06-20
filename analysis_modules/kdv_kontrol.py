"""
KDV Kontrol modülü.
Tüm vergi kod sütunlarında "40" kodunu arayıp ona denk gelen oran sütunlarındaki farklılıkları kontrol eder.
"""

import pandas as pd

def check_kdv_kontrol(df):
    """
    Tüm vergi kod sütunlarında "40" kodunu arayıp ona denk gelen oran sütunlarındaki farklılıkları kontrol eder.
    
    Args:
        df (pandas.DataFrame): Beyanname verileri içeren DataFrame
    
    Returns:
        dict: Analiz sonuçları
    """
    
    # Gerekli sütunları kontrol et
    if 'Gtip' not in df.columns:
        return {
            "status": "error",
            "message": "Gtip sütunu bulunamadı"
        }
    
    # Vergi kod ve oran sütunlarını bul
    vergi_kod_sutunlari = [col for col in df.columns if col.startswith('Vergi_') and col.endswith('_Kod')]
    vergi_oran_sutunlari = [col for col in df.columns if col.startswith('Vergi_') and col.endswith('_Oran')]
    
    if not vergi_kod_sutunlari:
        return {
            "status": "error",
            "message": "Vergi kod sütunları bulunamadı (Vergi_X_Kod formatında)"
        }
    
    if not vergi_oran_sutunlari:
        return {
            "status": "error", 
            "message": "Vergi oran sütunları bulunamadı (Vergi_X_Oran formatında)"
        }
    
    # KDV (kod 40) verilerini topla
    kdv_verileri = []
    
    for i, kod_sutun in enumerate(vergi_kod_sutunlari):
        # Kod sütunundan numarayı çıkar (örn: Vergi_2_Kod -> 2)
        try:
            vergi_no = kod_sutun.split('_')[1]
            oran_sutun = f'Vergi_{vergi_no}_Oran'
            
            if oran_sutun not in df.columns:
                continue
                
            # KDV kodu (40) olan satırları bul
            kdv_satirlari = df[df[kod_sutun].astype(str).str.strip() == '40'].copy()
            
            if len(kdv_satirlari) > 0:
                # Oran sütununu temizle ve sayıya çevir
                kdv_satirlari['Temiz_KDV_Oran'] = kdv_satirlari[oran_sutun].astype(str).str.replace(',', '.').str.replace('%', '').str.strip()
                kdv_satirlari['Temiz_KDV_Oran'] = pd.to_numeric(kdv_satirlari['Temiz_KDV_Oran'], errors='coerce')
                
                # Geçerli oranları filtrele
                kdv_satirlari = kdv_satirlari.dropna(subset=['Temiz_KDV_Oran'])
                
                if len(kdv_satirlari) > 0:
                    # Vergi sütun bilgisini ekle
                    kdv_satirlari['Vergi_Sutun_No'] = vergi_no
                    kdv_satirlari['Vergi_Kod_Sutun'] = kod_sutun
                    kdv_satirlari['Vergi_Oran_Sutun'] = oran_sutun
                    kdv_satirlari['Orijinal_KDV_Oran'] = kdv_satirlari[oran_sutun]
                    
                    kdv_verileri.append(kdv_satirlari)
        
        except (IndexError, ValueError):
            continue
    
    if not kdv_verileri:
        return {
            "status": "ok",
            "message": "KDV kodu (40) bulunamadı veya geçerli KDV oranı verisi yok"
        }
    
    # Tüm KDV verilerini birleştir
    tum_kdv_df = pd.concat(kdv_verileri, ignore_index=True)
    
    # GTİP bazında KDV oran farklılıklarını kontrol et
    gtip_oran_analizi = tum_kdv_df.groupby('Gtip')['Temiz_KDV_Oran'].nunique()
    
    # Birden fazla farklı KDV oranı olan GTİP'leri bul
    farkli_oran_gtip = gtip_oran_analizi[gtip_oran_analizi > 1].index.tolist()
    
    if len(farkli_oran_gtip) == 0:
        return {
            "status": "ok",
            "message": f"Toplam {len(tum_kdv_df)} KDV beyanı incelendi. Aynı GTİP kodunda farklı KDV oranı bulunamadı."
        }
    
    # Sonuç verilerini hazırla
    sonuc_verileri = []
    
    for gtip in farkli_oran_gtip:
        gtip_kdv_verileri = tum_kdv_df[tum_kdv_df['Gtip'] == gtip]
        
        # Bu GTİP için farklı KDV oranlarını bul
        farkli_oranlar = sorted(gtip_kdv_verileri['Temiz_KDV_Oran'].unique())
        
        # Her oran için örnek beyannameler
        for oran in farkli_oranlar:
            oran_verileri = gtip_kdv_verileri[gtip_kdv_verileri['Temiz_KDV_Oran'] == oran]
            
            # İlk 5 örneği al
            for _, satir in oran_verileri.head(5).iterrows():
                sonuc_satiri = {
                    'Gtip': gtip,
                    'KDV_Orani': oran,
                    'Vergi_Sutun': f"Vergi_{satir['Vergi_Sutun_No']}",
                    'Beyanname_no': satir.get('Beyanname_no', ''),
                    'Orijinal_KDV_Oran': satir['Orijinal_KDV_Oran']
                }
                
                # Firma bilgisi varsa ekle
                firma_sutunlari = ['Adi_unvani', 'Gonderen', 'Gonderen_adi', 'Ithalatci']
                for firma_sutun in firma_sutunlari:
                    if firma_sutun in satir and pd.notna(satir[firma_sutun]):
                        sonuc_satiri['Firma'] = satir[firma_sutun]
                        break
                
                # Ürün tanımı varsa ekle
                urun_sutunlari = ['Ticari_tanimi', 'Esya_tanimi', 'Aciklama']
                for urun_sutun in urun_sutunlari:
                    if urun_sutun in satir and pd.notna(satir[urun_sutun]):
                        sonuc_satiri['Urun_Tanimi'] = satir[urun_sutun]
                        break
                
                # Tarih bilgisi varsa ekle
                tarih_sutunlari = ['Tescil_tarihi', 'Beyanname_tarihi', 'Tarih']
                for tarih_sutun in tarih_sutunlari:
                    if tarih_sutun in satir and pd.notna(satir[tarih_sutun]):
                        sonuc_satiri['Tarih'] = satir[tarih_sutun]
                        break
                
                sonuc_verileri.append(sonuc_satiri)
    
    # DataFrame'e çevir
    sonuc_df = pd.DataFrame(sonuc_verileri)
    
    # Özet tablosu oluştur
    ozet_verileri = []
    for gtip in farkli_oran_gtip:
        gtip_kdv_verileri = tum_kdv_df[tum_kdv_df['Gtip'] == gtip]
        farkli_oranlar = sorted(gtip_kdv_verileri['Temiz_KDV_Oran'].unique())
        
        # Her oran için beyanname sayısını hesapla
        oran_detaylari = []
        for oran in farkli_oranlar:
            oran_sayisi = len(gtip_kdv_verileri[gtip_kdv_verileri['Temiz_KDV_Oran'] == oran])
            oran_detaylari.append(f'%{int(oran)} ({oran_sayisi} beyan)')
        
        ozet_verileri.append({
            'Gtip': gtip,
            'Farkli_KDV_Oran_Sayisi': len(farkli_oranlar),
            'KDV_Oran_Detaylari': ', '.join(oran_detaylari),
            'Toplam_KDV_Beyani': len(gtip_kdv_verileri),
            'Min_Oran': f'%{int(min(farkli_oranlar))}',
            'Max_Oran': f'%{int(max(farkli_oranlar))}'
        })
    
    ozet_df = pd.DataFrame(ozet_verileri)
    
    # HTML rapor oluştur
    html_rapor = _html_rapor_olustur(sonuc_df, ozet_df, tum_kdv_df)
    
    # Sonuç mesajı
    mesaj = f"{len(farkli_oran_gtip)} GTİP kodunda farklı KDV oranları bulundu. "
    mesaj += f"Toplam {len(tum_kdv_df)} KDV beyanı incelendi, {len(sonuc_verileri)} farklılık tespit edildi."
    
    return {
        "status": "warning",
        "message": mesaj,
        "data": sonuc_df,
        "summary": ozet_df,
        "html_report": html_rapor
    }

def _html_rapor_olustur(sonuc_df, ozet_df, tum_kdv_df):
    """
    Gelişmiş KDV kontrol için HTML rapor oluşturur
    """
    html = """
    <style>
    body {
        font-family: Arial, sans-serif;
        margin: 0;
        padding: 10px;
    }
    h2, h3 {
        color: #2c3e50;
        padding-bottom: 10px;
        border-bottom: 1px solid #eee;
    }
    .ozet-kutu {
        background-color: #f8f9fa;
        border: 1px solid #dee2e6;
        border-radius: 5px;
        padding: 15px;
        margin-bottom: 20px;
    }
    .istatistik-kutu {
        background-color: #e8f5e8;
        border: 1px solid #c3e6c3;
        border-radius: 5px;
        padding: 15px;
        margin-bottom: 20px;
    }
    .uyari-kutu {
        background-color: #fff3cd;
        border: 1px solid #ffeaa7;
        border-radius: 5px;
        padding: 15px;
        margin-bottom: 20px;
    }
    table {
        width: 100%;
        border-collapse: collapse;
        margin-bottom: 20px;
    }
    th {
        background-color: #f2f2f2;
        text-align: left;
        padding: 8px;
        border: 1px solid #ddd;
    }
    td {
        padding: 8px;
        border: 1px solid #ddd;
    }
    tr:nth-child(even) {
        background-color: #f8f9fa;
    }
    .uyari {
        color: #e74c3c;
        font-weight: bold;
    }
    .gtip-bolum {
        margin-top: 30px;
        padding-top: 10px;
        border-top: 1px dashed #ccc;
    }
    .oran-kutu {
        display: inline-block;
        margin-right: 15px;
        padding: 5px 10px;
        background-color: #e3f2fd;
        border-radius: 4px;
        border-left: 4px solid #2196f3;
    }
    .kritik-oran {
        background-color: #ffebee;
        border-left: 4px solid #f44336;
    }
    </style>
    
    <h2>🔍 Gelişmiş KDV Tutarlılık Kontrol Raporu</h2>
    
    <div class="ozet-kutu">
        <h3>📋 Kontrol Açıklaması</h3>
        <p>Bu kontrol, tüm vergi kod sütunlarında (Vergi_1_Kod, Vergi_2_Kod, Vergi_3_Kod vb.) <strong>KDV kodu "40"</strong> arayıp, 
        ona denk gelen oran sütunlarındaki (Vergi_X_Oran) farklılıkları tespit eder.</p>
        <p><strong>🎯 Kontrol Kriteri:</strong> Aynı GTİP kodu için farklı beyanlarda farklı KDV oranları beyan edilmiş mi?</p>
        <p><strong>⚠️ Risk:</strong> Aynı ürün için farklı KDV oranları beyan edilmesi tutarsızlık göstergesidir.</p>
    </div>
    """
    
    # Genel istatistikler
    toplam_kdv_beyani = len(tum_kdv_df)
    farkli_gtip_sayisi = tum_kdv_df['Gtip'].nunique()
    farkli_oran_sayisi = tum_kdv_df['Temiz_KDV_Oran'].nunique()
    
    html += f"""
    <div class="istatistik-kutu">
        <h3>📊 Genel İstatistikler</h3>
        <ul>
            <li><strong>Toplam KDV Beyanı:</strong> {toplam_kdv_beyani:,}</li>
            <li><strong>KDV Beyan Edilen GTİP Sayısı:</strong> {farkli_gtip_sayisi:,}</li>
            <li><strong>Kullanılan Farklı KDV Oranı Sayısı:</strong> {farkli_oran_sayisi}</li>
            <li><strong>Tutarsızlık Tespit Edilen GTİP Sayısı:</strong> {len(ozet_df)}</li>
        </ul>
    </div>
    """
    
    if not ozet_df.empty:
        html += """
        <div class="uyari-kutu">
            <h3>⚠️ Tespit Edilen Tutarsızlıklar</h3>
            <p>Aşağıdaki GTİP kodlarında aynı ürün için farklı KDV oranları beyan edilmiştir:</p>
        </div>
        """
        
        # Özet tablosunu ekle
        html += "<h3>📋 Tutarsızlık Özeti</h3>"
        html += ozet_df.to_html(index=False, classes="table table-striped", escape=False)
        
        # GTİP bazlı detaylar
        html += "<h3>🔍 GTİP Bazlı Detay Analiz</h3>"
        
        gtip_gruplari = sonuc_df.groupby('Gtip')
        
        for gtip, gtip_verileri in gtip_gruplari:
            html += f'<div class="gtip-bolum"><h4>📦 GTİP: {gtip}</h4>'
            
            # Ürün tanımı varsa ekle
            if 'Urun_Tanimi' in gtip_verileri.columns and not gtip_verileri['Urun_Tanimi'].isna().all():
                urun_tanimi = gtip_verileri['Urun_Tanimi'].iloc[0]
                html += f'<p><strong>🏷️ Ürün Tanımı:</strong> {urun_tanimi}</p>'
            
            # Farklı KDV oranlarını göster
            farkli_oranlar = sorted(gtip_verileri['KDV_Orani'].unique())
            html += '<p><strong>💰 Bulunan KDV Oranları:</strong></p>'
            html += '<div>'
            
            for oran in farkli_oranlar:
                oran_sayisi = len(gtip_verileri[gtip_verileri['KDV_Orani'] == oran])
                css_class = "oran-kutu"
                if oran != farkli_oranlar[0]:  # İlk oran dışındakiler kritik
                    css_class += " kritik-oran"
                html += f'<div class="{css_class}">%{int(oran)}: {oran_sayisi} beyanname</div>'
            
            html += '</div>'
            
            # Örnek beyannameleri göster
            html += '<p><strong>📄 Örnek Beyannameler:</strong></p>'
            
            # Gösterilecek sütunları seç
            gosterilecek_sutunlar = ['KDV_Orani', 'Vergi_Sutun', 'Beyanname_no', 'Orijinal_KDV_Oran']
            
            if 'Firma' in gtip_verileri.columns:
                gosterilecek_sutunlar.append('Firma')
            
            if 'Tarih' in gtip_verileri.columns:
                gosterilecek_sutunlar.append('Tarih')
            
            html += gtip_verileri[gosterilecek_sutunlar].head(10).to_html(index=False, classes="table table-striped")
            
            html += '</div>'
    else:
        html += """
        <div class="istatistik-kutu">
            <h3>✅ Sonuç</h3>
            <p>Hiçbir GTİP kodunda KDV oranı tutarsızlığı tespit edilmedi. Tüm KDV beyanları tutarlı görünmektedir.</p>
        </div>
        """
    
    return html 