# InterviewPilot AI

AI-powered платформа для подготовки к техническим собеседованиям.

## Что умеет

- Загрузка резюме (PDF) и выбор целевой роли
- Персонализированные вопросы на основе CV через RAG
- Оценка ответов по структурированной рубрике
- Follow-up вопросы при слабых ответах
- Финальный отчёт с рекомендациями
- Голосовой режим (Whisper)

## Стек

| Слой | Технология |
|---|---|
| Frontend | Next.js, TypeScript, Tailwind CSS |
| Backend | FastAPI, Python 3.11 |
| LLM Orchestration | LangGraph |
| LLM Provider | OpenAI API |
| Векторная БД | ChromaDB |
| Мониторинг | LangSmith |

## Запуск

### Через Docker (рекомендуется)

```bash
cp .env.example .env
# заполни .env своими ключами

docker compose up --build
```

- Backend: http://localhost:8000
- ChromaDB: http://localhost:8001
- API docs: http://localhost:8000/docs

### Локально

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

## Проверка LangSmith

После запуска открой http://localhost:8000/health/llm — вызов появится в [LangSmith дашборде](https://smith.langchain.com).