"""SQLAlchemy veritabanı modelleri."""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from backend.database import Base


class Email(Base):
    __tablename__ = "emails"

    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(String(255), unique=True, index=True, nullable=True)
    sender = Column(String(255), nullable=False)
    sender_name = Column(String(255), nullable=True)
    recipient = Column(String(255), nullable=False)
    subject = Column(String(500), nullable=False)
    body = Column(Text, nullable=False)
    html_body = Column(Text, nullable=True)
    received_at = Column(DateTime, default=datetime.utcnow)
    is_read = Column(Boolean, default=False)
    is_starred = Column(Boolean, default=False)
    is_archived = Column(Boolean, default=False)
    is_spam = Column(Boolean, default=False)

    # AI Analiz Sonuçları
    category = Column(String(100), nullable=True)       # İş, Kişisel, Spam, vb.
    priority = Column(Integer, nullable=True)            # 1-5 arası
    confidence = Column(Float, nullable=True)            # 0.0-1.0 arası
    sentiment = Column(String(50), nullable=True)        # Olumlu, Olumsuz, Tarafsız
    summary = Column(Text, nullable=True)               # AI özeti
    tags = Column(String(500), nullable=True)           # Virgülle ayrılmış etiketler
    requires_response = Column(Boolean, default=False)
    urgency_reason = Column(Text, nullable=True)

    # İlişkiler
    auto_responses = relationship("AutoResponse", back_populates="email", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "message_id": self.message_id,
            "sender": self.sender,
            "sender_name": self.sender_name,
            "recipient": self.recipient,
            "subject": self.subject,
            "body": self.body,
            "received_at": self.received_at.isoformat() if self.received_at else None,
            "is_read": self.is_read,
            "is_starred": self.is_starred,
            "is_archived": self.is_archived,
            "is_spam": self.is_spam,
            "category": self.category,
            "priority": self.priority,
            "confidence": self.confidence,
            "sentiment": self.sentiment,
            "summary": self.summary,
            "tags": self.tags.split(",") if self.tags else [],
            "requires_response": self.requires_response,
            "urgency_reason": self.urgency_reason,
            "auto_responses": [r.to_dict() for r in self.auto_responses],
        }


class AutoResponse(Base):
    __tablename__ = "auto_responses"

    id = Column(Integer, primary_key=True, index=True)
    email_id = Column(Integer, ForeignKey("emails.id"), nullable=False)
    response_text = Column(Text, nullable=False)
    tone = Column(String(100), nullable=True)     # Resmi, Samimi, Teknik
    language = Column(String(50), default="Türkçe")
    created_at = Column(DateTime, default=datetime.utcnow)
    is_sent = Column(Boolean, default=False)
    sent_at = Column(DateTime, nullable=True)

    email = relationship("Email", back_populates="auto_responses")

    def to_dict(self):
        return {
            "id": self.id,
            "email_id": self.email_id,
            "response_text": self.response_text,
            "tone": self.tone,
            "language": self.language,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "is_sent": self.is_sent,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
        }
