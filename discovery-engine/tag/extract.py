"""Second AI pass: pull the detail the brief's questions need from each real experience.

Run: TAG_BATCH=3 python extract.py [--limit N] [--out FILE] [--only ids.json]
Reads data/tagged_v3.jsonl (posts the first pass called relevant) and data/raw/*.jsonl,
writes data/extracted.jsonl. Same free-tier handling as tag.py: exhausted models are skipped,
the run exits when all are out, and re-running resumes where it stopped.
"""
import argparse
import concurrent.futures as cf
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gemini_batch import BATCH, call  # noqa: E402  (shared Gemini client)

ROOT = Path(__file__).resolve().parent.parent

FIELDS = {
    "start_reason": ["tax_saving", "long_term_wealth", "specific_goal", "extra_income", "friend_family", "video_or_influencer",
                     "app_prompt", "beat_fd_or_inflation", "unknown"],
    "expectation": ["quick_gains", "steady_long_term", "specific_target", "no_loss", "unknown"],
    "drop_reason": ["market_fall", "low_returns", "cash_crunch_or_life_event", "failed_instalment_or_mandate",
                    "app_or_support_issue", "switched_platform_or_fund", "needs_money", "lost_trust", "not_applicable", "unknown"],
    "what_checked": ["returns_or_xirr", "portfolio_value", "nav", "sip_status", "market_news", "none", "unknown"],
    "check_frequency": ["daily", "weekly", "monthly", "rare", "unknown"],
    "app_issue_area": ["sip_setup_or_date", "mandate_or_autopay", "returns_display", "charges_or_fees", "withdrawal_or_redemption",
                       "kyc_or_account", "customer_support", "crash_or_performance", "other", "none"],
    "outside_action": ["ask_online_community", "youtube_or_finfluencer", "friend_or_family", "advisor_or_distributor",
                       "compare_other_app", "search_online", "none", "unknown"],
    "influence_source": ["friend_or_family", "youtuber_or_finfluencer", "advisor", "app", "social_media", "self", "unknown"],
    "need_category": ["fund_guidance", "clear_returns_view", "reliable_autopay", "flexible_sip_options", "better_support",
                      "trust_reassurance", "learning_education", "tax_help", "none", "other"],
}

SYSTEM = f"""You read public posts about mutual fund SIPs in India (mostly Groww) and extract detail for a product research team.
Return ONLY JSON: {{"items": [...]}} with one item per input post, in order. Each item:
{{"id": str,""" + ",".join(f'\n "{k}": one of {v}' for k, v in FIELDS.items()) + """,
 "unmet_need": str,   // what the person wants and does not get, in at most 10 words; "" if none
 "evidence": str}}    // one short exact quote (max 200 chars) that supports the most important answer
Rules:
- Answer from what the post says. If it does not say, use "unknown" (or "none" where that value exists). Never guess from tone.
- drop_reason: only if the person paused, reduced, stopped, redeemed or is thinking of it; otherwise "not_applicable".
- what_checked / check_frequency: only if the post says what they look at or how often.
- app_issue_area: the part of the app or service the post complains about or is confused by; "none" if no complaint about it.
- outside_action: what the person does or did outside the app to decide (posting for advice on Reddit counts as ask_online_community).
- influence_source: who or what got them to start investing, if stated.
- need_category: the kind of unmet need, "none" if the post states no need or request.
- drop_reason (v2): a complaint, feature request or bad review is NOT a drop reason; use "not_applicable" unless the person says they paused, reduced, stopped, redeemed, switched away or are thinking of it. needs_money = they want to use the money for something else; cash_crunch_or_life_event = job loss, emergency, big expense or move; lost_trust = they say they distrust the platform or tell others to stay away.
- drop_reason (v2, cont.): asking whether to continue, stop or restructure SIPs because funds are in loss is low_returns (or market_fall); this counts as thinking of stopping. needs_money only when they say they need the cash; redeeming while angry at the app or telling others to stay away is lost_trust.
- failed_instalment_or_mandate (v2): only when the post says a debit, mandate or autopay failed or bounced. People skipping, forgetting or discontinuing instalments on their own is not a failed instalment; use "unknown" or the reason they give.
- app_issue_area (v2): a complaint about being unable to change, reduce, pause or time a SIP is sip_setup_or_date; a delay or problem getting money out is withdrawal_or_redemption; missing weekly SIPs, SWP or STP is sip_setup_or_date or other, not returns_display.
- need_category (v2): asking others what to do with their money, whether to keep, switch or restructure funds, or which fund to pick is fund_guidance. A complaint about a delayed redemption is better_support or trust_reassurance, not reliable_autopay; reliable_autopay only when the post is about instalments not being collected.
- Never recommend funds or give investment advice."""



def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int)
    ap.add_argument("--out", default=str(ROOT / "data" / "extracted.jsonl"))
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--only", help="JSON file: list of post ids")
    a = ap.parse_args()

    raw = {}
    for f in (ROOT / "data" / "raw").glob("*.jsonl"):
        for l in open(f):
            r = json.loads(l)
            raw[r["id"]] = r
    # Posts whose only theme is "Other" (mostly one-line praise) carry nothing for these questions, so they are skipped
    tagged = [json.loads(l) for l in open(ROOT / "data" / "tagged_v3.jsonl")]
    relevant = [t["id"] for t in tagged if t.get("relevant") and set(t.get("themes", [])) - {"T0"}]
    out = Path(a.out)
    done = {json.loads(l)["id"] for l in open(out)} if out.exists() else set()
    keep = set(json.load(open(a.only))) if a.only else None
    todo = [raw[i] for i in relevant if i not in done and (keep is None or i in keep)]
    if a.limit:
        todo = todo[: a.limit]
    batches = [todo[i:i + BATCH] for i in range(0, len(todo), BATCH)]
    print(f"{len(todo)} posts to extract in {len(batches)} batches", flush=True)
    with cf.ThreadPoolExecutor(a.workers) as ex:
        for n, res in enumerate(ex.map(lambda batch: call(SYSTEM, batch), batches), 1):
            # open and close per batch: the project-files mount only keeps a file once it is closed
            with out.open("a") as f:
                for r in res:
                    f.write(json.dumps(r, ensure_ascii=False) + "\n")
            if n % 10 == 0:
                print(f"{n}/{len(batches)} batches", flush=True)


if __name__ == "__main__":
    main()
