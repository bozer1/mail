"""FastAPI endpoint testleri."""
import pytest
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock
from httpx import AsyncClient, ASGITransport
import os

os.environ['ANTHROPIC_API_KEY'] = 'test-key-for-api-tests'
os.environ['DATABASE_URL'] = 'sqlite+aiosqlite:///./test_mail.db'


@pytest.fixture
async def client():
    """Test HTTP istemcisi oluştur - izole veritabanı ile."""
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
    from backend.database import Base, get_db
    from backend.main import app

    # Test için ayrı veritabanı
    test_engine = create_async_engine('sqlite+aiosqlite:///./test_mail_temp.db', echo=False)
    TestSession = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)

    # Tabloları oluştur
    from backend.models import Email, AutoResponse  # noqa
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Dependency override
    async def override_get_db():
        async with TestSession() as session:
            try:
                yield session
            finally:
                await session.close()

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c

    # Temizlik
    app.dependency_overrides.clear()
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()

    import os as _os
    if _os.path.exists('./test_mail_temp.db'):
        _os.remove('./test_mail_temp.db')


@pytest.mark.asyncio
async def test_health_check(client):
    """Sağlık kontrolü endpoint'i testi."""
    res = await client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_list_emails_empty(client):
    """Boş e-posta listesi testi."""
    res = await client.get("/api/emails")
    assert res.status_code == 200
    data = res.json()
    assert "emails" in data
    assert "total" in data
    assert isinstance(data["emails"], list)


@pytest.mark.asyncio
async def test_create_email(client):
    """E-posta oluşturma testi."""
    with patch('backend.ai_service.AIService.classify_email') as mock_classify:
        mock_classify.return_value = {
            "category": "İş",
            "priority": 3,
            "confidence": 0.85,
            "sentiment": "Tarafsız",
            "summary": "İş e-postası",
            "tags": ["iş", "proje"],
            "requires_response": True,
            "urgency_reason": None
        }

        res = await client.post("/api/emails?auto_classify=true", json={
            "sender": "test@example.com",
            "sender_name": "Test Kullanıcı",
            "recipient": "alici@example.com",
            "subject": "Test E-postası",
            "body": "Bu bir test e-postasıdır."
        })

    assert res.status_code == 200
    data = res.json()
    assert data["sender"] == "test@example.com"
    assert data["subject"] == "Test E-postası"
    assert "id" in data


@pytest.mark.asyncio
async def test_get_email(client):
    """E-posta detay testi."""
    # Önce e-posta oluştur
    with patch('backend.ai_service.AIService.classify_email') as mock_classify:
        mock_classify.return_value = {
            "category": "Kişisel", "priority": 2,
            "confidence": 0.9, "sentiment": "Olumlu",
            "summary": "Kişisel e-posta", "tags": [],
            "requires_response": False, "urgency_reason": None
        }
        create_res = await client.post("/api/emails?auto_classify=false", json={
            "sender": "arkadas@example.com",
            "recipient": "ben@example.com",
            "subject": "Merhaba!",
            "body": "Nasılsın?"
        })

    email_id = create_res.json()["id"]

    # Detay al
    res = await client.get(f"/api/emails/{email_id}")
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == email_id
    assert data["is_read"] == True  # Okuma otomatik işaretlenir


@pytest.mark.asyncio
async def test_email_not_found(client):
    """Olmayan e-posta testi."""
    res = await client.get("/api/emails/99999")
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_update_email(client):
    """E-posta güncelleme testi."""
    # E-posta oluştur
    create_res = await client.post("/api/emails?auto_classify=false", json={
        "sender": "test@test.com",
        "recipient": "ben@test.com",
        "subject": "Güncelleme Testi",
        "body": "Test içeriği"
    })
    email_id = create_res.json()["id"]

    # Yıldızla
    res = await client.patch(f"/api/emails/{email_id}", json={"is_starred": True})
    assert res.status_code == 200
    assert res.json()["is_starred"] == True


@pytest.mark.asyncio
async def test_delete_email(client):
    """E-posta silme testi."""
    create_res = await client.post("/api/emails?auto_classify=false", json={
        "sender": "sil@test.com",
        "recipient": "ben@test.com",
        "subject": "Silinecek E-posta",
        "body": "Bu silinecek."
    })
    email_id = create_res.json()["id"]

    # Sil
    res = await client.delete(f"/api/emails/{email_id}")
    assert res.status_code == 200

    # Silindiğini doğrula
    res = await client.get(f"/api/emails/{email_id}")
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_stats_endpoint(client):
    """İstatistik endpoint'i testi."""
    res = await client.get("/api/stats")
    assert res.status_code == 200
    data = res.json()
    assert "total" in data
    assert "unread" in data
    assert "by_category" in data
    assert "by_priority" in data


@pytest.mark.asyncio
async def test_search_emails(client):
    """E-posta arama testi."""
    # Test e-postası oluştur
    await client.post("/api/emails?auto_classify=false", json={
        "sender": "unique_search@test.com",
        "recipient": "ben@test.com",
        "subject": "Benzersiz Arama Konusu XYZ123",
        "body": "Arama testi içeriği"
    })

    # Ara
    res = await client.get("/api/emails?search=XYZ123")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 1
    assert any("XYZ123" in e["subject"] for e in data["emails"])


@pytest.mark.asyncio
async def test_pagination(client):
    """Sayfalama testi."""
    res = await client.get("/api/emails?skip=0&limit=5")
    assert res.status_code == 200
    data = res.json()
    assert len(data["emails"]) <= 5


if __name__ == "__main__":
    asyncio.run(test_health_check(None))
    print("API testleri tamamlandı!")
