from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from app.graph.state import InterviewState
from app.graph.nodes import (
    resume_parser, role_analyzer, question_generator,
    answer_evaluator, follow_up, next_question, final_feedback,
)


def should_follow_up(state: InterviewState) -> str:
    score = state.get("current_score", {})
    follow_up_count = state.get("follow_up_count", 0)
    max_follow_ups = state.get("max_follow_ups", 2)
    if score.get("is_weak") and follow_up_count < max_follow_ups:
        return "follow_up"
    return "next_question"


def should_continue(state: InterviewState) -> str:
    if state.get("is_complete"):
        return "final_feedback"
    return "question_generator"


def build_graph():
    graph = StateGraph(InterviewState)

    graph.add_node("resume_parser", resume_parser)
    graph.add_node("role_analyzer", role_analyzer)
    graph.add_node("question_generator", question_generator)
    graph.add_node("answer_evaluator", answer_evaluator)
    graph.add_node("follow_up", follow_up)
    graph.add_node("next_question", next_question)
    graph.add_node("final_feedback", final_feedback)

    graph.set_entry_point("resume_parser")
    graph.add_edge("resume_parser", "role_analyzer")
    graph.add_edge("role_analyzer", "question_generator")
    graph.add_edge("question_generator", "answer_evaluator")

    graph.add_conditional_edges(
        "answer_evaluator",
        should_follow_up,
        {"follow_up": "follow_up", "next_question": "next_question"}
    )
    graph.add_edge("follow_up", "answer_evaluator")

    graph.add_conditional_edges(
        "next_question",
        should_continue,
        {"final_feedback": "final_feedback", "question_generator": "question_generator"}
    )
    graph.add_edge("final_feedback", END)

    checkpointer = MemorySaver()
    # interrupt_before answer_evaluator — граф останавливается и ждёт ответа
    return graph.compile(
        checkpointer=checkpointer,
        interrupt_before=["answer_evaluator"],
    )


interview_graph = build_graph()