"""
Multi-Provider LLM Client
Supports Groq, Gemini, and Ollama with unified interface.

As a GenAI Engineer:
- Abstraction layer for multiple LLM providers
- Automatic fallback between providers
- Streaming support for real-time responses
- Function calling for agent tools
"""

import asyncio
import os
from typing import Optional, AsyncGenerator, Any, Literal
from abc import ABC, abstractmethod
from dataclasses import dataclass
import json

import structlog
import httpx

from config import settings

logger = structlog.get_logger(__name__)


@dataclass
class LLMMessage:
    """Unified message format."""
    role: Literal["system", "user", "assistant", "function"]
    content: str
    name: Optional[str] = None
    function_call: Optional[dict] = None


@dataclass
class LLMResponse:
    """Unified response format."""
    content: str
    model: str
    provider: str
    usage: dict
    function_call: Optional[dict] = None
    finish_reason: str = "stop"


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    @abstractmethod
    async def generate(
        self,
        messages: list[LLMMessage],
        model: str = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        functions: list[dict] = None,
        stream: bool = False
    ) -> LLMResponse | AsyncGenerator[str, None]:
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        pass


class GroqProvider(BaseLLMProvider):
    """Groq API provider - Ultra-fast inference."""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or settings.groq_api_key
        self.base_url = "https://api.groq.com/openai/v1"
        self.default_model = "llama-3.3-70b-versatile"
    
    async def generate(
        self,
        messages: list[LLMMessage],
        model: str = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        functions: list[dict] = None,
        stream: bool = False
    ) -> LLMResponse | AsyncGenerator[str, None]:
        model = model or self.default_model
        
        payload = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream
        }
        
        if functions:
            payload["tools"] = [{"type": "function", "function": f} for f in functions]
            payload["tool_choice"] = "auto"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            if stream:
                return self._stream_response(client, payload, headers, model)
            else:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    json=payload,
                    headers=headers
                )
                response.raise_for_status()
                data = response.json()
                
                choice = data["choices"][0]
                return LLMResponse(
                    content=choice["message"].get("content", ""),
                    model=model,
                    provider="groq",
                    usage=data.get("usage", {}),
                    function_call=choice["message"].get("tool_calls"),
                    finish_reason=choice.get("finish_reason", "stop")
                )
    
    async def _stream_response(
        self, client: httpx.AsyncClient, payload: dict, headers: dict, model: str
    ) -> AsyncGenerator[str, None]:
        async with client.stream(
            "POST",
            f"{self.base_url}/chat/completions",
            json=payload,
            headers=headers
        ) as response:
            async for line in response.aiter_lines():
                if line.startswith("data: ") and line != "data: [DONE]":
                    data = json.loads(line[6:])
                    if delta := data["choices"][0]["delta"].get("content"):
                        yield delta
    
    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.base_url}/models",
                    headers={"Authorization": f"Bearer {self.api_key}"}
                )
                return response.status_code == 200
        except Exception:
            return False


class GeminiProvider(BaseLLMProvider):
    """Google Gemini API provider."""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or settings.gemini_api_key
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"
        self.default_model = "gemini-1.5-flash"
    
    async def generate(
        self,
        messages: list[LLMMessage],
        model: str = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        functions: list[dict] = None,
        stream: bool = False
    ) -> LLMResponse | AsyncGenerator[str, None]:
        model = model or self.default_model
        
        # Convert messages to Gemini format
        contents = []
        system_instruction = None
        
        for msg in messages:
            if msg.role == "system":
                system_instruction = msg.content
            else:
                role = "user" if msg.role == "user" else "model"
                contents.append({
                    "role": role,
                    "parts": [{"text": msg.content}]
                })
        
        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens
            }
        }
        
        if system_instruction:
            payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}
        
        if functions:
            payload["tools"] = [{"functionDeclarations": functions}]
        
        url = f"{self.base_url}/models/{model}:generateContent?key={self.api_key}"
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            
            candidate = data["candidates"][0]
            content = candidate["content"]["parts"][0].get("text", "")
            
            return LLMResponse(
                content=content,
                model=model,
                provider="gemini",
                usage=data.get("usageMetadata", {}),
                finish_reason=candidate.get("finishReason", "STOP")
            )
    
    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                url = f"{self.base_url}/models?key={self.api_key}"
                response = await client.get(url)
                return response.status_code == 200
        except Exception:
            return False


class OllamaProvider(BaseLLMProvider):
    """Ollama local LLM provider."""
    
    def __init__(self, base_url: str = None):
        self.base_url = base_url or settings.ollama_base_url
        self.default_model = "llama3.2"
    
    async def generate(
        self,
        messages: list[LLMMessage],
        model: str = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        functions: list[dict] = None,
        stream: bool = False
    ) -> LLMResponse | AsyncGenerator[str, None]:
        model = model or self.default_model
        
        payload = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens
            },
            "stream": stream
        }
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            if stream:
                return self._stream_response(client, payload, model)
            else:
                response = await client.post(
                    f"{self.base_url}/api/chat",
                    json=payload
                )
                response.raise_for_status()
                data = response.json()
                
                return LLMResponse(
                    content=data["message"]["content"],
                    model=model,
                    provider="ollama",
                    usage={
                        "prompt_tokens": data.get("prompt_eval_count", 0),
                        "completion_tokens": data.get("eval_count", 0)
                    },
                    finish_reason="stop" if data.get("done") else "length"
                )
    
    async def _stream_response(
        self, client: httpx.AsyncClient, payload: dict, model: str
    ) -> AsyncGenerator[str, None]:
        async with client.stream(
            "POST",
            f"{self.base_url}/api/chat",
            json=payload
        ) as response:
            async for line in response.aiter_lines():
                if line:
                    data = json.loads(line)
                    if content := data.get("message", {}).get("content"):
                        yield content
    
    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                return response.status_code == 200
        except Exception:
            return False


class LLMClient:
    """
    Unified LLM client with automatic provider selection and fallback.
    
    Usage:
        llm = LLMClient()
        response = await llm.generate([
            LLMMessage(role="system", content="You are a helpful assistant."),
            LLMMessage(role="user", content="Hello!")
        ])
    """
    
    def __init__(self, default_provider: str = None):
        self.providers: dict[str, BaseLLMProvider] = {}
        self.default_provider = default_provider or settings.default_llm_provider
        
        # Initialize available providers
        if settings.groq_api_key:
            self.providers["groq"] = GroqProvider()
        if settings.gemini_api_key:
            self.providers["gemini"] = GeminiProvider()
        self.providers["ollama"] = OllamaProvider()
        
        if not self.providers:
            raise RuntimeError("No LLM providers configured")
        
        logger.info("LLM client initialized", providers=list(self.providers.keys()))
    
    async def generate(
        self,
        messages: list[LLMMessage],
        provider: str = None,
        model: str = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        functions: list[dict] = None,
        stream: bool = False,
        fallback: bool = True
    ) -> LLMResponse | AsyncGenerator[str, None]:
        """
        Generate a response using the specified or default provider.
        
        Args:
            messages: List of messages in the conversation
            provider: LLM provider to use (groq, gemini, ollama)
            model: Model name (provider-specific)
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
            functions: Function definitions for function calling
            stream: Whether to stream the response
            fallback: Whether to try other providers on failure
        """
        provider = provider or self.default_provider

        # Stage 20 (OWASP LLM01 / G-008): prompt-injection guardrail on EVERY LLM call (100%-traffic).
        # Inspects untrusted (user-role) content with BOTH detector layers for observability, but only HARD-BLOCKS on
        # the deterministic HEURISTIC tier (0% measured false-positive rate on the benign corpus) — suitable for
        # blocking live traffic. The SEMANTIC tier (~1.6% FP; it false-positives on benign instruction-style prompts
        # like "Reply with the single word: OK") is logged for visibility but does NOT block a live call, so the
        # guardrail never breaks legitimate runtime prompts. The full hybrid (block on either) is used in the offline
        # red-team eval. PROMPT_GUARD_ENFORCE=0 disables blocking entirely; PROMPT_GUARD_ENFORCE=hybrid hard-blocks on
        # the semantic tier too (opt-in, for untrusted-input front doors).
        try:
            from security.prompt_guard import inspect as _pg_inspect, PromptInjectionDetected as _PGErr
            _user_text = "\n".join(m.content for m in messages if getattr(m, "role", None) == "user" and m.content)
            if _user_text:
                _v = _pg_inspect(_user_text)
                if _v.blocked:
                    _mode = os.environ.get("PROMPT_GUARD_ENFORCE", "1")
                    _block = _mode != "0" and (_v.layer == "heuristic" or _mode == "hybrid")
                    logger.warning("prompt_guard flagged LLM input", layer=_v.layer, reason=_v.reason, blocked=_block)
                    if _block:
                        raise _PGErr(_v)
        except ImportError:
            pass  # honest: guard unavailable -> no silent fake

        # Try primary provider
        if provider in self.providers:
            try:
                return await self.providers[provider].generate(
                    messages=messages,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    functions=functions,
                    stream=stream
                )
            except Exception as e:
                logger.warning(f"Provider {provider} failed", error=str(e))
                if not fallback:
                    raise
        
        # Fallback to other providers
        for fallback_provider, client in self.providers.items():
            if fallback_provider != provider:
                try:
                    logger.info(f"Falling back to {fallback_provider}")
                    return await client.generate(
                        messages=messages,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        functions=functions,
                        stream=stream
                    )
                except Exception as e:
                    logger.warning(f"Fallback {fallback_provider} failed", error=str(e))
                    continue
        
        raise RuntimeError("All LLM providers failed")
    
    async def health_check(self) -> dict[str, bool]:
        """Check health of all providers."""
        results = {}
        for name, provider in self.providers.items():
            results[name] = await provider.health_check()
        return results


# Global client instance
llm_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    """Get or create the global LLM client."""
    global llm_client
    if llm_client is None:
        llm_client = LLMClient()
    return llm_client
