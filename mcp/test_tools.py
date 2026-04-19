import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

# импортируем функции напрямую
from mcp.server import Server  # noqa
# копируем функции из server.py для теста
import fitz
from openai import OpenAI
import json

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# вставь сюда функции _parse_resume, _generate_questions, _evaluate_answer из server.py
# или просто импортируй если они вынесены

async def test_evaluate():
    """Тест evaluate_answer — самый простой, не нужен PDF"""
    from mcp.server import _evaluate_answer  # если экспортированы

    result = await _evaluate_answer(
        question="Объясни разницу между REST и GraphQL",
        answer="REST использует фиксированные эндпоинты, GraphQL позволяет запрашивать только нужные поля"
    )
    print("✅ evaluate_answer:")
    print(json.dumps(result, ensure_ascii=False, indent=2))

asyncio.run(test_evaluate())