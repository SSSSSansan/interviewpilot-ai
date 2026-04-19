from fastapi import APIRouter
from langchain_openai import ChatOpenAI
from langsmith import traceable
import os

router = APIRouter()


@router.get("/health")
async def health_check():
    return {"status": "ok", "service": "interviewpilot-api"}


@router.get("/health/llm")
async def health_llm_check():
    """Тестовый вызов LLM — должен появиться в LangSmith дашборде"""
    result = await _test_llm_call()
    return {"status": "ok", "llm_response": result}


@traceable(name="test-llm-call")
async def _test_llm_call() -> str:
    llm = ChatOpenAI(
        model="gpt-4.1-mini",
        temperature=0.2,
        api_key=os.getenv("OPENAI_API_KEY"),
    )
    response = await llm.ainvoke("Say 'InterviewPilot is alive!' in one sentence.")
    return response.content