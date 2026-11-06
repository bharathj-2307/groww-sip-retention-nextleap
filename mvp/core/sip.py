"""Sample SIPs and the fixed rules that work out the facts.

Facts must be exact every time, so they come from rules, never from AI.
No real user data is used anywhere in the MVP.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

# Groww's published rules (help pages checked 1 Nov 2026).
MISS_LIMIT = 3            # SIP is cancelled after 3 skipped or missed in a row
SKIP_CUTOFF_DAYS = 2      # a skip within 2 days of the date does not apply
PAYDAY_GAP_DAYS = 2       # new date = 2 days after payday
PAY_LESS_MIN_GAP = 500    # hide "pay less" if the fund minimum is this close to the full amount

FUND_NAME = "Sample Equity Fund"  # generic on purpose: the MVP never names a real fund

MONTHS = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]


@dataclass(frozen=True)
class SampleSip:
    key: str
    label: str
    amount: int
    day: int              # day of month the instalment is due
    months_old: int
    misses_in_row: int
    fund_min: int
    skip_in_use: bool = False   # a skip is already booked for the next date
    day_offset: int | None = None  # if set, due date = today + offset (for the "too close to skip" case)


SAMPLE_SIPS = [
    SampleSip("A", "₹3,000 on the 5th · 0 missed", 3000, 5, 7, 0, 500),
    SampleSip("B", "₹2,000 on the 10th · 1 missed", 2000, 10, 5, 1, 500),
    SampleSip("C", "₹5,000 on the 1st · 2 missed in a row", 5000, 1, 9, 2, 1000),
    SampleSip("D", "₹1,000 due tomorrow · 0 missed", 1000, 0, 3, 0, 1000, day_offset=1),
]
SIPS_BY_KEY = {s.key: s for s in SAMPLE_SIPS}


def _next_on_day(today: date, day: int) -> date:
    """Next date with this day of month, strictly after today."""
    y, m = today.year, today.month
    if today.day >= day:
        m += 1
        if m == 13:
            y, m = y + 1, 1
    return date(y, m, min(day, 28))


def _add_month(d: date) -> date:
    y, m = (d.year + 1, 1) if d.month == 12 else (d.year, d.month + 1)
    return date(y, m, min(d.day, 28))


def fmt_date(d: date) -> str:
    return f"{d.day} {MONTHS[d.month - 1]}"


def fmt_inr(n: int) -> str:
    s = str(n)
    if len(s) <= 3:
        return "₹" + s
    head, tail = s[:-3], s[-3:]
    parts = []
    while len(head) > 2:
        parts.insert(0, head[-2:])
        head = head[:-2]
    if head:
        parts.insert(0, head)
    return "₹" + ",".join(parts + [tail])


def facts(sip: SampleSip, today: date | None = None) -> dict:
    """All facts the screens and the AI may use. Nothing else is allowed in AI text."""
    today = today or date.today()
    if sip.day_offset is not None:
        next_date = today + timedelta(days=sip.day_offset)
    else:
        next_date = _next_on_day(today, sip.day)
    after_next = _add_month(next_date)
    days_to_next = (next_date - today).days

    if sip.skip_in_use:
        skip_ok, skip_why = False, "A skip is already booked. You can skip one instalment at a time."
    elif days_to_next <= SKIP_CUTOFF_DAYS:
        skip_ok, skip_why = False, f"The next date is too close. A skip must be set more than {SKIP_CUTOFF_DAYS} days before it."
    else:
        skip_ok, skip_why = True, ""

    pay_less_ok = sip.amount - sip.fund_min >= PAY_LESS_MIN_GAP
    pay_less_why = "" if pay_less_ok else "The fund's minimum is the same as your amount, so it cannot go lower."

    invested = sip.amount * sip.months_old - sip.amount * sip.misses_in_row
    return {
        "fund": FUND_NAME,
        "amount": sip.amount,
        "amount_text": fmt_inr(sip.amount),
        "invested": invested,
        "invested_text": fmt_inr(invested),
        "months_old": sip.months_old,
        "misses_in_row": sip.misses_in_row,
        "miss_limit": MISS_LIMIT,
        "misses_left": MISS_LIMIT - sip.misses_in_row,
        "next_date": next_date,
        "next_date_text": fmt_date(next_date),
        "next_month_text": MONTHS[next_date.month - 1],
        "after_next_date": after_next,
        "after_next_text": fmt_date(after_next),
        "after_next_month_text": MONTHS[after_next.month - 1],
        "fund_min": sip.fund_min,
        "fund_min_text": fmt_inr(sip.fund_min),
        "skip_ok": skip_ok,
        "skip_why": skip_why,
        "pay_less_ok": pay_less_ok,
        "pay_less_why": pay_less_why,
        "move_date_ok": True,
        "today": today,
    }


def new_date_after_payday(payday: int) -> int:
    """SIP day = 2 days after payday, kept within 1-28."""
    d = payday + PAYDAY_GAP_DAYS
    if d > 28:
        d = d - 28
    return d


def facts_for_prompt(f: dict) -> str:
    """Plain list of facts passed to the AI. The gate checks the answer against these."""
    lines = [
        f"Fund: {f['fund']}",
        f"Monthly instalment: {f['amount_text']}",
        f"Total invested so far: {f['invested_text']} over {f['months_old']} months. It stays invested whatever the user chooses.",
        f"Next instalment date: {f['next_date_text']}",
        f"Instalment after that: {f['after_next_text']}",
        f"Missed in a row right now: {f['misses_in_row']}",
        f"Rule: Groww cancels a SIP after {f['miss_limit']} instalments in a row are skipped or missed.",
        "Rule: only one instalment can be skipped at a time.",
        f"Rule: a skip must be set more than {SKIP_CUTOFF_DAYS} days before the date.",
        f"Fund minimum instalment: {f['fund_min_text']}",
        "Rule: cancelling stops future instalments only. Invested money stays until the user redeems it.",
        "Rule: past returns do not tell future returns. Nobody can predict returns.",
        f"Option skip available: {'yes' if f['skip_ok'] else 'no. ' + f['skip_why']}",
        f"Option pay less this month available: {'yes, any amount from ' + f['fund_min_text'] + ' up to ' + f['amount_text'] + '. The full amount comes back from ' + f['after_next_text'] + ' by itself.' if f['pay_less_ok'] else 'no. ' + f['pay_less_why']}",
        "Option move date: yes. The user picks their payday and the SIP moves to 2 days after it.",
    ]
    return "\n".join(lines)
