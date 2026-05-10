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
    if (!r) { router.push("/"); return; }
    try { setReport(JSON.parse(r)); } catch { setReport(r); }
    setScores(s ? JSON.parse(s) : []);
    setRole(sessionStorage.getItem("role") || "");
  }, []);

  const avgScore = scores.length
    ? (scores.reduce((a, s) => a + (s.total_score || 0), 0) / scores.length).toFixed(1)
    : "—";

  const hire = Number(avgScore) >= 7 ? "Hire" : Number(avgScore) >= 5 ? "Maybe" : "No hire";
  const hireColor = hire === "Hire"
    ? "text-emerald-700 bg-emerald-50 border-emerald-200"
    : hire === "Maybe"
    ? "text-amber-700 bg-amber-50 border-amber-200"
    : "text-red-700 bg-red-50 border-red-200";

  const scoreColor = (s: number) =>
    s >= 7 ? "#059669" : s >= 5 ? "#D97706" : "#DC2626";

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

        {/* Summary header */}
        <div className="bg-white rounded-xl border border-[#E4E4E7] px-6 py-5 flex items-center justify-between">
          <div>
            <p className="text-xl font-semibold text-[#18181B] tracking-tight">Интервью завершено</p>
            <p className="text-sm text-[#A1A1AA] mt-0.5">{role} · {scores.length} вопросов</p>
          </div>
          <div className="text-right">
            <div className="text-4xl font-semibold text-[#18181B] tracking-tight">{avgScore}</div>
            <div className="text-xs text-[#A1A1AA]">из 10</div>
          </div>
        </div>

        {/* Hire badge */}
        <div className="flex items-center gap-2">
          <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-lg border text-sm font-medium ${hireColor}`}>
            {hire === "Hire" ? "✓" : hire === "Maybe" ? "~" : "✗"} {hire}
          </span>
          <span className="text-xs text-[#A1A1AA]">на основе среднего балла {avgScore}/10</span>
        </div>

        {/* Per-question scores */}
        {scores.length > 0 && (
          <div className="bg-white rounded-xl border border-[#E4E4E7] overflow-hidden">
            <div className="px-5 py-3 border-b border-[#E4E4E7]">
              <span className="text-xs font-medium text-[#A1A1AA] uppercase tracking-widest">По вопросам</span>
            </div>
            {scores.map((s, i) => (
              <div
                key={i}
                className="px-5 py-3 flex items-center gap-4 border-b border-[#F4F4F5] last:border-0"
              >
                <span className="text-xs text-[#A1A1AA] w-16">Вопрос {i + 1}</span>
                <div className="flex-1 h-1.5 bg-[#F4F4F5] rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all"
                    style={{
                      width: `${(s.total_score / 10) * 100}%`,
                      backgroundColor: scoreColor(s.total_score),
                    }}
                  />
                </div>
                <span
                  className="text-sm font-semibold w-10 text-right"
                  style={{ color: scoreColor(s.total_score) }}
                >
                  {s.total_score}/10
                </span>
              </div>
            ))}
          </div>
        )}

        {/* Final report */}
        <div className="bg-white rounded-xl border border-[#E4E4E7] overflow-hidden">
          <div className="px-5 py-3 border-b border-[#E4E4E7]">
            <span className="text-xs font-medium text-[#A1A1AA] uppercase tracking-widest">Детальный фидбек</span>
          </div>
          <div className="px-5 py-4">
            <p className="text-sm text-[#18181B] leading-relaxed whitespace-pre-wrap">{report}</p>
          </div>
        </div>

        {/* Actions */}
        <div className="flex gap-3">
          <button
            onClick={() => { sessionStorage.clear(); router.push("/"); }}
            className="flex-1 py-2.5 rounded-xl bg-[#18181B] text-white text-sm font-medium hover:bg-[#27272A] transition-colors"
          >
            Пройти ещё раз
          </button>
        </div>
      </div>
    </main>
  );
}
