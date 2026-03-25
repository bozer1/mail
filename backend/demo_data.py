"""Demo e-posta verileri - Test amaçlı."""
from datetime import datetime, timedelta
import random

DEMO_EMAILS = [
    {
        "sender": "ahmet.yilmaz@sirket.com",
        "sender_name": "Ahmet Yılmaz",
        "recipient": "kullanici@mail.com",
        "subject": "Q4 Proje Raporu - Acil İnceleme Gerekiyor",
        "body": """Merhaba,

Q4 proje raporunu hazırladım ve sizin onayınıza sunmam gerekiyor. Yarın sabah 10:00'da yönetim kurulu toplantısı var ve raporu bugün mesai bitimine kadar tamamlamamız gerekiyor.

Ekteki dosyaları inceleyip geri bildirimlerinizi paylaşabilir misiniz?

Özellikle şu konulara dikkat edilmesini istiyorum:
- Bütçe sapma analizi (Sayfa 3)
- Risk değerlendirmesi (Sayfa 7-9)
- Öneri kısmı (Sayfa 12)

Teşekkürler,
Ahmet Yılmaz
Proje Müdürü""",
        "received_at": datetime.utcnow() - timedelta(hours=2),
    },
    {
        "sender": "newsletter@techblog.io",
        "sender_name": "TechBlog Haber Bülteni",
        "recipient": "kullanici@mail.com",
        "subject": "Bu Haftanın Teknoloji Haberleri: AI, Python 3.13 ve Daha Fazlası",
        "body": """Merhaba,

Bu haftanın en önemli teknoloji haberleri:

🤖 YAPAY ZEKA
- OpenAI yeni GPT-5 modelini tanıttı
- Google Gemini Ultra 2.0 piyasaya çıkıyor
- Anthropic'in Claude 4.0 performans testleri yayınlandı

🐍 PYTHON
- Python 3.13 resmi olarak yayınlandı
- Yeni özellikler: Daha hızlı JIT derleyici, geliştirilmiş hata mesajları

☁️ CLOUD
- AWS yeni Türkiye veri merkezi açıyor
- Azure'dan yeni Kubernetes güncellemesi

Tüm haberleri okumak için: techblog.io/newsletter

Aboneliğinizi iptal etmek için tıklayın.

TechBlog Ekibi""",
        "received_at": datetime.utcnow() - timedelta(hours=5),
    },
    {
        "sender": "support@bankam.com.tr",
        "sender_name": "Bankam Müşteri Hizmetleri",
        "recipient": "kullanici@mail.com",
        "subject": "Hesap Ekstreniz Hazır - Kasım 2024",
        "body": """Sayın Müşterimiz,

Kasım 2024 dönemine ait hesap ekstreniz hazırlanmıştır.

Hesap Özeti:
- IBAN: TR12 3456 7890 1234 5678 9012
- Dönem: 01.11.2024 - 30.11.2024
- Açılış Bakiyesi: 15.234,50 TL
- Toplam Gelen: 8.500,00 TL
- Toplam Giden: 3.215,75 TL
- Kapanış Bakiyesi: 20.518,75 TL

Detaylı ekstreye internet bankacılığı üzerinden ulaşabilirsiniz.

Herhangi bir sorunuz için 444 0 000 numaralı müşteri hizmetlerimizi arayabilirsiniz.

Bankam A.Ş.""",
        "received_at": datetime.utcnow() - timedelta(hours=8),
    },
    {
        "sender": "ayse.kaya@musteri.com",
        "sender_name": "Ayşe Kaya",
        "recipient": "kullanici@mail.com",
        "subject": "Web Sitesi Tasarım Teklifi Hakkında",
        "body": """Merhaba,

Geçen hafta katıldığımız İstanbul Tech Summit'te tanışmıştık.

Şirketimiz için yeni bir web sitesi tasarımı istiyoruz. Projenin kapsamı şöyle:
- 10-15 sayfalık kurumsal web sitesi
- Mobil uyumlu tasarım
- E-ticaret entegrasyonu (yaklaşık 500 ürün)
- Çok dilli destek (TR, EN, DE)
- SEO optimizasyonu

Bütçemiz 50.000-80.000 TL arasında. Proje Ocak 2025'te başlaması gerekiyor.

Teklifinizi ve referanslarınızı paylaşabilir misiniz? Gerekirse toplantı da ayarlayabiliriz.

İyi çalışmalar,
Ayşe Kaya
Genel Müdür Yardımcısı
ABC Tekstil A.Ş.""",
        "received_at": datetime.utcnow() - timedelta(hours=12),
    },
    {
        "sender": "spam@prize-winner-2024.com",
        "sender_name": "Prize Committee",
        "recipient": "kullanici@mail.com",
        "subject": "🎉 TEBRİKLER! 50.000 DOLAR KAZANDINIZ! Hemen Talep Edin!",
        "body": """SİZİ SEÇTİK!!!

Bu ay düzenlediğimiz büyük çekilişte 50.000 DOLAR KAZANDINIZ!

Ödülünüzü almak için:
1. Adınızı ve soyadınızı bildirin
2. Banka hesap bilgilerinizi gönderin
3. 500$ işlem ücreti ödeyin

24 SAAT İÇİNDE YANIT VERMEZSENİZ ÖDÜLÜNÜZ İPTAL OLACAK!

Hemen tıklayın: suspicious-link.com/claim-prize

Şans sizinle olsun!""",
        "received_at": datetime.utcnow() - timedelta(hours=15),
    },
    {
        "sender": "mehmet.demir@universite.edu.tr",
        "sender_name": "Dr. Mehmet Demir",
        "recipient": "kullanici@mail.com",
        "subject": "Tez Danışmanlığı - Randevu Talebi",
        "body": """Sayın Hocam,

Doktora tez çalışmam olan "Derin Öğrenme Tabanlı Türkçe Duygu Analizi" konusunda danışmanlık almak istiyorum.

Bu hafta müsait olduğunuz bir zamanda 30-45 dakikalık bir görüşme yapabilir miyiz?

Tez özeti ve ön çalışma notlarımı ekledim. Özellikle şu konularda görüşünüze ihtiyacım var:
1. Veri seti seçimi ve hazırlama süreci
2. Model mimarisi karşılaştırması
3. Değerlendirme metrikleri

Uygun bir zaman dilimi için randevu alabilir miyim?

Teşekkürler ve saygılarımla,
Mehmet Demir
Doktora Öğrencisi - Bilgisayar Mühendisliği""",
        "received_at": datetime.utcnow() - timedelta(days=1),
    },
    {
        "sender": "fatma.ozturk@saglik.gov.tr",
        "sender_name": "Fatma Öztürk",
        "recipient": "kullanici@mail.com",
        "subject": "Sağlık Tarama Sonuçlarınız",
        "body": """Sayın Hastamız,

Geçtiğimiz hafta yapılan yıllık sağlık taramanızın sonuçları değerlendirilmiştir.

Genel sağlık durumunuz: İYİ
Kan değerleriniz normal sınırlar içindedir.

Öneriler:
- D vitamini seviyeniz düşük, günlük 1000 IU D vitamini takviyesi alabilirsiniz
- Düzenli egzersiz önerilmektedir (haftada 3-4 gün, 30 dakika)
- Sonraki kontrol tarihiniz: 15 Haziran 2025

Sonuç raporunuzu e-devlet kapısından indirebilirsiniz.

Sorularınız için randevu alabilirsiniz.

Dr. Fatma Öztürk
Aile Hekimi""",
        "received_at": datetime.utcnow() - timedelta(days=1, hours=3),
    },
    {
        "sender": "bilgi@turkishairlines.com",
        "sender_name": "Turkish Airlines",
        "recipient": "kullanici@mail.com",
        "subject": "Uçuş Rezervasyonunuz Onaylandı - TK 1234",
        "body": """Sayın Yolcumuz,

İstanbul (IST) - Berlin (BER) seferiniz için uçuş rezervasyonunuz onaylanmıştır.

UÇUŞ BİLGİLERİ
Uçuş: TK 1234
Tarih: 20 Aralık 2024, Cuma
Kalkış: İstanbul Havalimanı (IST) - 14:30
Varış: Berlin Brandenburg (BER) - 16:45
Süre: 3 saat 15 dakika
Koltuk: 23A (Pencere)

REZERVASYON KODU: ABC123

Check-in işleminizi 24 saat öncesinden web sitemizden yapabilirsiniz.
Bagaj hakkınız: 1 kabin çantası + 23 kg kontrollü bagaj

İyi yolculuklar!
Turkish Airlines""",
        "received_at": datetime.utcnow() - timedelta(days=2),
    },
    {
        "sender": "ali.veli@partner.com",
        "sender_name": "Ali Veli",
        "recipient": "kullanici@mail.com",
        "subject": "Ortaklık Anlaşması - Gözden Geçirme",
        "body": """Merhaba,

Avukatımız ortaklık anlaşması taslağını hazırladı. Ekte bulabilirsiniz.

Ana maddeler şöyle:
- %50-50 kar paylaşımı
- Minimum 2 yıllık taahhüt süresi
- Yıllık ciro hedefi: 5 milyon TL
- Karar alma: Mutabık kalınan konularda oybirliği

Lütfen hukuk ekibinizle gözden geçirip görüşlerinizi paylaşın. Önümüzdeki Salı'ya kadar yorum almanız mümkün mü?

Teşekkürler,
Ali Veli""",
        "received_at": datetime.utcnow() - timedelta(days=2, hours=5),
    },
    {
        "sender": "noreply@instagram.com",
        "sender_name": "Instagram",
        "recipient": "kullanici@mail.com",
        "subject": "Ahmet Yılmaz sizi takip etmeye başladı",
        "body": """Merhaba,

Ahmet Yılmaz (@ahmet.yilmaz) sizi Instagram'da takip etmeye başladı.

Profilinizi görüntüle → instagram.com/profile

Bunu siz başlatmadıysanız hesabınızı güvende tutun.

Yardım merkezi | Aboneliği iptal et

Instagram""",
        "received_at": datetime.utcnow() - timedelta(days=3),
    },
]


def get_demo_emails(count: int = 10) -> list:
    """Demo e-postaları döndür."""
    emails = DEMO_EMAILS[:count]
    # Tarih offset'i ayarla
    for i, email_data in enumerate(emails):
        if "received_at" not in email_data:
            email_data["received_at"] = datetime.utcnow() - timedelta(hours=i * 2)
    return emails
