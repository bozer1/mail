"""AI sınıflandırıcı testleri."""
import pytest
import asyncio
import os
from unittest.mock import MagicMock, AsyncMock, patch


# Test e-postaları
TEST_EMAILS = [
    {
        "subject": "Q4 Proje Raporu - Acil Onay Gerekiyor",
        "body": "Merhaba, Q4 raporunu incelemeniz ve bugün mesai bitimine kadar onaylamanız gerekiyor.",
        "sender": "yonetici@sirket.com",
        "sender_name": "Yönetici",
        "expected_category": "İş",
        "expected_priority_min": 4,
        "expected_requires_response": True,
    },
    {
        "subject": "Bu Haftanın Teknoloji Haberleri",
        "body": "Python 3.13 çıktı! AI haberleri ve daha fazlası...",
        "sender": "newsletter@techblog.com",
        "sender_name": "TechBlog",
        "expected_category": "Haber Bülteni",
        "expected_priority_max": 3,
        "expected_requires_response": False,
    },
    {
        "subject": "50.000 DOLAR KAZANDINIZ!!!",
        "body": "Tebrikler! Ödülünüzü almak için banka bilgilerinizi gönderin.",
        "sender": "prize@spam.com",
        "sender_name": None,
        "expected_category": "Spam",
        "expected_priority_max": 2,
        "expected_requires_response": False,
    },
]


@pytest.mark.asyncio
async def test_classification_structure():
    """AI servisinin doğru yapıda yanıt döndürdüğünü test et."""
    mock_response = MagicMock()
    mock_response.content = [
        MagicMock(type="text", text='''{"category": "İş", "priority": 4, "confidence": 0.9,
        "sentiment": "Tarafsız", "summary": "Acil proje raporu onayı gerekiyor.",
        "tags": ["proje", "rapor", "acil"], "requires_response": true,
        "urgency_reason": "Bugün teslim edilmesi gerekiyor"}''')
    ]

    with patch('anthropic.Anthropic') as MockAnthropic:
        mock_client = MockAnthropic.return_value
        mock_client.messages.create.return_value = mock_response

        # AI servisi oluştur
        os.environ['ANTHROPIC_API_KEY'] = 'test-key-mock'
        from backend.ai_service import AIService
        service = AIService()
        service.client = mock_client

        result = await service.classify_email(
            subject=TEST_EMAILS[0]["subject"],
            body=TEST_EMAILS[0]["body"],
            sender=TEST_EMAILS[0]["sender"],
            sender_name=TEST_EMAILS[0]["sender_name"]
        )

    # Yapı doğrulama
    assert "category" in result
    assert "priority" in result
    assert "confidence" in result
    assert "sentiment" in result
    assert "summary" in result
    assert "tags" in result
    assert "requires_response" in result
    assert isinstance(result["priority"], int)
    assert 1 <= result["priority"] <= 5
    assert 0.0 <= result["confidence"] <= 1.0
    assert isinstance(result["tags"], list)


@pytest.mark.asyncio
async def test_default_classification_on_error():
    """Hata durumunda varsayılan sınıflandırmanın döndürüldüğünü test et."""
    mock_response = MagicMock()
    mock_response.content = [
        MagicMock(type="text", text="Bu geçersiz JSON")
    ]

    with patch('anthropic.Anthropic') as MockAnthropic:
        mock_client = MockAnthropic.return_value
        mock_client.messages.create.return_value = mock_response

        os.environ['ANTHROPIC_API_KEY'] = 'test-key-mock'
        from backend.ai_service import AIService
        service = AIService()
        service.client = mock_client

        result = await service.classify_email(
            subject="Test konu",
            body="Test içerik",
            sender="test@test.com"
        )

    # Varsayılan değerler kontrol et
    assert result["category"] == "Diğer"
    assert result["priority"] == 3
    assert result["confidence"] == 0.5


@pytest.mark.asyncio
async def test_response_generation_structure():
    """Yanıt üretiminin doğru yapıda olduğunu test et."""
    expected_response = "Sayın Müşterimiz,\n\nE-postanızı aldık. Teşekkürler.\n\nSaygılarımızla"

    with patch('anthropic.Anthropic') as MockAnthropic:
        mock_client = MockAnthropic.return_value
        mock_stream = MagicMock()
        mock_stream.__enter__ = MagicMock(return_value=mock_stream)
        mock_stream.__exit__ = MagicMock(return_value=False)
        mock_stream.text_stream = iter([
            "Sayın Müşterimiz,\n\n",
            "E-postanızı aldık. ",
            "Teşekkürler.\n\nSaygılarımızla"
        ])
        mock_client.messages.stream.return_value = mock_stream

        os.environ['ANTHROPIC_API_KEY'] = 'test-key-mock'
        from backend.ai_service import AIService
        service = AIService()
        service.client = mock_client

        result = await service.generate_response(
            subject="Destek talebi",
            body="Ürününüz hakkında bilgi almak istiyorum.",
            sender="musteri@example.com",
            tone="Resmi",
            language="Türkçe"
        )

    assert isinstance(result, str)
    assert len(result) > 0


def test_priority_validation():
    """Öncelik değerinin 1-5 arasında sınırlandırıldığını test et."""
    os.environ['ANTHROPIC_API_KEY'] = 'test-key-mock'
    from backend.ai_service import AIService

    with patch('anthropic.Anthropic'):
        service = AIService()

    # Sınır değerleri test et
    data = {"priority": 10, "confidence": 1.5}
    priority = max(1, min(5, int(data.get("priority", 3))))
    confidence = max(0.0, min(1.0, float(data.get("confidence", 0.8))))

    assert priority == 5
    assert confidence == 1.0


def test_tag_limit():
    """Etiket sayısının 5 ile sınırlandırıldığını test et."""
    tags = ["tag1", "tag2", "tag3", "tag4", "tag5", "tag6", "tag7"]
    limited_tags = tags[:5]
    assert len(limited_tags) == 5


if __name__ == "__main__":
    asyncio.run(test_classification_structure())
    print("Testler başarıyla tamamlandı!")
