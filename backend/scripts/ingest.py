# backend/scripts/ingest.py
# Запускать один раз: python backend/scripts/ingest.py

import sys
import os

# Добавляем папку backend в путь
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "../../.env"))

from app.services.rag_service import ingest_documents

if __name__ == "__main__":
    folder = os.path.join(os.path.dirname(__file__), "../data/knowledge")
    folder = os.path.abspath(folder)

    if not os.path.exists(folder):
        print(f"❌ Папка не найдена: {folder}")
        sys.exit(1)

    print(f"📂 Загружаю документы из: {folder}")
    ingest_documents(folder)
    print("✅ Done.")