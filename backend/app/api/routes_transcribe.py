# backend/app/api/routes_transcribe.py

from fastapi import APIRouter, UploadFile, File, HTTPException
from openai import OpenAI
import os
import tempfile

router = APIRouter(prefix="/transcribe", tags=["transcribe"])
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

@router.post("")
async def transcribe_audio(file: UploadFile = File(...)):
    """
    Принимает аудио файл (mp3, webm, wav, m4a),
    транскрибирует через Whisper, возвращает текст.
    """
    allowed_types = ["audio/mpeg", "audio/webm", "audio/wav", "audio/mp4", "audio/m4a"]
    
    # сохраняем во временный файл (Whisper API требует файл, не bytes)
    suffix = "." + file.filename.split(".")[-1] if file.filename else ".mp3"
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name
    
    try:
        with open(tmp_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language="ru"  # можно убрать для автодетекта
            )
        return {"text": transcript.text}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")
    
    finally:
        os.unlink(tmp_path)  # удаляем временный файл