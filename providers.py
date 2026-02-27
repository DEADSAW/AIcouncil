"""
providers.py — LLM provider clients.

Supports:
  - Groq         (OpenAI-compatible)
  - Google Gemini (REST via httpx)
  - OpenRouter   (OpenAI-compatible)
  - Cerebras     (OpenAI-compatible)
  - Cohere       (Cohere SDK)

All providers expose a single function signature:
    chat(messages, model, **kwargs) -> str
"""

import os
from typing import Optional

import httpx
from openai import OpenAI
from dotenv import load_dotenv

try:
    import cohere as _cohere  # type: ignore
    _COHERE_AVAILABLE = True
except ImportError:
    _COHERE_AVAILABLE = False

from config import PROVIDERS

load_dotenv()


# ---------------------------------------------------------------------------
# Helper: build OpenAI-compatible client
# ---------------------------------------------------------------------------

def _openai_client(provider_id: str) -> Optional[OpenAI]:
    cfg = PROVIDERS[provider_id]
    api_key = os.getenv(cfg["env_key"], "")
    if not api_key:
        return None
    return OpenAI(api_key=api_key, base_url=cfg["base_url"])


# ---------------------------------------------------------------------------
# Per-provider chat functions
# ---------------------------------------------------------------------------

def _chat_openai_compatible(provider_id: str, messages: list[dict],
                             model: str, **kwargs) -> str:
    client = _openai_client(provider_id)
    if client is None:
        raise ValueError(f"No API key configured for provider '{provider_id}'. "
                         f"Set {PROVIDERS[provider_id]['env_key']} in your .env file.")
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=kwargs.get("max_tokens", 2048),
        temperature=kwargs.get("temperature", 0.7),
    )
    return response.choices[0].message.content or ""


def _chat_google(messages: list[dict], model: str, **kwargs) -> str:
    api_key = os.getenv("GOOGLE_API_KEY", "")
    if not api_key:
        raise ValueError("No API key configured for Google. Set GOOGLE_API_KEY in your .env file.")

    # Convert OpenAI-style messages to Google format
    contents = []
    system_text = ""
    for msg in messages:
        role = msg["role"]
        content = msg["content"]
        if role == "system":
            system_text = content
            continue
        g_role = "user" if role == "user" else "model"
        contents.append({"role": g_role, "parts": [{"text": content}]})

    payload: dict = {"contents": contents}
    if system_text:
        payload["system_instruction"] = {"parts": [{"text": system_text}]}
    payload["generationConfig"] = {
        "maxOutputTokens": kwargs.get("max_tokens", 2048),
        "temperature": kwargs.get("temperature", 0.7),
    }

    url = f"{PROVIDERS['google']['base_url']}/{model}:generateContent"
    with httpx.Client(timeout=60) as client:
        resp = client.post(
            url,
            params={"key": api_key},
            json=payload,
            headers={"Content-Type": "application/json"},
        )
        resp.raise_for_status()
        data = resp.json()

    try:
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError) as exc:
        raise RuntimeError(f"Unexpected Google API response: {data}") from exc


def _chat_cohere(messages: list[dict], model: str, **kwargs) -> str:
    api_key = os.getenv("COHERE_API_KEY", "")
    if not api_key:
        raise ValueError("No API key configured for Cohere. Set COHERE_API_KEY in your .env file.")

    if not _COHERE_AVAILABLE:
        raise ImportError("cohere package not installed. Run: pip install cohere")

    client = _cohere.Client(api_key)

    # Separate system message from conversation
    system_text = ""
    cohere_messages = []
    for msg in messages:
        if msg["role"] == "system":
            system_text = msg["content"]
        elif msg["role"] == "user":
            cohere_messages.append({"role": "USER", "message": msg["content"]})
        elif msg["role"] == "assistant":
            cohere_messages.append({"role": "CHATBOT", "message": msg["content"]})

    # Last message must be from USER
    if cohere_messages and cohere_messages[-1]["role"] == "USER":
        last_msg = cohere_messages.pop()
        user_message = last_msg["message"]
    else:
        user_message = ""

    response = client.chat(
        model=model,
        message=user_message,
        chat_history=cohere_messages if cohere_messages else None,
        preamble=system_text if system_text else None,
        max_tokens=kwargs.get("max_tokens", 2048),
        temperature=kwargs.get("temperature", 0.7),
    )
    return response.text or ""


# ---------------------------------------------------------------------------
# Public dispatch function
# ---------------------------------------------------------------------------

def chat(provider_id: str, messages: list[dict], model: str, **kwargs) -> str:
    """
    Call the given provider and return the assistant's reply as a string.

    Raises:
        ValueError  — if the API key is missing
        RuntimeError — if the API call fails
    """
    if provider_id not in PROVIDERS:
        raise ValueError(f"Unknown provider: '{provider_id}'")

    provider_type = PROVIDERS[provider_id]["type"]

    if provider_type == "openai_compatible":
        return _chat_openai_compatible(provider_id, messages, model, **kwargs)
    elif provider_type == "google":
        return _chat_google(messages, model, **kwargs)
    elif provider_type == "cohere":
        return _chat_cohere(messages, model, **kwargs)
    else:
        raise ValueError(f"Unsupported provider type: '{provider_type}'")


def is_provider_configured(provider_id: str) -> bool:
    """Return True if the provider has an API key set."""
    cfg = PROVIDERS.get(provider_id, {})
    return bool(os.getenv(cfg.get("env_key", ""), ""))
