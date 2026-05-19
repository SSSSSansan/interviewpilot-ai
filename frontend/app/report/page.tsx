"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

export default function ReportPage() {
  const router = useRouter();
  const [report, setReport] = useState<string>("");
  const [scores, setScores] = useState<any[]>([]);
  const [role, setRole] = useState("");

  useEffect(() => {
    const r = sessionStorage.getItem("final_report");
    const s = sessionStorage.getItem("all_scores");
    const total = sessionStorage.getItem("total_questions"); // добавь это
    if (!r) { router.push("/"); return; }
    try { setReport(JSON.parse(r)); } catch { setReport(r); }
    
    // берём только последние N scores где N = total_questions
    if (s) {
      const allScores = JSON.parse(s);
      const totalQ = Number(total) || 3;
      // берём последние totalQ уникальных оценок
      setScores(allScores.slice(-totalQ));
    }
    setRole(sessionStorage.getItem("role") || "");
  }, []);
  const avgScore = scores.length
    ? (scores.reduce((a, s) => a + (s.total_score || 0), 0) / scores.length).toFixed(1)
    : "—";

  const avg = Number(avgScore);
  const hire = avg >= 7 ? "Hire" : avg >= 5 ? "Maybe" : "No Hire";
  const hireColor = hire === "Hire"
    ? "text-emerald-700 bg-emerald-50 border-emerald-200"
    : hire === "Maybe"
    ? "text-amber-700 bg-amber-50 border-amber-200"
    : "text-red-700 bg-red-50 border-red-200";

  const scoreColor = (s: number) =>
    s >= 7 ? "#059669" : s >= 5 ? "#D97706" : "#DC2626";

  // Парсим markdown-отчёт в секции
  const parseReport = (text: string) => {
    const lines = text.split("\n").filter(l => l.trim());
    const sections: { title: string; items: string[] }[] = [];
    let current: { title: string; items: string[] } | null = null;

    for (const line of lines) {
      const clean = line.replace(/^#+\s*/, "").replace(/\*\*/g, "").trim();
      if (line.startsWith("#") || /^\d+\./.test(line)) {
        if (current) sections.push(current);
        current = { title: clean.replace(/^\d+\.\s*/, ""), items: [] };
      } else if (line.startsWith("-") || line.startsWith("•")) {
        current?.items.push(clean.replace(/^[-•]\s*/, ""));
      } else if (clean && current) {
        current.items.push(clean);
      }
    }
    if (current) sections.push(current);
    return sections;
  };

  const sections = parseReport(report);

  const sectionIcon: Record<string, string> = {
    "Общая оценка": "📋",
    "Сильные стороны": "✅",
    "Зоны роста": "📈",
    "Рекомендация": "🎯",
  };

  const sectionBg: Record<string, string> = {
    "Сильные стороны": "bg-emerald-50 border-emerald-200",
    "Зоны роста": "bg-amber-50 border-amber-200",
    "Рекомендация": "bg-blue-50 border-blue-200",
    "Общая оценка": "bg-white border-[#E4E4E7]",
  };

  return (
    <main className="min-h-screen bg-[#FAFAF9]">

      {/* Top bar */}
      <div className="border-b border-[#E4E4E7] bg-white px-6 py-3 flex items-center gap-3">
        <div className="w-6 h-6 rounded-md bg-[#18181B] flex items-center justify-center">
          <span className="text-white text-[10px] font-bold">IP</span>
        </div>
        <span className="text-sm text-[#A1A1AA]">/</span>
        <span className="text-sm font-medium text-[#18181B]">Отчёт</span>
        <span className="text-sm text-[#A1A1AA]">/</span>
        <span className="text-sm text-[#A1A1AA]">{role}</span>
      </div>

      <div className="max-w-2xl mx-auto px-6 py-10 flex flex-col gap-5">

        {/* Hero — итог */}
        <div className="bg-white rounded-2xl border border-[#E4E4E7] px-6 py-6">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-xs font-medium text-[#A1A1AA] uppercase tracking-widest mb-1">
                Результат интервью
              </p>
              <p className="text-2xl font-semibold text-[#18181B] tracking-tight">
                {role}
              </p>
              <p className="text-sm text-[#71717A] mt-0.5">
                {scores.length} вопросов · средний балл {avgScore}/10
              </p>
            </div>
            <div className="text-right">
              <div className="text-5xl font-bold text-[#18181B] tracking-tight leading-none">
                {avgScore}
              </div>
              <div className="text-xs text-[#A1A1AA] mt-1">из 10</div>
            </div>
          </div>

          {/* Progress bar общий */}
          <div className="mt-4 h-2 bg-[#F4F4F5] rounded-full overflow-hidden">
            <div
              className="h-full rounded-full transition-all duration-700"
              style={{
                width: `${(avg / 10) * 100}%`,
                backgroundColor: scoreColor(avg),
              }}
            />
          </div>

          {/* Hire badge */}
          <div className="mt-3 flex items-center gap-2">
            <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-lg border text-sm font-semibold ${hireColor}`}>
              {hire === "Hire" ? "✓ Hire" : hire === "Maybe" ? "~ Maybe" : "✗ No Hire"}
            </span>
          </div>
        </div>

        {/* По вопросам */}
        {scores.length > 0 && (
          <div className="bg-white rounded-xl border border-[#E4E4E7] overflow-hidden">
            <div className="px-5 py-3 border-b border-[#E4E4E7]">
              <span className="text-xs font-medium text-[#A1A1AA] uppercase tracking-widest">
                По вопросам
              </span>
            </div>
            {scores.map((s, i) => (
              <div key={i} className="px-5 py-3 flex items-center gap-4 border-b border-[#F4F4F5] last:border-0">
                <span className="text-xs text-[#A1A1AA] w-20 shrink-0">Вопрос {i + 1}</span>
                <div className="flex-1 h-1.5 bg-[#F4F4F5] rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full"
                    style={{
                      width: `${(s.total_score / 10) * 100}%`,
                      backgroundColor: scoreColor(s.total_score),
                    }}
                  />
                </div>
                <span
                  className="text-sm font-semibold w-12 text-right shrink-0"
                  style={{ color: scoreColor(s.total_score) }}
                >
                  {s.total_score}/10
                </span>
              </div>
            ))}
          </div>
        )}

        {/* Секции отчёта */}
        {sections.length > 0 ? (
          sections.map((section, i) => {
            const matchKey = Object.keys(sectionBg).find(k =>
              section.title.toLowerCase().includes(k.toLowerCase())
            );
            const bg = matchKey ? sectionBg[matchKey] : "bg-white border-[#E4E4E7]";
            const icon = matchKey ? sectionIcon[matchKey] : "📌";

            return (
              <div key={i} className={`rounded-xl border px-5 py-4 ${bg}`}>
                <div className="flex items-center gap-2 mb-3">
                  <span className="text-base">{icon}</span>
                  <span className="text-sm font-semibold text-[#18181B]">
                    {section.title}
                  </span>
                </div>
                <div className="flex flex-col gap-2">
                  {section.items.map((item, j) => (
                    <div key={j} className="flex items-start gap-2">
                      {section.items.length > 1 && (
                        <span className="text-[#A1A1AA] mt-0.5 shrink-0">·</span>
                      )}
                      <p className="text-sm text-[#18181B] leading-relaxed">
                        {item}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            );
          })
        ) : (
          /* Fallback если парсинг не сработал */
          <div className="bg-white rounded-xl border border-[#E4E4E7] px-5 py-4">
            <p className="text-sm text-[#18181B] leading-relaxed whitespace-pre-wrap">
              {report}
            </p>
          </div>
        )}

        {/* Кнопка */}
        <button
          onClick={() => { sessionStorage.clear(); router.push("/"); }}
          className="w-full py-3 rounded-xl bg-[#18181B] text-white text-sm font-medium hover:bg-[#27272A] transition-colors"
        >
          Пройти ещё раз →
        </button>
      </div>
    </main>
  );
}