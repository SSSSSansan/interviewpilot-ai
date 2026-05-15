import fitz  # PyMuPDF
import json
import re
from openai import AsyncOpenAI

client = AsyncOpenAI()


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """
    Извлекает весь текст из PDF.
    Работает с русскими и английскими резюме.
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text()
    doc.close()

    # Базовая чистка: убираем лишние пустые строки
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = text.strip()
    return text


async def parse_resume_pdf(pdf_bytes: bytes) -> dict:
    """
    Главная функция. Принимает PDF как bytes.
    Возвращает структурированный dict с данными резюме.
    Поддерживает русский и английский языки.
    """
    # Шаг 1: Извлечь текст
    raw_text = extract_text_from_pdf(pdf_bytes)

    if not raw_text or len(raw_text) < 50:
        # PDF пустой или не читаемый — вернуть дефолт
        return _empty_cv()

    # Шаг 2: Определить язык (грубо — по наличию кириллицы)
    has_cyrillic = bool(re.search(r'[а-яёА-ЯЁ]', raw_text))
    language_hint = "Резюме написано на русском языке." if has_cyrillic else "The resume is in English."

    # Шаг 3: Структурировать через GPT
    prompt = f"""Ты парсер резюме. {language_hint}

Извлеки структурированные данные из резюме ниже.
Верни ТОЛЬКО валидный JSON без markdown, без комментариев, без пояснений.

Правила:
- skills: технические навыки (фреймворки, инструменты, базы данных и т.д.)
- tech_stack: языки программирования (Python, JavaScript, Go и т.д.)  
- years_experience: суммарный опыт работы в годах (если не указан явно — оцени по датам)
- projects: список проектов, каждый как краткое описание одним предложением
- education: последнее/главное образование одной строкой
- languages: разговорные языки (Русский, English и т.д.)
- current_role: текущая или последняя должность (одна строка)
- summary: 2-3 предложения кто этот человек как специалист

Если какое-то поле не найдено — верни пустой список [] или пустую строку "".

Резюме:
\"\"\"
{raw_text[:4000]}
\"\"\"

JSON:"""

    response = await client.chat.completions.create(
        model="gpt-4.1-mini",
        temperature=0.0,
        messages=[{"role": "user", "content": prompt}]
    )

    raw_output = response.choices[0].message.content.strip()

    # Шаг 4: Парсим JSON, с fallback если GPT вернул что-то лишнее
    cv_data = _safe_parse_json(raw_output)
    cv_data["raw_text_preview"] = raw_text[:500]  # для дебага

    return cv_data


def _safe_parse_json(raw: str) -> dict:
    """
    Парсит JSON из ответа GPT.
    Обрабатывает случаи когда GPT добавил markdown-обёртку.
    """
    # Убрать ```json ... ``` если есть
    raw = re.sub(r'^```json\s*', '', raw, flags=re.MULTILINE)
    raw = re.sub(r'^```\s*', '', raw, flags=re.MULTILINE)
    raw = raw.strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Если всё равно не парсится — вернуть дефолт
        return _empty_cv()


def _empty_cv() -> dict:
    """Дефолтная структура если резюме не удалось распарсить."""
    return {
        "skills": [],
        "tech_stack": [],
        "years_experience": 0,
        "projects": [],
        "education": "",
        "languages": [],
        "current_role": "",
        "summary": "",
        "raw_text_preview": ""
    }


def format_cv_for_prompt(cv_data: dict) -> str:
    """
    Форматирует cv_data в строку для вставки в промпт LangGraph нод.
    Используется в question_generator и answer_evaluator.
    """
    lines = []

    if cv_data.get("current_role"):
        lines.append(f"Текущая роль: {cv_data['current_role']}")

    if cv_data.get("years_experience"):
        lines.append(f"Опыт: {cv_data['years_experience']} лет")

    if cv_data.get("tech_stack"):
        lines.append(f"Языки: {', '.join(cv_data['tech_stack'])}")

    if cv_data.get("skills"):
        lines.append(f"Навыки: {', '.join(cv_data['skills'][:10])}")  # топ-10

    if cv_data.get("projects"):
        projects_str = "; ".join(cv_data["projects"][:3])  # топ-3 проекта
        lines.append(f"Проекты: {projects_str}")

    if cv_data.get("education"):
        lines.append(f"Образование: {cv_data['education']}")

    return "\n".join(lines) if lines else "Данные резюме не доступны"