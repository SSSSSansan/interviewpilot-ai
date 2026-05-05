import sys
import os
import json
import asyncio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
import fitz
from openai import OpenAI
from dotenv import load_dotenv

# ▼▼▼ ДОБАВИТЬ: импорт RAG сервиса ▼▼▼
from backend.app.services.rag_service import retrieve_context
# ▲▲▲ конец добавления ▲▲▲

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

DEV_MODE = os.getenv("DEV_MODE", "true").lower() == "true"
FAST_MODEL = "gpt-4o-mini"
SMART_MODEL = "gpt-4o-mini" if DEV_MODE else "gpt-4.1"

server = Server("interviewpilot")


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="parse_resume",
            description="Извлекает навыки, стек, опыт и проекты из PDF резюме",
            inputSchema={
                "type": "object",
                "properties": {
                    "pdf_path": {"type": "string"}
                },
                "required": ["pdf_path"]
            }
        ),
        Tool(
            name="generate_questions",
            description="Генерирует вопросы для собеседования на основе CV и роли",
            inputSchema={
                "type": "object",
                "properties": {
                    "role": {"type": "string"},
                    "cv_context": {"type": "object"},
                    "rag_context": {"type": "string", "default": ""}
                },
                "required": ["role", "cv_context"]
            }
        ),
        Tool(
            name="evaluate_answer",
            description="Оценивает ответ кандидата, возвращает score 0-10 и feedback",
            inputSchema={
                "type": "object",
                "properties": {
                    "question": {"type": "string"},
                    "answer": {"type": "string"}
                },
                "required": ["question", "answer"]
            }
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "parse_resume":
        result = await _parse_resume(arguments["pdf_path"])
    elif name == "generate_questions":
        result = await _generate_questions(
            arguments["role"],
            arguments["cv_context"],
            arguments.get("rag_context", "")
        )
    elif name == "evaluate_answer":
        result = await _evaluate_answer(
            arguments["question"],
            arguments["answer"]
        )
    else:
        result = {"error": f"Unknown tool: {name}"}

    return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False))]


async def _parse_resume(pdf_path: str) -> dict:
    try:
        doc = fitz.open(pdf_path)
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
    except Exception as e:
        return {"error": f"Не удалось открыть PDF: {str(e)}"}

    max_chars = 1500 if DEV_MODE else 3500

    prompt = f"""Извлеки данные из резюме. Верни ТОЛЬКО JSON, без markdown.

Резюме:
{text[:max_chars]}

Формат:
{{
  "name": "имя",
  "skills": ["навык"],
  "tech_stack": ["технология"],
  "years_experience": 0,
  "projects": ["проект"],
  "languages": ["язык"],
  "role_relevance": {{"Backend": 0, "Frontend": 0, "ML": 0, "Data Analyst": 0, "PM": 0}}
}}"""

    r = client.chat.completions.create(
        model=FAST_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=400 if DEV_MODE else 800,
    )
    try:
        raw = r.choices[0].message.content.strip().replace("```json", "").replace("```", "")
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"raw_text": r.choices[0].message.content, "parse_error": True}


async def _generate_questions(role: str, cv_context: dict, rag_context: str = "") -> list[str]:
    n_questions = 3 if DEV_MODE else 5
    cv_summary = json.dumps(cv_context, ensure_ascii=False)[:800]

    # ▼▼▼ ИЗМЕНИТЬ: если rag_context не передан — достаём сами ▼▼▼
    if not rag_context:
        skills_query = ", ".join(cv_context.get("skills", [])[:5])
        rag_context = retrieve_context(
            query=f"вопросы для {role}, навыки: {skills_query}",
            role=role,
            top_k=3
        )
    # ▲▲▲ конец изменения ▲▲▲

    rag_section = f"\nКонтекст из базы знаний:\n{rag_context[:500]}" if rag_context else ""

    prompt = f"""Ты технический интервьюер. Сгенерируй {n_questions} вопроса.

Роль: {role}
CV: {cv_summary}{rag_section}

Верни ТОЛЬКО JSON массив без markdown:
["вопрос 1", "вопрос 2", "вопрос 3"]"""

    r = client.chat.completions.create(
        model=FAST_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=300 if DEV_MODE else 600,
    )
    try:
        raw = r.choices[0].message.content.strip().replace("```json", "").replace("```", "")
        return json.loads(raw)
    except json.JSONDecodeError:
        return [r.choices[0].message.content]


async def _evaluate_answer(question: str, answer: str) -> dict:
    prompt = f"""Оцени ответ кандидата. Каждый критерий строго от 0 до 2 (не больше!).

Вопрос: {question}
Ответ: {answer}

Критерии (0, 1 или 2 — только эти значения):
- technical_correctness: фактическая точность
- clarity: понятность
- depth: глубина
- confidence: структура и уверенность
- communication: качество коммуникации

Итого максимум = 10 (5 критериев × 2).
is_weak = true если total_score < 6.

Верни ТОЛЬКО JSON без markdown:
{{
  "scores": {{
    "technical_correctness": 1,
    "clarity": 1,
    "depth": 1,
    "confidence": 1,
    "communication": 1
  }},
  "total_score": 5,
  "reasoning": "краткое объяснение",
  "feedback": "конкретные рекомендации",
  "is_weak": true
}}"""

    r = client.chat.completions.create(
        model=FAST_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=250 if DEV_MODE else 400,
    )
    try:
        raw = r.choices[0].message.content.strip().replace("```json", "").replace("```", "")
        result = json.loads(raw)
        scores = result["scores"]
        for k in scores:
            scores[k] = max(0, min(2, int(scores[k])))
        result["total_score"] = sum(scores.values())
        result["is_weak"] = result["total_score"] < 6
        return result
    except json.JSONDecodeError:
        return {"raw": r.choices[0].message.content, "parse_error": True}


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())