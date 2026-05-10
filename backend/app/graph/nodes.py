import os
import json
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from langchain_openai import ChatOpenAI
from langsmith import traceable
from dotenv import load_dotenv
load_dotenv()

from app.graph.state import InterviewState

DEV_MODE = os.getenv("DEV_MODE", "true").lower() == "true"
FAST_MODEL = "gpt-4o-mini"
SMART_MODEL = "gpt-4o-mini" if DEV_MODE else "gpt-4.1"

fast_llm = ChatOpenAI(model=FAST_MODEL, temperature=0.7)
eval_llm = ChatOpenAI(model=FAST_MODEL, temperature=0.2)
smart_llm = ChatOpenAI(model=SMART_MODEL, temperature=0.3)


@traceable(name="resume_parser")
async def resume_parser(state: InterviewState) -> dict:
    pdf_path = state.get("pdf_path", "")

    if not pdf_path or not os.path.exists(pdf_path):
        return {
            "cv_data": {
                "name": "Test Candidate",
                "skills": ["Python", "FastAPI", "PostgreSQL"],
                "tech_stack": ["Python", "FastAPI", "Docker", "PostgreSQL"],
                "years_experience": 2,
                "projects": ["E-commerce API на FastAPI", "Телеграм бот"],
                "languages": ["Python", "SQL"],
                # ФИX БАГ 1: убрали перекос в сторону Backend
                "role_relevance": {"Backend": 5, "Frontend": 5, "ML": 5, "Data Analyst": 5, "PM": 5}
            }
        }

    try:
        import fitz
        doc = fitz.open(pdf_path)
        text = "".join(page.get_text() for page in doc)
        doc.close()
    except Exception as e:
        return {"cv_data": {"error": str(e)}}

    max_chars = 1500 if DEV_MODE else 3500
    prompt = f"""Извлеки данные из резюме. Верни ТОЛЬКО JSON без markdown.

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

    response = await fast_llm.ainvoke(prompt)
    try:
        raw = response.content.strip().replace("```json", "").replace("```", "")
        return {"cv_data": json.loads(raw)}
    except json.JSONDecodeError:
        return {"cv_data": {"raw": response.content, "parse_error": True}}


@traceable(name="role_analyzer")
async def role_analyzer(state: InterviewState) -> dict:
    cv_data = state.get("cv_data", {})
    role = state.get("role", "Backend")

    # ФИX БАГ 1: убрали логику перезаписи роли — уважаем выбор пользователя
    # role_analyzer теперь просто подтверждает роль без подмены
    return {"role": role, "cv_data": cv_data}


@traceable(name="question_generator")
async def question_generator(state: InterviewState) -> dict:
    existing_questions = state.get("questions", [])
    current_index = state.get("current_question_index", 0)

    if existing_questions:
        return {
            "questions": existing_questions,
            "current_question": existing_questions[current_index],
            "current_question_index": current_index,
        }

    cv_data = state.get("cv_data", {})
    role = state.get("role", "Backend")
    n_questions = 3 if DEV_MODE else 5
    cv_summary = json.dumps(cv_data, ensure_ascii=False)[:600]

    # ФИX БАГ 1: роль явно передаётся в промпт и подчёркивается
    prompt = f"""Ты технический интервьюер. Сгенерируй ровно {n_questions} вопроса ТОЛЬКО для роли: {role}.

ВАЖНО: вопросы должны быть строго по специализации "{role}". 
Не задавай вопросы по другим ролям.

CV кандидата: {cv_summary}

Примеры тем для роли {role}:
- Если ML Engineer: ML алгоритмы, обучение моделей, метрики, фреймворки (PyTorch/TensorFlow/sklearn)
- Если Frontend Engineer: React/Vue, CSS, браузерные API, производительность
- Если Backend Engineer: API, БД, архитектура сервисов, кэширование
- Если Data Analyst: SQL, статистика, визуализация, A/B тесты
- Если Product Manager: приоритизация, метрики, работа с командой

Верни ТОЛЬКО JSON массив без markdown, ровно {n_questions} элемента:
["вопрос 1", "вопрос 2", "вопрос 3"]"""

    response = await fast_llm.ainvoke(prompt)
    try:
        raw = response.content.strip().replace("```json", "").replace("```", "")
        questions = json.loads(raw)
    except json.JSONDecodeError:
        questions = [
            f"Расскажи о своём опыте в области {role}?",
            f"Какие инструменты ты используешь как {role}?",
            f"Опиши самый сложный проект в роли {role}?",
        ]

    return {
        "questions": questions,
        "current_question_index": 0,
        "current_question": questions[0],
        "follow_up_count": 0,
        "is_complete": False,
    }


@traceable(name="answer_evaluator")
async def answer_evaluator(state: InterviewState) -> dict:
    question = state.get("current_question", "")
    answer = state.get("current_answer", "")

    prompt = f"""Оцени ответ кандидата. Каждый критерий строго 0, 1 или 2 (не больше!).

Вопрос: {question}
Ответ: {answer}

Критерии (только 0, 1 или 2):
- technical_correctness
- clarity
- depth
- confidence
- communication

is_weak = true если сумма < 6.

Верни ТОЛЬКО JSON без markdown:
{{
  "scores": {{"technical_correctness": 1, "clarity": 1, "depth": 1, "confidence": 1, "communication": 1}},
  "total_score": 5,
  "reasoning": "объяснение",
  "feedback": "рекомендации",
  "is_weak": true
}}"""

    response = await eval_llm.ainvoke(prompt)
    try:
        raw = response.content.strip().replace("```json", "").replace("```", "")
        result = json.loads(raw)
        for k in result["scores"]:
            result["scores"][k] = max(0, min(2, int(result["scores"][k])))
        result["total_score"] = sum(result["scores"].values())
        result["is_weak"] = result["total_score"] < 6
    except json.JSONDecodeError:
        result = {
            "scores": {"technical_correctness": 1, "clarity": 1, "depth": 1, "confidence": 1, "communication": 1},
            "total_score": 5,
            "reasoning": "Ошибка парсинга",
            "feedback": "Попробуйте ответить подробнее",
            "is_weak": True,
        }

    return {
    "current_score": result,
    "all_scores": [result],
    }


@traceable(name="follow_up")
async def follow_up(state: InterviewState) -> dict:
    question = state.get("current_question", "")
    answer = state.get("current_answer", "")
    feedback = state.get("current_score", {}).get("feedback", "")
    follow_up_count = state.get("follow_up_count", 0)

    prompt = f"""Кандидат слабо ответил. Задай один уточняющий вопрос.

Исходный вопрос: {question}
Ответ: {answer}
Что не так: {feedback}

Верни ТОЛЬКО текст вопроса."""

    response = await fast_llm.ainvoke(prompt)

    return {
        "current_question": response.content.strip(),
        "current_answer": "",
        "follow_up_count": follow_up_count + 1,
    }


@traceable(name="next_question")
async def next_question(state: InterviewState) -> dict:
    questions = state.get("questions", [])
    current_index = state.get("current_question_index", 0)
    next_index = current_index + 1

    if next_index >= len(questions):
        return {
            "is_complete": True,
            "current_question_index": next_index,
            "current_question": "",
        }

    return {
        "current_question_index": next_index,
        "current_question": questions[next_index],
        "current_answer": "",
        "follow_up_count": 0,  # ФИX БАГ 3: сбрасываем счётчик follow_up для нового вопроса
        "is_complete": False,
    }


@traceable(name="final_feedback")
async def final_feedback(state: InterviewState) -> dict:
    all_scores = state.get("all_scores", [])
    role = state.get("role", "")
    cv_data = state.get("cv_data", {})
    questions = state.get("questions", [])

    if not all_scores:
        return {"final_report": "Нет данных для отчёта."}

    total_avg = sum(s.get("total_score", 0) for s in all_scores) / len(all_scores)
    feedbacks = [s.get("feedback", "") for s in all_scores if s.get("feedback")]

    prompt = f"""Напиши финальный отчёт по итогам технического интервью.

Роль: {role}
Кандидат: {cv_data.get("name", "Кандидат")}
Средний балл: {total_avg:.1f}/10
Вопросов задано: {len(questions)}

Фидбэк по ответам:
{chr(10).join(f"- {f}" for f in feedbacks)}

Структура:
1. Общая оценка
2. Сильные стороны (2-3 пункта)
3. Зоны роста (2-3 пункта)
4. Рекомендация: Hire / No Hire / Maybe

Пиши по-русски, конкретно."""

    response = await smart_llm.ainvoke(prompt)
    return {"final_report": response.content}