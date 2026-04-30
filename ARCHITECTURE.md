# Architecture

## Обзор

InterviewPilot AI — многошаговый LangGraph workflow с RAG и MCP интеграцией.

## Компоненты

- **Frontend** (Next.js) — загрузка резюме, выбор роли, интерфейс интервью
- **Backend** (FastAPI) — оркестрация, API роуты
- **MCP Server** — 3 тула: parse_resume, generate_questions, evaluate_answer
- **LangGraph** — workflow с ветвлением и циклами
- **ChromaDB** — векторная БД для RAG
- **LangSmith** — мониторинг всех LLM вызовов

## Путь одного запроса
Пользователь загружает PDF → POST /upload
parse_resume (MCP) → извлекает skills, stack, experience
question_generator (LangGraph нода) → RAG + generate_questions (MCP)
Пользователь отвечает (текст или голос → Whisper)
evaluate_answer (MCP) → score 0-10

score < 6 → follow_up вопрос → цикл обратно к evaluate_answer
score >= 6 → следующий вопрос


После всех вопросов → final_feedback (gpt-4.1)
Финальный отчёт → пользователь


## LangGraph граф
resume_parser → role_analyzer → question_generator
↓
answer_evaluator ←──────┐
↓               │
score < 6? → follow_up ─┘
↓
score >= 6? → next_question
↓
все вопросы? → final_feedback