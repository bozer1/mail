"""Claude AI servisi - E-posta sınıflandırma ve yanıt üretme."""
import json
import os
import logging
from typing import Optional
import anthropic

logger = logging.getLogger(__name__)

CATEGORIES = [
    "İş",
    "Kişisel",
    "Haber Bülteni",
    "Finansal",
    "Sosyal Medya",
    "Destek/Teknik",
    "Kampanya/Reklam",
    "Eğitim",
    "Sağlık",
    "Seyahat",
    "Spam",
    "Diğer"
]

SYSTEM_PROMPT_CLASSIFIER = """Sen bir uzman e-posta analiz yapay zekasısın.
E-postaları analiz ederek aşağıdaki bilgileri çıkarıyorsun:

1. **Kategori**: E-postanın türü (İş, Kişisel, Haber Bülteni, Finansal, Sosyal Medya, Destek/Teknik, Kampanya/Reklam, Eğitim, Sağlık, Seyahat, Spam, Diğer)
2. **Öncelik**: 1 (çok düşük) ile 5 (çok yüksek) arası
3. **Güven**: 0.0 ile 1.0 arası - sınıflandırma güven skoru
4. **Duygu**: Olumlu, Olumsuz veya Tarafsız
5. **Özet**: 1-2 cümlelik kısa özet
6. **Etiketler**: İlgili anahtar kelimeler (en fazla 5 adet)
7. **Yanıt Gerekiyor mu**: true/false
8. **Aciliyet Nedeni**: Eğer öncelik 4+ ise neden acil olduğunu açıkla

Her zaman JSON formatında yanıt ver."""

SYSTEM_PROMPT_RESPONDER = """Sen profesyonel bir e-posta asistanısın.
Verilen e-postaya uygun, doğal ve bağlama uygun bir yanıt yazıyorsun.

Kurallar:
- Yanıtı belirtilen tonda yaz (Resmi, Samimi veya Teknik)
- Belirtilen dilde yaz
- Gerçekçi ve kullanılabilir yanıtlar üret
- Spam veya reklam e-postalarına yanıt yazma
- Yanıtı "Merhaba [İsim]," gibi uygun bir selamlama ile başlat
- Uygun bir kapanış ile bitir
- Sadece yanıt metnini döndür, ekstra açıklama yapma"""


class AIService:
    def __init__(self):
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY ortam değişkeni ayarlanmamış!")
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = "claude-opus-4-6"

    async def classify_email(
        self,
        subject: str,
        body: str,
        sender: str,
        sender_name: Optional[str] = None
    ) -> dict:
        """E-postayı sınıflandır ve analiz et."""
        sender_info = f"{sender_name} <{sender}>" if sender_name else sender

        prompt = f"""Aşağıdaki e-postayı analiz et ve JSON formatında sonuç döndür:

Gönderen: {sender_info}
Konu: {subject}

İçerik:
{body[:3000]}

Mevcut kategoriler: {', '.join(CATEGORIES)}

Tam olarak şu JSON yapısını döndür:
{{
    "category": "kategori_adı",
    "priority": 1-5_arası_sayı,
    "confidence": 0.0-1.0_arası_ondalık,
    "sentiment": "Olumlu|Olumsuz|Tarafsız",
    "summary": "kısa özet",
    "tags": ["etiket1", "etiket2"],
    "requires_response": true|false,
    "urgency_reason": "acil ise neden ya da null"
}}"""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                system=SYSTEM_PROMPT_CLASSIFIER,
                messages=[{"role": "user", "content": prompt}]
            )

            # Yanıttan JSON'u çıkar
            text_content = ""
            for block in response.content:
                if block.type == "text":
                    text_content = block.text
                    break

            # JSON parse et
            text_content = text_content.strip()
            if "```json" in text_content:
                text_content = text_content.split("```json")[1].split("```")[0].strip()
            elif "```" in text_content:
                text_content = text_content.split("```")[1].split("```")[0].strip()

            result = json.loads(text_content)

            # Veri doğrulama
            result["priority"] = max(1, min(5, int(result.get("priority", 3))))
            result["confidence"] = max(0.0, min(1.0, float(result.get("confidence", 0.8))))
            result["tags"] = result.get("tags", [])[:5]

            return result

        except json.JSONDecodeError as e:
            logger.error(f"JSON parse hatası: {e}, Yanıt: {text_content}")
            return self._default_classification()
        except anthropic.BadRequestError as e:
            if "credit balance" in str(e).lower():
                raise ValueError("Anthropic API krediniz yetersiz. Lütfen console.anthropic.com adresinden hesabınıza kredi yükleyin.")
            raise
        except anthropic.APIError as e:
            logger.error(f"Anthropic API hatası: {e}")
            raise ValueError(f"Anthropic API hatası: {str(e)}")

    async def generate_response(
        self,
        subject: str,
        body: str,
        sender: str,
        sender_name: Optional[str] = None,
        tone: str = "Resmi",
        language: str = "Türkçe",
        additional_context: Optional[str] = None
    ) -> str:
        """E-posta için otomatik yanıt üret."""
        sender_display = sender_name if sender_name else sender.split("@")[0]

        context = f"\nEk bağlam: {additional_context}" if additional_context else ""

        prompt = f"""Aşağıdaki e-postaya {tone} tonda {language} dilinde bir yanıt yaz:

Gönderen: {sender_display} ({sender})
Konu: {subject}

E-posta İçeriği:
{body[:3000]}{context}

Ton: {tone}
Dil: {language}

Sadece yanıt metnini yaz. Başka açıklama ekleme."""

        try:
            with self.client.messages.stream(
                model=self.model,
                max_tokens=2048,
                system=SYSTEM_PROMPT_RESPONDER,
                messages=[{"role": "user", "content": prompt}]
            ) as stream:
                response_text = ""
                for text in stream.text_stream:
                    response_text += text
                return response_text.strip()

        except anthropic.BadRequestError as e:
            if "credit balance" in str(e).lower():
                raise ValueError("Anthropic API krediniz yetersiz. Lütfen hesabınıza kredi yükleyin.")
            raise
        except anthropic.APIError as e:
            logger.error(f"Yanıt üretme hatası: {e}")
            raise ValueError(f"Anthropic API hatası: {str(e)}")

    async def batch_classify(self, emails: list) -> list:
        """Birden fazla e-postayı toplu sınıflandır."""
        results = []
        for email in emails:
            result = await self.classify_email(
                subject=email.get("subject", ""),
                body=email.get("body", ""),
                sender=email.get("sender", ""),
                sender_name=email.get("sender_name")
            )
            results.append({"email_id": email.get("id"), "classification": result})
        return results

    def _default_classification(self) -> dict:
        """Hata durumunda varsayılan sınıflandırma."""
        return {
            "category": "Diğer",
            "priority": 3,
            "confidence": 0.5,
            "sentiment": "Tarafsız",
            "summary": "E-posta analiz edildi.",
            "tags": [],
            "requires_response": False,
            "urgency_reason": None
        }


# Singleton instance
_ai_service: Optional[AIService] = None


def get_ai_service() -> AIService:
    global _ai_service
    if _ai_service is None:
        _ai_service = AIService()
    return _ai_service
