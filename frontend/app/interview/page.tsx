"use client";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { submitAnswer } from "@/lib/api";
import VoiceRecorder from "@/components/VoiceRecorder";

export default function InterviewPage() {
  const router = useRouter();
  const [threadId, setThreadId] = useState("");
  const [question, setQuestion] = useState("");
  const [questionNumber, setQuestionNumber] = useState(1);
  const [totalQuestions, setTotalQuestions] = useState(3);
  const [isFollowUp, setIsFollowUp] = useState(false);
  const [answer, setAnswer] = useState("");
  const [loading, setLoading] = useState(false);
  const [lastScore, setLastScore] = useState<any>(null);
  const [role, setRole] = useState("");

  useEffect(() => {
    setThreadId(sessionStorage.getItem("thread_id") || "");
    setQuestion(sessionStorage.getItem("question") || "");
    setQuestionNumber(Number(sessionStorage.getItem("question_number")) || 1);
    setTotalQuestions(Number(sessionStorage.getItem("total_questions")) || 3);
    setRole(sessionStorage.getItem("role") || "");
  }, []);

  async function handleSubmit() {
    if (!answer.trim()) return;
    setLoading(true);
    try {
      const data = await submitAnswer(threadId, answer);
      if (data.is_complete) {
        sessionStorage.setItem("final_report", JSON.stringify(data.final_report));
        sessionStorage.setItem("all_scores", JSON.stringify(data.all_scores));
        router.push("/report");
        return;
      }

      if (data.last_score) setLastScore(data.last_score);

      const newNum = data.question_number;
      const prevNum = questionNumber;
      setIsFollowUp(newNum === prevNum);

      setQuestion(data.question);
      setQuestionNumber(newNum);
      setTotalQuestions(data.total_questions);
      setAnswer("");
    } finally {
      setLoading(false);
    }
  }

  const progress = (questionNumber / totalQuestions) * 100;

  const scoreColor = (score: number) => {
    if (score >= 7) return "text-emerald-700 bg-emerald-50 border-emerald-200";
    if (score >= 5) return "text-amber-700 bg-amber-50 border-amber-200";
    return "text-red-700 bg-red-50 border-red-200";
  };

  return (
    <main className="min-h-screen bg-[#FAFAF9]">

      {/* Top bar */}
      <div className="border-b border-[#E4E4E7] bg-white px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-6 h-6 rounded-md bg-[#18181B] flex items-center justify-center">
            <span className="text-white text-[10px] font-bold">IP</span>
          </div>
          <span className="text-sm text-[#A1A1AA]">/</span>
          <span className="text-sm font-medium text-[#18181B]">{role}</span>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs text-[#A1A1AA]">
            {isFollowUp ? `Вопрос ${questionNumber} из ${totalQuestions} · уточнение` : `Вопрос ${questionNumber} из ${totalQuestions}`}
          </span>
          <div className="w-24 h-1 bg-[#E4E4E7] rounded-full overflow-hidden">
            <div
              className="h-full bg-[#18181B] rounded-full transition-all duration-500"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-2xl mx-auto px-6 py-10 flex flex-col gap-5">

        {/* Feedback from previous answer */}
        {lastScore && (
          <div className={`rounded-xl border px-4 py-3 ${scoreColor(lastScore.total_score)}`}>
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs font-semibold uppercase tracking-wider">Фидбек на предыдущий ответ</span>
              <span className="text-sm font-semibold">{lastScore.total_score}/10</span>
            </div>
            <p className="text-sm leading-relaxed opacity-90">{lastScore.feedback}</p>
          </div>
        )}

        {/* Question */}
        <div className="bg-white rounded-xl border border-[#E4E4E7] px-5 py-5">
          {isFollowUp && (
            <span className="inline-block text-[11px] font-medium text-[#A1A1AA] uppercase tracking-widest mb-3 bg-[#F4F4F5] px-2 py-0.5 rounded">
              Уточняющий вопрос
            </span>
          )}
          <p className="text-[15px] leading-relaxed text-[#18181B] font-normal">{question}</p>
        </div>

        {/* Answer area */}
        <div className="bg-white rounded-xl border border-[#E4E4E7] overflow-hidden">
          <textarea
            value={answer}
            onChange={(e) => setAnswer(e.target.value)}
            placeholder="Введи ответ здесь..."
            rows={6}
            className="w-full px-5 py-4 text-sm text-[#18181B] placeholder-[#A1A1AA] bg-transparent resize-none focus:outline-none leading-relaxed"
            onKeyDown={(e) => {
              if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) handleSubmit();
            }}
          />
          <div className="px-4 py-3 border-t border-[#E4E4E7] flex items-center justify-between bg-[#FAFAF9]">
            <VoiceRecorder onTranscribed={(text) => setAnswer((prev) => prev ? prev + " " + text : text)} />
            <div className="flex items-center gap-3">
              <span className="text-[11px] text-[#A1A1AA]">⌘↵ отправить</span>
              <button
                onClick={handleSubmit}
                disabled={loading || !answer.trim()}
                className="px-4 py-1.5 rounded-lg bg-[#18181B] text-white text-sm font-medium hover:bg-[#27272A] disabled:bg-[#D4D4D8] disabled:cursor-not-allowed transition-colors"
              >
                {loading ? "Оцениваем..." : "Отправить"}
              </button>
            </div>
          </div>
        </div>

        {/* Criteria hint */}
        <div className="flex items-center gap-4 px-1">
          {["Точность", "Ясность", "Глубина", "Уверенность", "Коммуникация"].map((c) => (
            <span key={c} className="text-[11px] text-[#A1A1AA]">{c}</span>
          ))}
        </div>
      </div>
    </main>
  );
}
