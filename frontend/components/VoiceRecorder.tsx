"use client";
import { useState, useRef } from "react";
import { transcribeAudio } from "@/lib/api";

interface Props {
  onTranscribed: (text: string) => void;
}

export default function VoiceRecorder({ onTranscribed }: Props) {
  const [recording, setRecording] = useState(false);
  const [loading, setLoading] = useState(false);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  async function startRecording() {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const mediaRecorder = new MediaRecorder(stream);
    mediaRecorderRef.current = mediaRecorder;
    chunksRef.current = [];

    mediaRecorder.ondataavailable = (e) => chunksRef.current.push(e.data);
    mediaRecorder.onstop = async () => {
      setLoading(true);
      const blob = new Blob(chunksRef.current, { type: "audio/webm" });
      const file = new File([blob], "recording.webm", { type: "audio/webm" });
      try {
        const data = await transcribeAudio(file);
        onTranscribed(data.text);
      } catch {
        onTranscribed("");
      } finally {
        setLoading(false);
        stream.getTracks().forEach((t) => t.stop());
      }
    };

    mediaRecorder.start();
    setRecording(true);
  }

  function stopRecording() {
    mediaRecorderRef.current?.stop();
    setRecording(false);
  }

  if (loading) {
    return (
      <span className="text-xs text-[#A1A1AA] flex items-center gap-1.5">
        <span className="w-1.5 h-1.5 rounded-full bg-[#A1A1AA] animate-pulse inline-block" />
        Транскрибируем...
      </span>
    );
  }

  return (
    <button
      onClick={recording ? stopRecording : startRecording}
      className={`flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 rounded-lg border transition-colors ${
        recording
          ? "border-red-200 bg-red-50 text-red-600"
          : "border-[#E4E4E7] bg-white text-[#71717A] hover:border-[#A1A1AA]"
      }`}
    >
      <span className={`w-1.5 h-1.5 rounded-full inline-block ${recording ? "bg-red-500 animate-pulse" : "bg-[#A1A1AA]"}`} />
      {recording ? "Остановить" : "Голосом"}
    </button>
  );
}
