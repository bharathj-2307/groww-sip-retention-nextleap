"""Tag collected posts with Gemini using the codebook (v2).

Run: python tag.py [--limit N] [--out FILE]
Reads ../data/raw/*.jsonl, writes ../data/tagged.jsonl (one JSON per post).
Gemini is called through its OpenAI-compatible endpoint; the key is added by the network proxy.
"""
import argparse
import os
import concurrent.futures as cf
import json
import re
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
URL = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
MODELS = os.environ.get("TAG_MODELS", "gemini-3.5-flash,gemini-3.5-flash-lite,gemini-3.1-flash-lite").split(",")  # tried in order, two attempts each
BATCH = int(__import__("os").environ.get("TAG_BATCH", 8))
MAX_CHARS = 1200  # long posts are cut; the first part carries the personal story

THEMES = {
    "T1": "Why they started: stated reason for starting an SIP (tax saving, side income, friend/family, goal)",
    "T2": "Expectation gap: results or timeline differ from what they expected",
    "T3": "Confusing numbers: cannot read returns, XIRR, NAV, units, statements or charges",
    "T4": "Low or negative returns: worry or disappointment about returns",
    "T5": "Missed or failed instalment: autopay/mandate failure, low balance, bounced debit, SIP rejected",
    "T6": "Pause, reduce, stop or redeem: did or is considering pausing, lowering, stopping or withdrawing",
    "T7": "Life event or cash crunch: job loss/change, big expense, emergency, salary delay",
    "T8": "Checking too often: frequent checking, anxiety from daily movement",
    "T9": "Asking others: turns to friends, YouTube, finfluencers, Reddit for reassurance or advice, INCLUDING a post that itself asks others what to do, which fund to pick or whether the plan is good",
    "T10": "App friction: problems with the app itself (UI, finding or modifying a SIP, mandate setup, withdrawal delays, bugs)",
    "T11": "Trust and safety: doubts about safety of money or the platform",
    "T12": "Feature request: asks for an option or feature that does not exist (daily/weekly SIP, choose SIP date, step-up, etc.)",
    "T13": "Support and charges: customer support experience, penalties, bounce charges, fees, complaints not resolved",
    "T0": "Other: relevant but none of the above",
}

SYSTEM = f"""You label public posts about mutual fund SIPs (systematic investment plans) in India, mostly about the Groww app, for a product research team.
Return ONLY JSON: {{"items": [...]}} with one item per input post, in order, each:
{{"id": str,
 "relevant": bool,   // true only if the post is about someone's own (or a close person's) SIP / mutual fund investing experience or the app used for it. False for news, ads, stock tips, F&O/trading, bots, generic advice with no personal experience, replies by company staff.
 "themes": [codes],  // only from the list below; [] if not relevant
 "stage": "considering"|"0-3 months"|"3-12 months"|"12+ months"|"unknown",   // how long since THEIR first SIP, only if stated
 "status": "continuing"|"wavering"|"paused_or_reduced"|"stopped"|"unknown",
 "age_band": "under 25"|"25-35"|"36+"|"unknown",
 "income_type": "salaried"|"student"|"self_employed"|"unknown",
 "money_source": "salary"|"savings"|"family"|"unknown",
 "first_time_investor": "yes"|"no"|"unknown",
 "influenced_by_others": "yes"|"no"|"unknown",
 "months_since_first_sip": number|null,
 "quote": str,       // short exact quote (max 200 chars) from the post that supports the tags; "" if not relevant
 "confidence": "high"|"medium"|"low"}}
Rules: tag only what the post actually says. If age, income, timeline or status is not stated, use "unknown". Never guess from writing style. Never give investment advice. A post can have several themes.
Prompt v2 rules (from the hand-labelled golden set):
- Praise or complaints about the app or its service are relevant even with no SIP detail (e.g. "Groww is a great app, easy to use"): relevant=true, theme T0 if nothing else fits.
- Status: use "unknown" unless the post says what the person did with their SIP (kept going, paused, reduced, stopped, or is thinking of stopping). A complaint about the app or service alone is "unknown", not "wavering". "Continuing" needs a clear statement that they keep investing.
- Stage counts months since THEIR first SIP: "just started", "since last week" = "0-3 months"; "after 4 months", "6 months in" = "3-12 months"; "over a year" = "12+ months"; "planning to start", "want to start", "thinking of investing" = "considering"; no timeline stated = "unknown".
Themes:
""" + "\n".join(f"{k}: {v}" for k, v in THEMES.items())


EXHAUSTED = set()  # models that hit the free tier's daily request quota during this run


def call(posts):
    user = json.dumps([{"id": p["id"], "source": p["source"], "text": p["text"][:MAX_CHARS]} for p in posts],
                      ensure_ascii=False)
    for attempt in range(8):
        live = [m for m in MODELS if m not in EXHAUSTED]
        if not live:
            raise SystemExit("All models hit their daily free-tier quota; resume after it resets.")
        model = live[min(attempt // 2, len(live) - 1)]
        try:
            r = requests.post(URL, timeout=120, json={
                "model": model, "temperature": 0,
                "response_format": {"type": "json_object"},
                "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}]})
            if r.ok:
                content = r.json()["choices"][0]["message"]["content"]
                items = json.loads(re.sub(r"^```(?:json)?|```$", "", content.strip()))["items"]
                by_id = {i["id"]: i for i in items}
                if all(p["id"] in by_id for p in posts):
                    return [{**by_id[p["id"]], "model": model} for p in posts]
            elif r.status_code == 429:
                print("429", model, re.findall(r"quotaId.: .(\w+)", r.text), flush=True)
                if "PerDay" in r.text:
                    EXHAUSTED.add(model)  # daily quota gone: stop wasting calls on this model
                    continue
        except (requests.RequestException, ValueError, KeyError, TypeError):
            pass
        time.sleep(4 * (attempt + 1))
    return [{"id": p["id"], "error": True} for p in posts]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int)
    ap.add_argument("--out", default=str(ROOT / "data" / "tagged.jsonl"))
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--only", help="JSON file: list of post ids to tag")
    a = ap.parse_args()

    posts = [json.loads(l) for f in sorted((ROOT / "data" / "raw").glob("*.jsonl")) for l in open(f)]
    out = Path(a.out)
    done = {json.loads(l)["id"] for l in open(out)} if out.exists() else set()
    todo = [p for p in posts if p["id"] not in done]
    if a.only:
        keep = set(json.load(open(a.only)))
        todo = [p for p in todo if p["id"] in keep]
    if a.limit:
        todo = todo[: a.limit]
    batches = [todo[i:i + BATCH] for i in range(0, len(todo), BATCH)]
    print(f"{len(todo)} posts to tag in {len(batches)} batches", flush=True)
    meta = {p["id"]: p for p in posts}
    with out.open("a") as f, cf.ThreadPoolExecutor(a.workers) as ex:
        for n, res in enumerate(ex.map(call, batches), 1):
            for r in res:
                m = meta[r["id"]]
                f.write(json.dumps({**r, "source": m["source"], "date": m["date"], "url": m["url"],
                                    "rating": m["rating"]}, ensure_ascii=False) + "\n")
            f.flush()
            if n % 10 == 0:
                print(f"{n}/{len(batches)} batches", flush=True)


if __name__ == "__main__":
    main()
