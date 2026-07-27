"""
Voice Interface Module - STT-LLM-TTS Pipeline

Complete speech-to-speech interface:
- STT: OpenAI Whisper (local or API)
- LLM: Groq/Gemini/Ollama for reasoning
- TTS: Piper (local, fast, high quality)

Enables natural voice interaction with the Embodied Agent.
"""

import asyncio
import os
import tempfile
import wave
import io
from typing import Optional, AsyncGenerator, Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import structlog
import numpy as np

from config import settings
from agents.llm_client import get_llm_client, LLMMessage

logger = structlog.get_logger(__name__)


@dataclass
class VoiceResult:
    """Result from voice processing."""
    transcript: str
    response_text: str
    audio_path: Optional[str] = None
    duration_stt_ms: float = 0
    duration_llm_ms: float = 0
    duration_tts_ms: float = 0


class WhisperSTT:
    """
    Speech-to-Text using OpenAI Whisper.
    
    Supports:
    - Local model (whisper package)
    - OpenAI API (for production)
    """
    
    def __init__(self, model_name: str = "base"):
        self.model_name = model_name
        self._model = None
        self._initialized = False
        self._use_api = False
    
    async def initialize(self) -> None:
        """Initialize Whisper model."""
        try:
            import whisper
            
            logger.info("Loading Whisper model...", model=self.model_name)
            self._model = whisper.load_model(self.model_name)
            self._initialized = True
            logger.info("Whisper STT initialized", model=self.model_name)
            
        except ImportError:
            logger.warning("Whisper not available, checking for API fallback")
            if settings.openai_api_key:
                self._use_api = True
                self._initialized = True
                logger.info("Using OpenAI Whisper API")
            else:
                logger.error("No STT backend available")
    
    async def transcribe(self, audio_path: str, language: str = "en") -> str:
        """
        Transcribe audio file to text.
        
        Args:
            audio_path: Path to audio file (WAV, MP3, etc.)
            language: Language code (en, es, fr, etc.)
        
        Returns:
            Transcribed text
        """
        if not self._initialized:
            return "[STT not initialized]"
        
        start = datetime.utcnow()
        
        if self._use_api:
            return await self._transcribe_api(audio_path, language)
        
        try:
            result = self._model.transcribe(
                audio_path,
                language=language,
                task="transcribe",
                fp16=False  # CPU compatibility
            )
            
            duration = (datetime.utcnow() - start).total_seconds() * 1000
            logger.info("Transcription complete", duration_ms=duration)
            
            return result["text"].strip()
            
        except Exception as e:
            logger.error("Transcription failed", error=str(e))
            return f"[Transcription error: {e}]"
    
    async def _transcribe_api(self, audio_path: str, language: str) -> str:
        """Use OpenAI API for transcription."""
        try:
            import httpx
            
            async with httpx.AsyncClient() as client:
                with open(audio_path, "rb") as f:
                    response = await client.post(
                        "https://api.openai.com/v1/audio/transcriptions",
                        headers={"Authorization": f"Bearer {settings.openai_api_key}"},
                        files={"file": f},
                        data={"model": "whisper-1", "language": language}
                    )
                    return response.json().get("text", "")
        except Exception as e:
            logger.error("API transcription failed", error=str(e))
            return ""
    
    async def transcribe_stream(self, audio_stream: AsyncGenerator[bytes, None]) -> AsyncGenerator[str, None]:
        """Stream transcription for real-time processing."""
        buffer = []
        async for chunk in audio_stream:
            buffer.append(chunk)
            
            # Process every 3 seconds of audio
            if len(buffer) >= 48000 * 3:  # Assuming 16kHz mono
                audio_data = b"".join(buffer)
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                    self._save_wav(f.name, audio_data)
                    text = await self.transcribe(f.name)
                    os.unlink(f.name)
                    yield text
                buffer = []
    
    def _save_wav(self, path: str, audio_data: bytes, sample_rate: int = 16000) -> None:
        """Save raw audio bytes to WAV file."""
        with wave.open(path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(audio_data)


class PiperTTS:
    """
    Text-to-Speech using Piper.
    
    Piper is a fast, local TTS engine with good quality.
    Supports multiple languages and voices.
    """
    
    # Voice name to model path mapping
    VOICE_MODELS = {
        # English voices
        "amy": "en_US-amy-medium",
        "ryan": "en_US-ryan-medium",
        "jenny": "en_GB-jenny_dioco-medium",
        "lessac": "en_US-lessac-medium",
        # Hindi voice (local ONNX model)
        "priyamvada": "models/hi_IN-priyamvada-medium.onnx",
        # Telugu voice (local ONNX model)
        "padmavathi": "models/te_IN-padmavathi-medium.onnx",
        # Default
        "coqui": "en_US-lessac-medium"
    }
    
    def __init__(self, voice: str = "en_US-lessac-medium"):
        self.voice = self._resolve_voice(voice)
        self._initialized = False
        self._piper_path: Optional[Path] = None
    
    def _resolve_voice(self, voice_name: str) -> str:
        """Resolve voice name to model path."""
        return self.VOICE_MODELS.get(voice_name, voice_name)
    
    async def initialize(self) -> None:
        """Initialize Piper TTS."""
        try:
            # Check if piper is installed
            import subprocess
            result = subprocess.run(["piper", "--version"], capture_output=True)
            if result.returncode == 0:
                self._initialized = True
                logger.info("Piper TTS initialized", voice=self.voice)
            else:
                raise FileNotFoundError("Piper not in PATH")
                
        except FileNotFoundError:
            logger.warning("Piper not found, will use fallback")
            # Try to find piper in common locations
            possible_paths = [
                Path.home() / "piper" / "piper.exe",
                Path.home() / ".local" / "bin" / "piper",
                Path("/usr/local/bin/piper"),
            ]
            for p in possible_paths:
                if p.exists():
                    self._piper_path = p
                    self._initialized = True
                    logger.info("Found Piper at", path=str(p))
                    break
    
    async def synthesize(self, text: str, output_path: Optional[str] = None) -> str:
        """
        Synthesize text to speech.
        
        Args:
            text: Text to speak
            output_path: Optional output file path
        
        Returns:
            Path to generated audio file
        """
        if not self._initialized:
            logger.warning("TTS not initialized, returning empty")
            return ""
        
        if output_path is None:
            output_path = tempfile.mktemp(suffix=".wav")
        
        start = datetime.utcnow()
        
        try:
            import subprocess
            
            piper_cmd = str(self._piper_path) if self._piper_path else "piper"
            
            # Run piper
            process = subprocess.Popen(
                [piper_cmd, "--model", self.voice, "--output_file", output_path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            process.communicate(input=text.encode("utf-8"))
            
            duration = (datetime.utcnow() - start).total_seconds() * 1000
            logger.info("TTS complete", duration_ms=duration, chars=len(text))
            
            return output_path
            
        except Exception as e:
            logger.error("TTS synthesis failed", error=str(e))
            return ""
    
    async def synthesize_stream(self, text: str) -> AsyncGenerator[bytes, None]:
        """Stream TTS for real-time playback."""
        # For streaming, generate in chunks
        sentences = text.replace("!", ".").replace("?", ".").split(".")
        
        for sentence in sentences:
            sentence = sentence.strip()
            if sentence:
                audio_path = await self.synthesize(sentence + ".")
                if audio_path and os.path.exists(audio_path):
                    with open(audio_path, "rb") as f:
                        yield f.read()
                    os.unlink(audio_path)


class VoiceInterface:
    """
    Complete Voice Interface for the Embodied Agent.
    
    Pipeline: Audio In -> Whisper STT -> LLM -> Piper TTS -> Audio Out
    """
    
    def __init__(self):
        self.stt = WhisperSTT(model_name=settings.whisper_model)
        self.tts = PiperTTS(voice=settings.piper_voice)
        self._llm = None
        self._conversation_history: list[LLMMessage] = []
        self._system_prompt = """You are the voice interface for an AI Embodied Agent managing a manufacturing facility.

You control:
- 20+ autonomous robots in a warehouse
- 10-stage production line
- Multi-supplier supply chain

Commands you understand:
- "Show me the robots" / "Robot status"
- "Check manufacturing" / "Production status"
- "Supply chain status"
- "Start simulation" / "Stop simulation"
- "Switch to solution mode" / "Switch to problem mode"
- "What conflicts are there?"

Respond concisely and speak naturally. Keep responses under 3 sentences for voice output."""
    
    async def initialize(self) -> None:
        """Initialize all voice components."""
        await self.stt.initialize()
        await self.tts.initialize()
        self._llm = get_llm_client()
        
        self._conversation_history = [
            LLMMessage(role="system", content=self._system_prompt)
        ]
        
        logger.info("Voice Interface initialized")
    
    async def process_audio(self, audio_path: str) -> VoiceResult:
        """
        Process audio input through full STT-LLM-TTS pipeline.
        
        Args:
            audio_path: Path to input audio file
        
        Returns:
            VoiceResult with transcript, response, and output audio
        """
        result = VoiceResult(transcript="", response_text="")
        
        # 1. STT: Audio -> Text
        start_stt = datetime.utcnow()
        result.transcript = await self.stt.transcribe(audio_path)
        result.duration_stt_ms = (datetime.utcnow() - start_stt).total_seconds() * 1000
        
        logger.info("User said", transcript=result.transcript)
        
        # 2. LLM: Text -> Response
        start_llm = datetime.utcnow()
        
        self._conversation_history.append(LLMMessage(role="user", content=result.transcript))
        
        response = await self._llm.generate(self._conversation_history)
        result.response_text = response.content
        result.duration_llm_ms = (datetime.utcnow() - start_llm).total_seconds() * 1000
        
        self._conversation_history.append(LLMMessage(role="assistant", content=result.response_text))
        
        # Keep conversation manageable
        if len(self._conversation_history) > 20:
            self._conversation_history = self._conversation_history[:1] + self._conversation_history[-10:]
        
        logger.info("Agent response", response=result.response_text)
        
        # 3. TTS: Response -> Audio
        start_tts = datetime.utcnow()
        result.audio_path = await self.tts.synthesize(result.response_text)
        result.duration_tts_ms = (datetime.utcnow() - start_tts).total_seconds() * 1000
        
        return result
    
    async def process_text(self, text: str) -> VoiceResult:
        """Process text input (skip STT)."""
        result = VoiceResult(transcript=text, response_text="")
        
        self._conversation_history.append(LLMMessage(role="user", content=text))
        response = await self._llm.generate(self._conversation_history)
        result.response_text = response.content
        self._conversation_history.append(LLMMessage(role="assistant", content=result.response_text))
        
        result.audio_path = await self.tts.synthesize(result.response_text)
        
        return result
    
    def reset_conversation(self) -> None:
        """Clear conversation history."""
        self._conversation_history = [LLMMessage(role="system", content=self._system_prompt)]


# Global instance
_voice_interface: Optional[VoiceInterface] = None


async def get_voice_interface() -> VoiceInterface:
    """Get or create global voice interface."""
    global _voice_interface
    if _voice_interface is None:
        _voice_interface = VoiceInterface()
        await _voice_interface.initialize()
    return _voice_interface
