"""Reusable LLM client for ORCA Marine Intelligence & LangGraph Orchestrator.

Reuses existing LLM configuration and dependencies:
- OpenAI (gpt-4o-mini via OPENAI_API_KEY)
- Google Gemini (gemini-1.5-flash via GEMINI_API_KEY)
- httpx.AsyncClient for non-blocking HTTP requests with strict timeouts
- Transparent deterministic fallback on missing keys, timeouts, network errors, or malformed responses.
Never hardcodes credentials or adds external paid providers.
"""

import json
import logging
import os
import re
from typing import Any
import httpx

logger = logging.getLogger("orca.agents.llm_client")

DEFAULT_TIMEOUT_SECONDS = 6.0


def get_configured_llm_provider() -> str | None:
    """Return the currently configured LLM provider name ('openai', 'gemini') or None.
    
    Precedence order:
    1. Explicit preference via ORCA_LLM_PROVIDER ('openai' or 'gemini') if its key exists.
    2. 'openai' if OPENAI_API_KEY is configured.
    3. 'gemini' if GEMINI_API_KEY is configured.
    4. None (transparent deterministic fallback).
    """
    pref = os.environ.get("ORCA_LLM_PROVIDER", "").strip().lower()
    if pref == "openai" and os.environ.get("OPENAI_API_KEY"):
        return "openai"
    if pref == "gemini" and os.environ.get("GEMINI_API_KEY"):
        return "gemini"
    if os.environ.get("OPENAI_API_KEY"):
        return "openai"
    if os.environ.get("GEMINI_API_KEY"):
        return "gemini"
    return None


async def call_chat_llm(
    *,
    system_prompt: str,
    user_prompt: str,
    json_mode: bool = False,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> tuple[str | None, str]:
    """Invoke the configured LLM client.

    Returns:
        tuple of (response_text, generation_mode)
        where generation_mode is 'llm' if successful, or 'deterministic' on fallback/failure.
    """
    provider = get_configured_llm_provider()
    openai_key = os.environ.get("OPENAI_API_KEY")
    gemini_key = os.environ.get("GEMINI_API_KEY")
    openai_model = os.environ.get("ORCA_LLM_MODEL", "gpt-4o-mini")

    if provider == "openai" and openai_key:
        try:
            payload: dict[str, Any] = {
                "model": openai_model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.2,
                "max_tokens": 600,
            }
            if json_mode:
                payload["response_format"] = {"type": "json_object"}

            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {openai_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    content = data["choices"][0]["message"]["content"].strip()
                    if content:
                        return content, "llm"
                else:
                    logger.warning("OpenAI LLM request returned non-200 status: %s", resp.status_code)
        except (httpx.TimeoutException, httpx.HTTPError) as exc:
            logger.warning("OpenAI LLM call failed or timed out: %s", exc)
        except Exception as exc:
            logger.warning("Unexpected error during OpenAI LLM call: %s", exc)

    elif provider == "gemini" and gemini_key:
        try:
            gemini_model = os.environ.get("ORCA_LLM_MODEL", "gemini-1.5-flash")
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{gemini_model}:generateContent?key={gemini_key}"
            prompt_content = f"{system_prompt}\n\n{user_prompt}"
            if json_mode:
                prompt_content += "\n\nRespond ONLY with a valid JSON object without surrounding formatting."

            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(
                    url,
                    headers={"Content-Type": "application/json"},
                    json={
                        "contents": [
                            {"role": "user", "parts": [{"text": prompt_content}]}
                        ]
                    },
                )
                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        candidate_text = candidates[0]["content"]["parts"][0]["text"].strip()
                        if candidate_text:
                            return candidate_text, "llm"
                else:
                    logger.warning("Gemini LLM request returned non-200 status: %s", resp.status_code)
        except (httpx.TimeoutException, httpx.HTTPError) as exc:
            logger.warning("Gemini LLM call failed or timed out: %s", exc)
        except Exception as exc:
            logger.warning("Unexpected error during Gemini LLM call: %s", exc)

    return None, "deterministic"


async def call_json_llm(
    *,
    system_prompt: str,
    user_prompt: str,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> tuple[dict[str, Any] | None, str]:
    """Invoke the configured LLM and parse the output as a JSON dictionary.

    Returns:
        tuple of (parsed_dict, generation_mode)
    """
    raw_text, mode = await call_chat_llm(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        json_mode=True,
        timeout=timeout,
    )
    if not raw_text or mode != "llm":
        return None, "deterministic"

    # Strip markdown code blocks if the model wrapped the JSON (e.g. ```json ... ```)
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned)
        if match:
            cleaned = match.group(1).strip()

    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            return parsed, "llm"
        logger.warning("LLM returned valid JSON but not a dictionary: %s", type(parsed))
    except json.JSONDecodeError as exc:
        logger.warning("Failed to decode JSON from LLM response: %s; raw text: %s", exc, raw_text[:200])

    return None, "deterministic"
