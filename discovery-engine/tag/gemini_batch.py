"""Shared Gemini client for the two tagging passes (tag.py and extract.py).

Gemini is called through its OpenAI-compatible endpoint. The key is added by the network proxy, never stored here.
Free tier: each model has a daily request quota. A model that hits it is skipped for the rest of the run,
and the run stops when every model is out. Re-running resumes where it stopped.
"""
import json
import os
import re
import time

import requests

URL = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
MODELS = os.environ.get("TAG_MODELS", "gemini-3.5-flash,gemini-3.5-flash-lite,gemini-3.1-flash-lite").split(",")  # tried in order, two attempts each
BATCH = int(os.environ.get("TAG_BATCH", 3))  # posts per request
MAX_CHARS = 1200  # long posts are cut; the first part carries the personal story

EXHAUSTED = set()  # models that hit the daily quota during this run


def call(system, posts):
    """Send a batch of posts with the given instructions. Returns one result per post, in order.

    Each result is the model's item plus the model name, or {"id", "error": True} after all retries fail.
    """
    user = json.dumps([{"id": p["id"], "source": p["source"], "text": p["text"][:MAX_CHARS]} for p in posts],
                      ensure_ascii=False)
    for attempt in range(8):
        live = [m for m in MODELS if m not in EXHAUSTED]
        if not live:
            raise SystemExit("All models hit their daily free-tier quota; resume after it resets.")
        model = live[min(attempt // 2, len(live) - 1)]
        try:
            r = requests.post(URL, timeout=120, json={
                "model": model, "temperature": 0, "response_format": {"type": "json_object"},
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]})
            if r.ok:
                content = r.json()["choices"][0]["message"]["content"]
                items = json.loads(re.sub(r"^```(?:json)?|```$", "", content.strip()))["items"]
                by_id = {i["id"]: i for i in items}
                if all(p["id"] in by_id for p in posts):
                    return [{**by_id[p["id"]], "model": model} for p in posts]
            elif r.status_code == 429:
                print("429", model, re.findall(r"quotaId.: .(\w+)", r.text), flush=True)
                if "PerDay" in r.text:
                    EXHAUSTED.add(model)
                    continue
        except (requests.RequestException, ValueError, KeyError, TypeError):
            pass
        time.sleep(4 * (attempt + 1))
    return [{"id": p["id"], "error": True} for p in posts]
