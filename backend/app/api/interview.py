from fastapi import APIRouter
from pydantic import BaseModel
from app.graph.graph import interview_graph
import uuid

router = APIRouter(prefix="/interview", tags=["interview"])


class StartRequest(BaseModel):
    role: str = "Backend"
    pdf_path: str = ""


class AnswerRequest(BaseModel):
    thread_id: str
    answer: str


@router.post("/start")
async def start_interview(req: StartRequest):
    """Запускает интервью — останавливается перед первым answer_evaluator."""
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 50}

    initial_state = {
        "pdf_path": req.pdf_path,
        "role": req.role,
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

    return {
        "thread_id": thread_id,
        "question": state["current_question"],
        "question_number": state["current_question_index"] + 1,
        "total_questions": len(state["questions"]),
    }


@router.post("/answer")
async def submit_answer(req: AnswerRequest):
    """Принимает ответ, продолжает граф, возвращает следующий вопрос или отчёт."""
    config = {"configurable": {"thread_id": req.thread_id}, "recursion_limit": 50}

    # обновляем ответ в состоянии
    await interview_graph.aupdate_state(
        config,
        {"current_answer": req.answer},
    )

    # продолжаем граф с того места где остановились
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