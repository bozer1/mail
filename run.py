#!/usr/bin/env python3
"""Uygulama başlatıcı."""
import os
import sys
import uvicorn
from pathlib import Path

# Proje kök dizinini Python path'ine ekle
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def main():
    # .env dosyasını yükle
    env_file = project_root / ".env"
    if not env_file.exists():
        env_example = project_root / ".env.example"
        if env_example.exists():
            print("⚠️  .env dosyası bulunamadı. .env.example'dan kopyalanıyor...")
            import shutil
            shutil.copy(env_example, env_file)
            print("📝 Lütfen .env dosyasını düzenleyip ANTHROPIC_API_KEY değerini girin.")
            return

    from dotenv import load_dotenv
    load_dotenv(env_file)

    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key or api_key == "your_anthropic_api_key_here":
        print("❌ ANTHROPIC_API_KEY ayarlanmamış!")
        print("   .env dosyasına API anahtarınızı ekleyin.")
        print("   https://console.anthropic.com/keys adresinden API key alabilirsiniz.")
        return

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    debug = os.getenv("DEBUG", "false").lower() == "true"

    print("""
╔══════════════════════════════════════════════════════╗
║         🤖 AI E-posta Asistanı v1.0.0               ║
║──────────────────────────────────────────────────────║
║  Gelen mailleri sınıflandıran ve otomatik yanıt      ║
║  üreten yapay zeka sistemi                           ║
╚══════════════════════════════════════════════════════╝
    """)
    print(f"🚀 Sunucu başlatılıyor: http://localhost:{port}")
    print(f"📖 API Dokümantasyonu: http://localhost:{port}/docs")
    print(f"🔑 Anthropic API: ✓ Yapılandırılmış")
    print()

    uvicorn.run(
        "backend.main:app",
        host=host,
        port=port,
        reload=debug,
        log_level="info" if not debug else "debug"
    )


if __name__ == "__main__":
    main()
