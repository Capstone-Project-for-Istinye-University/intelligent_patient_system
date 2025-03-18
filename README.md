# Akıllı Hasta Yönetim Sistemi

Bu proje, hastaların semptomlarını analiz eden, uygun bölümlere yönlendiren ve randevu almalarını sağlayan bir yapay zeka destekli sağlık asistanı sistemidir.

## Özellikler

- Yapay zeka destekli semptom analizi
- Otomatik bölüm önerisi
- Randevu oluşturma ve yönetimi
- Hasta geçmişi takibi
- Sohbet arayüzü ile kolay kullanım

## Kurulum

1. Repoyu klonlayın:

```bash
git clone https://github.com/KULLANICI_ADI/intelligent_patient_system.git
cd intelligent_patient_system
```

2. Gerekli paketleri yükleyin:

```bash
pip install -r requirements.txt
```

3. Backend sunucusunu başlatın:

```bash
python main.py
```

4. Frontend sunucusunu başlatın:

```bash
python -m http.server 8081
```

5. Tarayıcınızda şu adresi açın:

```
http://localhost:8081/index.html
```

## Kullanım

1. TC kimlik numaranızı girerek sisteme giriş yapın
2. Semptomlarınızı açıklayın
3. Sistem size uygun bölümü önerecektir
4. Önerilen doktorlardan randevu alabilirsiniz
5. Randevularınızı görüntüleyebilir, güncelleyebilir veya iptal edebilirsiniz

## Katkıda Bulunma

1. Bu repoyu fork edin
2. Yeni bir branch oluşturun (`git checkout -b feature/yeniOzellik`)
3. Değişikliklerinizi commit edin (`git commit -am 'Yeni özellik: X'`)
4. Branch'inizi push edin (`git push origin feature/yeniOzellik`)
5. Pull Request oluşturun
