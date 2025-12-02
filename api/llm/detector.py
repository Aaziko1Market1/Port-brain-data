"""
EPIC 7C - LLM Detection
========================
Detects available LLM providers and selects the best one.

Checks:
1. Environment variables for cloud APIs (OpenAI, Groq, Anthropic)
2. Local Ollama installation
3. Docker containers (text-generation-webui, vllm, etc.)
"""

import os
import subprocess
import logging
import httpx
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class LLMProvider:
    """LLM provider configuration."""
    name: str
    available: bool
    models: List[str] = field(default_factory=list)
    endpoint: Optional[str] = None
    api_key: Optional[str] = None
    priority: int = 0  # Higher = better


@dataclass
class LLMCapabilities:
    """Detected LLM capabilities on this system."""
    providers: Dict[str, LLMProvider] = field(default_factory=dict)
    best_provider: Optional[str] = None
    best_model: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "providers": {
                name: {
                    "available": p.available,
                    "models": p.models,
                    "endpoint": p.endpoint,
                    "priority": p.priority
                }
                for name, p in self.providers.items()
            },
            "best_provider": self.best_provider,
            "best_model": self.best_model
        }


def _check_env_api_key(key_name: str) -> Optional[str]:
    """Check if an API key environment variable is set."""
    value = os.environ.get(key_name, "").strip()
    return value if value else None


def _detect_openai() -> LLMProvider:
    """Detect OpenAI API availability."""
    api_key = _check_env_api_key("OPENAI_API_KEY")
    
    if not api_key:
        return LLMProvider(name="openai", available=False, priority=100)
    
    # OpenAI available - list preferred models (best first)
    models = [
        "gpt-4o",           # Best overall
        "gpt-4-turbo",      # Fast + capable
        "gpt-4",            # Standard
        "gpt-3.5-turbo"     # Fallback
    ]
    
    return LLMProvider(
        name="openai",
        available=True,
        models=models,
        endpoint="https://api.openai.com/v1",
        api_key=api_key,
        priority=100  # Highest priority
    )


def _detect_anthropic() -> LLMProvider:
    """Detect Anthropic API availability."""
    api_key = _check_env_api_key("ANTHROPIC_API_KEY")
    
    if not api_key:
        return LLMProvider(name="anthropic", available=False, priority=90)
    
    models = [
        "claude-3-5-sonnet-20241022",
        "claude-3-opus-20240229",
        "claude-3-sonnet-20240229"
    ]
    
    return LLMProvider(
        name="anthropic",
        available=True,
        models=models,
        endpoint="https://api.anthropic.com",
        api_key=api_key,
        priority=90
    )


def _detect_groq() -> LLMProvider:
    """Detect Groq API availability."""
    api_key = _check_env_api_key("GROQ_API_KEY")
    
    if not api_key:
        return LLMProvider(name="groq", available=False, priority=80)
    
    models = [
        "llama-3.1-70b-versatile",
        "llama-3.1-8b-instant",
        "mixtral-8x7b-32768"
    ]
    
    return LLMProvider(
        name="groq",
        available=True,
        models=models,
        endpoint="https://api.groq.com/openai/v1",
        api_key=api_key,
        priority=80
    )


def _detect_ollama() -> LLMProvider:
    """Detect local Ollama installation."""
    try:
        # Try to run ollama list
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode != 0:
            return LLMProvider(name="ollama", available=False, priority=50)
        
        # Parse model list
        models = []
        for line in result.stdout.strip().split("\n"):
            if line and not line.startswith("NAME"):
                parts = line.split()
                if parts:
                    model_name = parts[0]
                    models.append(model_name)
        
        if not models:
            return LLMProvider(name="ollama", available=False, priority=50)
        
        # Sort models by preference (larger/better models first)
        model_priority = {
            "llama3:70b": 100,
            "llama3:latest": 90,
            "llama3": 90,
            "qwen2:72b": 85,
            "mixtral": 80,
            "mistral:latest": 70,
            "mistral": 70,
            "llama2:70b": 65,
            "llama2": 60,
        }
        
        def get_priority(m):
            for key, prio in model_priority.items():
                if key in m.lower():
                    return prio
            return 50
        
        models.sort(key=get_priority, reverse=True)
        
        return LLMProvider(
            name="ollama",
            available=True,
            models=models,
            endpoint="http://localhost:11434",
            priority=50
        )
        
    except FileNotFoundError:
        logger.debug("Ollama not found in PATH")
        return LLMProvider(name="ollama", available=False, priority=50)
    except subprocess.TimeoutExpired:
        logger.warning("Ollama command timed out")
        return LLMProvider(name="ollama", available=False, priority=50)
    except Exception as e:
        logger.warning(f"Error detecting Ollama: {e}")
        return LLMProvider(name="ollama", available=False, priority=50)


def _detect_docker_llm() -> LLMProvider:
    """Detect LLM running in Docker containers."""
    try:
        result = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode != 0:
            return LLMProvider(name="docker-llm", available=False, priority=40)
        
        containers = result.stdout.strip().split("\n")
        
        # Look for known LLM containers
        llm_containers = []
        for container in containers:
            container_lower = container.lower()
            if any(x in container_lower for x in [
                "text-generation", "vllm", "lmstudio", "localai", "llama"
            ]):
                llm_containers.append(container)
        
        if not llm_containers:
            return LLMProvider(name="docker-llm", available=False, priority=40)
        
        return LLMProvider(
            name="docker-llm",
            available=True,
            models=llm_containers,
            endpoint="http://localhost:8080",  # Common default
            priority=40
        )
        
    except FileNotFoundError:
        return LLMProvider(name="docker-llm", available=False, priority=40)
    except Exception as e:
        logger.debug(f"Error detecting Docker LLM: {e}")
        return LLMProvider(name="docker-llm", available=False, priority=40)


def detect_llm_capabilities() -> LLMCapabilities:
    """
    Detect all available LLM capabilities on this system.
    
    Returns:
        LLMCapabilities with all detected providers and best selection.
    """
    logger.info("Detecting available LLM providers...")
    
    capabilities = LLMCapabilities()
    
    # Check all providers
    providers = [
        _detect_openai(),
        _detect_anthropic(),
        _detect_groq(),
        _detect_ollama(),
        _detect_docker_llm()
    ]
    
    for provider in providers:
        capabilities.providers[provider.name] = provider
        status = "✓ Available" if provider.available else "✗ Not available"
        models_str = f" ({', '.join(provider.models[:3])})" if provider.models else ""
        logger.info(f"  {provider.name}: {status}{models_str}")
    
    # Select best available provider
    available_providers = [p for p in providers if p.available]
    
    if available_providers:
        # Sort by priority (descending)
        available_providers.sort(key=lambda p: p.priority, reverse=True)
        best = available_providers[0]
        
        capabilities.best_provider = best.name
        capabilities.best_model = best.models[0] if best.models else None
        
        logger.info(f"Selected LLM: {best.name} / {capabilities.best_model}")
    else:
        logger.warning("No LLM providers available. AI Co-Pilot will be disabled.")
    
    return capabilities


def get_best_llm_config() -> Optional[Dict[str, Any]]:
    """
    Get configuration for the best available LLM.
    
    Returns:
        Dict with provider, model, endpoint, api_key or None if no LLM available.
    """
    capabilities = detect_llm_capabilities()
    
    if not capabilities.best_provider:
        return None
    
    provider = capabilities.providers[capabilities.best_provider]
    
    return {
        "provider": provider.name,
        "model": capabilities.best_model,
        "endpoint": provider.endpoint,
        "api_key": provider.api_key
    }


@dataclass
class LLMConfig:
    """Configuration for the selected LLM."""
    provider: Optional[str]
    model: Optional[str]
    available: bool
    reason: str
    endpoint: Optional[str] = None
    api_key: Optional[str] = None


def detect_llm() -> LLMConfig:
    """
    Detect the best available LLM and return configuration.
    
    Priority order:
    1. Ollama with llama3 (preferred for local, good reasoning)
    2. Ollama with mistral
    3. OpenAI API (if OPENAI_API_KEY set)
    4. Anthropic API (if ANTHROPIC_API_KEY set)
    5. Groq API (if GROQ_API_KEY set)
    
    Returns:
        LLMConfig with provider, model, available status, and reason.
    """
    caps = detect_llm_capabilities()
    
    if not caps.best_provider:
        return LLMConfig(
            provider=None,
            model=None,
            available=False,
            reason="No LLM provider detected. Install Ollama or set API keys."
        )
    
    provider = caps.providers[caps.best_provider]
    
    return LLMConfig(
        provider=provider.name,
        model=caps.best_model,
        available=True,
        reason=f"Using {provider.name} with model {caps.best_model}",
        endpoint=provider.endpoint,
        api_key=provider.api_key
    )


if __name__ == "__main__":
    # Test detection
    logging.basicConfig(level=logging.INFO)
    
    print("\n" + "="*60)
    print("  LLM DETECTION TEST")
    print("="*60)
    
    # Test detect_llm (simple function)
    config = detect_llm()
    print(f"\ndetect_llm() result:")
    print(f"  Provider:  {config.provider}")
    print(f"  Model:     {config.model}")
    print(f"  Available: {config.available}")
    print(f"  Reason:    {config.reason}")
    
    # Full capabilities
    caps = detect_llm_capabilities()
    print("\nFull capabilities:")
    import json
    print(json.dumps(caps.to_dict(), indent=2))
