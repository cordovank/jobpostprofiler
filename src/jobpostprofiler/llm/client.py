"""
LLM CLIENT — thin wrapper around OpenAI-compatible API.

Provides:
  - get_client()         : cached OpenAI client
  - structured_call()    : single LLM call → validated Pydantic model
  - plain_call()         : single LLM call → raw string (for QA / markdown)
"""

from __future__ import annotations

import json
from typing import TypeVar, Type

from openai import OpenAI
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)

# Module-level client cache
_client_cache: dict[tuple, OpenAI] = {}


def get_client(*, base_url: str | None, api_key: str) -> OpenAI:
    key = (base_url, api_key)
    if key not in _client_cache:
        _client_cache[key] = OpenAI(base_url=base_url, api_key=api_key)
    return _client_cache[key]


def structured_call(
    *,
    client: OpenAI,
    model: str,
    system_prompt: str,
    user_message: str,
    output_type: Type[T],
    temperature: float = 0.0,
) -> T:
    """
    Single LLM call that returns a validated Pydantic model.

    Strategy:
      1. Ask model to respond ONLY with JSON matching the schema.
      2. Parse and validate with Pydantic.
      3. On parse failure: raise ValueError with raw content for debugging.

    Temperature=0 by default — extraction is not a creative task.
    """
    schema_str = json.dumps(output_type.model_json_schema(), indent=2)

    full_system = (
        f"{system_prompt}\n\n"
        f"SCHEMA REFERENCE (do not output this — it is for your reference only):\n"
        f"{schema_str}\n"
        f"- Respond with ONLY the filled JSON instance. Start with {{ and end with }}.\n"
        f"- All list fields must be [] when empty, NEVER null.\n"
        f"- Do not echo this schema in your response.\n"
        f"- No markdown fences, no commentary, no extra keys."
    )

    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": full_system},
            {"role": "user", "content": user_message},
        ],
        # temperature=temperature,
    )

    raw = (resp.choices[0].message.content or "").strip()

    # Strip markdown fences if model adds them despite instructions
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    # If multiple JSON objects present, take the last one.
    # Handles models that echo the schema before outputting the extraction.
    raw = _extract_last_json_object(raw)

    try:
        data = json.loads(raw)
        return output_type.model_validate(data)
    except Exception as exc:
        raise ValueError(
            f"LLM output failed validation for {output_type.__name__}.\n"
            f"Error: {exc}\n"
            f"Raw output:\n{raw}"
        ) from exc

def _extract_last_json_object(text: str) -> str:
    """
    Find the last top-level JSON object in a string.
    Handles models that prepend schema or commentary before the actual output.
    """
    last_start = text.rfind("{")
    if last_start == -1:
        return text

    # Walk back to find the outermost { that contains the last }
    depth = 0
    last_end = -1
    for i in range(len(text) - 1, -1, -1):
        if text[i] == "}":
            depth += 1
        elif text[i] == "{":
            depth -= 1
        if depth == 0 and text[i] == "{":
            last_end = i
            break

    # Scan forward from last_end to find the matching close brace
    depth = 0
    for i in range(last_end, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
        if depth == 0:
            return text[last_end:i + 1]

    return text

def plain_call(
    *,
    client: OpenAI,
    model: str,
    system_prompt: str,
    user_message: str,
    temperature: float = 0.2,
) -> str:
    """Single LLM call returning raw string. Used for markdown rendering and QA."""
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        # temperature=temperature,
    )
    return (resp.choices[0].message.content or "").strip()