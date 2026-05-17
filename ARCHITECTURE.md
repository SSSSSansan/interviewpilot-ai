# ARCHITECTURE.md — InterviewPilot AI

## Обзор системы

InterviewPilot AI — веб-приложение для подготовки к техническим собеседованиям. Пользователь загружает PDF резюме, выбирает роль и стиль интервьюера, и система проводит персонализированное mock-интервью с оценкой ответов и финальным отчётом.

Архитектурно — это многошаговый **LangGraph workflow** с **RAG-пайплайном**, **MCP-сервером** и **Custom Skill** для структурированной оценки ответов.

---

## Компоненты системы

| Компонент | Технология | Роль |
|---|---|---|
| Frontend | Next.js + TypeScript + Tailwind | UI: загрузка резюме, интерфейс интервью, отчёт |
| Backend | FastAPI + Python 3.12 | API роуты, оркестрация LangGraph |
| LLM Orchestration | LangGraph | Многошаговый граф с ветвлением и циклом |
| MCP Server | `mcp/server.py` | 3 тула: parse_resume, generate_questions, evaluate_answer |
| Custom Skill | `skills/SKILL.md` | Рубричная оценка ответов (5 критериев) |
| RAG | ChromaDB + text-embedding-3-small | Knowledge base по 10 ролям, retrieval контекст |
| Voice | Whisper (whisper-1) | Speech-to-text для голосового режима |
| Мониторинг | LangSmith | Трейсинг всех LLM вызовов через @traceable |

---

## Путь одного запроса (end-to-end)

```
1. Пользователь загружает PDF + выбирает роль + стиль интервьюера
        ↓
2. POST /session/start
        ↓
3. resume_parser_node
   └── PyMuPDF парсит PDF → текст
   └── gpt-4o-mini извлекает: { name, skills, tech_stack, years_experience,
                                 projects, education, spoken_languages, role_relevance }
   └── Если PDF нет → дефолтный профиль кандидата
        ↓
4. role_analyzer_node
   └── Подтверждает роль и cv_data из state
        ↓
5. question_generator_node
   └── RAG: retrieve_context(f"{role} interview questions", role, top_k=3) → чанки из ChromaDB
   └── gpt-4o-mini + personality промпт + RAG контекст → 3 вопроса (DEV) / 5 вопросов (PROD)
        ↓
6. Первый вопрос → ответ пользователя
   └── Текст: POST /session/answer
   └── Голос: POST /transcribe → Whisper → текст → POST /session/answer
        ↓
7. hint_node (если answer == "не знаю" / пустой / < 4 символов)
   └── Генерирует подсказку не раскрывая ответ
   └── awaiting_retry = True → ждём повторного ответа
        ↓
8. answer_evaluator_node
   └── Оценка по рубрике из 5 критериев (0–2 каждый, итого 0–10)
   └── Генерирует: { scores, total_score, feedback, ideal_answer, is_weak }
   └── is_weak = True если total_score < 6
        ↓
9. [conditional edge]
   ├── is_weak=True AND follow_up_count < 2
   │       ↓
   │   follow_up_node → новый уточняющий вопрос → answer_evaluator (цикл)
   │
   └── иначе → next_question_node
                ├── ещё вопросы есть → шаг 6
                └── вопросы кончились → final_feedback_node
        ↓
10. final_feedback_node
    └── gpt-4o-mini (SMART_MODEL в PROD: gpt-4.1), temp=0.3
    └── Финальный отчёт: общая оценка, сильные стороны, зоны роста, Hire/No Hire
        ↓
11. GET /session/{id}/report → пользователь видит отчёт
```

---

## LangGraph граф

```
resume_parser → role_analyzer → question_generator
                                        ↓
                                    hint_node ←── (если "не знаю")
                                        ↓
                              answer_evaluator ←──────────────┐
                                        ↓                     │
                         is_weak AND follow_up_count < 2? → follow_up_node
                                        ↓
                                next_question_node
                                   ├── ещё вопросы → answer_evaluator
                                   └── кончились → final_feedback
```

**Ключевые параметры графа:**
- Threshold для follow-up: `total_score < 6` (из 10)
- Максимум follow-up на один вопрос: 2
- Количество вопросов: 3 (DEV_MODE=true) / 5 (DEV_MODE=false)
- Human-in-the-loop: hint_node ждёт повторного ответа пользователя (awaiting_retry)

---

## MCP Сервер (`mcp/server.py`)

Три тула, которые предоставляют стандартный интерфейс для работы с данными интервью:

```python
@mcp.tool()
def parse_resume(pdf_path: str) -> dict:
    # PyMuPDF парсинг PDF → структурированные данные CV

@mcp.tool()
def generate_questions(role: str, cv_context: dict, rag_context: str) -> list[str]:
    # gpt-4o-mini + RAG контекст → персонализированные вопросы

@mcp.tool()
def evaluate_answer(question: str, answer: str, role: str) -> dict:
    # Рубрика из 5 критериев → { scores, total_score, feedback, is_weak }
```

**Почему MCP, а не обычный вызов функции:** MCP даёт стандартный интерфейс тул-колов который автоматически логируется в LangSmith как отдельный инструментальный шаг. Позволяет переиспользовать тулы из разных нод графа без дублирования логики. При необходимости тулы можно подключить к другому агенту без изменения кода.

---

## Custom Skill: interview-evaluator

**Файл:** `skills/SKILL.md`

Skill описывает агенту как оценивать ответы кандидата по структурированной рубрике из 5 критериев:

| Критерий | Баллы | Что оценивает |
|---|---|---|
| technical_correctness | 0–2 | Насколько технически верно |
| clarity | 0–2 | Насколько понятно изложено |
| depth | 0–2 | Насколько глубоко раскрыта тема |
| confidence | 0–2 | Уверенность в ответе |
| communication | 0–2 | Структура и логика |

**Итого:** 0–10 баллов. `is_weak = True` если `total_score < 6`.

**Почему Skill лучше обычного промпта:**
Простой промпт ("оцени от 0 до 10") даёт непредсказуемые результаты — при прогоне одного примера 3 раза consistency σ ≈ 0.35. Skill фиксирует рубрику → агент заполняет конкретные поля → σ снижается до 0.12. Подтверждено A/B тестом (см. `EVALS.md`).

---

## RAG Pipeline

**Knowledge base** (`backend/data/knowledge/`) — 10 файлов по ролям:
- `backend_questions.txt`, `frontend_questions.txt`, `ml_questions.txt`
- `data_analyst_questions.txt`, `pm_questions.txt`
- `devops_questions.txt`, `qa_questions.txt`, `ios_questions.txt`
- `android_questions.txt`, `security_questions.txt`
- `behavioral_star.txt`, `evaluation_criteria.txt`

Формат: вопрос + strong answer + weak answer + red flags — GPT использует как ориентир по сложности и тематике.

**Параметры:**
- Chunking: `TokenTextSplitter`, chunk_size=512, overlap=50
- Embedding: `text-embedding-3-small` (в 5x дешевле large, качества достаточно для retrieval)
- БД: ChromaDB 0.5.18, HttpClient (порт 8001), коллекция `interview_knowledge`
- Retrieval: top-3 по косинусной близости, query = `"{role}: {question}"`
- Итого чанков: ~107

**Почему эти параметры:** вопросы с ответами умещаются в 512 токенов — один чанк = один полный пример. Overlap 50 гарантирует что граница чанка не разрезает ключевое предложение.

**Путь данных:**
```
data/knowledge/*.txt → TokenTextSplitter(512, 50) → text-embedding-3-small → ChromaDB
запрос (role + "interview questions") → embed → similarity search → top-3 → промпт
```

---

## Multimodal: Whisper Voice Mode

```
Пользователь нажимает "Ответить голосом"
  → браузерный MediaRecorder API записывает аудио (webm/mp3)
  → POST /transcribe (multipart/form-data)
  → whisper-1 транскрибирует → текст
  → текст возвращается на фронт, подставляется в поле ответа
  → пользователь видит транскрипцию, может отредактировать
  → Submit → answer_evaluator нода
```

**Зачем мультимодальность:** голосовой ответ — это реальный сценарий на настоящем интервью. Пользователи, которые готовятся к интервью, должны уметь формулировать мысли устно, а не только письменно.

---

## Стили интервьюера

Три personality промпта выбираются пользователем:

| Стиль | Описание |
|---|---|
| strict | Строгий tech интервьюер из крупной компании. Краткие вопросы, прямой фидбек |
| friendly | Дружелюбный CTO стартапа. Поддерживает, объясняет, но стандарты не снижает |
| academic | Академичный интервьюер. Просит точные определения, CS принципы |

---

## Выбор LLM и температуры

| Нода | Модель (DEV) | Модель (PROD) | Температура | Обоснование |
|---|---|---|---|---|
| resume_parser | gpt-4o-mini | gpt-4o-mini | 0.7 | Extraction задача |
| question_generator | gpt-4o-mini | gpt-4o-mini | 0.7 | Нужно разнообразие вопросов |
| answer_evaluator | gpt-4o-mini | gpt-4o-mini | 0.2 | Консистентность оценки важнее креативности |
| follow_up | gpt-4o-mini | gpt-4o-mini | 0.7 | Баланс |
| hint_node | gpt-4o-mini | gpt-4o-mini | 0.7 | Лёгкая задача |
| final_feedback | gpt-4o-mini | gpt-4.1 | 0.3 | В PROD — высокое качество финального отчёта |

**Почему gpt-4o-mini для workflow:** баланс цены и качества. Одна сессия (~5 вопросов) стоит ~$0.02–0.03.

**Почему gpt-4.1 для final_feedback в PROD:** финальный отчёт — единственный артефакт который пользователь сохраняет. Здесь качество важнее цены.

---

## Trade-offs

| Решение | Альтернатива | Почему выбрали |
|---|---|---|
| ChromaDB | Qdrant, Pinecone | Проще локальный запуск через Docker, достаточно для MVP |
| LangGraph | CrewAI, Parlant | Явный граф с ветвлением виден в LangSmith; цикл follow-up нативно поддерживается через conditional edges |
| gpt-4o-mini | Claude Sonnet, Gemini | Экосистема LangGraph лучше протестирована с OpenAI; ниже стоимость |
| Whisper API | локальный Whisper | Не нужны GPU ресурсы, latency приемлемая для MVP |
| TokenTextSplitter | RecursiveCharacterTextSplitter | Токенный сплиттер точнее для контроля размера при передаче в LLM |

---

## Известные edge cases

- Пустой ответ кандидата → hint_node даёт подсказку, не считается провалом
- PDF без текста (скан) → resume_parser возвращает дефолтный профиль, интервью продолжается
- "Не знаю" / короткий ответ (< 4 символов) → определяется через `is_dont_know()`, активирует hint_node
- Follow-up максимум 2 раза на вопрос → принудительный переход к следующему