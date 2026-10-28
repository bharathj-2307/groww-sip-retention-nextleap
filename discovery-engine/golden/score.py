"""Score the AI tags against Bharath's hand labels (golden set).

Run: python score.py   -> prints agreement and every disagreement; writes ../data/golden_score.json
Hand labels are copied from the labelling doc as typed, then folded onto the codebook labels.
"""
import json
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
# gid: (relevant, themes, stage, status) exactly as Bharath wrote them (2026-10-23)
HAND = {
    "G01": ("Y", "T12", "Unknown", "Unknown"), "G02": ("Y", "T10", "0-3 months", "reduced"),
    "G03": ("Y", "T13", "unknown", "unkown"), "G04": ("Y", "T7", "unkown", "continuing"),
    "G05": ("Y", "T1", "0-3 months", "continuing"), "G06": ("Y", "T9", "3-12 months", "paused"),
    "G07": ("Y", "T10", "12+ months", "Cancelled"), "G08": ("Y", "T13", "unknown", "unknown"),
    "G09": ("Y", "T9", "0-3 months", "unknown"), "G10": ("Y", "T11", "unknown", "stopped"),
    "G11": ("Y", "T0", "unknown", "unknown"), "G12": ("Y", "T9", "12+ months", "continuing"),
    "G13": ("Y", "T0", "unknown", "unknown"), "G14": ("Y", "T9", "6-12 months", "continuing"),
    "G15": ("Y", "T9", "unknown", "paused"), "G16": ("N", "", "", ""),
    "G17": ("Y", "T9", "6-12 months", "continuing"), "G18": ("Y", "T9", "unknown", "unknown"),
    "G19": ("N", "", "", ""), "G20": ("Y", "T10", "unknown", "unknown"),
}
# Bharath's review of the first scoring (comments typed in the results doc, 2026-10-23). Where he wrote
# "This is correct"/"This works" in the AI column, the AI's value is adopted as the hand label.
REVIEWED = {
    "G11": ("N", "", "", ""),  # AI was right to drop it
    "G03": ("Y", "T13,T5", "unknown", "unkown"), "G07": ("Y", "T10,T5", "12+ months", "Cancelled"),
    "G08": ("Y", "T10,T13,T5", "unknown", "unknown"), "G10": ("Y", "T11,T6", "unknown", "stopped"),
    "G20": ("Y", "T10,T13,T3", "unknown", "unknown"),  # extra themes accepted ("This works")
    "G05": ("Y", "T1", "considering", "continuing"), "G09": ("Y", "T9", "considering", "unknown"),
    "G17": ("Y", "T9", "considering", "continuing"), "G18": ("Y", "T9", "considering", "unknown"),
    "G02": ("Y", "T10", "unknown", "unknown"), "G14": ("Y", "T9", "unknown", "continuing"),  # Bharath: not stated, so unknown
    "G12": ("Y", "T9", "12+ months", "wavering"), "G04": ("Y", "T7", "unkown", "paused_or_reduced"),
}
import sys
if "--reviewed" in sys.argv:
    HAND.update(REVIEWED)
STATUS = {"unkown": "unknown", "reduced": "paused_or_reduced", "paused": "paused_or_reduced", "cancelled": "stopped"}
STAGE = {"6-12 months": "3-12 months", "unkown": "unknown"}

key = json.load(open(DATA / "golden_ai_key.json"))
if "--retag" in sys.argv:  # AI tags from the v2 prompt, same 20 posts
    new = {json.loads(l)["id"]: json.loads(l) for l in open(DATA / "golden_retag.jsonl")}
    key = {g: {**v, **{k: new[v["id"]].get(k) for k in ("relevant", "themes", "stage", "status", "confidence", "quote")}} for g, v in key.items()}
res, rows = {"relevance": [], "themes_exact": [], "themes_overlap": [], "stage": [], "status": []}, []
for gid, (rel, th, stage, status) in HAND.items():
    ai = key[gid]
    h_rel = rel == "Y"
    h_th = {t.strip() for t in th.split(",") if t.strip()}
    a_th = set(ai["themes"])
    h_stage = STAGE.get(stage.lower(), stage.lower())
    h_status = STATUS.get(status.lower(), status.lower())
    a_status = {"pausing_or_reduced": "paused_or_reduced", "stopping_or_pausing": "paused_or_reduced"}.get(ai["status"], ai["status"])
    res["relevance"].append(h_rel == ai["relevant"])
    if h_rel and ai["relevant"]:  # themes / stage / status only compared where both call it relevant
        res["themes_exact"].append(h_th == a_th)
        res["themes_overlap"].append(bool(h_th & a_th))
        res["stage"].append(h_stage == ai["stage"])
        res["status"].append(h_status == a_status)
    rows.append({"gid": gid, "hand": {"relevant": h_rel, "themes": sorted(h_th), "stage": h_stage, "status": h_status},
                 "ai": {"relevant": ai["relevant"], "themes": sorted(a_th), "stage": ai["stage"], "status": a_status,
                        "confidence": ai["confidence"], "quote": ai["quote"]}})

summary = {k: {"agree": sum(v), "of": len(v), "pct": round(100 * sum(v) / len(v), 1)} for k, v in res.items()}
(DATA / ("golden_score_v2.json" if "--retag" in sys.argv else "golden_score_reviewed.json" if "--reviewed" in sys.argv else "golden_score.json")).write_text(json.dumps({"summary": summary, "rows": rows}, indent=1, ensure_ascii=False))
print(json.dumps(summary, indent=1))
for r in rows:
    h, a = r["hand"], r["ai"]
    diffs = [f for f in ("relevant", "themes", "stage", "status") if h[f] != a[f]]
    if diffs and not (not h["relevant"] and not a["relevant"]):
        print(r["gid"], "DIFF", diffs, "| hand", h, "| ai", {k: a[k] for k in ("relevant", "themes", "stage", "status")}, "| quote:", a["quote"][:90])
