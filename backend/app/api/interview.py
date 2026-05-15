from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pydantic import BaseModel
from app.graph.graph import interview_graph
import uuid
import os
import tempfile

router = APIRouter(prefix="/interview", tags=["interview"])


class AnswerRequest(BaseModel):
    thread_id: str
    answer: str


# ─── POST /interview/start ────────────────────────────────────────────

@router.post("/start")
async def start_interview(
    role: str = Form(...),
    interviewer_style: str = Form(default="friendly"),
    resume_pdf: UploadFile = File(default=None),
):
    """
    Запускает интервью.
    Принимает PDF резюме (опционально), роль и стиль интервьюера.
    Останавливается перед первым вопросом и возвращает его.
    """

    # Валидация роли
    allowed_roles = ["Backend", "Frontend", "ML", "Data Analyst", "PM",
                     "Backend Engineer", "Frontend Engineer", "ML Engineer"]
    if role not in allowed_roles:
        raise HTTPException(
            status_code=400,
            detail=f"Роль должна быть одной из: {allowed_roles}"
        )

    # Валидация стиля
    allowed_styles = ["strict", "friendly", "academic"]
    if interviewer_style not in allowed_styles:
        interviewer_style = "friendly"

    # Сохраняем PDF во временный файл
    pdf_path = ""
    tmp_file = None

    if resume_pdf and resume_pdf.filename:
        if not resume_pdf.filename.endswith(".pdf"):
            raise HTTPException(
                status_code=400,
                detail="Только PDF файлы поддерживаются"
            )

        pdf_bytes = await resume_pdf.read()

        # Сохраняем во временный файл
        # (LangGraph нода resume_parser берёт путь из state)
        tmp_file = tempfile.NamedTemporaryFile(
            delete=False,
            suffix=".pdf",
            prefix="resume_"
        )
        tmp_file.write(pdf_bytes)
        tmp_file.close()
        pdf_path = tmp_file.name

    # Запускаем граф
    thread_id = str(uuid.uuid4())
    config = {
        "configurable": {"thread_id": thread_id},
        "recursion_limit": 50
    }

    initial_state = {
        "pdf_path": pdf_path,
        "role": role,
        "interviewer_style": interviewer_style,
        "questions": [],
        "current_question_index": 0,
        "current_question": "",
        "current_answer": "",
        "current_score": {},
        "all_scores": [],
        "follow_up_count": 0,
        "max_follow_ups": 2,
        "final_report": "",
        "is_complete": False,
        "cv_data": {},
    }

    state = await interview_graph.ainvoke(initial_state, config=config)

    # Удаляем временный файл после парсинга
    if pdf_path and os.path.exists(pdf_path):
        try:
            os.unlink(pdf_path)
        except Exception:
            pass  # не критично если не удалилось

    # Формируем приветствие под стиль интервьюера
    intros = {
        "strict": f"Начнём. Вы претендуете на роль {role}.",
        "friendly": f"Привет! Рад познакомиться. Ты претендуешь на роль {role} — отлично, начнём!",
        "academic": f"Добро пожаловать. Проведём структурированное интервью на позицию {role}."
    }

    # Инфо о том что нашли в резюме (для фронтенда)
    cv_data = state.get("cv_data", {})
    cv_summary = {
        "name": cv_data.get("name", ""),
        "current_role": cv_data.get("current_role", ""),
        "tech_stack": cv_data.get("tech_stack", []),
        "skills_count": len(cv_data.get("skills", [])),
        "years_experience": cv_data.get("years_experience", 0),
        "parse_error": cv_data.get("parse_error", False),
    }

    return {
        "thread_id": thread_id,
        "interviewer_intro": intros[interviewer_style],
        "cv_parsed": cv_summary,
        "question": state["current_question"],
        "question_number": state["current_question_index"] + 1,
        "total_questions": len(state["questions"]),
    }


# ─── POST /interview/answer ───────────────────────────────────────────

@router.post("/answer")
async def submit_answer(req: AnswerRequest):
    """
    Принимает ответ пользователя.
    Продолжает граф, возвращает следующий вопрос или финальный отчёт.
    """
    config = {
        "configurable": {"thread_id": req.thread_id},
        "recursion_limit": 50
    }

    # Обновляем ответ в состоянии графа
    await interview_graph.aupdate_state(
        config,
        {"current_answer": req.answer},
    )

    # Продолжаем граф с того места где остановились
    state = await interview_graph.ainvoke(None, config=config)

    if state.get("final_report"):
        return {
            "is_complete": True,
            "final_report": state["final_report"],
            "all_scores": state["all_scores"],
        }

    return {
        "is_complete": False,
        "question": state["current_question"],
        "question_number": state["current_question_index"] + 1,
        "total_questions": len(state["questions"]),
        "last_score": state.get("current_score", {}),
    }