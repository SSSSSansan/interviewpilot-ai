"use client";
import { useState, useRef } from "react";
import { useRouter } from "next/navigation";
import { startInterview } from "@/lib/api";

const ROLES = [
  { id: "Backend",   icon: "⚙️",  desc: "API, databases, architecture" },
  { id: "Frontend",  icon: "🎨",  desc: "React, CSS, browser APIs" },
  { id: "ML",        icon: "🧠",  desc: "Models, training, deployment" },
  { id: "Data Analyst", icon: "📊", desc: "SQL, statistics, A/B tests" },
  { id: "PM",        icon: "🧭",  desc: "Prioritization, metrics, roadmap" },
  { id: "DevOps",    icon: "🚀",  desc: "CI/CD, Docker, Kubernetes, clouds" },
  { id: "QA",        icon: "🧪",  desc: "Testing, automation, quality" },
  { id: "iOS",       icon: "🍎",  desc: "Swift, SwiftUI, App Store" },
  { id: "Android",   icon: "🤖",  desc: "Kotlin, Jetpack Compose, Play Store" },
  { id: "Security",  icon: "🔐",  desc: "OWASP, pentesting, cryptography" },
];

const STYLES = [
  { id: "friendly", icon: "😊", label: "Дружелюбный", desc: "Стартап CTO, поддерживает" },
  { id: "strict",   icon: "🧊", label: "Строгий",     desc: "FAANG-стиль, без поблажек" },
  { id: "academic", icon: "🎓", label: "Академичный", desc: "Просит точные определения" },
];

export default function Home() {
  const router = useRouter();
  const [role, setRole] = useState("Backend");
  const [style, setStyle] = useState("friendly");
  const [resumeFile, setResumeFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);

  async function handleStart() {
    setLoading(true);
    setError("");
    try {
      const data = await startInterview(role, style, resumeFile || undefined);

      if (!data.thread_id) {
        setError("Не удалось запустить интервью. Проверь что бэкенд запущен.");
        return;
      }

      sessionStorage.setItem("thread_id", data.thread_id);
      sessionStorage.setItem("question", data.question);
      sessionStorage.setItem("question_number", String(data.question_number));
      sessionStorage.setItem("total_questions", String(data.total_questions));
      sessionStorage.setItem("role", role);
      sessionStorage.setItem("interviewer_style", style);
      sessionStorage.setItem("interviewer_intro", data.interviewer_intro || "");

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
        <div className="mb-8">
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

        {/* PDF Upload */}
        <div className="mb-5">
          <p className="text-xs font-medium text-[#71717A] uppercase tracking-widest mb-3">
            Резюме (необязательно)
          </p>
          <div
            onClick={() => fileRef.current?.click()}
            className={`flex items-center gap-3 px-4 py-3 rounded-xl border cursor-pointer transition-all duration-150 ${
              resumeFile
                ? "border-[#18181B] bg-white"
                : "border-dashed border-[#D4D4D8] bg-white hover:border-[#A1A1AA]"
            }`}
          >
            <span className="text-lg">{resumeFile ? "📄" : "📎"}</span>
            <div className="flex-1">
              {resumeFile ? (
                <span className="text-sm font-medium text-[#18181B]">{resumeFile.name}</span>
              ) : (
                <span className="text-sm text-[#A1A1AA]">Загрузить PDF резюме</span>
              )}
            </div>
            {resumeFile && (
              <button
                onClick={(e) => { e.stopPropagation(); setResumeFile(null); }}
                className="text-xs text-[#A1A1AA] hover:text-red-500 transition-colors"
              >
                ✕
              </button>
            )}
          </div>
          <input
            ref={fileRef}
            type="file"
            accept=".pdf"
            className="hidden"
            onChange={(e) => setResumeFile(e.target.files?.[0] || null)}
          />
          {resumeFile && (
            <p className="text-xs text-[#71717A] mt-1.5 px-1">
              ✓ Вопросы будут персонализированы под твоё резюме
            </p>
          )}
        </div>

        {/* Role selector */}
        <div className="mb-5">
          <p className="text-xs font-medium text-[#71717A] uppercase tracking-widest mb-3">
            Направление
          </p>
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
                {role === r.id && <div className="w-2 h-2 rounded-full bg-[#18181B]" />}
              </button>
            ))}
          </div>
        </div>

        {/* Interviewer style */}
        <div className="mb-6">
          <p className="text-xs font-medium text-[#71717A] uppercase tracking-widest mb-3">
            Стиль интервьюера
          </p>
          <div className="grid grid-cols-3 gap-2">
            {STYLES.map((s) => (
              <button
                key={s.id}
                onClick={() => setStyle(s.id)}
                className={`flex flex-col items-center gap-1.5 px-3 py-3 rounded-xl border text-center transition-all duration-150 ${
                  style === s.id
                    ? "border-[#18181B] bg-white shadow-sm"
                    : "border-[#E4E4E7] bg-white hover:border-[#A1A1AA]"
                }`}
              >
                <span className="text-xl">{s.icon}</span>
                <span className="text-xs font-medium text-[#18181B]">{s.label}</span>
                <span className="text-[10px] text-[#A1A1AA] leading-tight">{s.desc}</span>
              </button>
            ))}
          </div>
        </div>

        {error && <p className="text-red-500 text-xs mb-4 px-1">{error}</p>}

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