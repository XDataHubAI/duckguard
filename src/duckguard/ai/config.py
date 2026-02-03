"""AI configuration for DuckGuard."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any


@dataclass
class AIConfig:
    """Configuration for AI-powered features."""

    provider: str = "openai"
    model: str | None = None
    api_key: str | None = None
    base_url: str | None = None
    temperature: float = 0.3
    max_tokens: int = 2000
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def effective_model(self) -> str:
        """Get the effective model name based on provider."""
        if self.model:
            return self.model
        defaults = {
            "openai": "gpt-4o-mini",
            "anthropic": "claude-3-5-haiku-20241022",
            "ollama": "llama3",
        }
        return defaults.get(self.provider, "gpt-4o-mini")

    @property
    def effective_api_key(self) -> str | None:
        """Get API key from config or environment."""
        if self.api_key:
            return self.api_key
        env_vars = {
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
        }
        env_var = env_vars.get(self.provider)
        if env_var:
            return os.environ.get(env_var)
        return None


# Global config singleton
_config: AIConfig | None = None


def configure(
    provider: str = "openai",
    model: str | None = None,
    api_key: str | None = None,
    base_url: str | None = None,
    temperature: float = 0.3,
    **kwargs: Any,
) -> AIConfig:
    """
    Configure the AI backend for DuckGuard.

    Args:
        provider: LLM provider ("openai", "anthropic", "ollama")
        model: Model name (defaults based on provider)
        api_key: API key (or set via environment variable)
        base_url: Custom base URL (for Ollama or proxies)
        temperature: Sampling temperature (default: 0.3 for consistency)
        **kwargs: Additional provider-specific options

    Returns:
        AIConfig instance

    Example:
        from duckguard.ai import configure

        # OpenAI
        configure(provider="openai", api_key="sk-...")

        # Anthropic
        configure(provider="anthropic")  # uses ANTHROPIC_API_KEY env

        # Local Ollama
        configure(provider="ollama", model="llama3",
                  base_url="http://localhost:11434")
    """
    global _config
    _config = AIConfig(
        provider=provider,
        model=model,
        api_key=api_key,
        base_url=base_url,
        temperature=temperature,
        extra=kwargs,
    )
    return _config


def get_config() -> AIConfig:
    """Get the current AI configuration, or create a default one."""
    global _config
    if _config is None:
        _config = AIConfig()
    return _config


def _get_client(config: AIConfig | None = None):
    """
    Get an LLM client based on configuration.

    Returns a callable that takes a prompt and returns a string response.
    """
    cfg = config or get_config()

    if cfg.provider == "openai":
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError(
                "OpenAI support requires the openai package. "
                "Install with: pip install duckguard[llm]"
            )

        client = OpenAI(
            api_key=cfg.effective_api_key,
            base_url=cfg.base_url,
        )

        def call_openai(prompt: str, system: str = "") -> str:
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})

            response = client.chat.completions.create(
                model=cfg.effective_model,
                messages=messages,
                temperature=cfg.temperature,
                max_tokens=cfg.max_tokens,
            )
            return response.choices[0].message.content or ""

        return call_openai

    elif cfg.provider == "anthropic":
        try:
            from anthropic import Anthropic
        except ImportError:
            raise ImportError(
                "Anthropic support requires the anthropic package. "
                "Install with: pip install duckguard[llm]"
            )

        client = Anthropic(api_key=cfg.effective_api_key)

        def call_anthropic(prompt: str, system: str = "") -> str:
            response = client.messages.create(
                model=cfg.effective_model,
                max_tokens=cfg.max_tokens,
                system=system if system else "You are a data quality expert.",
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text

        return call_anthropic

    elif cfg.provider == "ollama":
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError(
                "Ollama support uses the openai package. "
                "Install with: pip install openai"
            )

        client = OpenAI(
            api_key="ollama",
            base_url=cfg.base_url or "http://localhost:11434/v1",
        )

        def call_ollama(prompt: str, system: str = "") -> str:
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})

            response = client.chat.completions.create(
                model=cfg.effective_model,
                messages=messages,
                temperature=cfg.temperature,
            )
            return response.choices[0].message.content or ""

        return call_ollama

    else:
        raise ValueError(
            f"Unsupported AI provider: {cfg.provider}. "
            f"Supported: openai, anthropic, ollama"
        )
