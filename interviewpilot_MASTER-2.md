# InterviewPilot AI — Master Implementation Guide

> **Этот файл — главный контекст проекта.**
> Кидай его в начале любой сессии с LLM. В конце каждого этапа обновляй статус этапа (DONE / IN PROGRESS / TODO) и чеклист задач.

---

## Быстрый статус (реальный, обновлён 11 мая)

| Этап | Статус | Заметки |
|---|---|---|
| Этап 1 — Фундамент и инфраструктура | DONE | Репо, Docker, LangSmith подключён |
| Этап 2 — MCP сервер | DONE | server.py с 3 тулами |
| Этап 3 — Custom Skill | DONE | SKILL.md готов |
| Этап 4 — RAG pipeline | DONE | ChromaDB, ingestion, retrieval |
| Этап 5 — LangGraph workflow | DONE | Граф с ветвлением и циклом |
| Этап 6 — Multimodal (Whisper) | DONE | POST /transcribe работает |
| Этап 7 — Frontend | DONE | Next.js страницы задеплоены |
| Этап 7.5 — PDF парсинг резюме | TODO ⚠️ | Критически важно — без него CV-aware логика не работает |
| Этап 7.6 — Фича: Эталонный ответ | TODO | ideal_answer поле в evaluate_answer |
| Этап 7.7 — Фича: Реакция на "не знаю" | TODO | Новая нода hint_node в LangGraph |
| Этап 7.8 — Фича: Личность интервьюера | TODO | Выбор стиля в начале + system prompt |
| Этап 8 — Evals и A/B тест | TODO | Golden dataset 30 примеров + run_evals.py |
| Этап 9 — Документация и LLM обоснование | TODO | ARCHITECTURE.md, EVALS.md, презентация |
| Этап 10 — Финальная проверка и демо | TODO | Дедлайн 20 мая |

**Дедлайн сдачи:** 20 мая
**Demo Days:** 26–28 мая

> ⚠️ **Важно:** PDF парсинг резюме — нулевой приоритет. Пока его нет, generate_questions работает без CV-данных и вопросы generic. Это нужно закрыть первым делом.

---

## Часть 1 — Описание проекта

### Что это

InterviewPilot AI — веб-приложение для подготовки к техническим собеседованиям.

Пользователь загружает PDF резюме, выбирает целевую роль (Backend Engineer, Frontend, ML Engineer, Data Analyst, Product Manager) и стиль интервьюера, и система проводит персонализированное mock-интервью:
- генерирует вопросы на основе CV и роли
- оценивает ответы по структурированной рубрике
- задаёт follow-up вопросы если ответ слабый
- показывает эталонный ответ после каждой оценки
- реагирует на "не знаю" / пустой ответ — даёт hint как настоящий интервьюер
- в конце выдаёт финальный отчёт с оценкой, сильными/слабыми сторонами и roadmap улучшений

Дополнительно: голосовой режим — пользователь отвечает голосом, система транскрибирует через Whisper и оценивает.

### Проблема которую решаем

Студенты и джуниор-инженеры готовятся к интервью неструктурированно: не знают какие вопросы ждать, нет реалистичной симуляции, нет персонализированного фидбека. InterviewPilot решает это через CV-aware генерацию вопросов, рубричную оценку ответов и интерактивное поведение интервьюера.

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
| PDF парсинг | PyMuPDF (fitz) | Быстро, без внешних зависимостей |
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
│   │   ├── page.tsx                  # Главная — загрузка резюме + выбор роли + выбор интервьюера
│   │   ├── interview/page.tsx        # Страница интервью
│   │   └── report/page.tsx           # Финальный отчёт
│   ├── components/
│   │   ├── ResumeUpload.tsx
│   │   ├── ChatInterface.tsx
│   │   ├── InterviewerSelector.tsx   # Новый компонент выбора стиля интервьюера
│   │   ├── IdealAnswerPanel.tsx      # Новый компонент эталонного ответа
│   │   └── VoiceRecorder.tsx
│   └── package.json
├── mcp/
│   └── server.py                     # Custom MCP сервер (3 тула)
├── skills/
│   └── interview-evaluator/
│       └── SKILL.md
├── evals/
│   ├── golden_dataset.json
│   └── run_evals.py
├── docker-compose.yml
├── .env.example
├── README.md
├── ARCHITECTURE.md
└── EVALS.md
```

### LangGraph Workflow (обновлённый с новыми нодами)

```
[Пользователь загружает PDF + выбирает роль + выбирает стиль интервьюера]
        ↓
  resume_parser_node       # PyMuPDF извлекает текст → GPT структурирует в dict
        ↓
  role_analyzer_node       # Анализирует соответствие CV и роли
        ↓
  question_generator_node  # RAG + MCP generate_questions() → список вопросов
        ↓
  answer_evaluator_node    # MCP evaluate_answer() → score, feedback, ideal_answer
        ↓
  [conditional edge — что за ответ?]
    answer == "не знаю" / пустой / "skip"
                   → hint_node  → ждём новый ответ от пользователя (human-in-the-loop)
    score < 6      → follow_up_node → answer_evaluator_node (цикл, max 2 раза)
    score >= 6     → next_question_node (если вопросы ещё есть)
                     или final_feedback_node (если все закончились)
        ↓
  final_feedback_node      # gpt-4.1, итоговый отчёт
```

**Ключевые параметры:**
- Threshold для follow-up: score < 6 (из 10)
- Максимум follow-up на один вопрос: 2
- Количество вопросов на сессию: 5–7 в зависимости от роли
- Hint срабатывает: если answer содержит "не знаю", "не знаю как", "skip", "" (пустой), "затрудняюсь"

### State (обновлённый)

```python
class InterviewState(TypedDict):
    cv_data: dict               # результат parse_resume
    role: str                   # выбранная роль
    interviewer_style: str      # "strict" | "friendly" | "academic"
    questions: list[str]        # сгенерированные вопросы
    current_question_idx: int
    current_question: str
    current_answer: str
    is_dont_know: bool          # флаг что пользователь не знает ответа
    follow_up_count: int        # счётчик follow-up для текущего вопроса
    scores: list[dict]          # история оценок
    rag_context: str            # retrieved context из ChromaDB
    final_report: dict          # финальный отчёт
```

### MCP Сервер (3 тула — без изменений в интерфейсе, расширен evaluate_answer)

```python
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
        ideal_answer: str,     # ← НОВОЕ: как надо было ответить
        is_weak: bool
    }
    """
```

---

## Часть 3.5 — Три новые фичи (детально)

---

### Фича 1: Эталонный ответ после оценки

**Суть:** После каждой оценки пользователь видит не только score и feedback, но и пример сильного ответа — как именно надо было ответить, с правильными терминами и структурой.

**Зачем это круто:** Самая полезная фича для обучения. Пользователь понимает не только "ты ответил плохо" но и "вот как выглядит хороший ответ". На Demo Days это моментально видно и объяснимо.

**Как реализовать:**

1. В `mcp/server.py` добавить поле `ideal_answer` в промпт `evaluate_answer`:

```python
# В промпте evaluate_answer добавить:
"""
...все предыдущие критерии...

ideal_answer: строка, 3-5 предложений — пример сильного ответа на этот вопрос.
Пиши ideal_answer так, как отвечал бы опытный инженер с 3 годами опыта.
Структурируй: сначала суть, потом детали, потом пример из практики.
"""
```

2. В `InterviewState` поле уже приходит в `scores` — ничего менять в State не нужно.

3. На фронтенде в `interview/page.tsx` после получения ответа от `/session/answer` показывать коллапсируемый блок "Посмотреть эталонный ответ" (по умолчанию скрыт — пользователь сначала думает сам, потом смотрит).

```tsx
// После фидбека:
<details className="mt-4 border rounded-lg p-4 bg-green-50">
  <summary className="cursor-pointer font-medium text-green-800">
    💡 Посмотреть эталонный ответ
  </summary>
  <p className="mt-2 text-green-900">{feedback.ideal_answer}</p>
</details>
```

**Сложность:** низкая. Одно поле в промпте + один UI блок.
**Время:** 2-3 часа.

---

### Фича 2: Реакция на "не знаю"

**Суть:** Если пользователь пишет "не знаю", "затрудняюсь", "пропустить" или оставляет пустое поле — интервьюер не просто переходит дальше, а ведёт себя как живой человек: даёт hint и предлагает попробовать ещё раз.

**Зачем это круто:** Реальные интервьюеры так и делают. Это создаёт эффект присутствия, а не ощущение что ты просто кликаешь кнопки. Плюс это новая нода в LangGraph — дополнительный условный переход для менторов.

**Как реализовать:**

1. В `graph/nodes.py` добавить детектор и новую ноду:

```python
DONT_KNOW_PHRASES = [
    "не знаю", "не знаю как", "затрудняюсь", "skip",
    "пропустить", "не уверен", "i don't know", "idk", ""
]

def is_dont_know(answer: str) -> bool:
    return answer.strip().lower() in DONT_KNOW_PHRASES or len(answer.strip()) < 5

async def hint_node(state: InterviewState) -> InterviewState:
    """
    Генерирует подсказку когда пользователь не знает ответа.
    Hint не раскрывает ответ полностью — только направляет.
    """
    prompt = f"""Ты интервьюер ({state['interviewer_style']} стиль).
Кандидат не знает ответа на вопрос: "{state['current_question']}"

Дай короткую подсказку (1-2 предложения) которая:
- Направляет в правильную сторону, но не даёт готовый ответ
- Звучит как живой интервьюер, не как учитель
- Заканчивается вопросом "Попробуешь ответить?"

Примеры хороших hint'ов:
- "Подумай о том, как данные передаются между клиентом и сервером. Попробуешь ответить?"
- "Вспомни о сложности алгоритмов — с чего бы ты начал? Попробуешь?"
"""
    # вызов gpt-4.1-mini, temp 0.5
    hint = await llm.ainvoke(prompt)
    return {**state, "hint": hint, "awaiting_retry": True}
```

2. В `graph/graph.py` добавить conditional edge:

```python
def route_after_answer(state):
    if is_dont_know(state["current_answer"]):
        return "hint_node"
    elif state["scores"][-1]["score"] < 6 and state["follow_up_count"] < 2:
        return "follow_up_node"
    else:
        return "next_question_or_finish"
```

3. На фронтенде: когда бэкенд возвращает `hint` вместо `feedback` — показывать hint bubble и поле для повторного ответа.

**Сложность:** средняя. Новая нода + conditional edge + небольшое изменение фронта.
**Время:** 4-5 часов.

---

### Фича 3: Личность интервьюера

**Суть:** В начале пользователь выбирает стиль интервьюера. Это меняет tone of voice во всех промптах.

| Стиль | Поведение |
|---|---|
| 🧊 Строгий (FAANG) | Лаконичный, без лишних слов, сразу follow-up если ответ слабый |
| 😊 Дружелюбный (стартап) | Подбадривает, объясняет почему вопрос важен |
| 🎓 Академичный | Просит формальные определения, ссылается на теорию |

**Зачем это круто:** Нулевые затраты на инфраструктуру — это просто system prompt. Но визуально и с точки зрения опыта — огромная разница. На Demo Days сразу видно "живой" продукт. Плюс добавляет replay value: пользователь захочет пройти снова с другим стилем.

**Как реализовать:**

1. На главной странице добавить выбор (3 карточки с иконками):

```tsx
// components/InterviewerSelector.tsx
const styles = [
  { id: "strict",   icon: "🧊", label: "Строгий", desc: "FAANG-стиль, без поблажек" },
  { id: "friendly", icon: "😊", label: "Дружелюбный", desc: "Стартап CTO, поддерживает" },
  { id: "academic", icon: "🎓", label: "Академичный", desc: "Просит точные определения" },
]
```

2. В `InterviewState` добавить поле `interviewer_style: str` (уже добавлено выше).

3. В каждом промпте добавить personality prefix:

```python
INTERVIEWER_PROMPTS = {
    "strict": "Ты строгий технический интервьюер из крупной tech-компании. "
              "Краткие, точные вопросы. Никаких похвал. Сразу переходи к сути.",
    "friendly": "Ты дружелюбный CTO стартапа. Поддерживаешь кандидата, "
                "объясняешь зачем важен вопрос. Но стандарты не снижаешь.",
    "academic": "Ты академичный технический интервьюер. Просишь точные определения, "
                "ссылаешься на Computer Science принципы. Оцениваешь строгость формулировок.",
}
```

4. В `POST /session/start` принимать `interviewer_style` как параметр.

**Сложность:** низкая. Только промпты + UI выбор + один новый параметр в API.
**Время:** 3-4 часа.

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
Верни JSON с полями: scores (dict), total (int), feedback (str), ideal_answer (str)
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
| hint_node | gpt-4.1-mini | 0.5 | Лёгкая задача — направляющая подсказка |
| resume_parser | gpt-4.1-mini | 0.0 | Extraction задача, нужна детерминированность |
| final_feedback | gpt-4.1 | 0.3 | Финальный отчёт требует высокого качества |

**Почему gpt-4.1-mini а не Claude/Gemini/локальная:**
- Claude Sonnet сопоставим по качеству, но экосистема LangGraph лучше протестирована с OpenAI
- Gemini — меньше документации для LangGraph интеграции
- Локальная модель — latency слишком высокая для real-time интервью, качество хуже для русскоязычного контента

**Стоимость одной сессии (~10 вопросов):** ~$0.02–0.03

---

## Часть 6 — API Endpoints (обновлённые)

```
POST /session/start
  Body: { resume_pdf: file, role: str, interviewer_style: str }
  Response: { session_id: str, first_question: str, interviewer_intro: str }

POST /session/answer
  Body: { session_id: str, answer: str }
  Response: {
    type: "hint" | "feedback" | "complete",
    hint: str | null,          # если тип hint
    feedback: str | null,      # если тип feedback
    score: int | null,
    ideal_answer: str | null,  # всегда при feedback
    next_question: str | null,
    is_complete: bool
  }

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

### Этап 7.5 — PDF парсинг резюме ⚠️ ПРИОРИТЕТ №1

**Статус: TODO**
**Оценка времени: 3-4 часа**

**Почему критично:** Без PDF парсинга `generate_questions` не получает CV-данные и генерирует generic вопросы. Вся персонализация, которая является сутью продукта, не работает.

**Задачи:**

- [ ] Убедиться что PyMuPDF установлен: `pip install pymupdf`
- [ ] Реализовать `backend/app/services/resume_parser.py`:

```python
import fitz  # PyMuPDF
from openai import AsyncOpenAI

async def parse_resume_pdf(pdf_bytes: bytes) -> dict:
    """
    Принимает PDF как bytes, возвращает структурированные данные CV.
    """
    # Шаг 1: Извлечь текст из PDF
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text()
    doc.close()

    # Шаг 2: Структурировать через GPT
    client = AsyncOpenAI()
    response = await client.chat.completions.create(
        model="gpt-4.1-mini",
        temperature=0.0,
        messages=[{
            "role": "user",
            "content": f"""Извлеки из резюме структурированные данные. Верни только JSON, без markdown.

Резюме:
{text}

Верни JSON:
{{
  "skills": ["список навыков"],
  "tech_stack": ["список технологий"],
  "years_experience": 0,
  "projects": ["краткое описание проектов"],
  "education": "образование одной строкой",
  "languages": ["языки программирования"]
}}"""
        }]
    )
    import json
    return json.loads(response.choices[0].message.content)
```

- [ ] Подключить `parse_resume_pdf` к роуту `POST /session/start`:
  - Принять `resume_pdf` как `UploadFile`
  - Прочитать `pdf_bytes = await resume_pdf.read()`
  - Вызвать `cv_data = await parse_resume_pdf(pdf_bytes)`
  - Передать `cv_data` в `InterviewState`

- [ ] Обновить MCP тул `parse_resume` — он теперь может просто вызывать `parse_resume_pdf` или быть заменён прямым вызовом сервиса (решить что проще интегрировать)

- [ ] Протестировать: залить своё реальное резюме, убедиться что `cv_data` содержит правильные данные

- [ ] Убедиться что `generate_questions` получает `cv_data` и использует его в промпте

**Критерий завершения:** после загрузки PDF, первый вопрос интервью упоминает конкретный навык или проект из резюме.

---

### Этап 7.6 — Фича: Эталонный ответ

**Статус: TODO**
**Оценка времени: 2-3 часа**

**Задачи:**

- [ ] В `mcp/server.py` добавить `ideal_answer` в промпт тула `evaluate_answer`:
  - После секции с критериями оценки добавить инструкцию генерировать `ideal_answer` (3-5 предложений)
  - Добавить поле в JSON схему ответа
- [ ] Убедиться что `ideal_answer` доходит через API до фронтенда (проверить `/session/answer` response)
- [ ] В `interview/page.tsx` добавить компонент `IdealAnswerPanel`:
  - По умолчанию скрыт (accordion / details)
  - Заголовок: "💡 Посмотреть эталонный ответ"
  - Показывается только после того как пользователь нажал "Отправить ответ"
- [ ] Убедиться что в LangSmith трейсе видно поле `ideal_answer` в выводе ноды `answer_evaluator`

**Критерий завершения:** после оценки появляется кнопка "Посмотреть эталонный ответ" и при нажатии показывается качественный пример ответа.

---

### Этап 7.7 — Фича: Реакция на "не знаю"

**Статус: TODO**
**Оценка времени: 4-5 часов**

**Задачи:**

- [ ] Добавить в `InterviewState` поля: `is_dont_know: bool`, `hint: str`, `awaiting_retry: bool`
- [ ] Создать хелпер `is_dont_know(answer: str) -> bool` в `graph/nodes.py`
- [ ] Реализовать `hint_node` (см. код в Части 3.5)
- [ ] Обновить conditional edge в `graph/graph.py` — добавить `route_after_answer` функцию (см. Часть 3.5)
- [ ] Обновить API ответ `/session/answer` — добавить поле `type: "hint" | "feedback" | "complete"`
- [ ] На фронтенде в `interview/page.tsx`:
  - Если `response.type === "hint"` — показать hint bubble (другой стиль, иконка интервьюера)
  - Поле ответа остаётся доступным, кнопка "Попробовать снова"
  - После retry — обычный флоу оценки
- [ ] Проверить в LangSmith что `hint_node` видна как отдельная нода в трейсе

**Критерий завершения:** ввод "не знаю" показывает hint от интервьюера и предлагает ответить снова, а не просто переходит к следующему вопросу.

---

### Этап 7.8 — Фича: Личность интервьюера

**Статус: TODO**
**Оценка времени: 3-4 часа**

**Задачи:**

- [ ] Добавить `interviewer_style: str` в `InterviewState`
- [ ] Создать `INTERVIEWER_PROMPTS` dict в `graph/nodes.py` (см. код в Части 3.5)
- [ ] Обновить промпты нод `question_generator`, `answer_evaluator`, `follow_up`, `hint_node` — добавить personality prefix в начало каждого system message
- [ ] Обновить `POST /session/start` — принимать `interviewer_style` (default: "friendly")
- [ ] Создать `components/InterviewerSelector.tsx` — 3 карточки с иконками и описанием
- [ ] Добавить `InterviewerSelector` на главную страницу (`app/page.tsx`) между выбором роли и кнопкой "Начать"
- [ ] Проверить что при выборе "Строгий" — тон заметно отличается от "Дружелюбного"

**Критерий завершения:** при выборе разных стилей, ответы интервьюера заметно отличаются по тону. Демонстрируется на Demo Days как первое что показываешь.

---

### Этап 8 — Evals и A/B тест

**Статус: TODO**
**Оценка времени: 1 день**

**Задачи:**

- [ ] Составить `evals/golden_dataset.json` — минимум 30 примеров (структура выше)
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
- [ ] Добавить LLM-as-judge метрику (отдельный GPT вызов оценивает качество feedback строки 1–5)
- [ ] Написать `EVALS.md` с таблицей результатов A/B и выводами

**Критерий завершения:** `python evals/run_evals.py` выполняется без ошибок, EVALS.md содержит таблицу сравнения A/B с числовыми результатами.

---

### Этап 9 — Документация и LLM обоснование

**Статус: TODO**
**Оценка времени: 1 день**

**Задачи:**

- [ ] Финализировать `ARCHITECTURE.md`:
  - Диаграмма всей системы с новыми нодами (hint_node, InterviewerSelector)
  - Путь одного запроса от пользователя до ответа (шаг за шагом)
  - Секция: почему LangGraph (а не CrewAI/Parlant)
  - Секция: почему ChromaDB (а не Qdrant/Pinecone)
  - Секция: trade-offs которые были сделаны сознательно
- [ ] Добавить в README секцию "Выбор LLM и гиперпараметры"
- [ ] Добавить базовый guardrail в `evaluate_answer` ноду (защита от prompt injection)
- [ ] Подготовить презентацию (10–15 слайдов):
  - Слайд 1: Проблема
  - Слайд 2: Решение + demo ссылка
  - Слайды 3–5: Архитектура + LangGraph граф (с новыми нодами)
  - Слайды 6–8: RAG + MCP + Skill
  - Слайд 9: Три новые фичи (эталонный ответ, hint, личность) — WOW слайд
  - Слайды 10–11: Evals + A/B результаты
  - Слайд 12: Cost анализ (сколько стоит 1 сессия)
  - Слайд 13: Выводы + что бы сделал иначе
- [ ] Обновить README с публичной ссылкой на демо

**Критерий завершения:** все 4 документа готовы, презентация сделана.

---

### Этап 10 — Финальная проверка и демо

**Статус: TODO**
**Даты: 18–20 мая**

**Задачи:**

- [ ] Прогнать финальный чеклист курса (см. ниже)
- [ ] Проверить что `docker compose up` поднимает всё с нуля
- [ ] Проверить публичный деплой end-to-end
- [ ] Открыть LangSmith дашборд — убедиться что трейсы реальных сессий видны, включая новые ноды
- [ ] Сдать репозиторий менторам до 20 мая
- [ ] Прорепетировать 10-минутную защиту
- [ ] Подготовить ноутбук для Demo Days: браузер открыт на демо, LangSmith дашборд открыт

---

## Часть 9 — Финальный чеклист курса

**Обязательные:**
- [ ] Собственный MCP-сервер с 3 тулами (parse_resume, generate_questions, evaluate_answer)
- [ ] Собственный Skill с SKILL.md
- [ ] LangGraph workflow с многошаговым графом, ветвлением и циклом (включая hint_node)
- [ ] RAG-пайплайн с обоснованным выбором chunking + embedding + ChromaDB
- [ ] Обработка PDF (PyMuPDF → GPT структуризация)
- [ ] Мультимодальность: Whisper speech-to-text
- [ ] LangSmith логирование — реальные трейсы видны
- [ ] Golden dataset 30+ примеров + автоматизированный прогон evals
- [ ] A/B эксперимент с числовыми результатами
- [ ] Обоснованный выбор LLM и гиперпараметров
- [ ] Веб-фронтенд (Next.js)
- [ ] GitHub репозиторий с README
- [ ] ARCHITECTURE.md или mindmap
- [ ] EVALS.md с метриками и результатами A/B
- [ ] Презентация 10–15 слайдов

**Рекомендуемые:**
- [ ] Docker + docker-compose
- [ ] Деплой на публичный URL
- [ ] Guardrails (защита от prompt injection)
- [ ] Три новые фичи (эталонный ответ + hint + личность) — прямо повышают оценку

---

## Часть 10 — Вопросы менторов (готовься к ответам)

**Архитектура (40% оценки):**
- Почему LangGraph а не CrewAI или Parlant?
- Покажи путь одного запроса от загрузки PDF до финального отчёта
- Где в графе ветвление? Где цикл? (hint_node — ещё один условный переход!)
- Почему gpt-4.1-mini для workflow, а gpt-4.1 для финального фидбека?
- Сколько стоит одна пользовательская сессия? (~$0.02–0.03)
- Что произойдёт если OpenAI API недоступно?

**LLM-инженерия (25% оценки):**
- Как эволюционировал промпт для evaluate_answer? (v1 — простой, v2 — рубрика с ideal_answer)
- Что в golden dataset? Почему именно эти примеры? Как покрываются edge cases?
- Расскажи про A/B: гипотеза, что сравнивали, результат?
- Как устроен RAG: chunking, embeddings, retrieval?

**Обязательные модули (20% оценки):**
- Покажи MCP-сервер. Почему MCP а не обычный API вызов?
- Покажи SKILL.md. Когда Skill полезнее обычного промпта?
- Где мультимодальность? (Whisper для голосового режима)
- Покажи LangSmith дашборд с реальными трейсами

---

## Часть 11 — Смета API

| Что | Модель | Цена | Использование (100 сессий) | Итого |
|---|---|---|---|---|
| Workflow (генерация, оценка, hint) | gpt-4.1-mini | $0.40/1M in, $1.60/1M out | ~700K in + 200K out | ~$0.60 |
| Final feedback | gpt-4.1 | $2/1M in, $8/1M out | ~100K in + 50K out | ~$0.60 |
| Embeddings | text-embedding-3-small | $0.02/1M | ~500K токенов | ~$0.01 |
| Whisper | whisper-1 | $0.006/мин | ~50 мин аудио | ~$0.30 |
| Evals (прогоны датасета) | gpt-4.1-mini | — | ~200K токенов | ~$0.10 |
| **Итого за всю разработку** | | | | **~$5–15** |

---

## Порядок работы на оставшиеся 9 дней

| День | Что делать |
|---|---|
| День 1-2 (11-12 мая) | **Этап 7.5** — PDF парсинг. Без него не работает ничего. |
| День 2-3 (12-13 мая) | **Этап 7.6** — Эталонный ответ (быстро, 2-3 часа) |
| День 3-4 (13-14 мая) | **Этап 7.7** — Реакция на "не знаю" |
| День 4-5 (14-15 мая) | **Этап 7.8** — Личность интервьюера |
| День 5-6 (15-16 мая) | **Этап 8** — Evals и A/B тест |
| День 7-8 (17-18 мая) | **Этап 9** — Документация и презентация |
| День 9 (19-20 мая) | **Этап 10** — Финальная проверка, сдача |

---

*Последнее обновление: 11 мая 2026*
