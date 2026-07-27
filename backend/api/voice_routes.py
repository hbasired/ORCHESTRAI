"""
Voice API Routes
Endpoints for voice interaction with the Embodied Agent.
"""

from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
import tempfile
import os

import structlog

from voice import get_voice_interface

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/voice", tags=["voice"])


@router.post("/process")
async def process_voice(audio: UploadFile = File(...)):
    """
    Process voice input through STT-LLM-TTS pipeline.
    
    Accepts audio file, returns JSON with transcript, response, and audio path.
    """
    voice = await get_voice_interface()
    
    # Save uploaded audio to temp file
    temp_input = tempfile.mktemp(suffix=".wav")
    try:
        with open(temp_input, "wb") as f:
            content = await audio.read()
            f.write(content)
        
        result = await voice.process_audio(temp_input)
        
        return {
            "transcript": result.transcript,
            "response": result.response_text,
            "audio_path": result.audio_path,
            "timings": {
                "stt_ms": result.duration_stt_ms,
                "llm_ms": result.duration_llm_ms,
                "tts_ms": result.duration_tts_ms,
                "total_ms": result.duration_stt_ms + result.duration_llm_ms + result.duration_tts_ms
            }
        }
    finally:
        if os.path.exists(temp_input):
            os.unlink(temp_input)


@router.post("/text")
async def process_text(text: str):
    """Process text input, return voice response."""
    voice = await get_voice_interface()
    result = await voice.process_text(text)
    
    return {
        "input": text,
        "response": result.response_text,
        "audio_path": result.audio_path
    }


@router.get("/audio/{filename}")
async def get_audio(filename: str):
    """Serve generated audio file."""
    import tempfile
    audio_path = os.path.join(tempfile.gettempdir(), filename)
    
    if not os.path.exists(audio_path):
        raise HTTPException(404, "Audio not found")
    
    return FileResponse(audio_path, media_type="audio/wav")


@router.post("/reset")
async def reset_conversation():
    """Reset conversation history."""
    voice = await get_voice_interface()
    voice.reset_conversation()
    return {"status": "conversation_reset"}


@router.get("/status")
async def voice_status():
    """Check voice interface status."""
    voice = await get_voice_interface()
    return {
        "stt_initialized": voice.stt._initialized,
        "tts_initialized": voice.tts._initialized,
        "whisper_model": voice.stt.model_name,
        "piper_voice": voice.tts.voice
    }
