from typing import TypedDict, Annotated
import operator


class InterviewState(TypedDict):
    # CV данные
    cv_data: dict
    role: str
    pdf_path: str
    interviewer_style: str

    # Вопросы
    questions: list[str]
    current_question_index: int
    current_question: str

    # Ответы и оценки
    current_answer: str
    current_score: dict
    all_scores: Annotated[list, operator.add]

    # Follow-up
    follow_up_count: int
    max_follow_ups: int

    # Hint (реакция на "не знаю")
    hint: str
    awaiting_retry: bool

    # Финал
    final_report: str
    is_complete: bool