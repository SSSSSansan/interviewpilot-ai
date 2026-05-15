from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
import uuid

from app.services.resume_parser import parse_resume_pdf, format_cv_for_prompt

router = APIRouter()

# Временное хранилище сессий в памяти (для MVP)
# В продакшене заменить на Redis или БД
sessions: dict = {}


# ─── Модели запросов ────────────────────────────────────────────────

class AnswerRequest(BaseModel):
    session_id: str
    answer: str


# ─── POST /session/start ─────────────────────────────────────────────

@router.post("/session/start")
async def start_session(
    resume_pdf: UploadFile = File(...),
    role: str = Form(...),
    interviewer_style: str = Form(default="friendly")
):
    """
    Принимает PDF резюме, роль и стиль интервьюера.
    Парсит CV, инициализирует граф, возвращает первый вопрос.
    """

    # Валидация файла
    if not resume_pdf.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Только PDF файлы поддерживаются")

    # Валидация роли
    allowed_roles = ["Backend Engineer", "Frontend Engineer", "ML Engineer", "Data Analyst", "Product Manager"]
    if role not in allowed_roles:
        raise HTTPException(status_code=400, detail=f"Роль должна быть одной из: {allowed_roles}")

    # Валидация стиля интервьюера
    allowed_styles = ["strict", "friendly", "academic"]
    if interviewer_style not in allowed_styles:
        interviewer_style = "friendly"

    # Читаем PDF
    pdf_bytes = await resume_pdf.read()

    # Парсим резюме
    try:
        cv_data = await parse_resume_pdf(pdf_bytes)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка парсинга резюме: {str(e)}")

    # Форматируем CV для промптов
    cv_summary = format_cv_for_prompt(cv_data)

    # Генерируем вопросы через LangGraph
    # TODO: заменить на вызов графа когда он готов
    # Пока используем прямой вызов для тестирования парсера
    from openai import AsyncOpenAI
    from app.services.resume_parser import format_cv_for_prompt

    openai_client = AsyncOpenAI()

    questions_response = await openai_client.chat.completions.create(
        model="gpt-4.1-mini",
        temperature=0.7,
        messages=[{
            "role": "user",
            "content": f"""Ты технический интервьюер. Роль кандидата: {role}.

Данные резюме кандидата:
{cv_summary}

Сгенерируй 6 вопросов для технического интервью.
Требования:
- 4 технических вопроса по стеку кандидата и роли
- 2 behavioral вопроса (расскажи о проекте, сложной ситуации)
- Вопросы должны быть конкретными, не generic
- Если в резюме есть конкретные технологии — спроси именно про них

Верни ТОЛЬКО JSON массив строк, без markdown:
["вопрос 1", "вопрос 2", "вопрос 3", "вопрос 4", "вопрос 5", "вопрос 6"]"""
        }]
    )

    import json, re
    raw_questions = questions_response.choices[0].message.content.strip()
    raw_questions = re.sub(r'^```json\s*', '', raw_questions, flags=re.MULTILINE)
    raw_questions = re.sub(r'^```\s*', '', raw_questions, flags=re.MULTILINE)
    questions = json.loads(raw_questions.strip())

    # Приветствие интервьюера под стиль
    intros = {
        "strict": f"Начнём. Вы претендуете на роль {role}. Первый вопрос:",
        "friendly": f"Привет! Рад познакомиться. Ты претендуешь на роль {role} — отлично. Начнём с первого вопроса:",
        "academic": f"Добро пожаловать. Сегодня мы проведём структурированное интервью на позицию {role}. Приступим:"
    }

    # Создаём сессию
    session_id = str(uuid.uuid4())
    sessions[session_id] = {
        "cv_data": cv_data,
        "cv_summary": cv_summary,
        "role": role,
        "interviewer_style": interviewer_style,
        "questions": questions,
        "current_question_idx": 0,
        "scores": [],
        "follow_up_count": 0,
        "awaiting_retry": False,
    }

    return {
        "session_id": session_id,
        "cv_parsed": {
            "skills_found": len(cv_data.get("skills", [])),
            "tech_stack": cv_data.get("tech_stack", []),
            "years_experience": cv_data.get("years_experience", 0),
            "current_role": cv_data.get("current_role", "")
        },
        "interviewer_intro": intros[interviewer_style],
        "first_question": questions[0],
        "total_questions": len(questions)
    }


# ─── POST /session/answer ────────────────────────────────────────────

@router.post("/session/answer")
async def submit_answer(body: AnswerRequest):
    """
    Принимает ответ пользователя.
    Возвращает feedback, score, ideal_answer и следующий вопрос (или hint).
    """
    session = sessions.get(body.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Сессия не найдена")

    answer = body.answer.strip()
    current_question = session["questions"][session["current_question_idx"]]

    # Проверяем "не знаю"
    dont_know_phrases = [
        "не знаю", "не знаю как", "затрудняюсь", "skip", "пропустить",
        "не уверен", "i don't know", "idk", "хз", "понятия не имею",
        "не могу ответить", "pass"
    ]
    is_dont_know = answer.lower() in dont_know_phrases or len(answer) < 5

    if is_dont_know and not session.get("awaiting_retry"):
        # Генерируем hint
        hint = await _generate_hint(
            question=current_question,
            role=session["role"],
            style=session["interviewer_style"]
        )
        session["awaiting_retry"] = True
        return {
            "type": "hint",
            "hint": hint,
            "feedback": None,
            "score": None,
            "ideal_answer": None,
            "next_question": None,
            "is_complete": False
        }

    # Сбрасываем флаг retry
    session["awaiting_retry"] = False

    # Оцениваем ответ
    evaluation = await _evaluate_answer(
        question=current_question,
        answer=answer,
        role=session["role"],
        cv_summary=session["cv_summary"]
    )

    score = evaluation.get("score", 5)
    session["scores"].append({
        "question": current_question,
        "answer": answer,
        "score": score,
        "feedback": evaluation.get("feedback", ""),
    })

    # Follow-up если ответ слабый
    if score < 6 and session["follow_up_count"] < 2:
        session["follow_up_count"] += 1
        follow_up = await _generate_follow_up(
            question=current_question,
            answer=answer,
            feedback=evaluation.get("feedback", ""),
            style=session["interviewer_style"]
        )
        return {
            "type": "follow_up",
            "hint": None,
            "feedback": evaluation.get("feedback"),
            "score": score,
            "ideal_answer": evaluation.get("ideal_answer"),
            "next_question": follow_up,
            "is_complete": False
        }

    # Переходим к следующему вопросу
    session["follow_up_count"] = 0
    session["current_question_idx"] += 1

    if session["current_question_idx"] >= len(session["questions"]):
        # Интервью завершено — генерируем финальный отчёт
        report = await _generate_final_report(
            scores=session["scores"],
            role=session["role"],
            cv_summary=session["cv_summary"]
        )
        sessions[body.session_id]["final_report"] = report
        return {
            "type": "complete",
            "hint": None,
            "feedback": evaluation.get("feedback"),
            "score": score,
            "ideal_answer": evaluation.get("ideal_answer"),
            "next_question": None,
            "is_complete": True,
            "report": report
        }

    next_q = session["questions"][session["current_question_idx"]]
    return {
        "type": "feedback",
        "hint": None,
        "feedback": evaluation.get("feedback"),
        "score": score,
        "ideal_answer": evaluation.get("ideal_answer"),
        "next_question": next_q,
        "is_complete": False
    }


# ─── GET /session/{session_id}/report ────────────────────────────────

@router.get("/session/{session_id}/report")
async def get_report(session_id: str):
    session = sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Сессия не найдена")
    report = session.get("final_report")
    if not report:
        raise HTTPException(status_code=400, detail="Интервью ещё не завершено")
    return report


# ─── Вспомогательные функции ─────────────────────────────────────────

async def _evaluate_answer(question: str, answer: str, role: str, cv_summary: str) -> dict:
    from openai import AsyncOpenAI
    import json, re

    openai_client = AsyncOpenAI()

    prompt = f"""Ты строгий технический интервьюер. Роль кандидата: {role}.

Контекст резюме кандидата:
{cv_summary}

Вопрос: {question}
Ответ кандидата: {answer}

Оцени ответ по 5 критериям (0-2 балла каждый) и верни ТОЛЬКО JSON без markdown:

{{
  "score": <сумма всех критериев, 0-10>,
  "technical_correctness": <0-2>,
  "clarity": <0-2>,
  "depth": <0-2>,
  "confidence": <0-2>,
  "communication": <0-2>,
  "feedback": "<конкретный фидбек 2-3 предложения, что хорошо и что улучшить>",
  "ideal_answer": "<пример сильного ответа 3-5 предложений, как ответил бы опытный инженер>",
  "is_weak": <true если score < 6, иначе false>
}}

Будь конкретным. Ideal_answer должен содержать правильные термины и структуру."""

    response = await openai_client.chat.completions.create(
        model="gpt-4.1-mini",
        temperature=0.2,
        messages=[{"role": "user", "content": prompt}]
    )

    raw = response.choices[0].message.content.strip()
    raw = re.sub(r'^```json\s*', '', raw, flags=re.MULTILINE)
    raw = re.sub(r'^```\s*', '', raw, flags=re.MULTILINE)

    try:
        return json.loads(raw.strip())
    except:
        return {
            "score": 5,
            "feedback": "Ответ получен.",
            "ideal_answer": "Не удалось сгенерировать эталонный ответ.",
            "is_weak": False
        }


async def _generate_hint(question: str, role: str, style: str) -> str:
    from openai import AsyncOpenAI

    openai_client = AsyncOpenAI()

    style_instructions = {
        "strict": "Кратко и по делу. Без лишних слов.",
        "friendly": "Поддержи кандидата, скажи что ничего страшного, дай направление.",
        "academic": "Направь к теоретическим основам вопроса."
    }

    prompt = f"""Ты технический интервьюер ({style} стиль). {style_instructions.get(style, '')}
Кандидат не знает ответа на вопрос: "{question}"

Дай подсказку которая:
- Направляет в правильную сторону, НО не раскрывает ответ
- Занимает 1-2 предложения
- Заканчивается вопросом "Попробуешь ответить?"

Верни только текст подсказки, без пояснений."""

    response = await openai_client.chat.completions.create(
        model="gpt-4.1-mini",
        temperature=0.5,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content.strip()


async def _generate_follow_up(question: str, answer: str, feedback: str, style: str) -> str:
    from openai import AsyncOpenAI

    openai_client = AsyncOpenAI()

    prompt = f"""Ты технический интервьюер ({style} стиль).
Кандидат ответил слабо на вопрос: "{question}"
Его ответ: "{answer}"
Твой фидбек: "{feedback}"

Задай уточняющий follow-up вопрос который:
- Даёт шанс раскрыть тему глубже
- Конкретный, не общий
- 1 предложение

Верни только текст вопроса."""

    response = await openai_client.chat.completions.create(
        model="gpt-4.1-mini",
        temperature=0.5,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content.strip()


async def _generate_final_report(scores: list, role: str, cv_summary: str) -> dict:
    from openai import AsyncOpenAI
    import json, re

    openai_client = AsyncOpenAI()

    scores_text = "\n".join([
        f"Q: {s['question']}\nA: {s['answer']}\nScore: {s['score']}/10\nFeedback: {s['feedback']}"
        for s in scores
    ])

    avg_score = sum(s["score"] for s in scores) / len(scores) if scores else 0

    prompt = f"""Ты опытный технический интервьюер. Роль кандидата: {role}.

Резюме кандидата:
{cv_summary}

Результаты интервью:
{scores_text}

Средний балл: {avg_score:.1f}/10

Составь финальный отчёт. Верни ТОЛЬКО JSON без markdown:
{{
  "overall_score": {avg_score:.1f},
  "verdict": "<одна строка: нанять / на следующий этап / отказать>",
  "summary": "<2-3 предложения общего впечатления>",
  "strengths": ["<сила 1>", "<сила 2>", "<сила 3>"],
  "weaknesses": ["<слабость 1>", "<слабость 2>"],
  "roadmap": [
    {{"topic": "<тема для изучения>", "resource": "<конкретный ресурс или тип ресурса>"}},
    {{"topic": "<тема 2>", "resource": "<ресурс 2>"}},
    {{"topic": "<тема 3>", "resource": "<ресурс 3>"}}
  ]
}}"""

    response = await openai_client.chat.completions.create(
        model="gpt-4.1",
        temperature=0.3,
        messages=[{"role": "user", "content": prompt}]
    )

    raw = response.choices[0].message.content.strip()
    raw = re.sub(r'^```json\s*', '', raw, flags=re.MULTILINE)
    raw = re.sub(r'^```\s*', '', raw, flags=re.MULTILINE)

    try:
        return json.loads(raw.strip())
    except:
        return {
            "overall_score": avg_score,
            "verdict": "Требует дополнительной оценки",
            "summary": "Интервью завершено.",
            "strengths": [],
            "weaknesses": [],
            "roadmap": []
        }