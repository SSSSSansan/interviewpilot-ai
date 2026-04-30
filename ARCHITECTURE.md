# ARCHITECTURE.md — InterviewPilot AI

## Обзор системы

InterviewPilot AI — веб-приложение для подготовки к техническим собеседованиям. Пользователь загружает PDF резюме, выбирает роль, и система проводит персонализированное mock-интервью с оценкой ответов и финальным отчётом.

Архитектурно — это многошаговый **LangGraph workflow** с **RAG-пайплайном**, **MCP-сервером** и **Custom Skill** для структурированной оценки ответов.

---

## Компоненты системы

| Компонент | Технология | Роль |
|---|---|---|
| Frontend | Next.js + TypeScript + Tailwind | UI: загрузка резюме, интерфейс интервью, отчёт |
| Backend | FastAPI + Python 3.11 | API роуты, оркестрация LangGraph |
| LLM Orchestration | LangGraph | Многошаговый граф с ветвлением и циклом |
| MCP Server | `mcp/server.py` | 3 тула: parse_resume, generate_questions, evaluate_answer |
| Custom Skill | `skills/skills.md` | Рубричная оценка ответов (5 критериев) |
| RAG | ChromaDB + text-embedding-3-small | Knowledge base по ролям, retrieval контекст |
| Voice | Whisper (whisper-1) | Speech-to-text для голосового режима |
| Мониторинг | LangSmith | Трейсинг всех LLM вызовов |

---

## Путь одного запроса (end-to-end)

```
1. Пользователь загружает PDF + выбирает роль
        ↓
2. POST /session/start
        ↓
3. resume_parser_node
   └── MCP: parse_resume(pdf_path)
   └── Возвращает: { skills, tech_stack, years_experience, projects, education }
        ↓
4. role_analyzer_node
   └── gpt-4.1-mini, temp=0.0
   └── Анализирует соответствие CV и выбранной роли
        ↓
5. question_generator_node
   └── RAG: retrieve_context(role, skills) → top-3 чанка из ChromaDB
   └── MCP: generate_questions(role, cv_context, rag_context)
   └── Возвращает список из 5–7 вопросов
        ↓
6. Первый вопрос → ответ пользователя (текст или голос → POST /transcribe → Whisper)
        ↓
7. POST /session/answer
        ↓
8. answer_evaluator_node
   └── MCP: evaluate_answer(question, answer, role)
   └── Custom Skill: interview-evaluator (рубрика из 5 критериев)
   └── Возвращает: { score, criteria, reasoning, feedback, is_weak }
        ↓
9. [conditional edge]
   ├── is_weak=true AND follow_up_count < 2
   │       ↓
   │   follow_up_node → answer_evaluator_node  (цикл, макс. 2 раза)
   │
   └── иначе → следующий вопрос (п.6) или final_feedback (если вопросы кончились)
        ↓
10. final_feedback_node
    └── gpt-4.1, temp=0.3
    └── Генерирует финальный отчёт: overall_score, strengths, weaknesses, roadmap
        ↓
11. GET /session/{id}/report → пользователь видит отчёт
```

---

## LangGraph граф

```
resume_parser → role_analyzer → question_generator
                                        ↓
                              answer_evaluator ←──────────────┐
                                        ↓                     │
                               is_weak AND count<2? → follow_up_node
                                        ↓
                               ещё вопросы? → answer_evaluator (следующий)
                                        ↓
                                 final_feedback
```

**Ключевые параметры графа:**
- Threshold для follow-up: `score < 6` (из 10)
- Максимум follow-up на один вопрос: 2
- Количество вопросов на сессию: 5–7 в зависимости от роли

---

## MCP Сервер (`mcp/server.py`)

Три тула, которые вызываются нодами LangGraph графа:

```python
@mcp.tool()
def parse_resume(pdf_path: str) -> dict:
    # PyMuPDF парсинг PDF → структурированные данные CV

@mcp.tool()
def generate_questions(role: str, cv_context: dict, rag_context: str) -> list[str]:
    # gpt-4.1-mini + RAG контекст → 5-7 персонализированных вопросов

@mcp.tool()
def evaluate_answer(question: str, answer: str, role: str) -> dict:
    # Custom Skill (рубрика) → { score, criteria, feedback, is_weak }
```

**Почему MCP, а не обычный вызов функции:** MCP даёт стандартный интерфейс тул-колов, который автоматически логируется в LangSmith как отдельный инструментальный шаг. Также это позволяет переиспользовать тулы из разных нод графа без дублирования логики.

---

## Custom Skill: interview-evaluator

**Файл:** `skills/skills.md`

Skill описывает агенту как оценивать ответы кандидата по структурированной рубрике из 5 критериев:

| Критерий | Баллы | Что оценивает |
|---|---|---|
| technical_correctness | 0–2 | Насколько технически верно |
| clarity | 0–2 | Насколько понятно изложено |
| depth | 0–2 | Насколько глубоко раскрыта тема |
| confidence | 0–2 | Уверенность в ответе |
| communication | 0–2 | Структура и логика |

**Итого:** 0–10 баллов. `is_weak = true` если `score < 6`.

**Почему Skill лучше обычного промпта:**
Простой промпт ("оцени от 1 до 10") даёт непредсказуемые результаты: при прогоне одного примера 3 раза std ≈ 1.0. Skill фиксирует рубрику → агент заполняет конкретные поля → std снижается до ≈ 0.3. Подтверждено A/B тестом (см. `EVALS.md`).

---

## RAG Pipeline

**Knowledge base** (`backend/data/knowledge/`):
- Технические вопросы и примеры ответов по каждой роли (~50 документов)
- STAR-примеры для behavioral вопросов (~20 документов)
- Критерии оценки и red flags по ролям (~10 документов)

**Параметры:**
- Chunking: 512 токенов, overlap 50
- Embedding: `text-embedding-3-small` (в 5x дешевле large, качества достаточно)
- БД: ChromaDB (локально, persistent volume в Docker)
- Retrieval: top-3 по косинусной близости

**Почему эти параметры:** вопросы с ответами не очень длинные — 512 токенов захватывает один полный пример. Overlap 50 гарантирует что граница чанка не разрезает ключевое предложение.

**Путь данных:**
```
documents/ → chunk(512, overlap=50) → embed → ChromaDB
запрос (роль + skills) → embed → similarity search → top-3 → промпт
```

---

## Multimodal: Whisper Voice Mode

```
Пользователь нажимает "Ответить голосом"
  → браузерный MediaRecorder API записывает аудио (webm/mp3)
  → POST /transcribe (multipart/form-data)
  → whisper-1 транскрибирует
  → текст возвращается на фронт, подставляется в поле ответа
  → пользователь видит транскрипцию, может отредактировать
  → Submit → answer_evaluator нода
```

---

## Выбор LLM и температуры

| Нода | Модель | Температура | Обоснование |
|---|---|---|---|
| question_generator | gpt-4.1-mini | 0.7 | Нужно разнообразие вопросов |
| answer_evaluator | gpt-4.1-mini | 0.2 | Консистентность оценки важнее креативности |
| follow_up | gpt-4.1-mini | 0.5 | Лёгкая задача, лёгкий баланс |
| resume_parser | gpt-4.1-mini | 0.0 | Extraction задача, детерминированность |
| final_feedback | gpt-4.1 | 0.3 | Высокое качество для финального отчёта |

**Почему gpt-4.1-mini для workflow:** баланс цены и качества. Одна сессия (~10 вопросов) стоит ~$0.02–0.03.

**Почему gpt-4.1 для final_feedback:** финальный отчёт — единственный артефакт, который пользователь сохраняет. Здесь качество важнее цены.

---

## Trade-offs

| Решение | Альтернатива | Почему выбрали |
|---|---|---|
| ChromaDB | Qdrant, Pinecone | Проще локальный запуск, достаточно для MVP |
| LangGraph | CrewAI, Parlant | Явный граф с ветвлением лучше виден в LangSmith; цикл follow-up нативно поддерживается через conditional edges |
| gpt-4.1-mini | Claude Sonnet, Gemini | Экосистема LangGraph лучше протестирована с OpenAI |
| Whisper API | локальный Whisper | Не нужны GPU ресурсы, достаточно для MVP |