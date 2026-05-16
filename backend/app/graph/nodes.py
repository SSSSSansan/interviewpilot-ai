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

# ── Личность интервьюера ──────────────────────────────────────────────
INTERVIEWER_PROMPTS = {
    "strict": (
        "Ты строгий технический интервьюер из крупной tech-компании. "
        "Краткие точные вопросы. Никаких похвал. Сразу переходи к сути. "
        "Если ответ слабый — говори прямо."
    ),
    "friendly": (
        "Ты дружелюбный CTO стартапа. Поддерживаешь кандидата, "
        "объясняешь зачем важен вопрос. Но стандарты не снижаешь. "
        "Используй разговорный тон."
    ),
    "academic": (
        "Ты академичный технический интервьюер. Просишь точные определения, "
        "ссылаешься на Computer Science принципы. "
        "Оцениваешь строгость формулировок и теоретическую базу."
    ),
}

def get_personality(style: str) -> str:
    return INTERVIEWER_PROMPTS.get(style, INTERVIEWER_PROMPTS["friendly"])


@traceable(name="resume_parser")
async def resume_parser(state: InterviewState) -> dict:
    import re
    pdf_path = state.get("pdf_path", "")

    if not pdf_path or not os.path.exists(pdf_path):
        return {
            "cv_data": {
                "name": "Кандидат",
                "skills": ["Python", "FastAPI", "PostgreSQL"],
                "tech_stack": ["Python", "FastAPI", "Docker", "PostgreSQL"],
                "years_experience": 2,
                "projects": ["E-commerce API на FastAPI", "Телеграм бот"],
                "languages": ["Python", "SQL"],
                "current_role": "",
                "education": "",
                "spoken_languages": [],
                "role_relevance": {
                    "Backend": 5, "Frontend": 5,
                    "ML": 5, "Data Analyst": 5, "PM": 5
                }
            }
        }

    try:
        import fitz
        doc = fitz.open(pdf_path)
        text = "".join(page.get_text() for page in doc)
        doc.close()
    except Exception as e:
        return {"cv_data": {"error": str(e)}}

    has_cyrillic = bool(re.search(r'[а-яёА-ЯЁ]', text))
    language_hint = (
        "Резюме написано на русском языке."
        if has_cyrillic
        else "The resume is in English."
    )

    max_chars = 1500 if DEV_MODE else 3500

    prompt = f"""Ты парсер резюме. {language_hint}
Извлеки данные из резюме ниже. Верни ТОЛЬКО валидный JSON без markdown и без комментариев.

Резюме:
{text[:max_chars]}

Формат ответа (все поля обязательны):
{{
  "name": "имя кандидата или пустая строка",
  "current_role": "текущая или последняя должность",
  "skills": ["фреймворки", "инструменты", "БД и т.д."],
  "tech_stack": ["языки программирования"],
  "years_experience": 0,
  "projects": ["краткое описание проекта одним предложением"],
  "education": "последнее образование одной строкой",
  "spoken_languages": ["разговорные языки: Русский, English и т.д."],
  "role_relevance": {{
    "Backend": 0, "Frontend": 0, "ML": 0, "Data Analyst": 0, "PM": 0
  }}
}}

Если поле не найдено — пустая строка "" или пустой список [].
role_relevance: от 0 до 10, насколько резюме подходит под каждую роль."""

    response = await fast_llm.ainvoke(prompt)

    try:
        raw = response.content.strip().replace("```json", "").replace("```", "").strip()
        cv_data = json.loads(raw)
    except json.JSONDecodeError:
        cv_data = {
            "name": "", "current_role": "", "skills": [], "tech_stack": [],
            "years_experience": 0, "projects": [], "education": "",
            "spoken_languages": [],
            "role_relevance": {"Backend": 5, "Frontend": 5, "ML": 5, "Data Analyst": 5, "PM": 5},
            "parse_error": True
        }

    return {"cv_data": cv_data}


@traceable(name="role_analyzer")
async def role_analyzer(state: InterviewState) -> dict:
    cv_data = state.get("cv_data", {})
    role = state.get("role", "Backend")
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
    style = state.get("interviewer_style", "friendly")
    personality = get_personality(style)
    n_questions = 3 if DEV_MODE else 5
    cv_summary = json.dumps(cv_data, ensure_ascii=False)[:600]

    prompt = f"""{personality}

Сгенерируй ровно {n_questions} вопроса для роли: {role}.
ВАЖНО: вопросы строго по специализации "{role}".

CV кандидата: {cv_summary}

Темы для роли {role}:
- Если ML Engineer: ML алгоритмы, обучение моделей, метрики, фреймворки
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
    role = state.get("role", "Backend")
    style = state.get("interviewer_style", "friendly")
    cv_data = state.get("cv_data", {})
    personality = get_personality(style)

    cv_context = ""
    if cv_data.get("tech_stack"):
        cv_context = f"Стек кандидата: {', '.join(cv_data['tech_stack'][:5])}"

    prompt = f"""{personality}
Роль кандидата: {role}. {cv_context}

Вопрос: {question}
Ответ кандидата: {answer}

Оцени ответ по 5 критериям (каждый строго 0, 1 или 2):
- technical_correctness: технически верно?
- clarity: понятно изложено?
- depth: достаточно глубоко?
- confidence: уверенно?
- communication: структурированно?

is_weak = true если сумма < 6.

ideal_answer — пример сильного ответа (3-5 предложений).
Как ответил бы опытный инженер с 3+ годами опыта.
Структура: суть → детали → пример.

Верни ТОЛЬКО валидный JSON без markdown:
{{
  "scores": {{"technical_correctness": 1, "clarity": 1, "depth": 1, "confidence": 1, "communication": 1}},
  "total_score": 5,
  "reasoning": "краткое объяснение оценки",
  "feedback": "конкретный фидбек 2-3 предложения",
  "ideal_answer": "пример сильного ответа 3-5 предложений",
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
        if not result.get("ideal_answer"):
            result["ideal_answer"] = ""
    except json.JSONDecodeError:
        result = {
            "scores": {"technical_correctness": 1, "clarity": 1, "depth": 1,
                       "confidence": 1, "communication": 1},
            "total_score": 5,
            "reasoning": "Ошибка парсинга",
            "feedback": "Попробуйте ответить подробнее",
            "ideal_answer": "",
            "is_weak": True,
        }

    return {
        "current_score": result,
        "all_scores": state.get("all_scores", []) + [result],
    }


@traceable(name="follow_up")
async def follow_up(state: InterviewState) -> dict:
    question = state.get("current_question", "")
    answer = state.get("current_answer", "")
    feedback = state.get("current_score", {}).get("feedback", "")
    follow_up_count = state.get("follow_up_count", 0)
    style = state.get("interviewer_style", "friendly")
    personality = get_personality(style)

    prompt = f"""{personality}

Кандидат слабо ответил. Задай один уточняющий вопрос.
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
        "follow_up_count": 0,
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


def is_dont_know(answer: str) -> bool:
    dont_know_phrases = [
        "не знаю", "незнаю", "не знаю как", "затрудняюсь",
        "skip", "пропустить", "не уверен", "не уверена",
        "i don't know", "idk", "хз", "понятия не имею",
        "не могу ответить", "pass", "не знаю ответа",
    ]
    cleaned = answer.strip().lower()
    return cleaned in dont_know_phrases or len(cleaned) < 4


@traceable(name="hint_node")
async def hint_node(state: InterviewState) -> dict:
    answer = state.get("current_answer", "")
    awaiting_retry = state.get("awaiting_retry", False)

    if awaiting_retry:
        return {"awaiting_retry": False, "hint": ""}

    if not is_dont_know(answer):
        return {"awaiting_retry": False, "hint": ""}

    question = state.get("current_question", "")
    style = state.get("interviewer_style", "friendly")

    style_instructions = {
        "strict": "Кратко и по делу. Без лишних слов.",
        "friendly": "Поддержи кандидата, скажи что ничего страшного и дай направление.",
        "academic": "Направь к теоретическим основам вопроса.",
    }

    prompt = f"""Ты технический интервьюер. Стиль: {style}. {style_instructions.get(style, '')}

Кандидат не знает ответа на вопрос: "{question}"

Дай подсказку которая:
- Направляет в правильную сторону, НО не раскрывает ответ
- Занимает 1-2 предложения максимум
- Заканчивается вопросом "Попробуешь ответить?"

Верни только текст подсказки, без пояснений и кавычек."""

    response = await fast_llm.ainvoke(prompt)
    return {
        "hint": response.content.strip(),
        "awaiting_retry": True,
        "current_answer": "",
    }