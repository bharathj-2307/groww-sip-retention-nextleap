"""Count themes, segments and drop-off links from data/tagged.jsonl.

Run: python analyze.py   -> prints a summary and writes ../data/summary.json
"""
import json
import sys
from collections import Counter
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
THEME_NAMES = {
    "T1": "Why they started", "T2": "Expectation gap", "T3": "Confusing numbers",
    "T4": "Low or negative returns", "T5": "Missed or failed instalment",
    "T6": "Pause, reduce, stop or redeem", "T7": "Life event or cash crunch",
    "T8": "Checking too often", "T9": "Asking others", "T10": "App friction",
    "T11": "Trust and safety", "T12": "Feature request", "T13": "Support and charges", "T0": "Other",
}
DROP = {"wavering", "paused_or_reduced", "stopped"}
STATUS_FIX = {"stopping_or_pausing": "paused_or_reduced", "pausing_or_reduced": "paused_or_reduced", "considering": "wavering"}
STAGE_OK = {"considering", "0-3 months", "3-12 months", "12+ months"}


def clean(r):
    """Model sometimes strays from the allowed labels; fold the strays into the nearest label."""
    r = dict(r)
    r["status"] = STATUS_FIX.get(r.get("status"), r.get("status", "unknown"))
    st = (r.get("stage") or "unknown").strip()
    r["stage"] = st if st in STAGE_OK else ("12+ months" if st[:1].isdigit() or st.startswith("36") else "unknown")
    for f in ("first_time_investor", "influenced_by_others"):
        r[f] = {"false": "no", "true": "yes"}.get(str(r.get(f)).lower(), r.get(f, "unknown"))
    r["themes"] = [t for t in r.get("themes", []) if t in THEME_NAMES]
    for f, ok in (("age_band", {"under 25", "25-35", "36+"}), ("income_type", {"salaried", "student", "self_employed"})):
        v = str(r.get(f) or "unknown").strip()
        r[f] = v if v in ok else "unknown"  # stray labels (a bare age, a wrong field's value) are not trusted
    return r


def pct(a, b):
    return round(100 * a / b, 1) if b else 0.0


def in_segment(r):
    """Draft segment: salaried, 25-35, first-time investor, 3-12 months in. Only counts what the post states."""
    return (r.get("income_type") == "salaried" and r.get("age_band") == "25-35"
            and r.get("first_time_investor") == "yes" and r.get("stage") == "3-12 months")


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else "tagged.jsonl"
    rows = [clean(json.loads(l)) for l in open(DATA / src)]
    rel = [r for r in rows if r.get("relevant")]
    out = {"posts_tagged": len(rows), "relevant": len(rel)}

    by_source = {}
    for s in sorted({r["source"] for r in rows}):
        a = [r for r in rows if r["source"] == s]
        by_source[s] = {"collected": len(a), "relevant": sum(1 for r in a if r.get("relevant"))}
    out["by_source"] = by_source

    n = len(rel)
    tc = Counter(t for r in rel for t in r.get("themes", []))
    out["themes"] = {t: {"name": THEME_NAMES.get(t, t), "posts": c, "share_pct": pct(c, n)}
                     for t, c in tc.most_common()}

    for field in ("stage", "status", "age_band", "income_type", "money_source",
                  "first_time_investor", "influenced_by_others"):
        out[field] = dict(Counter(r.get(field, "unknown") for r in rel))

    # Themes among posts that show drop-off vs continuing (the "beyond sentiment" view)
    drop = [r for r in rel if r.get("status") in DROP]
    cont = [r for r in rel if r.get("status") == "continuing"]
    link = {}
    for t in THEME_NAMES:
        d = sum(1 for r in drop if t in r.get("themes", []))
        c = sum(1 for r in cont if t in r.get("themes", []))
        both = d + c
        link[t] = {"name": THEME_NAMES[t], "in_drop_pct": pct(d, len(drop)), "in_continuing_pct": pct(c, len(cont)),
                   "drop_posts": d, "drop_rate_among_theme_pct": pct(d, both)}
    out["drop_vs_continuing"] = {"drop_posts": len(drop), "continuing_posts": len(cont), "themes": link}

    # Opportunity score = how common x how tied to dropping off (share of relevant posts * drop share of status-known posts with the theme)
    opp = []
    for t, v in link.items():
        if t in ("T0", "T6"):  # T6 (pause/stop) is the outcome itself, so its link to dropping off is circular
            continue
        share = tc.get(t, 0) / n if n else 0
        opp.append({"theme": t, "name": v["name"], "share_pct": pct(tc.get(t, 0), n),
                    "drop_rate_among_theme_pct": v["drop_rate_among_theme_pct"],
                    "score": round(share * v["drop_rate_among_theme_pct"], 2)})
    out["opportunity"] = sorted(opp, key=lambda x: -x["score"])

    # Draft segment vs everyone else (only stated attributes count; "unknown" is never assumed)
    seg = [r for r in rel if in_segment(r)]
    rest = [r for r in rel if not in_segment(r)]
    seg_cmp = {"segment_posts": len(seg), "other_posts": len(rest), "themes": {}}
    for t in THEME_NAMES:
        seg_cmp["themes"][t] = {"segment_pct": pct(sum(1 for r in seg if t in r.get("themes", [])), len(seg)),
                                "other_pct": pct(sum(1 for r in rest if t in r.get("themes", [])), len(rest))}
    seg_cmp["segment_drop_pct"] = pct(sum(1 for r in seg if r.get("status") in DROP), len(seg))
    seg_cmp["other_drop_pct"] = pct(sum(1 for r in rest if r.get("status") in DROP), len(rest))
    out["segment_vs_rest"] = seg_cmp

    # How many relevant posts state each segment attribute at all
    out["stated_attributes_pct"] = {
        f: pct(sum(1 for r in rel if r.get(f) not in (None, "unknown")), n)
        for f in ("age_band", "income_type", "money_source", "first_time_investor", "stage", "status")}
    # Drop-off by stage, among posts that state both
    out["drop_by_stage"] = {}
    for st in ("considering", "0-3 months", "3-12 months", "12+ months"):
        a = [r for r in rel if r["stage"] == st and r["status"] != "unknown"]
        out["drop_by_stage"][st] = {"posts": len(a), "drop_pct": pct(sum(1 for r in a if r["status"] in DROP), len(a))}

    # Looser segment cuts, because strict segment posts are rare
    def cut(f):
        a = [r for r in rel if f(r)]
        k = [r for r in a if r["status"] != "unknown"]
        return {"posts": len(a), "status_known": len(k), "drop_pct": pct(sum(1 for r in k if r["status"] in DROP), len(k))}
    out["segment_cuts"] = {
        "salaried": cut(lambda r: r["income_type"] == "salaried"),
        "age 25-35": cut(lambda r: r["age_band"] == "25-35"),
        "salaried and 25-35": cut(lambda r: r["income_type"] == "salaried" and r["age_band"] == "25-35"),
        "first-time investor, 0-12 months": cut(lambda r: r["first_time_investor"] == "yes" and r["stage"] in ("0-3 months", "3-12 months")),
        "all four (strict)": cut(in_segment),
    }
    out["confidence"] = dict(Counter(r.get("confidence") for r in rel))
    out["model_used"] = dict(Counter(r.get("model") for r in rows))

    (DATA / ("summary_v3.json" if "v3" in src else "summary.json")).write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
