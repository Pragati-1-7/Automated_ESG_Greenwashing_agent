"""
llm_providers.py

STEP 2: LLM provider abstraction for claim extraction.

WHY THIS FILE EXISTS
---------------------
The claim extraction engine (claim_extractor.py) needs to send a prompt to
an LLM and get text back. We don't want that code hard-wired to one vendor
(Groq vs Ollama), and we don't want automated tests to require a live API
key. So every provider implements the same tiny interface:

    provider.complete(system_prompt, user_prompt) -> str

and claim_extractor.py only ever talks to that interface, never to Groq or
Ollama directly. This is the standard "adapter pattern": each provider is a
thin adapter around a different backend, all shaped the same way.

PROVIDERS
---------
- MockLLMProvider   : deterministic, no network calls, used by tests and by
                       anyone without an API key. NEVER pretends to be real.
- GroqLLMProvider   : calls Groq's OpenAI-compatible chat completions API.
- OllamaLLMProvider : calls a local Ollama server's /api/chat endpoint.

Both real providers raise LLMConfigurationError with a clear message if
required configuration (API key / base URL / model name) is missing --
they never silently fall back to mock behaviour.
"""

from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod
from typing import Optional


class LLMConfigurationError(Exception):
    """Raised when a real LLM provider is selected but not properly configured."""


class LLMProviderError(Exception):
    """Raised when a real LLM provider's API call itself fails (network, HTTP error, etc.)."""


class BaseLLMProvider(ABC):
    """Common interface every provider must implement."""

    #: Human-readable identifier stored in ClaimRecord.extraction_method,
    #: e.g. "mock", "llm:groq:llama-3.1-70b-versatile", "llm:ollama:llama3".
    provider_label: str

    @abstractmethod
    def complete(self, system_prompt: str, user_prompt: str) -> str:
        """Send a system+user prompt to the LLM and return its raw text response."""
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Mock provider (Part 8 of the Step 2 spec)
# ---------------------------------------------------------------------------

class MockLLMProvider(BaseLLMProvider):
    """Deterministic, offline stand-in for a real LLM.

    Used by:
      - automated tests (tests/test_claim_extractor.py) so CI never needs a
        live API key,
      - anyone running the pipeline without Groq/Ollama configured, via
        `EXTRACTION_MODE=mock` in .env or `--mock` on the CLI scripts.

    IMPORTANT: this does NOT call any LLM. It returns pre-written, clearly
    labelled JSON so it can be told apart from real extraction results at a
    glance. Every claim it returns explains this in its own `notes`-style
    text where relevant, and `provider_label` is always "mock" so callers
    can programmatically detect it (see ClaimRecord.extraction_method).
    """

    provider_label = "mock"

    def __init__(self, canned_responses: Optional[dict[int, str]] = None) -> None:
        """
        Args:
            canned_responses: optional mapping of page_number -> JSON string
                to return for that page. If a page number is not in this
                dict, an empty claims list is returned for it. If None,
                claim_extractor.py supplies its own default canned claims
                for the bundled sample PDF (see mock_data.py).
        """
        self._canned_responses = canned_responses or {}

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        # The extractor always includes "PAGE_NUMBER: <n>" as the first line
        # of the user prompt (see claim_extractor.py); parse it back out so
        # the mock provider can return the right canned response per page
        # without the extractor needing any mock-specific branching.
        page_number = self._extract_page_number(user_prompt)
        if page_number in self._canned_responses:
            return self._canned_responses[page_number]
        return json.dumps({"claims": []})

    @staticmethod
    def _extract_page_number(user_prompt: str) -> Optional[int]:
        for line in user_prompt.splitlines():
            if line.startswith("PAGE_NUMBER:"):
                try:
                    return int(line.split(":", 1)[1].strip())
                except ValueError:
                    return None
        return None


# ---------------------------------------------------------------------------
# Groq provider
# ---------------------------------------------------------------------------

class GroqLLMProvider(BaseLLMProvider):
    """Calls Groq's OpenAI-compatible /openai/v1/chat/completions endpoint.

    Configuration (from environment / .env):
        GROQ_API_KEY     - required
        LLM_MODEL_NAME    - required, e.g. "llama-3.1-70b-versatile"
    """

    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None) -> None:
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        self.model_name = model_name or os.getenv("LLM_MODEL_NAME")

        if not self.api_key or self.api_key == "your_groq_api_key_here":
            raise LLMConfigurationError(
                "GROQ_API_KEY is not set. Copy .env.example to .env and set a real "
                "Groq API key, or run with --mock / EXTRACTION_MODE=mock instead."
            )
        if not self.model_name:
            raise LLMConfigurationError(
                "LLM_MODEL_NAME is not set. Set it in .env, e.g. "
                "LLM_MODEL_NAME=llama-3.1-70b-versatile"
            )

        self.provider_label = f"llm:groq:{self.model_name}"

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        try:
            import requests
        except ImportError as e:
            raise LLMConfigurationError(
                "The 'requests' package is required for GroqLLMProvider. "
                "Install it with: pip install requests"
            ) from e

        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0,
            "response_format": {"type": "json_object"},
        }

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
        except Exception as e:  # noqa: BLE001
            raise LLMProviderError(f"Groq API call failed: {e}") from e

        data = response.json()
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as e:
            raise LLMProviderError(f"Unexpected Groq API response shape: {data}") from e


# ---------------------------------------------------------------------------
# Ollama provider
# ---------------------------------------------------------------------------

class OllamaLLMProvider(BaseLLMProvider):
    """Calls a local Ollama server's /api/chat endpoint.

    Configuration (from environment / .env):
        OLLAMA_BASE_URL  - required, e.g. "http://localhost:11434"
        LLM_MODEL_NAME    - required, e.g. "llama3"
    """

    def __init__(self, base_url: Optional[str] = None, model_name: Optional[str] = None) -> None:
        self.base_url = (base_url or os.getenv("OLLAMA_BASE_URL") or "").rstrip("/")
        self.model_name = model_name or os.getenv("LLM_MODEL_NAME")

        if not self.base_url:
            raise LLMConfigurationError(
                "OLLAMA_BASE_URL is not set. Set it in .env, e.g. "
                "OLLAMA_BASE_URL=http://localhost:11434"
            )
        if not self.model_name:
            raise LLMConfigurationError(
                "LLM_MODEL_NAME is not set. Set it in .env, e.g. LLM_MODEL_NAME=llama3"
            )

        self.provider_label = f"llm:ollama:{self.model_name}"

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        try:
            import requests
        except ImportError as e:
            raise LLMConfigurationError(
                "The 'requests' package is required for OllamaLLMProvider. "
                "Install it with: pip install requests"
            ) from e

        url = f"{self.base_url}/api/chat"
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "format": "json",
            "stream": False,
            "options": {"temperature": 0},
        }

        try:
            response = requests.post(url, json=payload, timeout=120)
            response.raise_for_status()
        except Exception as e:  # noqa: BLE001
            raise LLMProviderError(
                f"Ollama API call failed (is `ollama serve` running at {self.base_url}?): {e}"
            ) from e

        data = response.json()
        try:
            return data["message"]["content"]
        except KeyError as e:
            raise LLMProviderError(f"Unexpected Ollama API response shape: {data}") from e


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def get_provider(mode: Optional[str] = None) -> BaseLLMProvider:
    """Build the right provider from an explicit mode or the EXTRACTION_MODE env var.

    Args:
        mode: one of "mock", "groq", "ollama". If None, read from the
            EXTRACTION_MODE environment variable, defaulting to "mock" so
            the pipeline is always runnable without any credentials.

    Raises:
        LLMConfigurationError: if mode is "groq"/"ollama" and required
            configuration is missing, or if mode is not recognised.
    """
    resolved_mode = (mode or os.getenv("EXTRACTION_MODE") or "mock").strip().lower()

    if resolved_mode == "mock":
        return MockLLMProvider()
    if resolved_mode == "groq":
        return GroqLLMProvider()
    if resolved_mode == "ollama":
        return OllamaLLMProvider()

    raise LLMConfigurationError(
        f"Unknown EXTRACTION_MODE '{resolved_mode}'. Expected one of: mock, groq, ollama."
    )
