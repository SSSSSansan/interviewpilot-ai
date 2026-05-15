const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

export async function startInterview(role: string, resumeFile?: File) {
  const formData = new FormData();
  formData.append("role", role);
  formData.append("interviewer_style", "friendly");
  if (resumeFile) {
    formData.append("resume_pdf", resumeFile);
  }

  const res = await fetch(`${API_BASE}/interview/start`, {
    method: "POST",
    body: formData,
  });
  return res.json();
}

export async function submitAnswer(threadId: string, answer: string) {
  const res = await fetch(`${API_BASE}/interview/answer`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ thread_id: threadId, answer }),
  });
  return res.json();
}

export async function transcribeAudio(file: File) {
  const formData = new FormData();
  formData.append("file", file);
  const res = await fetch(`${API_BASE}/transcribe`, {
    method: "POST",
    body: formData,
  });
  return res.json();
}