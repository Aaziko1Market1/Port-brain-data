"""
EPIC 7C/7D - LLM Detector Tests
================================
Tests for LLM detection and client initialization.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import os
os.environ['DB_CONFIG_PATH'] = 'config/db_config.yml'

from unittest.mock import patch, MagicMock
import subprocess


def test_detect_llm_with_ollama_llama3():
    """
    Test that detect_llm picks llama3 when Ollama has llama3 and mistral.
    """
    from api.llm.detector import detect_llm, _detect_ollama
    
    # Mock ollama list output with llama3 and mistral
    mock_output = """NAME              ID              SIZE      MODIFIED
llama3:latest     365c0bd3c000    4.7 GB    7 days ago
mistral:latest    6577803aa9a0    4.4 GB    7 days ago"""
    
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=mock_output,
            stderr=""
        )
        
        # Clear any cached results
        from api.llm import client as llm_client
        llm_client._llm_capabilities = None
        llm_client._llm_client = None
        
        config = detect_llm()
        
        # Should pick ollama with llama3 (highest priority local model)
        assert config.available == True
        assert config.provider == "ollama"
        assert "llama3" in config.model.lower()
        print(f"✓ detect_llm correctly picked: {config.provider} / {config.model}")


def test_detect_llm_with_only_mistral():
    """
    Test that detect_llm picks mistral when llama3 is not available.
    """
    from api.llm.detector import detect_llm
    
    mock_output = """NAME              ID              SIZE      MODIFIED
mistral:latest    6577803aa9a0    4.4 GB    7 days ago"""
    
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=mock_output,
            stderr=""
        )
        
        from api.llm import client as llm_client
        llm_client._llm_capabilities = None
        llm_client._llm_client = None
        
        config = detect_llm()
        
        assert config.available == True
        assert config.provider == "ollama"
        assert "mistral" in config.model.lower()
        print(f"✓ detect_llm correctly picked mistral: {config.model}")


def test_detect_llm_no_providers():
    """
    Test that detect_llm returns unavailable when no providers exist.
    """
    from api.llm.detector import detect_llm
    
    with patch('subprocess.run') as mock_run:
        # Simulate ollama not found
        mock_run.side_effect = FileNotFoundError("ollama not found")
        
        # Clear env vars for cloud APIs
        with patch.dict(os.environ, {
            'OPENAI_API_KEY': '',
            'ANTHROPIC_API_KEY': '',
            'GROQ_API_KEY': ''
        }, clear=False):
            from api.llm import client as llm_client
            llm_client._llm_capabilities = None
            llm_client._llm_client = None
            
            config = detect_llm()
            
            assert config.available == False
            assert config.provider is None
            assert "No LLM provider" in config.reason
            print(f"✓ detect_llm correctly returns unavailable: {config.reason}")


def test_llm_client_available_reflects_config():
    """
    Test that LLMClient.available reflects the config state.
    """
    from api.llm.client import get_llm_client, DisabledLLMClient
    
    # Test with mocked unavailable state
    with patch('subprocess.run') as mock_run:
        mock_run.side_effect = FileNotFoundError("ollama not found")
        
        with patch.dict(os.environ, {
            'OPENAI_API_KEY': '',
            'ANTHROPIC_API_KEY': '',
            'GROQ_API_KEY': ''
        }, clear=False):
            from api.llm import client as llm_client
            llm_client._llm_capabilities = None
            llm_client._llm_client = None
            
            client = get_llm_client(force_refresh=True)
            
            assert isinstance(client, DisabledLLMClient)
            print("✓ LLMClient correctly returns DisabledLLMClient when unavailable")


def test_disabled_client_returns_message():
    """
    Test that DisabledLLMClient returns a meaningful message.
    """
    from api.llm.client import DisabledLLMClient
    
    client = DisabledLLMClient()
    result = client.generate("test prompt")
    
    assert "not available" in result.lower() or "unavailable" in result.lower()
    assert len(result) > 20  # Non-empty meaningful message
    print(f"✓ DisabledLLMClient returns message: {result[:60]}...")


def test_real_detection():
    """
    Test actual LLM detection on this machine.
    """
    from api.llm.detector import detect_llm
    from api.llm import client as llm_client
    
    # Clear cache
    llm_client._llm_capabilities = None
    llm_client._llm_client = None
    
    config = detect_llm()
    
    print(f"\n  Real detection result:")
    print(f"    Provider:  {config.provider}")
    print(f"    Model:     {config.model}")
    print(f"    Available: {config.available}")
    print(f"    Reason:    {config.reason}")
    
    # Just verify it returns a valid config structure
    assert hasattr(config, 'provider')
    assert hasattr(config, 'model')
    assert hasattr(config, 'available')
    assert hasattr(config, 'reason')
    print("✓ Real detection returns valid LLMConfig structure")
    
    return config


def run_all_tests():
    """Run all LLM detector tests."""
    print()
    print("=" * 70)
    print("  LLM DETECTOR TESTS")
    print("=" * 70)
    print()
    
    passed = 0
    failed = 0
    
    tests = [
        ("Detect LLM with Ollama llama3", test_detect_llm_with_ollama_llama3),
        ("Detect LLM with only mistral", test_detect_llm_with_only_mistral),
        ("Detect LLM no providers", test_detect_llm_no_providers),
        ("LLM client reflects config", test_llm_client_available_reflects_config),
        ("Disabled client returns message", test_disabled_client_returns_message),
        ("Real detection on this machine", test_real_detection),
    ]
    
    for name, test_fn in tests:
        try:
            test_fn()
            passed += 1
        except Exception as e:
            print(f"✗ {name} FAILED: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print()
    print("=" * 70)
    print(f"  RESULTS: {passed} passed, {failed} failed")
    print("=" * 70)
    print()
    
    return failed == 0


if __name__ == "__main__":
    import sys
    success = run_all_tests()
    sys.exit(0 if success else 1)
