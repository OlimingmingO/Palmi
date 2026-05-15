"""LLM client — Qwen-Max (primary) + DeepSeek-V3 (fallback).

Provides an async chat_completion function that:
- Calls the primary LLM (Qwen-Max) first
- Falls back to secondary (DeepSeek-V3) on failure
- Uses OpenAI-compatible API format
- Logs token usage for cost tracking
"""
import logging
from typing import Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# Timeout for LLM API calls (seconds)
LLM_TIMEOUT = 30.0

# Retry-worthy status codes
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


async def _call_llm(
    messages: list[dict],
    base_url: str,
    api_key: str,
    model: str,
    temperature: float = 0.7,
    max_tokens: int = 1024,
) -> str:
    """Make a single LLM API call. Raises on failure."""
    async with httpx.AsyncClient(timeout=LLM_TIMEOUT) as client:
        response = await client.post(
            f"{base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
        )

        if response.status_code in RETRYABLE_STATUS_CODES:
            raise httpx.HTTPStatusError(
                f"Retryable error: {response.status_code}",
                request=response.request,
                response=response,
            )

        response.raise_for_status()
        data = response.json()

        # Log token usage
        usage = data.get("usage", {})
        logger.info(
            "LLM call complete | model=%s | prompt_tokens=%d | completion_tokens=%d | total_tokens=%d",
            model,
            usage.get("prompt_tokens", 0),
            usage.get("completion_tokens", 0),
            usage.get("total_tokens", 0),
        )

        # Extract assistant message content
        choices = data.get("choices", [])
        if not choices:
            raise ValueError("LLM returned empty choices")

        return choices[0]["message"]["content"]


async def chat_completion(
    messages: list[dict],
    model: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 1024,
) -> str:
    """Call LLM and return assistant message content.

    Tries primary (Qwen-Max) first, falls back to DeepSeek-V3 on failure.

    Args:
        messages: List of message dicts [{"role": "user", "content": "..."}]
        model: Override model name (uses primary by default)
        temperature: Sampling temperature (0.0-1.0)
        max_tokens: Maximum response tokens

    Returns:
        Assistant message content as plain string.

    Raises:
        Exception: If both primary and fallback fail.
    """
    # Determine which models to try
    primary_model = model or settings.LLM_PRIMARY_MODEL
    primary_base_url = settings.LLM_PRIMARY_BASE_URL
    primary_api_key = settings.LLM_PRIMARY_API_KEY

    # Try primary
    try:
        logger.debug("Calling primary LLM: %s", primary_model)
        return await _call_llm(
            messages=messages,
            base_url=primary_base_url,
            api_key=primary_api_key,
            model=primary_model,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    except (httpx.TimeoutException, httpx.HTTPStatusError, httpx.ConnectError) as e:
        logger.warning("Primary LLM failed (%s: %s), trying fallback...", type(e).__name__, str(e))

    # Try fallback
    try:
        logger.debug("Calling fallback LLM: %s", settings.LLM_FALLBACK_MODEL)
        return await _call_llm(
            messages=messages,
            base_url=settings.LLM_FALLBACK_BASE_URL,
            api_key=settings.LLM_FALLBACK_API_KEY,
            model=settings.LLM_FALLBACK_MODEL,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    except Exception as e:
        logger.error("Both primary and fallback LLM failed. Last error: %s", str(e))
        raise RuntimeError(
            f"LLM service unavailable. Primary ({primary_model}) and fallback ({settings.LLM_FALLBACK_MODEL}) both failed."
        ) from e
