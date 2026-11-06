"""The 5-check quality gate. Plain rules, so every pass or fail can be explained.

1. Facts match     every number and month in the text is a known fact
2. Rules correct   no wrong statement of Groww's rules
3. No advice       no fund names, no buy/sell/switch/stop advice, no return forecasts
4. Calm tone       no fear or urgency words, no exclamation marks
5. Right group     the group is clear, and only options that apply are offered

If any check fails the user sees Groww's current pop-up and a help link.
"""
from __future__ import annotations

import re

from .ai import GROUPS, CONFIDENCE_MIN
from .sip import MONTHS, CHANGE_CUTOFF_WORKDAYS, CANCEL_NOTICE_DAYS, PAYDAY_GAP_DAYS, PAY_LESS_LIMIT, FUND_NAME

SIP_DAY_MAX = 28  # a SIP date can be any day from 1 to 28

HINDI_MONTHS = ["जनवरी", "फ़रवरी", "फरवरी", "मार्च", "अप्रैल", "मई", "जून", "जुलाई",
                "अगस्त", "सितंबर", "सितम्बर", "अक्टूबर", "नवंबर", "नवम्बर", "दिसंबर", "दिसम्बर"]
HINDI_MONTH_INDEX = {"जनवरी": 1, "फ़रवरी": 2, "फरवरी": 2, "मार्च": 3, "अप्रैल": 4, "मई": 5,
                     "जून": 6, "जुलाई": 7, "अगस्त": 8, "सितंबर": 9, "सितम्बर": 9, "अक्टूबर": 10,
                     "नवंबर": 11, "नवम्बर": 11, "दिसंबर": 12, "दिसम्बर": 12}
DEV_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")

# Fund houses and brands sold in India. Any mention means the text names a fund.
FUND_BRANDS = [
    "hdfc", "icici", "sbi", "axis", "nippon", "kotak", "parag parikh", "ppfas", "quant", "mirae",
    "uti", "tata", "aditya birla", "absl", "dsp", "motilal", "navi", "edelweiss", "franklin",
    "canara", "bandhan", "invesco", "hsbc", "pgim", "sundaram", "baroda", "lic mf", "mahindra",
    "whiteoak", "bajaj finserv", "jm financial", "union mf", "groww nifty", "zerodha", "nifty 50",
    "nifty50", "sensex", "small cap", "smallcap", "mid cap", "midcap", "large cap", "flexi cap",
    "flexicap", "index fund", "liquid fund", "debt fund", "elss", "gold", "fixed deposit", " fd ",
    "bitcoin", "crypto",
]
ADVICE = [
    r"\byou should\b", r"\byou must\b", r"\bi (?:would )?(?:recommend|suggest|advise)\b",
    r"\bbetter to\b", r"\bbest (?:fund|option|choice)\b", r"\bswitch to\b",
    r"\bconsider (?:investing|buying|switching|selling|redeeming)\b",
    r"\b(?:buy|sell) (?:more|now|units)\b", r"\bredeem now\b",
    r"\b(?:market|returns?|nav|fund) (?:will|is going to) (?:grow|rise|go up|fall|go down|recover|increase|drop)\b",
    r"\bguarantee", r"\bassured returns?\b", r"\bsure to (?:grow|gain)\b",
    r"\b(?:markets?|returns?|navs?|funds?|prices?) (?:always|usually|surely|will surely) (?:recover|bounce back|go up|grow|rise)\b",
    r"\balways (?:recover|bounce back)\b", r"\bkeep (?:going|investing)\b", r"\bdon'?t stop\b",
    r"चाहिए", r"सलाह देत", r"\bkarna chahiye\b",
]
FEAR = [
    r"\bhurry\b", r"\burgent", r"\bimmediately\b", r"\blast chance\b", r"\bact now\b",
    r"\bdon'?t miss\b", r"\btoo late\b", r"\blose everything\b", r"\blose all\b", r"\bwarning\b",
    r"\bdanger", r"\bpanic", r"\bregret", r"\brisk losing\b", r"\bdisaster\b", r"\bterrible\b",
    r"\bfomo\b", r"\bjaldi\b", r"\bturant\b", r"जल्दी", r"तुरंत", r"आखिरी मौका", r"खतरा", r"पछता",
]
WRONG_RULES = [
    # cancelling or skipping does not take away or withdraw invested money
    r"\b(?:lose|lost|forfeit)\b[^.]{0,30}\b(?:invest|money|amount|savings)",
    r"\bcancel\w*\b[^.]{0,40}\b(?:withdraw|refund|return)s? (?:your|the) (?:money|investment|amount)",
    r"\bmoney will be (?:withdrawn|refunded|lost)\b",
    # only one skip at a time
    r"\bskip (?:two|2|three|3|multiple|several) (?:months|instalments|installments)\b(?! (?:is|are) not)",
    r"\bpause (?:for )?(?:up to )?(?:\d+|three|six|twelve) months\b",
    # invested money is not "safe": it stays invested and its value can go up or down
    r"\bsafe(?:ly)?\b", r"\bsecure(?:d|ly)?\b", r"\bprotected\b", r"सुरक्षित",
    # Groww does not charge a penalty
    r"\bgroww (?:will )?charges? (?:a )?(?:penalty|fine|fee)\b",
]
NEGATION = re.compile(r"\b(?:not|cannot|can't|can not|isn't|unavailable|already|too close|used|locked|opens again|again on)\b|नहीं|संभव नहीं|इस्तेमाल", re.I)


def _known_dates(f: dict) -> list:
    ds = [f["next_date"], f["after_next_date"], f["third_date"], f["target_date"], f["target_after_date"]]
    if f.get("pay_less_reopen"):
        ds.append(f["pay_less_reopen"])
    return ds


def _allowed_numbers(f: dict, extra_text: str = "") -> set[int]:
    nums = {f["amount"], f["invested"], f["months_old"], f["misses_in_row"], f["miss_limit"],
            f["misses_left"], f["fund_min"], f["today"].year, f["pay_less_used"], f["pay_less_left"],
            CHANGE_CUTOFF_WORKDAYS, CANCEL_NOTICE_DAYS, PAYDAY_GAP_DAYS, PAY_LESS_LIMIT, 0, 1, 12,
            SIP_DAY_MAX}
    for d in _known_dates(f):
        nums.update({d.day, d.year})
    # Numbers the user wrote may be repeated if they look like an amount or a day, not an ID.
    for n in _numbers(extra_text):
        if n <= 31 or (f["fund_min"] <= n <= f["amount"] * 12):
            nums.add(n)
    return nums


def _numbers(text: str) -> list[int]:
    t = text.translate(DEV_DIGITS)
    out = []
    for m in re.finditer(r"\d[\d,]*", t):
        s = m.group(0).rstrip(",").replace(",", "")
        if s:
            out.append(int(s))
    return out


def _months(text: str) -> set[int]:
    found = set()
    low = text.lower()
    for i, name in enumerate(MONTHS, 1):
        if name == "May":
            # "may" is also a common word, so count it only next to a number: "5 May", "May 5"
            if re.search(r"\d\s+may\b|\bmay\s+\d", low):
                found.add(i)
        elif re.search(r"\b" + name.lower() + r"\b", low) or re.search(r"\b" + name[:3] + r"\b", text):
            found.add(i)
    for name, i in HINDI_MONTH_INDEX.items():
        if name in text:
            found.add(i)
    return found


def _check(name: str, label: str, passed: bool, detail: str = "") -> dict:
    return {"name": name, "label": label, "passed": passed, "detail": detail}


def check_text(text: str, f: dict, *, group: str, confidence: float = 1.0,
               user_text: str = "") -> list[dict]:
    """Run all five checks on an AI text shown to the user."""
    low = " " + text.lower() + " "
    checks = []

    # 1 Facts match
    allowed = _allowed_numbers(f, user_text)
    bad_nums = [n for n in _numbers(text) if n not in allowed]
    ok_months = {d.month for d in _known_dates(f)} | {f["today"].month} | {
        MONTHS.index(m) + 1 for M in f.get("pay_less_use_months", []) for m in MONTHS if m.startswith(M)}
    bad_months = [MONTHS[m - 1] for m in _months(text) if m not in ok_months]
    # Each date written must be a real SIP date, not just a known number.
    ok_dates = {(d.day, d.month) for d in _known_dates(f)}
    t = text.translate(DEV_DIGITS)
    month_alt = "|".join([m for m in MONTHS] + [m[:3] for m in MONTHS] + list(HINDI_MONTH_INDEX))
    for m in re.finditer(r"(\d{1,2})(?:st|nd|rd|th)?\s+(?:of\s+)?(" + month_alt + r")\b", t, re.I):
        day, name = int(m.group(1)), m.group(2)
        mon = HINDI_MONTH_INDEX.get(name) or next(i for i, x in enumerate(MONTHS, 1) if x.lower().startswith(name.lower()[:3]))
        if (day, mon) not in ok_dates:
            bad_nums.append(f"{day} {MONTHS[mon - 1]}")
    detail = ""
    if bad_nums:
        detail += f"Unknown numbers: {bad_nums[:4]}. "
    if bad_months:
        detail += f"Unknown months: {bad_months}."
    checks.append(_check("facts", "Facts match", not bad_nums and not bad_months, detail.strip()))

    # 2 Rules correct
    hits = []
    for m in re.finditer(r"(\d+|zero|one|two|three|four|five)\s+(?:\w+\s+){0,3}?in a row", low):
        word = m.group(1)
        n = {"zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5}.get(word, None)
        n = int(word) if n is None else n
        if n not in (f["misses_in_row"], f["miss_limit"], f["misses_left"]):
            hits.append(m.group(0))
    # "cancels after 2 missed payments" must use the real limit too
    for m in re.finditer(r"after\s+(\d+|one|two|three|four|five)\s+(?:\w+\s+){0,2}?(?:missed|skipped|failed)", low):
        w = m.group(1)
        n = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5}.get(w) or int(w)
        if n != f["miss_limit"]:
            hits.append(m.group(0))
    for m in re.finditer(r"(\d+|one|two|three|four)\s+times?\s+in\s+(?:any\s+|the\s+last\s+)?12\s+months", low):
        w = m.group(1)
        n = {"one": 1, "two": 2, "three": 3, "four": 4}.get(w) or int(w)
        if n not in (PAY_LESS_LIMIT, f["pay_less_used"], f["pay_less_left"]):
            hits.append(m.group(0))
    for p in WRONG_RULES:
        m = re.search(p, low)
        if m and not NEGATION.search(low[max(0, m.start() - 25):m.end() + 15]):
            hits.append(m.group(0))
    checks.append(_check("rules", "Rules correct", not hits, ("Wrong rule: " + "; ".join(hits[:3])) if hits else ""))

    # 3 No advice
    scrub = low.replace(FUND_NAME.lower(), " ")
    brands = [b.strip() for b in FUND_BRANDS if b in scrub]
    advice = [re.search(p, scrub).group(0) for p in ADVICE if re.search(p, scrub)]
    det = ""
    if brands:
        det += f"Names a fund or product: {brands[:3]}. "
    if advice:
        det += f"Advice words: {advice[:3]}."
    checks.append(_check("advice", "No advice", not brands and not advice, det.strip()))

    # 4 Calm tone
    fear = [re.search(p, low).group(0) for p in FEAR if re.search(p, low)]
    if "!" in text:
        fear.append("!")
    checks.append(_check("tone", "Calm tone", not fear, ("Pressure words: " + ", ".join(fear[:3])) if fear else ""))

    # 5 Right group
    problems = []
    if group not in GROUPS:
        problems.append(f"unknown group '{group}'")
    if confidence < CONFIDENCE_MIN:
        problems.append(f"AI not sure ({confidence:.2f})")
    for opt, ok_key, words in (("skip", "skip_ok", r"\bskip(?:ping)?\b|स्किप"),
                               ("pay less", "pay_less_ok", r"\bpay less|कम (?:पैसे|राशि|रकम)")):
        if not f[ok_key]:
            denied = False
            for m in re.finditer(words, low):
                near = low[max(0, m.start() - 25):m.end() + 25]
                # "you can skip", "you may pay less", "with one tap": a clear offer, whatever came before
                if re.search(r"\b(?:can|may|could)\s+(?:still\s+)?(?:skip|pay less)|with one tap|\btap to\b", near):
                    problems.append(f"offers {opt}, which is not available")
                    break
                if NEGATION.search(low[max(0, m.start() - 40):m.end() + 80]):
                    denied = True
                    continue
                if denied:
                    continue  # a later mention after the answer already said it is not available
                problems.append(f"offers {opt}, which is not available")
                break
    if f.get("too_close"):
        # The locked instalment itself cannot be skipped, only the one after it.
        locked = r"\bskip(?:ping)?\s+(?:the\s+)?(?:this month|this (?:instalment|installment|payment)|next (?:one|instalment|payment)|" + \
                 re.escape(f["next_date_text"].lower()) + "|" + MONTHS[f["next_date"].month - 1].lower() + r")\b"
        m = re.search(locked, low)
        if m and not NEGATION.search(low[max(0, m.start() - 40):m.end() + 20]):
            problems.append("offers to skip the locked instalment")
    checks.append(_check("group", "Right group", not problems, "; ".join(problems)))
    return checks


def check_group(group: str, confidence: float) -> dict:
    """The gate on the sorting step alone. Unsure goes to the general pop-up."""
    ok = group in GROUPS and confidence >= CONFIDENCE_MIN
    detail = "" if ok else (f"AI not sure ({confidence:.2f})" if group in GROUPS else f"unknown group '{group}'")
    return _check("group", "Right group", ok, detail)


def passed(checks: list[dict]) -> bool:
    return all(c["passed"] for c in checks)
