"""Pick the ~20-post golden set for hand labelling.

Run: python make_golden.py
Writes ../data/golden_posts.json (what Bharath sees: id, source, text) and
../data/golden_ai_key.json (the AI's tags for those posts, kept hidden until Bharath has labelled).
Selection is stratified (fixed seed): mixed sources, at least one post per common theme, and a few the AI called not relevant.
"""
import json
import random
import re
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
random.seed(23)

raw = {}
for f in (DATA / "raw").glob("*.jsonl"):
    for l in open(f):
        r = json.loads(l)
        raw[r["id"]] = r
tagged = [json.loads(l) for l in open(DATA / "tagged.jsonl")]


def clean(t):
    t = re.sub(r"\bu/\w+", "u/[user]", t)
    t = re.sub(r"https?://\S+", "[link]", t)
    return re.sub(r"\s+", " ", t).strip()


def ok(r):
    n = len(clean(raw[r["id"]]["text"]))
    return 140 <= n <= 650


pool = [r for r in tagged if not r.get("error") and ok(r)]
rel = [r for r in pool if r["relevant"]]
notrel = [r for r in pool if not r["relevant"]]

picked, used = [], set()


def take(cands):
    cands = [c for c in cands if c["id"] not in used]
    if cands:
        c = random.choice(cands)
        picked.append(c)
        used.add(c["id"])


# one relevant post for each theme worth testing, from varied sources
for t in ["T1", "T2", "T3", "T4", "T5", "T6", "T7", "T9", "T10", "T11", "T12", "T13"]:
    take([r for r in rel if t in r["themes"]])
# a post where the AI was unsure, and two that state facts about the person (age / income / stage)
take([r for r in rel if r["confidence"] != "high"])
take([r for r in rel if r["age_band"] != "unknown" and r["stage"] != "unknown"])
take([r for r in rel if r["income_type"] == "salaried" and r["first_time_investor"] == "yes"])
# posts the AI threw out as not relevant (tests whether it throws out the right ones)
for src in ("reddit", "play", "youtube", "tqna"):
    take([r for r in notrel if r["source"] == src])
take([r for r in rel if "T8" in r["themes"] or "T5" in r["themes"]])
picked = picked[:20]
random.shuffle(picked)

shown, key = [], {}
for i, r in enumerate(picked, 1):
    gid = f"G{i:02d}"
    m = raw[r["id"]]
    shown.append({"gid": gid, "source": m["source"], "text": clean(m["text"])})
    key[gid] = {k: r.get(k) for k in ("id", "relevant", "themes", "stage", "status", "age_band", "income_type",
                                      "first_time_investor", "confidence", "quote")}
(DATA / "golden_posts.json").write_text(json.dumps(shown, indent=1, ensure_ascii=False))
(DATA / "golden_ai_key.json").write_text(json.dumps(key, indent=1, ensure_ascii=False))
print(len(shown), "posts;", sum(1 for k in key.values() if k["relevant"]), "AI-relevant")
