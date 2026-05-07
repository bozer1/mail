"""IMAP/SMTP e-posta istemcisi."""
import os
import logging
import email as email_lib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import decode_header
from typing import List, Optional
import imaplib
import smtplib
import ssl

logger = logging.getLogger(__name__)


def decode_str(value: str) -> str:
    """E-posta başlıklarındaki kodlanmış stringleri çöz."""
    if not value:
        return ""
    decoded_parts = decode_header(value)
    result = []
    for part, charset in decoded_parts:
        if isinstance(part, bytes):
            try:
                result.append(part.decode(charset or "utf-8", errors="replace"))
            except (LookupError, UnicodeDecodeError):
                result.append(part.decode("utf-8", errors="replace"))
        else:
            result.append(str(part))
    return "".join(result)


class IMAPClient:
    """IMAP protokolü ile e-posta okuma."""

    def __init__(self, host=None, port=None, username=None, password=None):
        self.host = host or os.getenv("IMAP_HOST", "imap.gmail.com")
        self.port = int(port or os.getenv("IMAP_PORT", "993"))
        self.username = username or os.getenv("IMAP_USERNAME", "")
        self.password = password or os.getenv("IMAP_PASSWORD", "")
        self.connection = None

    def connect(self) -> bool:
        """IMAP sunucusuna bağlan."""
        try:
            context = ssl.create_default_context()
            self.connection = imaplib.IMAP4_SSL(self.host, self.port, ssl_context=context)
            self.connection.login(self.username, self.password)
            logger.info(f"IMAP bağlantısı kuruldu: {self.host}")
            return True
        except Exception as e:
            logger.error(f"IMAP bağlantı hatası: {e}")
            return False

    def disconnect(self):
        """IMAP bağlantısını kapat."""
        if self.connection:
            try:
                self.connection.logout()
            except Exception:
                pass
            self.connection = None

    def fetch_emails(self, folder: str = "INBOX", limit: int = 20) -> List[dict]:
        """Belirtilen klasörden e-postaları çek."""
        if not self.connection:
            if not self.connect():
                return []

        try:
            self.connection.select(folder)
            status, messages = self.connection.search(None, "ALL")

            if status != "OK":
                return []

            email_ids = messages[0].split()
            # En yeni e-postaları al
            email_ids = email_ids[-limit:] if len(email_ids) > limit else email_ids
            email_ids.reverse()

            emails = []
            for email_id in email_ids:
                try:
                    email_data = self._fetch_single_email(email_id)
                    if email_data:
                        emails.append(email_data)
                except Exception as e:
                    logger.warning(f"E-posta çekme hatası (ID: {email_id}): {e}")
                    continue

            return emails

        except Exception as e:
            logger.error(f"E-posta listesi hatası: {e}")
            return []

    def _fetch_single_email(self, email_id: bytes) -> Optional[dict]:
        """Tek bir e-postayı çek ve parse et."""
        status, msg_data = self.connection.fetch(email_id, "(RFC822)")
        if status != "OK":
            return None

        raw_email = msg_data[0][1]
        msg = email_lib.message_from_bytes(raw_email)

        # Başlıkları parse et
        subject = decode_str(msg.get("Subject", ""))
        sender_raw = decode_str(msg.get("From", ""))
        recipient = decode_str(msg.get("To", ""))
        message_id = msg.get("Message-ID", "")
        date_str = msg.get("Date", "")

        # Gönderen adı ve e-postayı ayır
        sender_name = ""
        sender_email = sender_raw
        if "<" in sender_raw and ">" in sender_raw:
            parts = sender_raw.split("<")
            sender_name = parts[0].strip().strip('"')
            sender_email = parts[1].rstrip(">").strip()

        # Gövdeyi çıkar
        body_text = ""
        body_html = ""

        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition", ""))

                if "attachment" in content_disposition:
                    continue

                if content_type == "text/plain":
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or "utf-8"
                        body_text = payload.decode(charset, errors="replace")
                elif content_type == "text/html":
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or "utf-8"
                        body_html = payload.decode(charset, errors="replace")
        else:
            payload = msg.get_payload(decode=True)
            if payload:
                charset = msg.get_content_charset() or "utf-8"
                content_type = msg.get_content_type()
                if content_type == "text/html":
                    body_html = payload.decode(charset, errors="replace")
                else:
                    body_text = payload.decode(charset, errors="replace")

        return {
            "message_id": message_id,
            "sender": sender_email,
            "sender_name": sender_name,
            "recipient": recipient,
            "subject": subject,
            "body": body_text or "HTML içerik mevcut",
            "html_body": body_html,
            "date": date_str,
        }


class SMTPClient:
    """SMTP protokolü ile e-posta gönderme."""

    def __init__(self, host=None, port=None, username=None, password=None):
        self.host = host or os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.port = int(port or os.getenv("SMTP_PORT", "587"))
        self.username = username or os.getenv("SMTP_USERNAME", "")
        self.password = password or os.getenv("SMTP_PASSWORD", "")

    def send_email(
        self,
        to_address: str,
        subject: str,
        body: str,
        reply_to_message_id: Optional[str] = None
    ) -> bool:
        """E-posta gönder."""
        try:
            msg = MIMEMultipart("alternative")
            msg["From"] = self.username
            msg["To"] = to_address
            msg["Subject"] = f"Re: {subject}" if not subject.startswith("Re:") else subject

            if reply_to_message_id:
                msg["In-Reply-To"] = reply_to_message_id
                msg["References"] = reply_to_message_id

            text_part = MIMEText(body, "plain", "utf-8")
            msg.attach(text_part)

            context = ssl.create_default_context()
            with smtplib.SMTP(self.host, self.port) as server:
                server.ehlo()
                server.starttls(context=context)
                server.login(self.username, self.password)
                server.send_message(msg)

            logger.info(f"E-posta gönderildi: {to_address}")
            return True

        except Exception as e:
            logger.error(f"E-posta gönderme hatası: {e}")
            return False


def get_imap_client(host=None, port=None, username=None, password=None) -> IMAPClient:
    return IMAPClient(host=host, port=port, username=username, password=password)


def get_smtp_client(host=None, port=None, username=None, password=None) -> SMTPClient:
    return SMTPClient(host=host, port=port, username=username, password=password)
