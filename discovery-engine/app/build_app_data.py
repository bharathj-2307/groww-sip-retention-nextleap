"""Bundle the results the Streamlit app reads into app/data/.

Run: python build_app_data.py
Keeps only short quotes (not full post text), links back to the public post, and no usernames.
Re-run after the second pass or the opportunity ranking changes.
"""
import json
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data"
OUT = HERE / "data"
OUT.mkdir(exist_ok=True)
sys.path.insert(0, str(HERE.parent / "analyze"))
from analyze import clean  # noqa: E402

raw = {}
for f in (DATA / "raw").glob("*.jsonl"):
    for l in open(f):
        r = json.loads(l)
        raw[r["id"]] = r
ex = {}
if (DATA / "extracted.jsonl").exists():
    for l in open(DATA / "extracted.jsonl"):
        x = json.loads(l)
        if not x.get("error"):
            ex[x["id"]] = x

EXTRA = ["start_reason", "expectation", "drop_reason", "what_checked", "check_frequency", "app_issue_area",
         "outside_action", "influence_source", "need_category", "unmet_need"]
rows = []
for l in open(DATA / "tagged_v3.jsonl"):
    t = clean(json.loads(l))
    if not t.get("relevant"):
        continue
    x = ex.get(t["id"], {})
    rows.append({
        "id": t["id"], "source": t["source"], "date": raw[t["id"]].get("date"), "url": raw[t["id"]]["url"],
        "themes": ",".join(t["themes"]), "stage": t["stage"], "status": t["status"], "age_band": t["age_band"],
        "income_type": t["income_type"], "money_source": t.get("money_source", "unknown"),
        "first_time_investor": t["first_time_investor"], "influenced_by_others": t.get("influenced_by_others", "unknown"),
        "confidence": t["confidence"], "quote": (x.get("evidence") or t.get("quote") or "")[:220],
        "second_pass": bool(x), **{k: x.get(k) for k in EXTRA},
    })
df = pd.DataFrame(rows)
df.to_parquet(OUT / "posts.parquet", index=False)

meta = {"collected": {}, "relevant": {}}
for l in open(DATA / "tagged_v3.jsonl"):
    t = json.loads(l)
    meta["collected"][t["source"]] = meta["collected"].get(t["source"], 0) + 1
    if t.get("relevant"):
        meta["relevant"][t["source"]] = meta["relevant"].get(t["source"], 0) + 1
meta["second_pass_posts"] = int(df["second_pass"].sum())
(OUT / "meta.json").write_text(json.dumps(meta, indent=1))

for name in ("opportunities", "summary_v3"):
    p = DATA / f"{name}.json"
    if p.exists():
        (OUT / f"{name}.json").write_text(p.read_text())

gold = {}
for key, fn in (("first_round_first_labels", "golden_score.json"), ("first_round_reviewed_labels", "golden_score_reviewed.json"),
                ("final", "golden_score_v2.json")):
    p = DATA / fn
    if p.exists():
        gold[key] = json.load(open(p))["summary"]
(OUT / "golden.json").write_text(json.dumps(gold, indent=1))
print(len(df), "posts bundled;", meta["second_pass_posts"], "with second-pass fields")
