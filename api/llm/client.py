"""
EPIC 7C - LLM Client Abstraction
=================================
Unified interface for different LLM providers.

Supports:
- OpenAI API
- Anthropic API
- Groq API
- Ollama (local)
"""

import os
import json
import logging
import httpx
from typing import Dict, Any, Optional
from abc import ABC, abstractmethod

from .detector import detect_llm_capabilities, LLMCapabilities

logger = logging.getLogger(__name__)

# System prompt enforcing accuracy
ACCURACY_SYSTEM_PROMPT = """You are a trade intelligence analyst assistant for GTI-OS Control Tower.

CRITICAL RULES:
1. ALL facts, numbers, HS codes, countries, values, and volumes MUST come ONLY from the JSON context provided.
2. NEVER invent or hallucinate any data. If information is not in the context, say "Not available in data."
3. You may summarize, explain, and provide insights based ONLY on the provided data.
4. Format responses clearly with bullet points and sections when appropriate.
5. Be concise and business-focused.

Your role is to help users understand trade data, buyer profiles, and risk signals using ONLY the structured data provided."""


class BaseLLMClient(ABC):
    """Abstract base class for LLM clients."""
    
    @abstractmethod
    def generate(self, prompt: str, system_prompt: str = None, context: Dict = None) -> str:
        """Generate a response from the LLM."""
        pass
    
    def summarize(self, text: str) -> str:
        """Summarize text."""
        return self.generate(f"Summarize the following:\n\n{text}")
    
    def explain_buyer(self, buyer_data: Dict) -> str:
        """Explain a buyer profile for sales/business use."""
        prompt = """Explain this buyer to a manufacturer looking for potential business partners.
Focus on:
1. Company overview (size, location, activity period)
2. Product focus (top HS codes and what they trade)
3. Volume and value patterns
4. Main trade routes/lanes
5. Risk assessment and any concerns
6. Business opportunity summary

Use ONLY the data provided. Do not invent any numbers or facts."""
        
        return self.generate(prompt, context=buyer_data)
    
    def analyze_risk(self, risk_data: Dict) -> str:
        """Analyze risk signals for an entity."""
        prompt = """Analyze the risk profile for this entity.
Explain:
1. Overall risk level and score interpretation
2. Main risk factors (reason codes)
3. What the risk signals mean for business
4. Recommended due diligence steps

Use ONLY the data provided."""
        
        return self.generate(prompt, context=risk_data)
    
    def answer_question(self, question: str, context: Dict) -> str:
        """Answer a specific question using provided context."""
        prompt = f"""Answer this question using ONLY the provided data context:

Question: {question}

If the answer is not available in the data, say "This information is not available in the current data."
Never invent or estimate numbers."""
        
        return self.generate(prompt, context=context)


class OpenAIClient(BaseLLMClient):
    """OpenAI API client."""
    
    def __init__(self, api_key: str, model: str = "gpt-4o", endpoint: str = None):
        self.api_key = api_key
        self.model = model
        self.endpoint = endpoint or "https://api.openai.com/v1"
        self.client = httpx.Client(timeout=60.0)
    
    def generate(self, prompt: str, system_prompt: str = None, context: Dict = None) -> str:
        system = system_prompt or ACCURACY_SYSTEM_PROMPT
        
        # Build user message with context
        user_message = prompt
        if context:
            user_message = f"DATA CONTEXT:\n```json\n{json.dumps(context, indent=2, default=str)}\n```\n\n{prompt}"
        
        try:
            response = self.client.post(
                f"{self.endpoint}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user_message}
                    ],
                    "temperature": 0.3,  # Lower for factual accuracy
                    "max_tokens": 2000
                }
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
            
        except httpx.HTTPError as e:
            logger.error(f"OpenAI API error: {e}")
            raise RuntimeError(f"LLM request failed: {e}")


class AnthropicClient(BaseLLMClient):
    """Anthropic Claude API client."""
    
    def __init__(self, api_key: str, model: str = "claude-3-5-sonnet-20241022"):
        self.api_key = api_key
        self.model = model
        self.client = httpx.Client(timeout=60.0)
    
    def generate(self, prompt: str, system_prompt: str = None, context: Dict = None) -> str:
        system = system_prompt or ACCURACY_SYSTEM_PROMPT
        
        user_message = prompt
        if context:
            user_message = f"DATA CONTEXT:\n```json\n{json.dumps(context, indent=2, default=str)}\n```\n\n{prompt}"
        
        try:
            response = self.client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "system": system,
                    "messages": [
                        {"role": "user", "content": user_message}
                    ],
                    "max_tokens": 2000
                }
            )
            response.raise_for_status()
            data = response.json()
            return data["content"][0]["text"]
            
        except httpx.HTTPError as e:
            logger.error(f"Anthropic API error: {e}")
            raise RuntimeError(f"LLM request failed: {e}")


class GroqClient(BaseLLMClient):
    """Groq API client (OpenAI-compatible)."""
    
    def __init__(self, api_key: str, model: str = "llama-3.1-70b-versatile"):
        self.api_key = api_key
        self.model = model
        self.endpoint = "https://api.groq.com/openai/v1"
        self.client = httpx.Client(timeout=60.0)
    
    def generate(self, prompt: str, system_prompt: str = None, context: Dict = None) -> str:
        system = system_prompt or ACCURACY_SYSTEM_PROMPT
        
        user_message = prompt
        if context:
            user_message = f"DATA CONTEXT:\n```json\n{json.dumps(context, indent=2, default=str)}\n```\n\n{prompt}"
        
        try:
            response = self.client.post(
                f"{self.endpoint}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user_message}
                    ],
                    "temperature": 0.3,
                    "max_tokens": 2000
                }
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
            
        except httpx.HTTPError as e:
            logger.error(f"Groq API error: {e}")
            raise RuntimeError(f"LLM request failed: {e}")


class OllamaClient(BaseLLMClient):
    """Ollama local LLM client."""
    
    def __init__(self, model: str = "llama3:latest", endpoint: str = "http://localhost:11434"):
        self.model = model
        self.endpoint = endpoint
        self.client = httpx.Client(timeout=120.0)  # Longer timeout for local models
    
    def generate(self, prompt: str, system_prompt: str = None, context: Dict = None) -> str:
        system = system_prompt or ACCURACY_SYSTEM_PROMPT
        
        user_message = prompt
        if context:
            user_message = f"DATA CONTEXT:\n```json\n{json.dumps(context, indent=2, default=str)}\n```\n\n{prompt}"
        
        full_prompt = f"{system}\n\nUser: {user_message}\n\nAssistant:"
        
        try:
            response = self.client.post(
                f"{self.endpoint}/api/generate",
                json={
                    "model": self.model,
                    "prompt": full_prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.3,
                        "num_predict": 2000
                    }
                }
            )
            response.raise_for_status()
            data = response.json()
            return data.get("response", "")
            
        except httpx.HTTPError as e:
            logger.error(f"Ollama API error: {e}")
            raise RuntimeError(f"LLM request failed: {e}")
        except Exception as e:
            logger.error(f"Ollama error: {e}")
            raise RuntimeError(f"LLM request failed: {e}")


class DisabledLLMClient(BaseLLMClient):
    """Placeholder client when no LLM is available."""
    
    def generate(self, prompt: str, system_prompt: str = None, context: Dict = None) -> str:
        return "AI Co-Pilot is not available. No LLM provider configured. Please set up OpenAI API key or install Ollama."


# Global client instance (singleton)
_llm_client: Optional[BaseLLMClient] = None
_llm_capabilities: Optional[LLMCapabilities] = None


def get_llm_client(force_refresh: bool = False) -> BaseLLMClient:
    """
    Get the LLM client singleton.
    
    Automatically detects and selects the best available LLM provider.
    
    Args:
        force_refresh: If True, re-detect capabilities and recreate client.
        
    Returns:
        LLMClient instance (may be DisabledLLMClient if no LLM available)
    """
    global _llm_client, _llm_capabilities
    
    if _llm_client is not None and not force_refresh:
        return _llm_client
    
    # Detect capabilities
    _llm_capabilities = detect_llm_capabilities()
    
    if not _llm_capabilities.best_provider:
        logger.warning("No LLM available - AI features disabled")
        _llm_client = DisabledLLMClient()
        return _llm_client
    
    provider = _llm_capabilities.providers[_llm_capabilities.best_provider]
    model = _llm_capabilities.best_model
    
    # Create appropriate client
    if provider.name == "openai":
        _llm_client = OpenAIClient(
            api_key=provider.api_key,
            model=model,
            endpoint=provider.endpoint
        )
    elif provider.name == "anthropic":
        _llm_client = AnthropicClient(
            api_key=provider.api_key,
            model=model
        )
    elif provider.name == "groq":
        _llm_client = GroqClient(
            api_key=provider.api_key,
            model=model
        )
    elif provider.name == "ollama":
        _llm_client = OllamaClient(
            model=model,
            endpoint=provider.endpoint
        )
    else:
        logger.warning(f"Unknown provider: {provider.name}")
        _llm_client = DisabledLLMClient()
    
    logger.info(f"LLM Client initialized: {provider.name} / {model}")
    return _llm_client


def get_llm_status() -> Dict[str, Any]:
    """Get current LLM status and capabilities."""
    global _llm_capabilities
    
    if _llm_capabilities is None:
        _llm_capabilities = detect_llm_capabilities()
    
    return {
        "available": _llm_capabilities.best_provider is not None,
        "provider": _llm_capabilities.best_provider,
        "model": _llm_capabilities.best_model,
        "capabilities": _llm_capabilities.to_dict()
    }


# Type alias for convenience
LLMClient = BaseLLMClient
