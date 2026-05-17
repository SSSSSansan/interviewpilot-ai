"""
run_evals.py — запускает golden dataset через evaluate_answer и считает метрики.

Использование:
  python evals/run_evals.py              # A вариант промпта (простой)
  python evals/run_evals.py --variant b  # B вариант промпта (с рубрикой)

Результаты сохраняются в evals/results_a.json или evals/results_b.json
"""

import asyncio
import json
import os
import sys
import argparse
import statistics
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv()

from langchain_openai import ChatOpenAI

# ── Промпты для A/B теста ──────────────────────────────────────────────

PROMPT_A = """Оцени ответ кандидата на технический вопрос.

Роль: {role}
Вопрос: {question}
Ответ: {answer}

Поставь оценку от 0 до 10. Дай краткий фидбек.

Верни ТОЛЬКО валидный JSON:
{{
  "total_score": 5,
  "feedback": "краткий фидбек"
}}"""

PROMPT_B = """Ты технический интервьюер. Оцени ответ кандидата строго по рубрике.

Роль: {role}
Вопрос: {question}
Ответ кандидата: {answer}

Оцени по 5 критериям (каждый строго 0, 1 или 2):
- technical_correctness: технически верно?
- clarity: понятно изложено?
- depth: достаточно глубоко?
- confidence: уверенно?
- communication: структурированно?

is_weak = true если сумма < 6.

ideal_answer — пример сильного ответа (3-5 предложений).

Верни ТОЛЬКО валидный JSON без markdown:
{{
  "scores": {{"technical_correctness": 1, "clarity": 1, "depth": 1, "confidence": 1, "communication": 1}},
  "total_score": 5,
  "feedback": "конкретный фидбек 2-3 предложения",
  "ideal_answer": "пример сильного ответа",
  "is_weak": true
}}"""

JUDGE_PROMPT = """Оцени качество фидбека технического интервьюера по шкале 1-5.

Вопрос: {question}
Ответ кандидата: {answer}
Фидбек интервьюера: {feedback}

Критерии оценки фидбека:
1 — бесполезный, слишком общий
2 — есть конкретика но мало
3 — средний, есть полезные моменты
4 — хороший, конкретный и actionable
5 — отличный, точно указывает что улучшить и как

Верни ТОЛЬКО JSON:
{{"judge_score": 4, "reason": "одно предложение почему"}}"""


async def evaluate_single(llm, prompt_template: str, item: dict) -> dict:
    """Прогоняет один пример через модель."""
    prompt = prompt_template.format(
        role=item["role"],
        question=item["question"],
        answer=item["answer"]
    )

    response = await llm.ainvoke(prompt)
    raw = response.content.strip().replace("```json", "").replace("```", "").strip()

    try:
        result = json.loads(raw)
        total_score = result.get("total_score", 0)

        # Для промпта A total_score уже есть
        # Для промпта B считаем из scores если есть
        if "scores" in result:
            total_score = sum(result["scores"].values())
            result["total_score"] = total_score

        return {
            "id": item["id"],
            "role": item["role"],
            "question": item["question"],
            "answer_type": item["answer_type"],
            "expected_min": item["expected_score_min"],
            "expected_max": item["expected_score_max"],
            "actual_score": total_score,
            "feedback": result.get("feedback", ""),
            "in_range": item["expected_score_min"] <= total_score <= item["expected_score_max"],
            "raw_result": result
        }
    except json.JSONDecodeError:
        return {
            "id": item["id"],
            "role": item["role"],
            "question": item["question"],
            "answer_type": item["answer_type"],
            "expected_min": item["expected_score_min"],
            "expected_max": item["expected_score_max"],
            "actual_score": -1,
            "feedback": "",
            "in_range": False,
            "parse_error": True,
            "raw_result": {}
        }


async def judge_feedback(llm, item_result: dict) -> int:
    """LLM-as-judge: оценивает качество фидбека по шкале 1-5."""
    if not item_result.get("feedback"):
        return 0

    prompt = JUDGE_PROMPT.format(
        question=item_result["question"],
        answer=item_result.get("answer_type", ""),
        feedback=item_result["feedback"]
    )

    response = await llm.ainvoke(prompt)
    raw = response.content.strip().replace("```json", "").replace("```", "").strip()

    try:
        result = json.loads(raw)
        return result.get("judge_score", 0)
    except json.JSONDecodeError:
        return 0


async def run_evals(variant: str = "a"):
    print(f"\n{'='*50}")
    print(f"  InterviewPilot — Evals Runner (Вариант {variant.upper()})")
    print(f"{'='*50}\n")

    # Загружаем датасет
    dataset_path = os.path.join(os.path.dirname(__file__), "golden_dataset.json")
    with open(dataset_path, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    print(f"Загружено примеров: {len(dataset)}")

    # Выбираем промпт
    prompt_template = PROMPT_A if variant == "a" else PROMPT_B
    print(f"Промпт: {'A (простой)' if variant == 'a' else 'B (с рубрикой)'}\n")

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.1)

    # Прогоняем все примеры
    print("Прогоняем примеры...")
    results = []
    for i, item in enumerate(dataset):
        result = await evaluate_single(llm, prompt_template, item)
        results.append(result)
        status = "✅" if result["in_range"] else "❌"
        print(f"  {status} [{i+1:2d}/30] {result['answer_type']:10s} | "
              f"ожидали {result['expected_min']}-{result['expected_max']}, "
              f"получили {result['actual_score']}")

    # Считаем LLM-as-judge
    print("\nЗапускаем LLM-as-judge...")
    judge_scores = []
    for result in results:
        score = await judge_feedback(llm, result)
        result["judge_score"] = score
        judge_scores.append(score)

    # ── Метрики ──────────────────────────────────────────────────────
    total = len(results)
    in_range = sum(1 for r in results if r["in_range"])
    accuracy = in_range / total * 100

    # Accuracy по типам ответов
    by_type = {}
    for r in results:
        t = r["answer_type"]
        if t not in by_type:
            by_type[t] = {"total": 0, "correct": 0}
        by_type[t]["total"] += 1
        if r["in_range"]:
            by_type[t]["correct"] += 1

    # Consistency — прогоняем 3 раза первые 5 примеров
    print("\nПроверяем consistency (3 прогона × 5 примеров)...")
    consistency_scores = {item["id"]: [] for item in dataset[:5]}
    for run in range(3):
        for item in dataset[:5]:
            result = await evaluate_single(llm, prompt_template, item)
            consistency_scores[item["id"]].append(result["actual_score"])

    consistency_stds = []
    for item_id, scores in consistency_scores.items():
        if len(scores) > 1:
            std = statistics.stdev(scores)
            consistency_stds.append(std)

    avg_std = statistics.mean(consistency_stds) if consistency_stds else 0
    avg_judge = statistics.mean([s for s in judge_scores if s > 0]) if judge_scores else 0

    # ── Вывод результатов ──────────────────────────────────────────
    print(f"\n{'='*50}")
    print(f"  РЕЗУЛЬТАТЫ — Вариант {variant.upper()}")
    print(f"{'='*50}")
    print(f"  Accuracy:       {accuracy:.1f}%  ({in_range}/{total} в диапазоне)")
    print(f"  LLM-as-judge:   {avg_judge:.2f}/5.0 (качество фидбека)")
    print(f"  Consistency:    σ={avg_std:.2f} (меньше = стабильнее)")
    print(f"\n  По типам ответов:")
    for t, stats in by_type.items():
        t_acc = stats["correct"] / stats["total"] * 100
        print(f"    {t:12s}: {t_acc:.0f}% ({stats['correct']}/{stats['total']})")
    print(f"{'='*50}\n")

    # Сохраняем результаты
    output = {
        "variant": variant.upper(),
        "timestamp": datetime.now().isoformat(),
        "prompt_type": "simple" if variant == "a" else "rubric",
        "metrics": {
            "accuracy": round(accuracy, 1),
            "total_examples": total,
            "in_range": in_range,
            "llm_as_judge_avg": round(avg_judge, 2),
            "consistency_std_avg": round(avg_std, 2),
            "by_type": {
                t: {
                    "accuracy": round(s["correct"] / s["total"] * 100, 1),
                    "correct": s["correct"],
                    "total": s["total"]
                }
                for t, s in by_type.items()
            }
        },
        "results": results
    }

    out_path = os.path.join(os.path.dirname(__file__), f"results_{variant}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"Результаты сохранены: evals/results_{variant}.json")
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--variant", choices=["a", "b"], default="a",
                        help="a = простой промпт, b = промпт с рубрикой")
    args = parser.parse_args()
    asyncio.run(run_evals(args.variant))