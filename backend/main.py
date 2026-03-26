"""FastAPI ana uygulaması - AI E-posta Asistanı."""
import os
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import List, Optional

import anthropic
from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from dotenv import load_dotenv

from backend.database import get_db, init_db
from backend.models import Email, AutoResponse
from backend.schemas import (
    EmailCreate, EmailUpdate, AutoResponseCreate,
    BatchAnalyzeRequest, SendEmailRequest
)
from backend.ai_service import get_ai_service
from backend.demo_data import get_demo_emails
from backend.email_client import get_imap_client, get_smtp_client

# .env dosyasını yükle
load_dotenv()

# Logging yapılandırması
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Uygulama yaşam döngüsü yönetimi."""
    await init_db()
    logger.info("Veritabanı başlatıldı")
    yield
    logger.info("Uygulama kapatılıyor")


app = FastAPI(
    title="AI E-posta Asistanı",
    description="Gelen mailleri sınıflandıran ve otomatik yanıt üreten yapay zeka sistemi",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =================== E-POSTA ENDPOINT'LERİ ===================

@app.get("/api/emails", summary="E-postaları listele")
async def list_emails(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    category: Optional[str] = Query(None),
    priority: Optional[int] = Query(None, ge=1, le=5),
    is_read: Optional[bool] = Query(None),
    is_starred: Optional[bool] = Query(None),
    is_archived: Optional[bool] = Query(False),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """E-postaları filtreli olarak listele."""
    query = select(Email).options(selectinload(Email.auto_responses))

    # Filtreler
    filters = [Email.is_spam == False]
    if not is_archived:
        filters.append(Email.is_archived == False)
    if category:
        filters.append(Email.category == category)
    if priority:
        filters.append(Email.priority == priority)
    if is_read is not None:
        filters.append(Email.is_read == is_read)
    if is_starred is not None:
        filters.append(Email.is_starred == is_starred)
    if search:
        search_term = f"%{search}%"
        filters.append(
            (Email.subject.ilike(search_term)) |
            (Email.sender.ilike(search_term)) |
            (Email.body.ilike(search_term))
        )

    from sqlalchemy import and_
    query = query.where(and_(*filters))
    query = query.order_by(desc(Email.received_at))
    query = query.offset(skip).limit(limit)

    result = await db.execute(query)
    emails = result.scalars().all()

    # Toplam sayı
    count_query = select(func.count(Email.id)).where(and_(*filters))
    count_result = await db.execute(count_query)
    total = count_result.scalar()

    return {
        "emails": [e.to_dict() for e in emails],
        "total": total,
        "skip": skip,
        "limit": limit
    }


@app.get("/api/emails/{email_id}", summary="E-posta detayı")
async def get_email(email_id: int, db: AsyncSession = Depends(get_db)):
    """Belirli bir e-postanın detaylarını getir."""
    result = await db.execute(
        select(Email)
        .options(selectinload(Email.auto_responses))
        .where(Email.id == email_id)
    )
    email = result.scalar_one_or_none()
    if not email:
        raise HTTPException(status_code=404, detail="E-posta bulunamadı")

    # Okundu olarak işaretle
    if not email.is_read:
        email.is_read = True
        await db.commit()

    return email.to_dict()


@app.post("/api/emails", summary="Yeni e-posta ekle")
async def create_email(
    email_data: EmailCreate,
    auto_classify: bool = Query(True, description="Otomatik sınıflandır"),
    db: AsyncSession = Depends(get_db)
):
    """Yeni e-posta ekle ve isteğe bağlı olarak sınıflandır."""
    # Duplicate check
    if email_data.message_id:
        existing = await db.execute(
            select(Email).where(Email.message_id == email_data.message_id)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Bu e-posta zaten mevcut")

    email = Email(
        message_id=email_data.message_id,
        sender=email_data.sender,
        sender_name=email_data.sender_name,
        recipient=email_data.recipient,
        subject=email_data.subject,
        body=email_data.body,
        html_body=email_data.html_body,
        received_at=datetime.utcnow()
    )
    db.add(email)
    await db.commit()
    await db.refresh(email)

    # Otomatik sınıflandırma
    if auto_classify:
        try:
            ai = get_ai_service()
            classification = await ai.classify_email(
                subject=email.subject,
                body=email.body,
                sender=email.sender,
                sender_name=email.sender_name
            )
            email.category = classification["category"]
            email.priority = classification["priority"]
            email.confidence = classification["confidence"]
            email.sentiment = classification["sentiment"]
            email.summary = classification["summary"]
            email.tags = ",".join(classification.get("tags", []))
            email.requires_response = classification["requires_response"]
            email.urgency_reason = classification.get("urgency_reason")
            email.is_spam = classification["category"] == "Spam"
            await db.commit()
        except Exception as e:
            logger.error(f"Otomatik sınıflandırma hatası: {e}")

    # Relationship'leri yükleyerek döndür
    result = await db.execute(
        select(Email).options(selectinload(Email.auto_responses)).where(Email.id == email.id)
    )
    return result.scalar_one().to_dict()


@app.patch("/api/emails/{email_id}", summary="E-posta güncelle")
async def update_email(
    email_id: int,
    update_data: EmailUpdate,
    db: AsyncSession = Depends(get_db)
):
    """E-postanın durumunu güncelle."""
    result = await db.execute(select(Email).where(Email.id == email_id))
    email = result.scalar_one_or_none()
    if not email:
        raise HTTPException(status_code=404, detail="E-posta bulunamadı")

    for field, value in update_data.model_dump(exclude_none=True).items():
        setattr(email, field, value)

    await db.commit()
    result = await db.execute(
        select(Email).options(selectinload(Email.auto_responses)).where(Email.id == email_id)
    )
    return result.scalar_one().to_dict()


@app.delete("/api/emails/{email_id}", summary="E-postayı sil")
async def delete_email(email_id: int, db: AsyncSession = Depends(get_db)):
    """E-postayı veritabanından sil."""
    result = await db.execute(select(Email).where(Email.id == email_id))
    email = result.scalar_one_or_none()
    if not email:
        raise HTTPException(status_code=404, detail="E-posta bulunamadı")

    await db.delete(email)
    await db.commit()
    return {"message": "E-posta silindi"}


# =================== AI ENDPOINT'LERİ ===================

@app.post("/api/emails/{email_id}/classify", summary="E-postayı AI ile sınıflandır")
async def classify_email(email_id: int, db: AsyncSession = Depends(get_db)):
    """E-postayı Claude AI ile sınıflandır."""
    result = await db.execute(select(Email).where(Email.id == email_id))
    email = result.scalar_one_or_none()
    if not email:
        raise HTTPException(status_code=404, detail="E-posta bulunamadı")

    try:
        ai = get_ai_service()
        classification = await ai.classify_email(
            subject=email.subject,
            body=email.body,
            sender=email.sender,
            sender_name=email.sender_name
        )

        email.category = classification["category"]
        email.priority = classification["priority"]
        email.confidence = classification["confidence"]
        email.sentiment = classification["sentiment"]
        email.summary = classification["summary"]
        email.tags = ",".join(classification.get("tags", []))
        email.requires_response = classification["requires_response"]
        email.urgency_reason = classification.get("urgency_reason")
        email.is_spam = classification["category"] == "Spam"

        await db.commit()

        result2 = await db.execute(
            select(Email).options(selectinload(Email.auto_responses)).where(Email.id == email_id)
        )
        updated = result2.scalar_one()

        return {
            "message": "E-posta başarıyla sınıflandırıldı",
            "classification": classification,
            "email": updated.to_dict()
        }

    except anthropic.BadRequestError as e:
        if "credit balance" in str(e).lower():
            raise HTTPException(status_code=402, detail="Anthropic API krediniz yetersiz. Lütfen hesabınıza kredi yükleyin.")
        raise HTTPException(status_code=400, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Sınıflandırma hatası: {e}")
        raise HTTPException(status_code=500, detail=f"Sınıflandırma hatası: {str(e)}")


@app.post("/api/emails/batch-classify", summary="Toplu sınıflandırma")
async def batch_classify(
    request: BatchAnalyzeRequest,
    db: AsyncSession = Depends(get_db)
):
    """Birden fazla e-postayı toplu sınıflandır."""
    results = []
    for email_id in request.email_ids:
        result = await db.execute(select(Email).where(Email.id == email_id))
        email = result.scalar_one_or_none()
        if not email:
            continue

        try:
            ai = get_ai_service()
            classification = await ai.classify_email(
                subject=email.subject,
                body=email.body,
                sender=email.sender,
                sender_name=email.sender_name
            )
            email.category = classification["category"]
            email.priority = classification["priority"]
            email.confidence = classification["confidence"]
            email.sentiment = classification["sentiment"]
            email.summary = classification["summary"]
            email.tags = ",".join(classification.get("tags", []))
            email.requires_response = classification["requires_response"]
            email.urgency_reason = classification.get("urgency_reason")
            email.is_spam = classification["category"] == "Spam"

            await db.commit()
            results.append({"email_id": email_id, "status": "success", "category": classification["category"]})
        except Exception as e:
            results.append({"email_id": email_id, "status": "error", "error": str(e)})

    return {"results": results}


@app.post("/api/emails/{email_id}/generate-response", summary="Otomatik yanıt üret")
async def generate_response(
    email_id: int,
    request: AutoResponseCreate,
    db: AsyncSession = Depends(get_db)
):
    """Claude AI ile otomatik e-posta yanıtı üret."""
    result = await db.execute(select(Email).where(Email.id == email_id))
    email = result.scalar_one_or_none()
    if not email:
        raise HTTPException(status_code=404, detail="E-posta bulunamadı")

    if email.is_spam or (email.category and email.category == "Spam"):
        raise HTTPException(status_code=400, detail="Spam e-postalara yanıt üretilemez")

    try:
        ai = get_ai_service()
        response_text = await ai.generate_response(
            subject=email.subject,
            body=email.body,
            sender=email.sender,
            sender_name=email.sender_name,
            tone=request.tone,
            language=request.language,
            additional_context=request.additional_context
        )

        auto_response = AutoResponse(
            email_id=email_id,
            response_text=response_text,
            tone=request.tone,
            language=request.language
        )
        db.add(auto_response)
        await db.commit()
        await db.refresh(auto_response)

        return {
            "message": "Yanıt başarıyla üretildi",
            "response": auto_response.to_dict()
        }

    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Yanıt üretme hatası: {e}")
        raise HTTPException(status_code=500, detail=f"Yanıt üretme hatası: {str(e)}")


@app.post("/api/responses/{response_id}/send", summary="Yanıtı gönder")
async def send_response(response_id: int, db: AsyncSession = Depends(get_db)):
    """Üretilen yanıtı SMTP ile gönder."""
    result = await db.execute(
        select(AutoResponse)
        .options(selectinload(AutoResponse.email))
        .where(AutoResponse.id == response_id)
    )
    auto_response = result.scalar_one_or_none()
    if not auto_response:
        raise HTTPException(status_code=404, detail="Yanıt bulunamadı")

    if auto_response.is_sent:
        raise HTTPException(status_code=400, detail="Bu yanıt zaten gönderildi")

    smtp_user = os.getenv("SMTP_USERNAME", "")
    smtp_pass = os.getenv("SMTP_PASSWORD", "")

    if not smtp_user or smtp_user == "your_email@gmail.com" or not smtp_pass:
        # SMTP ayarsız → sadece "gönderildi" olarak işaretle (demo modu)
        auto_response.is_sent = True
        auto_response.sent_at = datetime.utcnow()
        await db.commit()
        return {"message": "Yanıt kaydedildi (SMTP ayarı olmadığı için gerçek gönderim yapılmadı)"}

    try:
        smtp = get_smtp_client()
        success = smtp.send_email(
            to_address=auto_response.email.sender,
            subject=auto_response.email.subject,
            body=auto_response.response_text,
            reply_to_message_id=auto_response.email.message_id
        )

        if success:
            auto_response.is_sent = True
            auto_response.sent_at = datetime.utcnow()
            await db.commit()
            return {"message": "Yanıt başarıyla gönderildi"}
        else:
            raise HTTPException(status_code=500, detail="E-posta gönderilemedi")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gönderme hatası: {str(e)}")


# =================== İSTATİSTİK ENDPOINT'LERİ ===================

@app.get("/api/stats", summary="İstatistikler")
async def get_stats(db: AsyncSession = Depends(get_db)):
    """Genel istatistikleri getir."""
    # Toplam
    total = (await db.execute(
        select(func.count(Email.id)).where(Email.is_archived == False)
    )).scalar()

    # Okunmamış
    unread = (await db.execute(
        select(func.count(Email.id)).where(
            Email.is_read == False, Email.is_archived == False, Email.is_spam == False
        )
    )).scalar()

    # Yıldızlı
    starred = (await db.execute(
        select(func.count(Email.id)).where(Email.is_starred == True)
    )).scalar()

    # Yanıt gerektiren
    requires_response = (await db.execute(
        select(func.count(Email.id)).where(
            Email.requires_response == True,
            Email.is_archived == False
        )
    )).scalar()

    # Spam
    spam = (await db.execute(
        select(func.count(Email.id)).where(Email.is_spam == True)
    )).scalar()

    # Kategoriye göre
    category_result = await db.execute(
        select(Email.category, func.count(Email.id))
        .where(Email.category.isnot(None), Email.is_archived == False)
        .group_by(Email.category)
    )
    by_category = {row[0]: row[1] for row in category_result.fetchall()}

    # Önceliğe göre
    priority_result = await db.execute(
        select(Email.priority, func.count(Email.id))
        .where(Email.priority.isnot(None), Email.is_archived == False)
        .group_by(Email.priority)
    )
    by_priority = {str(row[0]): row[1] for row in priority_result.fetchall()}

    return {
        "total": total or 0,
        "unread": unread or 0,
        "starred": starred or 0,
        "requires_response": requires_response or 0,
        "spam": spam or 0,
        "by_category": by_category,
        "by_priority": by_priority
    }


# =================== DEMO & IMAP ENDPOINT'LERİ ===================

@app.post("/api/demo/load", summary="Demo verileri yükle")
async def load_demo_data(
    count: int = Query(10, ge=1, le=10),
    db: AsyncSession = Depends(get_db)
):
    """Demo e-postalarını yükle ve AI ile sınıflandır."""
    demo_emails = get_demo_emails(count)
    added = 0
    classified = 0

    for email_data in demo_emails:
        # Duplicate check (sender+subject kombinasyonu)
        existing = await db.execute(
            select(Email).where(
                Email.sender == email_data["sender"],
                Email.subject == email_data["subject"]
            )
        )
        if existing.scalar_one_or_none():
            continue

        email = Email(
            sender=email_data["sender"],
            sender_name=email_data.get("sender_name"),
            recipient=email_data["recipient"],
            subject=email_data["subject"],
            body=email_data["body"],
            received_at=email_data.get("received_at", datetime.utcnow())
        )
        db.add(email)
        await db.commit()
        await db.refresh(email)
        added += 1

        # AI sınıflandırması
        try:
            ai = get_ai_service()
            classification = await ai.classify_email(
                subject=email.subject,
                body=email.body,
                sender=email.sender,
                sender_name=email.sender_name
            )
            email.category = classification["category"]
            email.priority = classification["priority"]
            email.confidence = classification["confidence"]
            email.sentiment = classification["sentiment"]
            email.summary = classification["summary"]
            email.tags = ",".join(classification.get("tags", []))
            email.requires_response = classification["requires_response"]
            email.urgency_reason = classification.get("urgency_reason")
            email.is_spam = classification["category"] == "Spam"
            await db.commit()
            classified += 1
        except Exception as e:
            logger.warning(f"Sınıflandırma hatası: {e}")

    return {
        "message": f"{added} e-posta eklendi, {classified} tanesi sınıflandırıldı",
        "added": added,
        "classified": classified
    }


@app.post("/api/imap/fetch", summary="IMAP'tan e-posta çek")
async def fetch_from_imap(
    folder: str = Query("INBOX"),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db)
):
    """IMAP sunucusundan e-posta çek."""
    client = get_imap_client()
    emails = client.fetch_emails(folder=folder, limit=limit)
    client.disconnect()

    if not emails:
        return {"message": "E-posta bulunamadı veya bağlantı hatası", "added": 0}

    added = 0
    for email_data in emails:
        # Duplicate check
        if email_data.get("message_id"):
            existing = await db.execute(
                select(Email).where(Email.message_id == email_data["message_id"])
            )
            if existing.scalar_one_or_none():
                continue

        email = Email(
            message_id=email_data.get("message_id"),
            sender=email_data["sender"],
            sender_name=email_data.get("sender_name"),
            recipient=email_data.get("recipient", ""),
            subject=email_data["subject"],
            body=email_data["body"],
            html_body=email_data.get("html_body")
        )
        db.add(email)
        await db.commit()
        await db.refresh(email)
        added += 1

        # AI sınıflandırması
        try:
            ai = get_ai_service()
            classification = await ai.classify_email(
                subject=email.subject,
                body=email.body,
                sender=email.sender,
                sender_name=email.sender_name
            )
            email.category = classification["category"]
            email.priority = classification["priority"]
            email.confidence = classification["confidence"]
            email.sentiment = classification["sentiment"]
            email.summary = classification["summary"]
            email.tags = ",".join(classification.get("tags", []))
            email.requires_response = classification["requires_response"]
            email.urgency_reason = classification.get("urgency_reason")
            email.is_spam = classification["category"] == "Spam"
            await db.commit()
        except Exception as e:
            logger.warning(f"Sınıflandırma hatası: {e}")

    return {"message": f"{added} yeni e-posta eklendi", "added": added}


@app.get("/api/health", summary="Sağlık kontrolü")
async def health_check():
    """API sağlık durumu."""
    api_key_set = bool(os.getenv("ANTHROPIC_API_KEY"))
    return {
        "status": "healthy",
        "version": "1.0.0",
        "anthropic_api_configured": api_key_set,
        "timestamp": datetime.utcnow().isoformat()
    }


# Statik dosyaları sun
frontend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")


@app.get("/", response_class=FileResponse, include_in_schema=False)
async def serve_frontend():
    """Frontend uygulamasını sun."""
    index_path = os.path.join(frontend_path, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "AI E-posta Asistanı API'si - /docs adresinden Swagger UI'ya erişin"}
