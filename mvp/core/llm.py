"""Small Gemini client using Google's OpenAI-compatible endpoint.

The API key comes from the GEMINI_API_KEY environment variable or Streamlit secrets.
It is never stored in the repo.
"""
from __future__ import annotations

import json
import os
import re
import time

import requests

BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
MODELS = [m.strip() for m in os.environ.get(
    "GEMINI_MODELS", "gemini-3.5-flash,gemini-3.5-flash-lite,gemini-3.1-flash-lite").split(",") if m.strip()]


class LLMError(Exception):
    pass


def _api_key() -> str:
    key = os.environ.get("GEMINI_API_KEY", "")
    if not key:
        try:
            import streamlit as st  # only present in the app
            key = st.secrets.get("GEMINI_API_KEY", "")
        except Exception:
            key = ""
    # In the build environment a proxy adds the real key, so a placeholder is fine there.
    return key or "placeholder"


def chat(system: str, user: str, *, json_mode: bool = False, temperature: float = 0.2,
         timeout: int = 40) -> tuple[str, str]:
    """Return (text, model). Tries each model in turn on quota or server errors."""
    headers = {"Authorization": f"Bearer {_api_key()}", "Content-Type": "application/json"}
    last = ""
    for model in MODELS:
        body = {
            "model": model,
            "temperature": temperature,
            "messages": [{"role": "system", "content": system},
                         {"role": "user", "content": user}],
        }
        if json_mode:
            body["response_format"] = {"type": "json_object"}
        for attempt in range(2):
            try:
                r = requests.post(BASE_URL, headers=headers, json=body, timeout=timeout)
            except requests.RequestException as e:
                last = f"{model}: {e}"
                time.sleep(1.5)
                continue
            if r.status_code == 200:
                try:
                    text = r.json()["choices"][0]["message"]["content"] or ""
                except Exception:
                    last = f"{model}: bad response"
                    break
                return text.strip(), model
            last = f"{model}: HTTP {r.status_code} {r.text[:200]}"
            if r.status_code == 429 and "day" in r.text.lower():
                break  # daily quota gone for this model, try the next one
            if r.status_code in (429, 500, 502, 503, 504):
                time.sleep(2 * (attempt + 1))
                continue
            break
    raise LLMError(last or "no model answered")


def parse_json(text: str) -> dict:
    text = text.strip()
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise ValueError("no JSON object in reply")
    return json.loads(m.group(0))
