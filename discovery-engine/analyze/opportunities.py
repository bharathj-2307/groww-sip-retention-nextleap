"""Rank opportunity areas from the tagged posts (+ second-pass extraction when present).

Run: python opportunities.py   -> writes ../data/opportunities.json and prints the ranking.

An opportunity area is a named group of posts defined by themes and extracted fields. Each area gets:
  reach, drop-off link (with a 95% interval on the difference), early-life weight, fixability, segment skew,
  evidence strength, metric lever, a score and three quotes.
"""
import json
import math
import random
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analyze import DROP, clean  # noqa: E402  (label clean-up shared with the main analysis)

DATA = Path(__file__).resolve().parent.parent / "data"
random.seed(7)

# name: (rule on a post, fixable, metric lever)
# rule(r, x): r = tagged post, x = extracted fields (dict, empty when the second pass has not covered the post)
AREAS = {
    "Autopay and mandate reliability": (
        lambda r, x: "T5" in r["themes"] or x.get("app_issue_area") == "mandate_or_autopay"
        or x.get("drop_reason") == "failed_instalment_or_mandate", "in_app", "Instalment success rate"),
    "SIP set-up and date control": (
        lambda r, x: x.get("app_issue_area") == "sip_setup_or_date" or x.get("need_category") == "flexible_sip_options",
        "in_app", "Starting well and keeping instalments on schedule"),
    "Clear view of returns": (
        lambda r, x: "T3" in r["themes"] or x.get("app_issue_area") == "returns_display" or x.get("need_category") == "clear_returns_view",
        "in_app", "Surviving the first dip"),
    "Support and grievance resolution": (
        lambda r, x: "T13" in r["themes"] or x.get("app_issue_area") == "customer_support" or x.get("need_category") == "better_support",
        "in_app", "Recovering after a failed instalment or pause"),
    "Withdrawal and redemption experience": (
        lambda r, x: x.get("app_issue_area") == "withdrawal_or_redemption", "in_app", "Resisting the exit"),
    "Charges and fee transparency": (
        lambda r, x: x.get("app_issue_area") == "charges_or_fees", "in_app", "Resisting the exit"),
    "App stability and performance": (
        lambda r, x: x.get("app_issue_area") == "crash_or_performance", "in_app", "Instalment success rate"),
    "Trust and reassurance": (
        lambda r, x: "T11" in r["themes"] or x.get("need_category") == "trust_reassurance" or x.get("drop_reason") == "lost_trust",
        "partly", "Resisting the exit"),
    "Expectation setting on returns and timing": (
        lambda r, x: "T2" in r["themes"] or x.get("expectation") in ("quick_gains", "no_loss"), "partly", "Surviving the first dip"),
    "Reassurance during market falls": (
        lambda r, x: x.get("drop_reason") in ("market_fall", "low_returns") or "T4" in r["themes"], "partly", "Surviving the first dip"),
    "Cash-crunch resilience (pause, not stop)": (
        lambda r, x: "T7" in r["themes"] or x.get("drop_reason") in ("cash_crunch_or_life_event", "needs_money"), "partly",
        "Coming back after a pause"),
    "Decision help for beginners": (
        lambda r, x: x.get("need_category") in ("fund_guidance", "learning_education")
        or x.get("outside_action") in ("ask_online_community", "youtube_or_finfluencer"), "outside", "Starting well"),
}
WEIGHT = {"in_app": 1.0, "partly": 0.6, "outside": 0.3}


def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((c - h) / d, (c + h) / d)


def diff_ci(k1, n1, k0, n0, z=1.96):
    """Difference in proportions (in minus out), normal-approximation interval, in percentage points."""
    if n1 == 0 or n0 == 0:
        return (None, None, None)
    p1, p0 = k1 / n1, k0 / n0
    se = math.sqrt(p1 * (1 - p1) / n1 + p0 * (1 - p0) / n0)
    return (100 * (p1 - p0), 100 * (p1 - p0 - z * se), 100 * (p1 - p0 + z * se))


def main():
    tagged = [clean(json.loads(l)) for l in open(DATA / "tagged_v3.jsonl")]
    rel = [r for r in tagged if r.get("relevant")]
    ex_path = DATA / "extracted.jsonl"
    ex = {}
    if ex_path.exists():
        for l in open(ex_path):
            x = json.loads(l)
            if not x.get("error"):
                ex[x["id"]] = x
    raw = {}
    for f in (DATA / "raw").glob("*.jsonl"):
        for l in open(f):
            r = json.loads(l)
            raw[r["id"]] = r
    n = len(rel)
    known = [r for r in rel if r["status"] != "unknown"]
    stage_known = [r for r in rel if r["stage"] != "unknown"]
    overall_early = sum(1 for r in stage_known if r["stage"] in ("0-3 months", "3-12 months")) / max(1, len(stage_known))
    sal_all = [r for r in rel if r["income_type"] != "unknown"]
    sal_rate_all = sum(1 for r in sal_all if r["income_type"] == "salaried") / max(1, len(sal_all))
    age_all = [r for r in rel if r["age_band"] != "unknown"]
    age_rate_all = sum(1 for r in age_all if r["age_band"] == "25-35") / max(1, len(age_all))

    out = []
    for name, (rule, fix, lever) in AREAS.items():
        inn = [r for r in rel if rule(r, ex.get(r["id"], {}))]
        ids = {r["id"] for r in inn}
        k_in = [r for r in inn if r["status"] != "unknown"]
        k_out = [r for r in known if r["id"] not in ids]
        d1 = sum(1 for r in k_in if r["status"] in DROP)
        d0 = sum(1 for r in k_out if r["status"] in DROP)
        diff, lo, hi = diff_ci(d1, len(k_in), d0, len(k_out))
        sk = [r for r in inn if r["stage"] != "unknown"]
        early = sum(1 for r in sk if r["stage"] in ("0-3 months", "3-12 months")) / len(sk) if sk else None
        si = [r for r in inn if r["income_type"] != "unknown"]
        ai = [r for r in inn if r["age_band"] != "unknown"]
        reach = 100 * len(inn) / n
        hi_conf = sum(1 for r in inn if r["confidence"] == "high") / max(1, len(inn))
        sources = Counter(r["source"] for r in inn)
        enough = len(k_in) >= 30 and lo is not None and lo > 0
        score = round(reach * max(0.0, diff or 0.0) * WEIGHT[fix] / 100, 2)
        # quotes: prefer posts that also state a drop, then high confidence, then a readable length
        def key(r):
            q = (ex.get(r["id"], {}).get("evidence") or r.get("quote") or "")
            return (r["status"] in DROP, r["confidence"] == "high", 60 <= len(q) <= 220)
        pool = sorted(inn, key=lambda r: (key(r), random.random()), reverse=True)
        quotes = []
        for r in pool:
            q = (ex.get(r["id"], {}).get("evidence") or r.get("quote") or "").strip()
            if q and len(q) >= 25 and q not in [x["quote"] for x in quotes]:
                quotes.append({"quote": q, "source": r["source"], "url": raw[r["id"]]["url"]})
            if len(quotes) == 3:
                break
        out.append({
            "area": name, "posts": len(inn), "reach_pct": round(reach, 1),
            "drop_rate_in_pct": round(100 * d1 / len(k_in), 1) if k_in else None, "status_known_in": len(k_in),
            "drop_rate_out_pct": round(100 * d0 / len(k_out), 1) if k_out else None,
            "drop_diff_pp": None if diff is None else round(diff, 1),
            "drop_diff_ci_pp": None if lo is None else [round(lo, 1), round(hi, 1)],
            "early_life_pct": None if early is None else round(100 * early, 1), "stage_known_in": len(sk),
            "early_life_vs_all_pp": None if early is None else round(100 * (early - overall_early), 1),
            "salaried_share_pct": round(100 * sum(1 for r in si if r["income_type"] == "salaried") / len(si), 1) if si else None,
            "salaried_share_all_pct": round(100 * sal_rate_all, 1), "income_known_in": len(si),
            "age_25_35_share_pct": round(100 * sum(1 for r in ai if r["age_band"] == "25-35") / len(ai), 1) if ai else None,
            "age_25_35_share_all_pct": round(100 * age_rate_all, 1), "age_known_in": len(ai),
            "fixable": fix, "metric_lever": lever, "high_confidence_pct": round(100 * hi_conf, 1),
            "sources": dict(sources), "evidence": "firm" if enough else "thin", "score": score, "quotes": quotes,
            "second_pass_coverage_pct": round(100 * sum(1 for r in inn if r["id"] in ex) / max(1, len(inn)), 1),
        })
    out.sort(key=lambda a: -a["score"])
    (DATA / "opportunities.json").write_text(json.dumps({"relevant_posts": n, "status_known": len(known), "areas": out}, indent=1,
                                                         ensure_ascii=False))
    print("relevant", n, "status known", len(known), "second-pass rows", len(ex))
    for a in out:
        print(f'{a["score"]:5.2f} {a["area"][:42]:42} reach {a["reach_pct"]:5.1f}% n={a["posts"]:4d} drop {a["drop_rate_in_pct"]}% vs {a["drop_rate_out_pct"]}% '
              f'diff {a["drop_diff_pp"]} {a["drop_diff_ci_pp"]} early {a["early_life_pct"]} {a["evidence"]} cov {a["second_pass_coverage_pct"]}%')


if __name__ == "__main__":
    main()
