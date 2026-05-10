"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { startInterview } from "@/lib/api";

const ROLES = [
  { id: "Backend Engineer", icon: "⚙️", desc: "API, databases, architecture" },
  { id: "Frontend Engineer", icon: "🎨", desc: "React, CSS, browser APIs" },
  { id: "ML Engineer", icon: "🧠", desc: "Models, training, deployment" },
  { id: "Data Analyst", icon: "📊", desc: "SQL, statistics, A/B tests" },
  { id: "Product Manager", icon: "🧭", desc: "Prioritization, metrics, roadmap" },
];

export default function Home() {
  const router = useRouter();
  const [role, setRole] = useState("Backend Engineer");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleStart() {
    setLoading(true);
    setError("");
    try {
      const data = await startInterview(role);
      sessionStorage.setItem("thread_id", data.thread_id);
      sessionStorage.setItem("question", data.question);
      sessionStorage.setItem("question_number", String(data.question_number));
      sessionStorage.setItem("total_questions", String(data.total_questions));
      sessionStorage.setItem("role", role);
      router.push("/interview");
    } catch {
      setError("Не удалось запустить интервью. Проверь что бэкенд запущен.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen bg-[#FAFAF9] flex items-center justify-center p-6">
      <div className="w-full max-w-lg">

        {/* Header */}
        <div className="mb-10">
          <div className="inline-flex items-center gap-2 mb-5">
            <div className="w-7 h-7 rounded-lg bg-[#18181B] flex items-center justify-center">
              <span className="text-white text-xs font-bold">IP</span>
            </div>
            <span className="text-sm font-medium text-[#18181B] tracking-tight">InterviewPilot</span>
          </div>
          <h1 className="text-3xl font-semibold text-[#18181B] tracking-tight leading-tight">
            Подготовься к<br />техническому интервью
          </h1>
          <p className="mt-2 text-[#71717A] text-sm leading-relaxed">
            AI задаёт вопросы по твоей роли, оценивает ответы<br />и даёт детальный фидбек после каждого.
          </p>
        </div>

        {/* Role selector */}
        <div className="mb-5">
          <p className="text-xs font-medium text-[#71717A] uppercase tracking-widest mb-3">Выбери направление</p>
          <div className="grid grid-cols-1 gap-2">
            {ROLES.map((r) => (
              <button
                key={r.id}
                onClick={() => setRole(r.id)}
                className={`flex items-center gap-3 px-4 py-3 rounded-xl border text-left transition-all duration-150 ${
                  role === r.id
                    ? "border-[#18181B] bg-white shadow-sm"
                    : "border-[#E4E4E7] bg-white hover:border-[#A1A1AA]"
                }`}
              >
                <span className="text-lg">{r.icon}</span>
                <div className="flex-1">
                  <span className="text-sm font-medium text-[#18181B]">{r.id}</span>
                  <span className="text-xs text-[#A1A1AA] ml-2">{r.desc}</span>
                </div>
                {role === r.id && (
                  <div className="w-2 h-2 rounded-full bg-[#18181B]" />
                )}
              </button>
            ))}
          </div>
        </div>

        {error && (
          <p className="text-red-500 text-xs mb-4 px-1">{error}</p>
        )}

        {/* CTA */}
        <button
          onClick={handleStart}
          disabled={loading}
          className="w-full py-3 rounded-xl bg-[#18181B] text-white text-sm font-medium tracking-tight hover:bg-[#27272A] disabled:bg-[#A1A1AA] disabled:cursor-not-allowed transition-colors"
        >
          {loading ? "Запускаем..." : "Начать интервью →"}
        </button>

        <div className="flex items-center justify-center gap-6 mt-6">
          {[["3–5", "вопросов"], ["5", "критериев"], ["AI", "фидбек"]].map(([val, label]) => (
            <div key={label} className="text-center">
              <div className="text-sm font-semibold text-[#18181B]">{val}</div>
              <div className="text-xs text-[#A1A1AA]">{label}</div>
            </div>
          ))}
        </div>
      </div>
    </main>
  );
}
