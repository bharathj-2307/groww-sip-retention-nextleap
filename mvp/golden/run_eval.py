"""Score the MVP's AI on the golden set.

Run from the mvp folder:  python3 -m golden.run_eval
Writes golden/results.json and prints a summary.
Fresh holdout set:        python3 -m golden.run_eval --holdout   (writes golden/holdout_results.json)
The first holdout run, before any fixes, is kept in golden/holdout_results_before_fixes.json.
"""
from __future__ import annotations

import json
import sys
import time
from datetime import date
from pathlib import Path

from core import ai, gate
from core.sip import SIPS_BY_KEY, facts

HERE = Path(__file__).parent
ROUTE = ai.GROUP_SCREEN  # same group-to-screen map as the app


def main() -> None:
    holdout = "--holdout" in sys.argv
    gs = json.loads((HERE / ("holdout_set.json" if holdout else "golden_set.json")).read_text())
    today = date.fromisoformat(gs["frozen_today"])
    only = set(a for a in sys.argv[1:] if not a.startswith("--"))
    out = {"today": str(today), "sort": [], "explain": [], "questions": [], "gate_tests": []}

    # 1 Sorting
    if not only or "sort" in only:
        for it in gs["sort_items"]:
            r = ai.classify(it["text"])
            g = r.get("group", "error")
            conf = r.get("confidence", 0.0)
            gate_ok = gate.check_group(g, conf)["passed"]
            shown = g if gate_ok else "other"  # unsure goes to the general pop-up
            ok_set = {it["expected"], *it.get("also_ok", [])}
            out["sort"].append({**it, "got": g, "confidence": conf, "gate_passed": gate_ok,
                                "shown_group": shown, "exact": g == it["expected"],
                                "acceptable": g in ok_set, "route_ok": ROUTE.get(shown) in {ROUTE[x] for x in ok_set},
                                "model": r.get("model"), "error": r.get("error")})
            print(it["id"], g, conf, "ok" if g in ok_set else "MISS", flush=True)
            time.sleep(0.5)

    # 2 Explanations, every sample SIP in English and Hindi
    if (not only or "explain" in only) and not holdout:
        for key in SIPS_BY_KEY:
            f = facts(SIPS_BY_KEY[key], today)
            for lang in ("en", "hi"):
                r = ai.explain(f, lang)
                checks = gate.check_text(r.get("text", ""), f, group="cash_short") if "text" in r else []
                out["explain"].append({"sip": key, "lang": lang, "text": r.get("text"), "error": r.get("error"),
                                       "checks": checks, "passed": bool(checks) and gate.passed(checks),
                                       "model": r.get("model")})
                print("explain", key, lang, gate.passed(checks) if checks else "ERR", flush=True)

    # 3 Follow-up questions
    if not only or "questions" in only:
        for it in gs["question_items"]:
            f = facts(SIPS_BY_KEY[it["sip"]], today)
            r = ai.answer(it["text"], f)
            checks = gate.check_text(r.get("text", ""), f, group="cash_short", user_text=it["text"]) if "text" in r else []
            behaviour = "decline" if r.get("declined") else "answer"
            out["questions"].append({**it, "answer": r.get("text"), "declined": r.get("declined"),
                                     "behaviour_ok": behaviour == it["expect"], "checks": checks,
                                     "passed": bool(checks) and gate.passed(checks), "error": r.get("error"),
                                     "model": r.get("model")})
            print(it["id"], behaviour, gate.passed(checks) if checks else "ERR", flush=True)

    # 4 Gate tests: known good and known bad texts, no AI
    for it in gs["gate_tests"]:
        f = facts(SIPS_BY_KEY[it["sip"]], today)
        checks = gate.check_text(it["text"], f, group="cash_short")
        p = gate.passed(checks)
        out["gate_tests"].append({**it, "passed": p, "correct": p == it["should_pass"],
                                  "failed_checks": [c["label"] for c in checks if not c["passed"]]})

    # Summary
    s = {}
    if out["sort"]:
        n = len(out["sort"])
        s["sort_items"] = n
        s["group_accuracy_exact"] = sum(x["exact"] for x in out["sort"]) / n
        s["group_accuracy_acceptable"] = sum(x["acceptable"] for x in out["sort"]) / n
        s["route_accuracy_after_gate"] = sum(x["route_ok"] for x in out["sort"]) / n
        cs = [x for x in out["sort"] if x["expected"] == "cash_short"]
        s["cash_short_recall"] = sum(x["got"] == "cash_short" and x["gate_passed"] for x in cs) / max(1, len(cs))
        s["sort_gate_pass_rate"] = sum(x["gate_passed"] for x in out["sort"]) / n
    texts = out["explain"] + out["questions"]
    if texts:
        s["ai_texts"] = len(texts)
        s["text_gate_pass_rate"] = sum(x["passed"] for x in texts) / len(texts)
    if out["questions"]:
        s["question_behaviour_ok"] = sum(x["behaviour_ok"] for x in out["questions"]) / len(out["questions"])
    s["gate_tests_correct"] = f'{sum(x["correct"] for x in out["gate_tests"])}/{len(out["gate_tests"])}'
    out["summary"] = s
    (HERE / ("holdout_results.json" if holdout else "results.json")).write_text(json.dumps(out, ensure_ascii=False, indent=1, default=str))
    print(json.dumps(s, indent=1))


if __name__ == "__main__":
    main()
