"""Pydantic şemaları - API giriş/çıkış doğrulama."""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field


class EmailCreate(BaseModel):
    sender: str = Field(..., description="Gönderen e-posta adresi")
    sender_name: Optional[str] = Field(None, description="Gönderen adı")
    recipient: str = Field(..., description="Alıcı e-posta adresi")
    subject: str = Field(..., description="E-posta konusu")
    body: str = Field(..., description="E-posta içeriği")
    html_body: Optional[str] = Field(None, description="HTML içerik")
    message_id: Optional[str] = Field(None, description="Benzersiz mesaj ID")


class EmailUpdate(BaseModel):
    is_read: Optional[bool] = None
    is_starred: Optional[bool] = None
    is_archived: Optional[bool] = None
    is_spam: Optional[bool] = None


class ClassificationResult(BaseModel):
    category: str
    priority: int
    confidence: float
    sentiment: str
    summary: str
    tags: List[str]
    requires_response: bool
    urgency_reason: Optional[str] = None


class AutoResponseCreate(BaseModel):
    email_id: int
    tone: str = Field(default="Resmi", description="Yanıt tonu: Resmi, Samimi, Teknik")
    language: str = Field(default="Türkçe", description="Yanıt dili")
    additional_context: Optional[str] = Field(None, description="Ek bağlam")


class AutoResponseResult(BaseModel):
    id: int
    email_id: int
    response_text: str
    tone: str
    language: str
    created_at: datetime
    is_sent: bool


class EmailStats(BaseModel):
    total: int
    unread: int
    starred: int
    by_category: dict
    by_priority: dict
    requires_response: int
    spam: int


class BatchAnalyzeRequest(BaseModel):
    email_ids: List[int]


class SendEmailRequest(BaseModel):
    response_id: int


class SettingsUpdate(BaseModel):
    imap_host: Optional[str] = None
    imap_port: Optional[int] = None
    imap_username: Optional[str] = None
    imap_password: Optional[str] = None
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = None
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
