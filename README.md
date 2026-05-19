# InterviewPilot AI 🎯

AI-платформа для подготовки к техническим собеседованиям. Загружаешь резюме, выбираешь роль — система проводит персонализированное mock-интервью с оценкой ответов, follow-up вопросами и финальным отчётом.

## Демо

> Запусти локально через Docker (см. ниже) или открой [LangSmith дашборд](https://smith.langchain.com) для просмотра трейсов.

---

## Что умеет

- 📄 **Парсинг резюме** — загрузка PDF, извлечение навыков, стека, опыта и проектов
- 🎯 **10 ролей** — Backend, Frontend, ML, Data Analyst, PM, DevOps, QA, iOS, Android, Security
- 🧠 **RAG-пайплайн** — вопросы генерируются с учётом knowledge base по каждой роли (107 чанков, ChromaDB)
- 📊 **Рубричная оценка** — 5 критериев × 2 балла, итого 0–10
- 🔁 **Follow-up вопросы** — автоматически при слабом ответе (score < 6), максимум 2 раза
- 💡 **Hint система** — подсказка если кандидат не знает ответа (human-in-the-loop)
- 🎙️ **Голосовой режим** — ответы голосом через Whisper speech-to-text
- 🎭 **3 стиля интервьюера** — strict / friendly / academic
- 📈 **Финальный отчёт** — сильные стороны, зоны роста, рекомендация Hire / No Hire

---

## Архитектура

```
PDF резюме → resume_parser → role_analyzer → question_generator (RAG)
                                                      ↓
                                              hint_node (если "не знаю")
                                                      ↓
                                            answer_evaluator ←──────┐
                                                      ↓              │
                                          is_weak AND count<2? → follow_up
                                                      ↓
                                            next_question / final_feedback
```

Подробнее: [ARCHITECTURE.md](./ARCHITECTURE.md) | [EVALS.md](./EVALS.md)

---

## Стек

| Слой | Технология |
|---|---|
| Frontend | Next.js 14, TypeScript, Tailwind CSS |
| Backend | FastAPI, Python 3.12 |
| LLM Orchestration | LangGraph |
| LLM Provider | OpenAI (gpt-4o-mini / gpt-4.1) |
| Векторная БД | ChromaDB 0.5.18 |
| Embeddings | text-embedding-3-small |
| Voice | Whisper (whisper-1) |
| MCP Server | `mcp/server.py` (3 тула) |
| Мониторинг | LangSmith |
| Контейнеризация | Docker + docker-compose |

---

## Быстрый старт

### Через Docker (рекомендуется)

```bash
git clone https://github.com/твой-юзер/InterviewPilotAI.git
cd InterviewPilotAI

cp .env.example .env
# заполни .env:
# OPENAI_API_KEY=sk-...
# LANGCHAIN_API_KEY=ls__...
# LANGCHAIN_TRACING_V2=true
# LANGCHAIN_PROJECT=InterviewPilotAI

docker compose up --build
```

| Сервис | URL |
|---|---|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API docs | http://localhost:8000/docs |
| ChromaDB | http://localhost:8001 |

### Залить knowledge base в ChromaDB

После первого запуска:

```bash
docker exec -it interviewpilot-backend python -c \
  "from app.services.rag_service import ingest_documents; ingest_documents('data/knowledge')"
```

### Локально (без Docker)

```bash
# Backend
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# ChromaDB (отдельный терминал)
docker run -d -p 8001:8000 --name chroma chromadb/chroma:0.5.18

# Frontend (отдельный терминал)
cd frontend
npm install
npm run dev
```

---

## Переменные окружения

```env
OPENAI_API_KEY=sk-...
LANGCHAIN_API_KEY=ls__...
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=InterviewPilotAI
CHROMA_HOST=localhost
CHROMA_PORT=8001
DEV_MODE=true   # false для PROD (больше вопросов, gpt-4.1 для финального отчёта)
```

---

## Evals

Проведён A/B тест двух вариантов промпта `answer_evaluator` на golden dataset из 30 примеров:

| Метрика | Вариант A (простой) | Вариант B (рубрика) |
|---|---|---|
| Accuracy | 66.7% | 23.3%* |
| LLM-as-judge | 4.0/5.0 | 4.0/5.0 |
| Consistency σ | 0.12 | 0.35 |

*низкая accuracy варианта B — артефакт несовпадения шкал датасета и рубрики, не ошибка модели.

Подробнее: [EVALS.md](./EVALS.md)

```bash
# Запуск evals
source backend/venv/bin/activate
python evals/run_evals.py --variant a
python evals/run_evals.py --variant b
```

---

## Структура проекта

```
InterviewPilotAI/
├── backend/
│   ├── app/
│   │   ├── api/          # FastAPI роуты
│   │   ├── graph/        # LangGraph ноды и граф
│   │   └── services/     # rag_service, resume_parser
│   ├── data/knowledge/   # Knowledge base (10 ролей, .txt)
│   └── main.py
├── frontend/             # Next.js приложение
├── mcp/                  # MCP сервер (3 тула)
├── skills/               # Custom Skill (SKILL.md)
├── evals/                # Golden dataset + run_evals.py
├── ARCHITECTURE.md
└── EVALS.md
```

---

## LangSmith мониторинг

Все LLM вызовы трейсятся через `@traceable`. После запуска:

1. Открой [smith.langchain.com](https://smith.langchain.com)
2. Проект: `InterviewPilotAI`
3. Видишь трейсы: `resume_parser → role_analyzer → question_generator → answer_evaluator → ...`