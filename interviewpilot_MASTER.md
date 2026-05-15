# InterviewPilot AI — Master Implementation Guide

> **Этот файл — главный контекст проекта.**
> Кидай его в начале любой сессии с LLM. В конце каждого этапа обновляй статус этапа (DONE / IN PROGRESS / TODO) и чеклист задач.

---

## Быстрый статус (обновляй сюда)

| Этап | Статус | Заметки |
|---|---|---|
| Этап 1 — Фундамент и инфраструктура | DONE | |
| Этап 2 — MCP сервер | DONE | |
| Этап 3 — Custom Skill | DONE | |
| Этап 4 — RAG pipeline | DONE | |
| Этап 5 — LangGraph workflow | DONE | |
| Этап 6 — Multimodal (Whisper) | DONE | |
| Этап 7 — Frontend | DONE | |
| Этап 8 — Evals и A/B тест | TODO | |
| Этап 9 — Документация и LLM обоснование | TODO | |
| Этап 10 — Финальная проверка и демо | TODO | |

**Дедлайн сдачи:** 20 мая
**Demo Days:** 26–28 мая

---

## Часть 1 — Описание проекта

### Что это

InterviewPilot AI — веб-приложение для подготовки к техническим собеседованиям.

Пользователь загружает PDF резюме, выбирает целевую роль (Backend Engineer, Frontend, ML Engineer, Data Analyst, Product Manager), и система проводит персонализированное mock-интервью:
- генерирует вопросы на основе CV и роли
- оценивает ответы по структурированной рубрике
- задаёт follow-up вопросы если ответ слабый
- в конце выдаёт финальный отчёт с оценкой, сильными/слабыми сторонами и roadmap улучшений

Дополнительно: голосовой режим — пользователь отвечает голосом, система транскрибирует через Whisper и оценивает.

### Проблема которую решаем

Студенты и джуниор-инженеры готовятся к интервью неструктурированно: не знают какие вопросы ждать, нет реалистичной симуляции, нет персонализированного фидбека. InterviewPilot решает это через CV-aware генерацию вопросов и рубричную оценку ответов.

### Целевой пользователь

Студент или джуниор-инженер (0–2 года опыта), который готовится к первому техническому собеседованию и хочет понять свои слабые места до реального интервью.

---

## Часть 2 — Технический стек

| Слой | Технология | Зачем |
|---|---|---|
| Frontend | Next.js + TypeScript + Tailwind CSS | Быстрая разработка, хорошая типизация |
| Backend | FastAPI + Python 3.11 | Async, быстро, хорошо совместим с LangChain |
| LLM Orchestration | LangGraph | Многошаговый граф с ветвлением и циклами |
| LLM Provider | OpenAI API | Качество + зрелые инструменты |
| Модель (workflow) | gpt-4.1-mini | Баланс цены и качества для генерации/оценки |
| Модель (feedback) | gpt-4.1 | Высокое качество для финального отчёта |
| Embeddings | text-embedding-3-small | Дёшево, достаточно качественно |
| Voice | whisper-1 | Стандарт для speech-to-text |
| Векторная БД | ChromaDB | Просто запускается, хорошо подходит для MVP |
| Мониторинг | LangSmith | Обязательно по требованиям курса |
| Контейнеризация | Docker + docker-compose | Однокомандный запуск для демо |
| Деплой | Vercel (frontend) + Railway/Render (backend) | Бесплатный tier для MVP |

---

## Часть 3 — Архитектура

### Структура репозитория

```
interviewpilot/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── routes_interview.py   # POST /session/start, /session/answer
│   │   │   └── routes_transcribe.py  # POST /transcribe
│   │   ├── graph/
│   │   │   ├── __init__.py
│   │   │   ├── graph.py              # LangGraph граф — главный файл
│   │   │   ├── nodes.py              # Все ноды графа
│   │   │   └── state.py              # InterviewState dataclass
│   │   └── services/
│   │       ├── resume_parser.py      # PyMuPDF парсинг PDF
│   │       └── rag_service.py        # ChromaDB retrieval
│   ├── main.py
│   └── requirements.txt
├── frontend/
│   ├── app/
│   │   ├── page.tsx                  # Главная — загрузка резюме
│   │   ├── interview/page.tsx        # Страница интервью
│   │   └── report/page.tsx           # Финальный отчёт
│   ├── components/
│   │   ├── ResumeUpload.tsx
│   │   ├── ChatInterface.tsx
│   │   └── VoiceRecorder.tsx
│   └── package.json
├── mcp/
│   └── server.py                     # Custom MCP сервер (3 тула)
├── skills/
│   └── interview-evaluator/
│       └── SKILL.md                  # Custom Skill (обязательно!)
├── evals/
│   ├── golden_dataset.json           # 30+ примеров для evals
│   └── run_evals.py                  # Скрипт автопрогона
├── docker-compose.yml
├── .env.example
├── README.md
├── ARCHITECTURE.md
└── EVALS.md
```

### LangGraph Workflow (детально)

```
[Пользователь загружает PDF + выбирает роль]
        ↓
  resume_parser           # Извлекает skills, tech_stack, years_exp, projects
        ↓
  role_analyzer           # Анализирует соответствие CV и роли
        ↓
  question_generator      # RAG + MCP generate_questions() → список вопросов
        ↓
  answer_evaluator        # MCP evaluate_answer() → score, feedback
        ↓
  [conditional edge]
    score < 6  →  follow_up  →  answer_evaluator  (цикл, max 2 раза)
    score >= 6 →  next_question (если вопросы ещё есть)
                  или final_feedback (если все вопросы закончились)
        ↓
  final_feedback          # gpt-4.1, итоговый отчёт
```

**Ключевые параметры:**
- Threshold для follow-up: score < 6 (из 10)
- Максимум follow-up на один вопрос: 2
- Количество вопросов на сессию: 5–7 в зависимости от роли

### State (что хранится между нодами)

```python
class InterviewState(TypedDict):
    cv_data: dict           # результат parse_resume
    role: str               # выбранная роль
    questions: list[str]    # сгенерированные вопросы
    current_question_idx: int
    current_question: str
    current_answer: str
    follow_up_count: int    # счётчик follow-up для текущего вопроса
    scores: list[dict]      # история оценок
    rag_context: str        # retrieved context из ChromaDB
    final_report: dict      # финальный отчёт
```

### MCP Сервер (3 тула)

```python
# mcp/server.py

@mcp.tool()
def parse_resume(pdf_path: str) -> dict:
    """
    Извлекает структурированные данные из PDF резюме.
    Возвращает: {
        skills: list[str],
        tech_stack: list[str],
        years_experience: int,
        projects: list[str],
        education: str
    }
    """

@mcp.tool()
def generate_questions(role: str, cv_context: dict, rag_context: str) -> list[str]:
    """
    Генерирует персонализированные вопросы под роль и CV.
    Возвращает список из 5–7 вопросов (технические + behavioral).
    """

@mcp.tool()
def evaluate_answer(question: str, answer: str, role: str) -> dict:
    """
    Оценивает ответ по структурированной рубрике.
    Возвращает: {
        score: int (0-10),
        technical_correctness: int (0-2),
        clarity: int (0-2),
        depth: int (0-2),
        confidence: int (0-2),
        communication: int (0-2),
        reasoning: str,
        feedback: str,
        is_weak: bool
    }
    """
```

### Custom Skill — interview-evaluator

Файл: `skills/interview-evaluator/SKILL.md`

Skill описывает агенту:
- **Триггер:** когда нужно оценить ответ кандидата по нескольким измерениям одновременно
- **Когда Skill лучше простого промпта:** обычный промпт даёт одну цифру без объяснения, Skill обеспечивает структурированную рубрику из 5 измерений — консистентность оценок вырастает (это и есть гипотеза A/B теста)
- **Формат вывода:** строго JSON с полями score, reasoning, feedback, is_weak

### RAG Pipeline

**Что в knowledge base:**
- Типичные технические вопросы по каждой роли (Backend, Frontend, ML, DA, PM)
- STAR-примеры для behavioral вопросов
- Шаблоны сильных и слабых ответов с объяснениями
- Критерии оценки и red flags для каждой роли
- System design примеры (базовые)

**Технические параметры:**
- Chunking: 512 токенов, overlap 50 (обоснование: вопросы с ответами не очень длинные, 512 хватает для одного примера)
- Embedding: text-embedding-3-small (обоснование: в 5x дешевле large, качество достаточное для этой задачи)
- БД: ChromaDB (локально через docker, персистентный volume)
- Retrieval: top-3 по косинусной близости
- Контекст инжектируется в промпт question_generator

**Путь данных:**
```
documents/ → chunk → embed (text-embedding-3-small) → ChromaDB
запрос (роль + skills) → embed → similarity search → top-3 chunks → промпт
```

### Multimodal: Whisper Voice Mode

```
Пользователь нажимает "Ответить голосом"
  → браузерный MediaRecorder записывает аудио (webm/mp3)
  → POST /transcribe с аудио файлом
  → whisper-1 API транскрибирует
  → текст возвращается на фронт и подставляется в поле ответа
  → пользователь видит транскрипцию, может отредактировать
  → Submit → answer_evaluator нода
```

Endpoint: `POST /transcribe` — принимает `multipart/form-data` с полем `audio`, возвращает `{ text: str }`.

---

## Часть 4 — Evals и A/B тест

### Golden Dataset структура

Файл: `evals/golden_dataset.json`

```json
[
  {
    "id": "001",
    "role": "Backend Engineer",
    "question": "Объясни разницу между REST и GraphQL",
    "answer": "REST использует фиксированные endpoints...",
    "answer_type": "strong",
    "expected_score_min": 7,
    "expected_score_max": 10
  },
  {
    "id": "002",
    "role": "Backend Engineer",
    "question": "Объясни разницу между REST и GraphQL",
    "answer": "Это разные способы делать API",
    "answer_type": "vague",
    "expected_score_min": 1,
    "expected_score_max": 3
  }
]
```

**Распределение 30 примеров:**
- strong (хорошие ответы): 8 примеров → ожидаем 7–10
- weak (слабые ответы): 8 примеров → ожидаем 3–5
- vague (расплывчатые): 7 примеров → ожидаем 1–3
- incorrect (технически неверные): 7 примеров → ожидаем 0–2

**Покрытие ролей:** Backend, Frontend, ML, Data Analyst, PM — по 6 примеров каждая.

### Метрики

1. **Accuracy** — процент случаев когда оценка попадает в expected_score range
2. **Consistency** — std отклонение при прогоне одного примера 3 раза подряд (меньше = лучше)
3. **LLM-as-judge** — отдельный вызов GPT оценивает качество фидбека (1–5)

### A/B Эксперимент

**Гипотеза:** структурированная рубрика даёт более консистентные и полезные оценки чем простой промпт.

**Вариант A (простой промпт):**
```
Оцени ответ кандидата на вопрос от 1 до 10.
Вопрос: {question}
Ответ: {answer}
Верни только цифру.
```

**Вариант B (рубрика — наш основной подход):**
```
Оцени ответ кандидата по 5 критериям (0-2 балла каждый):
- Technical correctness: насколько технически верно
- Clarity: насколько понятно изложено
- Depth: насколько глубоко раскрыта тема
- Confidence: уверенность в ответе
- Communication: структура и логика ответа

Вопрос: {question}
Ответ: {answer}
Верни JSON с полями: scores (dict), total (int), feedback (str)
```

**Что сравниваем на golden dataset:**
- Accuracy попадания в expected range
- Consistency (std при 3 прогонах)
- LLM-as-judge оценка фидбека

**Ожидаемый результат:** вариант B лучше по consistency, вариант A иногда лучше по скорости.

---

## Часть 5 — Выбор LLM и гиперпараметры

| Нода | Модель | Температура | Обоснование |
|---|---|---|---|
| question_generator | gpt-4.1-mini | 0.7 | Нужно разнообразие вопросов, не всегда одинаковые |
| answer_evaluator | gpt-4.1-mini | 0.2 | Оценка должна быть консистентной, не случайной |
| follow_up | gpt-4.1-mini | 0.5 | Лёгкая задача — уточняющий вопрос |
| resume_parser | gpt-4.1-mini | 0.0 | Extraction задача, нужна детерминированность |
| final_feedback | gpt-4.1 | 0.3 | Финальный отчёт требует высокого качества |

**Почему gpt-4.1-mini а не Claude/Gemini/локальная:**
- Claude Sonnet сопоставим по качеству, но экосистема LangGraph лучше протестирована с OpenAI
- Gemini — меньше документации для LangGraph интеграции
- Локальная модель — latency слишком высокая для real-time интервью, качество хуже для русскоязычного контента

**Стоимость одной сессии (~10 вопросов):** ~$0.02–0.03

---

## Часть 6 — API Endpoints

```
POST /session/start
  Body: { resume_pdf: file, role: str }
  Response: { session_id: str, first_question: str }

POST /session/answer
  Body: { session_id: str, answer: str }
  Response: { feedback: str, score: int, next_question: str | null, is_complete: bool }

POST /transcribe
  Body: multipart/form-data { audio: file }
  Response: { text: str }

GET /session/{session_id}/report
  Response: { overall_score: float, strengths: list, weaknesses: list, roadmap: list }

GET /health
  Response: { status: "ok" }
```

---

## Часть 7 — .env переменные

```bash
# .env.example — скопируй в .env и заполни значения

OPENAI_API_KEY=sk-...

# LangSmith мониторинг (обязательно!)
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=lsv2_...
LANGCHAIN_PROJECT=interviewpilot

# ChromaDB
CHROMA_HOST=localhost
CHROMA_PORT=8001

# FastAPI
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000

# Frontend (в frontend/.env.local)
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## Часть 8 — Этапы реализации

---

### Этап 1 — Фундамент и инфраструктура

**Статус: TODO**
**Даты: 13–17 апреля**

**Цель:** репозиторий создан, оба сервиса стартуют, LangSmith видит трейсы.

**Задачи:**

- [ ] Создать GitHub репозиторий `interviewpilot`
- [ ] Создать папочную структуру согласно разделу "Структура репозитория" выше
- [ ] Инициализировать FastAPI проект:
  - `pip install fastapi uvicorn python-dotenv langchain langgraph langchain-openai chromadb pymupdf openai mcp langsmith`
  - Создать `main.py` с базовым приложением
  - Добавить эндпоинт `GET /health` → `{ "status": "ok" }`
- [ ] Инициализировать Next.js проект: `npx create-next-app@latest frontend --typescript --tailwind --app`
- [ ] Создать `docker-compose.yml` с сервисами `backend` и `chromadb`
  - ChromaDB image: `chromadb/chroma`, порт 8001
  - Добавить persistent volume для ChromaDB данных
- [ ] Создать `.env.example` со всеми ключами из раздела выше (без значений)
- [ ] **Критично: подключить LangSmith**
  - Зарегистрироваться на smith.langchain.com
  - Создать проект `interviewpilot`
  - Добавить ключи в `.env`
  - Написать тестовый скрипт `test_langsmith.py`: один простой вызов через `langchain-openai`
  - Убедиться что трейс появился в дашборде LangSmith
- [ ] Написать базовый `README.md` (описание + инструкция запуска)
- [ ] Закоммитить всё в репозиторий

**Критерий завершения:** `docker compose up` поднимает FastAPI и ChromaDB, `GET /health` возвращает 200, тестовый LLM вызов виден в LangSmith.

---

### Этап 2 — MCP Сервер

**Статус: TODO**
**Даты: 17–21 апреля**

**Цель:** рабочий MCP сервер с 3 тулами, протестированный локально.

**Задачи:**

- [ ] Установить MCP Python SDK: `pip install mcp`
- [ ] Создать `mcp/server.py` с базовой структурой MCP сервера
- [ ] Реализовать тул `parse_resume(pdf_path: str) -> dict`:
  - Использовать PyMuPDF (`import fitz`) для извлечения текста из PDF
  - Передать текст в gpt-4.1-mini с промптом на извлечение структурированных данных
  - Вернуть dict с полями: skills, tech_stack, years_experience, projects, education
- [ ] Реализовать тул `generate_questions(role, cv_context, rag_context) -> list[str]`:
  - Принимает роль, данные CV и контекст из RAG
  - Генерирует 5–7 персонализированных вопросов через gpt-4.1-mini
  - Возвращает список строк
- [ ] Реализовать тул `evaluate_answer(question, answer, role) -> dict`:
  - Использует рубрику из 5 измерений (это вариант B для A/B теста)
  - Температура: 0.2
  - Возвращает dict с полями из раздела MCP выше
- [ ] Написать тесты для каждого тула (простые скрипты, не pytest)
- [ ] Обновить ARCHITECTURE.md — добавить секцию про MCP

**Критерий завершения:** все 3 тула вызываются напрямую и возвращают корректные данные.

---

### Этап 3 — Custom Skill

**Статус: TODO**
**Даты: 21–23 апреля**

**Цель:** валидный SKILL.md файл, готовый к демонстрации менторам.

**Задачи:**

- [ ] Создать директорию `skills/interview-evaluator/`
- [ ] Написать `skills/interview-evaluator/SKILL.md` со следующими секциями:
  - `name`: interview-evaluator
  - `description`: что делает Skill
  - `triggers`: когда агент должен его использовать (ключевые слова, сценарии)
  - `when_not_to_use`: когда не нужен (например, для простых да/нет вопросов)
  - `input_format`: что принимает (вопрос + ответ + роль)
  - `output_format`: строго JSON схема
  - `example`: один полный пример входа и выхода
  - `notes`: почему Skill лучше обычного промпта в этом сценарии
- [ ] Убедиться что структура файла соответствует стандарту курса
- [ ] Добавить ссылку на SKILL.md в ARCHITECTURE.md

**Критерий завершения:** SKILL.md содержит все секции, можно объяснить менторам чем Skill отличается от обычного промпта.

---

### Этап 4 — RAG Pipeline

**Статус: TODO**
**Даты: 23–28 апреля**

**Цель:** ChromaDB наполнена данными, retrieval работает и возвращает релевантный контекст.

**Задачи:**

- [ ] Собрать knowledge base (файлы в `backend/data/knowledge/`):
  - Технические вопросы и ответы по каждой роли (~50 документов)
  - STAR-примеры для behavioral вопросов (~20 документов)
  - Критерии оценки и red flags по ролям (~10 документов)
- [ ] Реализовать `backend/app/services/rag_service.py`:
  - Функция `ingest_documents(folder_path)`: chunking (512 токенов, overlap 50) → embed → ChromaDB
  - Функция `retrieve_context(query, role, top_k=3)`: embed запрос → similarity search → вернуть строку с контекстом
- [ ] Написать скрипт `backend/scripts/ingest.py` для первичного наполнения БД
- [ ] Запустить ingestion: `python backend/scripts/ingest.py`
- [ ] Протестировать retrieval: несколько тестовых запросов, убедиться что возвращается релевантный контекст
- [ ] Подключить `retrieve_context` к MCP туле `generate_questions`
- [ ] Задокументировать в ARCHITECTURE.md: chunking стратегия и почему именно эти параметры

**Критерий завершения:** запрос `retrieve_context("вопросы для backend engineer", "Backend Engineer")` возвращает 3 релевантных чанка.

---

### Этап 5 — LangGraph Workflow

**Статус: TODO**
**Даты: 28 апреля – 5 мая**

**Цель:** полный рабочий граф от загрузки резюме до финального отчёта, видный в LangSmith.

**Задачи:**

- [ ] Создать `backend/app/graph/state.py` — `InterviewState` TypedDict (см. раздел State выше)
- [ ] Создать `backend/app/graph/nodes.py` — реализовать каждую ноду:
  - `resume_parser_node`: вызывает MCP тул `parse_resume`
  - `role_analyzer_node`: анализирует соответствие CV и роли
  - `question_generator_node`: вызывает `retrieve_context` + MCP тул `generate_questions`
  - `answer_evaluator_node`: вызывает MCP тул `evaluate_answer`
  - `follow_up_node`: генерирует уточняющий вопрос (gpt-4.1-mini, temp 0.5)
  - `final_feedback_node`: финальный отчёт (gpt-4.1, temp 0.3)
- [ ] Создать `backend/app/graph/graph.py`:
  - Собрать граф из нод
  - Добавить conditional edge после `answer_evaluator_node`:
    - `score < 6` AND `follow_up_count < 2` → `follow_up_node`
    - иначе → `next_question_or_finish` (хелпер-функция)
  - Добавить edge `follow_up_node` → `answer_evaluator_node` (это цикл)
- [ ] Подключить граф к FastAPI эндпоинтам (`/session/start`, `/session/answer`)
- [ ] Проверить трейс в LangSmith: одна полная сессия (5 вопросов, 1–2 follow-up) должна быть видна как один связный трейс
- [ ] Убедиться что LangSmith показывает ветвление (conditional edges)

**Критерий завершения:** можно запустить полную сессию через curl/httpie, граф проходит все ноды, LangSmith показывает полный трейс с ветвлением.

---

### Этап 6 — Multimodal (Whisper)

**Статус: TODO**
**Даты: 5–7 мая**

**Цель:** голосовой режим работает end-to-end: говорю → текст → оценка.

**Задачи:**

- [ ] Реализовать `backend/app/api/routes_transcribe.py`:
  - `POST /transcribe` принимает `UploadFile` (аудио)
  - Передаёт файл в `openai.audio.transcriptions.create(model="whisper-1")`
  - Возвращает `{ "text": "транскрибированный текст" }`
- [ ] Протестировать endpoint через Postman или curl с реальным аудио файлом
- [ ] Убедиться что трейс вызова Whisper виден в LangSmith
- [ ] Подготовить для фронтенда (этап 7): API задокументирован, endpoint работает

**Критерий завершения:** `POST /transcribe` с mp3/webm файлом возвращает корректный текст.

---

### Этап 7 — Frontend

**Статус: TODO**
**Даты: 7–12 мая**

**Цель:** рабочий веб-интерфейс, все экраны реализованы, голосовой режим работает.

**Задачи:**

- [ ] **Страница 1 — Главная / загрузка резюме** (`app/page.tsx`):
  - Drag & drop зона для PDF
  - Выбор роли (dropdown: Backend, Frontend, ML, Data Analyst, PM)
  - Кнопка "Начать интервью" → POST /session/start
- [ ] **Страница 2 — Интервью** (`app/interview/page.tsx`):
  - Отображение текущего вопроса
  - Текстовое поле для ответа
  - Кнопка "Ответить голосом" → VoiceRecorder компонент
  - Кнопка "Отправить" → POST /session/answer
  - Отображение фидбека и оценки после ответа
  - Прогресс-бар (вопрос X из Y)
- [ ] **Страница 3 — Финальный отчёт** (`app/report/page.tsx`):
  - Overall score
  - Сильные стороны (список)
  - Слабые стороны (список)
  - Roadmap: что изучить (список с ресурсами)
- [ ] **Компонент VoiceRecorder** (`components/VoiceRecorder.tsx`):
  - Использует браузерный `MediaRecorder API`
  - Запись → стоп → отправка в `POST /transcribe`
  - Отображение транскрипции в поле ответа
- [ ] Задеплоить фронтенд на Vercel
- [ ] Задеплоить бэкенд на Railway или Render
- [ ] Убедиться что деплой работает end-to-end

**Критерий завершения:** можно открыть публичный URL, загрузить резюме, пройти интервью из 3+ вопросов, получить отчёт.

---

### Этап 8 — Evals и A/B тест

**Статус: TODO**
**Даты: 12–16 мая**

**Цель:** EVALS.md заполнен, автопрогон работает, A/B результаты задокументированы.

**Задачи:**

- [ ] Составить `evals/golden_dataset.json`:
  - Минимум 30 примеров (см. структуру в разделе Evals)
  - Покрыть все 4 типа ответов: strong, weak, vague, incorrect
  - Покрыть все 5 ролей
- [ ] Реализовать `evals/run_evals.py`:
  - Загружает golden_dataset.json
  - Для каждого примера вызывает `evaluate_answer` (MCP тул)
  - Считает accuracy (попадание в expected range)
  - Считает consistency (прогнать каждый пример 3 раза, взять std)
  - Сохраняет результаты в `evals/results.json`
- [ ] Провести A/B тест:
  - Прогнать `run_evals.py` с промптом варианта A (простой)
  - Прогнать с промптом варианта B (рубрика)
  - Сравнить accuracy и consistency
- [ ] Добавить LLM-as-judge метрику:
  - Отдельный GPT вызов оценивает качество feedback строки (1–5)
- [ ] Написать `EVALS.md`:
  - Описание датасета
  - Методика прогона
  - Таблица результатов A/B
  - Выводы: какой промпт лучше и почему

**Критерий завершения:** `python evals/run_evals.py` выполняется без ошибок, EVALS.md содержит таблицу сравнения A/B с числовыми результатами.

---

### Этап 9 — Документация и LLM обоснование

**Статус: TODO**
**Даты: 16–18 мая**

**Цель:** все документы готовы, архитектура описана, презентация сделана.

**Задачи:**

- [ ] Финализировать `ARCHITECTURE.md`:
  - Диаграмма всей системы (можно Mermaid или ссылка на Excalidraw)
  - Путь одного запроса от пользователя до ответа (шаг за шагом)
  - Секция: почему LangGraph (а не CrewAI/Parlant)
  - Секция: почему ChromaDB (а не Qdrant/Pinecone)
  - Секция: trade-offs которые были сделаны сознательно
- [ ] Добавить в README секцию "Выбор LLM и гиперпараметры" (скопировать из Части 5 этого файла)
- [ ] Добавить базовый guardrail в `evaluate_answer` ноду:
  - Проверка что ответ не содержит попытки prompt injection
  - Простой prefix check или отдельный classifier промпт
- [ ] Подготовить презентацию (10–15 слайдов):
  - Слайд 1: Проблема (1 слайд)
  - Слайд 2: Решение + demo ссылка (1 слайд)
  - Слайды 3–5: Архитектура + LangGraph граф
  - Слайды 6–8: RAG + MCP + Skill
  - Слайды 9–11: Evals + A/B результаты
  - Слайд 12: Cost анализ (сколько стоит 1 сессия)
  - Слайд 13: Выводы + что бы сделал иначе
- [ ] Обновить README с публичной ссылкой на демо

**Критерий завершения:** все 4 документа (README, ARCHITECTURE.md, EVALS.md, презентация) заполнены и готовы к сдаче.

---

### Этап 10 — Финальная проверка и демо

**Статус: TODO**
**Даты: 18–20 мая**

**Цель:** всё работает, всё сдано, готовы к Demo Days.

**Задачи:**

- [ ] Прогнать финальный чеклист курса (см. ниже)
- [ ] Проверить что `docker compose up` поднимает всё с нуля (на чистой машине)
- [ ] Проверить публичный деплой end-to-end
- [ ] Открыть LangSmith дашборд — убедиться что трейсы реальных сессий видны
- [ ] Сдать репозиторий менторам до 20 мая
- [ ] Прорепетировать 10-минутную защиту:
  - Проблема → решение → демо → архитектура → метрики → выводы
  - Подготовить ответы на вопросы менторов (см. ниже)
- [ ] Подготовить ноутбук для Demo Days: браузер открыт на демо, LangSmith дашборд открыт

**Критерий завершения:** репозиторий сдан, публичное демо работает.

---

## Часть 9 — Финальный чеклист курса

Прогони перед сдачей:

**Обязательные (без них к защите не допускают):**
- [ ] Собственный MCP-сервер с 3 тулами (parse_resume, generate_questions, evaluate_answer)
- [ ] Собственный Skill с SKILL.md (skills/interview-evaluator/SKILL.md)
- [ ] LangGraph workflow с многошаговым графом, ветвлением (conditional edges) и циклом (follow_up)
- [ ] RAG-пайплайн с обоснованным выбором chunking + embedding + ChromaDB
- [ ] Обработка PDF (parse_resume через PyMuPDF)
- [ ] Мультимодальность: Whisper speech-to-text, осмысленно встроен в flow
- [ ] LangSmith логирование — реальные трейсы видны в дашборде
- [ ] Golden dataset 30+ примеров + автоматизированный прогон evals
- [ ] A/B эксперимент с числовыми результатами и выводами
- [ ] Обоснованный выбор LLM и гиперпараметров (задокументировано)
- [ ] Веб-фронтенд (Next.js) — не CLI
- [ ] GitHub репозиторий с README и инструкцией запуска
- [ ] ARCHITECTURE.md или mindmap диаграмма
- [ ] EVALS.md с метриками и результатами A/B
- [ ] Презентация 10–15 слайдов

**Рекомендуемые (повышают оценку):**
- [ ] Docker + docker-compose (однокомандный запуск)
- [ ] Деплой на публичный URL (Vercel + Railway)
- [ ] Guardrails (защита от prompt injection в evaluate_answer)
- [ ] Однокомандный локальный запуск работает на чистой машине

---

## Часть 10 — Вопросы менторов (готовься к ответам)

**Архитектура (40% оценки):**
- Почему LangGraph а не CrewAI или Parlant?
- Покажи путь одного запроса от загрузки PDF до финального отчёта
- Где в графе ветвление? Где цикл?
- Почему gpt-4.1-mini для workflow, а gpt-4.1 для финального фидбека?
- Сколько стоит одна пользовательская сессия? (~$0.02–0.03)
- Что произойдёт если OpenAI API недоступно?

**LLM-инженерия (25% оценки):**
- Как эволюционировал промпт для evaluate_answer? Покажи v1 и текущую версию
- Что в golden dataset? Почему именно эти примеры? Как покрываются edge cases?
- Расскажи про A/B: гипотеза, что сравнивали, результат, какое решение приняли?
- Как устроен RAG: chunking, embeddings, retrieval? Какие альтернативы пробовали?

**Обязательные модули (20% оценки):**
- Покажи MCP-сервер. Почему MCP а не обычный API вызов?
- Покажи SKILL.md. Когда Skill полезнее обычного промпта?
- Где в проекте мультимодальность? Что было бы потеряно без неё?
- Покажи LangSmith дашборд с реальными трейсами

---

## Часть 11 — Смета API

| Что | Модель | Цена | Использование (100 сессий) | Итого |
|---|---|---|---|---|
| Workflow (генерация, оценка) | gpt-4.1-mini | $0.40/1M in, $1.60/1M out | ~600K in + 150K out | ~$0.48 |
| Final feedback | gpt-4.1 | $2/1M in, $8/1M out | ~100K in + 50K out | ~$0.60 |
| Embeddings | text-embedding-3-small | $0.02/1M | ~500K токенов | ~$0.01 |
| Whisper | whisper-1 | $0.006/мин | ~50 мин аудио | ~$0.30 |
| Evals (прогоны датасета) | gpt-4.1-mini | — | ~200K токенов | ~$0.10 |
| **Итого за всю разработку** | | | | **~$5–15** |

---

*Последнее обновление: [дата] — обновляй при каждом закрытом этапе*
