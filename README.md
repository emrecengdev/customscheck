# Beyanname Kontrol Uygulaması

Bu uygulama, gümrük beyanname XML verilerini analiz etmek, çeşitli kontroller yapmak ve pivot tablolar oluşturmak için geliştirilmiş bir araçtır.

## Özellikler

- XML formatındaki gümrük beyanname verilerini içe aktarma
- Verileri tablo formunda görüntüleme ve filtreleme
- Çeşitli veri kontrollerini otomatik çalıştırma:
  - Eksik değer kontrolü
  - Tekrarlanan veri kontrolü
  - Ağırlık tutarlılığı kontrolü (brüt >= net)
  - Döviz tutarları kontrolü
  - Vergi tutarlılığı kontrolü
- Pivot tablolar oluşturma:
  - GTIP kodlarına göre özet
  - Menşei ülkelere göre özet
  - Rejim kodlarına göre özet
  - GTIP-Ülke çapraz tablosu
  - Özel pivot tablolar
- Grafikler oluşturma:
  - Çubuk grafikleri
  - Pasta grafikleri
  - Saçılım grafikleri
- Dashboard üzerinde verilerin özet gösterimi

## Kurulum

Uygulamayı çalıştırmak için aşağıdaki bağımlılıkların yüklü olması gerekmektedir:

```
python 3.6+
pandas
numpy
matplotlib
PyQt5
```

Bağımlılıkları yüklemek için:

```bash
pip install pandas numpy matplotlib PyQt5
```

## Kullanım

Uygulamayı başlatmak için:

```bash
python customs_check.py
```

### XML Verilerini İçe Aktarma

1. "XML Dosyası İçe Aktar" butonuna tıklayarak tek bir XML dosyası seçebilir veya
2. "XML Klasörü İçe Aktar" butonuna tıklayarak bir klasördeki tüm XML dosyalarını içe aktarabilirsiniz.

İçe aktarılan dosyalar, üst kısımdaki açılır menüden seçilebilir.

### Veri Görünümü

Bu sekmede, içe aktarılan veriler tablo halinde görüntülenir. Sütun seçip filtreleme yapabilirsiniz.

### Analizler

Bu sekme altında üç alt sekme bulunur:

1. **Veri Kontrolleri**: Çeşitli veri kontrollerini çalıştırabilir ve sonuçları görüntüleyebilirsiniz.
2. **Pivot Tablolar**: Önceden tanımlanmış pivot tablolar oluşturabilir veya kendi özel pivot tablonuzu tanımlayabilirsiniz.
3. **Grafikler**: Farklı türde grafikler oluşturabilirsiniz.

### Dashboard

Bu sekmede, içe aktarılan verinin özet bilgileri ve tespit edilen sorunlar görüntülenir.

## Geliştirme

Uygulama modüler bir yapıda tasarlanmıştır:

- `customs_check.py`: Ana uygulama ve kullanıcı arayüzü
- `xml_processor.py`: XML işleme fonksiyonları
- `analysis.py`: Veri analizi ve kontrol fonksiyonları
- `custom_widgets.py`: Özel UI bileşenleri

Yeni kontrol ve analiz fonksiyonları ekleyerek uygulamayı genişletebilirsiniz.

## Lisans

Bu proje [MIT Lisansı](LICENSE) altında lisanslanmıştır. 