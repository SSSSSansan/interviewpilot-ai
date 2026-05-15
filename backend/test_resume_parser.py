"""
Быстрый тест парсера резюме.
Запуск: python test_resume_parser.py

Положи своё резюме как resume.pdf рядом с этим файлом.
"""

from dotenv import load_dotenv
load_dotenv()

import asyncio
import sys
import os

# Добавляем путь чтобы импорты работали
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.resume_parser import parse_resume_pdf, format_cv_for_prompt


async def test_parser():
    pdf_path = "resume.pdf"  # положи сюда своё резюме

    if not os.path.exists(pdf_path):
        print(f"❌ Файл {pdf_path} не найден.")
        print("   Положи своё резюме как resume.pdf рядом с этим скриптом.")
        return

    print(f"📄 Читаю {pdf_path}...")
    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    print("🤖 Парсю через GPT...")
    cv_data = await parse_resume_pdf(pdf_bytes)

    print("\n✅ Результат парсинга:")
    print(f"  Текущая роль:  {cv_data.get('current_role', '—')}")
    print(f"  Опыт:          {cv_data.get('years_experience', 0)} лет")
    print(f"  Языки прогр.:  {cv_data.get('tech_stack', [])}")
    print(f"  Навыки:        {cv_data.get('skills', [])[:5]}...")
    print(f"  Проектов:      {len(cv_data.get('projects', []))}")
    print(f"  Образование:   {cv_data.get('education', '—')}")
    print(f"  Разг. языки:   {cv_data.get('languages', [])}")

    print("\n📝 Форматированный CV для промпта:")
    print(format_cv_for_prompt(cv_data))

    print("\n🎉 Парсер работает корректно!")


if __name__ == "__main__":
    asyncio.run(test_parser())