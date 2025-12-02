"""
EPIC 7C - LLM Module
=====================
LLM detection, selection, and client abstraction.
"""

from .detector import (
    detect_llm_capabilities, 
    get_best_llm_config,
    detect_llm,
    LLMConfig
)
from .client import LLMClient, get_llm_client, get_llm_status

__all__ = [
    'detect_llm_capabilities',
    'get_best_llm_config',
    'detect_llm',
    'LLMConfig',
    'LLMClient',
    'get_llm_client',
    'get_llm_status'
]
