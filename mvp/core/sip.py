"""Sample SIPs and the fixed rules that work out the facts.

Facts must be exact every time, so they come from rules, never from AI.
No real user data is used anywhere in the MVP.
"""
from __future__ import annotations

import calendar
from dataclasses import dataclass, field
from datetime import date, timedelta

# Groww's published rules (help pages checked 1 Nov 2026) and Steady SIP rules (agreed 6 Nov 2026).
MISS_LIMIT = 3             # Groww cancels a SIP after 3 skipped or missed in a row
CHANGE_CUTOFF_WORKDAYS = 2  # instalment within 2 working days: skip and amount or date changes apply only from the next one
CANCEL_NOTICE_DAYS = 7      # instalment within 7 days: it may still be taken after a cancel (Groww pages say 3 working or 7 days)
PAYDAY_GAP_DAYS = 2        # new SIP date = 2 days after payday
PAY_LESS_LIMIT = 2         # pay less can be used 2 times in any 12 months

FUND_NAME = "Sample Equity Fund"  # generic on purpose: the MVP never names a real fund

MONTHS = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]


@dataclass(frozen=True)
class SampleSip:
    key: str
    label: str
    hint: str
    amount: int
    day: int                  # day of month the instalment is due
    months_old: int
    misses_in_row: int
    fund_min: int
    pay_less_months_ago: tuple = field(default_factory=tuple)  # pay less used this many months ago
    next_workday: bool = False  # due date = next working day (debit too close to change)
    check: str = ""             # what a tester should look for in this case


SAMPLE_SIPS = [
    SampleSip("A", "Never missed a payment",
              "₹3,000 SIP on the 5th. Never missed a payment.",
              3000, 5, 7, 0, 500,
              check="Are the choices before cancelling clear?"),
    SampleSip("B", "Payment is 1 or 2 days away",
              "The next ₹3,000 payment is in 1 or 2 days. It is too late to change it.",
              3000, 0, 7, 0, 500, next_workday=True,
              check="Is it clear what happens if your balance is low?"),
    SampleSip("C", "Already paid less twice",
              "Paid less in each of the last 2 months. Pay less is locked for now.",
              3000, 5, 9, 0, 500, pay_less_months_ago=(2, 1),
              check="Is it clear why Pay less is locked?"),
    SampleSip("D", "Missed last 2 payments",
              "Missed the last 2 payments. One more miss cancels the SIP.",
              2000, 15, 6, 2, 500,
              check="Is the message calm? Skip should not be offered."),
]
SIPS_BY_KEY = {s.key: s for s in SAMPLE_SIPS}


def _month_add(d: date, n: int, day: int | None = None) -> date:
    """Same day n months later. If that month is shorter, use its last day (30 Jan + 1 month = 28 Feb)."""
    m = d.month - 1 + n
    y, m = d.year + m // 12, m % 12 + 1
    return date(y, m, min(day or d.day, calendar.monthrange(y, m)[1]))


def _next_on_day(today: date, day: int) -> date:
    """Next date with this day of month, strictly after today."""
    d = date(today.year, today.month, min(day, 28))
    return d if d > today else _month_add(d, 1, day)


def _next_workday(today: date) -> date:
    d = today + timedelta(days=1)
    while d.weekday() >= 5:
        d += timedelta(days=1)
    return d


def workdays_until(today: date, due: date) -> int:
    """Working days (Mon-Fri) after today up to and including the due date. Holidays are ignored."""
    n, d = 0, today
    while d < due:
        d += timedelta(days=1)
        if d.weekday() < 5:
            n += 1
    return n


def fmt_date(d: date, year: bool = False) -> str:
    return f"{d.day} {MONTHS[d.month - 1]}" + (f" {d.year}" if year else "")


def fmt_short(d: date) -> str:
    return f"{d.day} {MONTHS[d.month - 1][:3]}"


def fmt_inr(n: int) -> str:
    s = str(int(n))
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
    next_date = _next_workday(today) if sip.next_workday else _next_on_day(today, sip.day)
    after_next = _month_add(next_date, 1)
    third = _month_add(next_date, 2)
    too_close = workdays_until(today, next_date) <= CHANGE_CUTOFF_WORKDAYS
    cancel_may_debit = (next_date - today).days <= CANCEL_NOTICE_DAYS

    # Pay less history. Each use was on an instalment date some months ago.
    uses = sorted(_month_add(next_date, -m) for m in sip.pay_less_months_ago)
    window_start = _month_add(today, -12, today.day)
    uses_in_window = [u for u in uses if u > window_start]
    used = len(uses_in_window)
    pay_less_left = max(0, PAY_LESS_LIMIT - used)
    reopen = _month_add(uses_in_window[0], 12) if pay_less_left == 0 else None

    # The month the options act on: this instalment, or the next one when the debit is too close.
    target = after_next if too_close else next_date
    target_after = third if too_close else after_next

    if too_close:
        skip_ok, skip_why = False, f"This instalment is within {CHANGE_CUTOFF_WORKDAYS} working days, so it cannot be skipped."
    elif sip.misses_in_row >= MISS_LIMIT - 1:
        skip_ok, skip_why = False, f"You have missed {sip.misses_in_row} in a row. One more miss would cancel the SIP."
    else:
        skip_ok, skip_why = True, ""

    if pay_less_left == 0:
        pay_less_ok, pay_less_why = False, f"Used {used} times in the last 12 months."
    elif sip.amount <= sip.fund_min:
        pay_less_ok, pay_less_why = False, "Your amount is already the fund's minimum."
    else:
        pay_less_ok, pay_less_why = True, ""

    invested = sip.amount * (sip.months_old - sip.misses_in_row)
    if sip.pay_less_months_ago:
        invested -= 2000 * len(sip.pay_less_months_ago)  # those months paid ₹1,000 instead of ₹3,000
    if pay_less_left == 0:
        screen = "options_pay_less_used"
    elif too_close:
        screen = "options_too_close"
    else:
        screen = "options"

    return {
        "key": sip.key,
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
        "third_date": third,
        "too_close": too_close,
        "cancel_may_debit": cancel_may_debit,
        "target_date": target,
        "target_text": fmt_date(target),
        "target_month_text": MONTHS[target.month - 1],
        "target_after_date": target_after,
        "target_after_text": fmt_date(target_after),
        "target_after_month_text": MONTHS[target_after.month - 1],
        "fund_min": sip.fund_min,
        "fund_min_text": fmt_inr(sip.fund_min),
        "skip_ok": skip_ok,
        "skip_why": skip_why,
        "pay_less_ok": pay_less_ok,
        "pay_less_why": pay_less_why,
        "pay_less_used": used,
        "pay_less_left": pay_less_left,
        "pay_less_use_months": [MONTHS[u.month - 1][:3] for u in uses_in_window],
        "pay_less_reopen": reopen,
        "pay_less_reopen_text": fmt_date(reopen, year=True) if reopen else "",
        "move_date_ok": True,
        "screen": screen,
        "today": today,
    }


def new_day_after_payday(payday: int) -> int:
    """SIP day = 2 days after payday. SIP dates run 1-28, so late paydays roll to early next month."""
    d = payday + PAYDAY_GAP_DAYS
    if d > 28:
        d = max(1, d - 30)
    return d


def next_on_new_day(f: dict, new_day: int) -> date:
    """First instalment on the new day, in the month the options act on."""
    t = f["target_date"]
    d = date(t.year, t.month, new_day)
    if workdays_until(f["today"], d) <= CHANGE_CUTOFF_WORKDAYS or (f["too_close"] and d <= f["next_date"]):
        d = _month_add(d, 1, new_day)
    return d


def pay_less_choices(f: dict) -> list[int]:
    """Amount buttons: fund minimum upwards in ₹500 steps, below the full amount, at most 5."""
    out, a = [], f["fund_min"]
    while a < f["amount"] and len(out) < 5:
        out.append(a)
        a += 500
    return out


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
        "Rule: only one instalment can be skipped at a time. A skip counts as 1 missed.",
        f"Rule: if an instalment is within {CHANGE_CUTOFF_WORKDAYS} working days, a skip or change does not apply to it. It applies from the next instalment.",
        "Rule: if the balance is short on the debit date, the payment fails and counts as 1 missed. The SIP stays active.",
        f"Fund minimum instalment: {f['fund_min_text']}",
        f"Rule: pay less this month lowers ONE instalment to any amount from the fund minimum up to the full amount. The next instalment goes back to the full amount by itself. It can be used {PAY_LESS_LIMIT} times in any 12 months.",
        f"Rule: cancelling stops future instalments only. Invested money stays until the user redeems it. An instalment due within {CANCEL_NOTICE_DAYS} days may still be taken.",
        "Rule: nobody can predict returns.",
    ]
    if f["too_close"]:
        lines.append(f"Situation: the {f['next_date_text']} instalment is within {CHANGE_CUTOFF_WORKDAYS} working days. It cannot be changed. Options apply from {f['target_text']}.")
    lines += [
        f"Option skip: {'available for ' + f['target_text'] if f['skip_ok'] else 'NOT available. ' + f['skip_why']}",
        f"Option pay less: {'available for the ' + f['target_text'] + ' instalment. Full amount returns on ' + f['target_after_text'] + '. Uses left in 12 months: ' + str(f['pay_less_left']) if f['pay_less_ok'] else 'NOT available. ' + f['pay_less_why'] + (' It opens again on ' + f['pay_less_reopen_text'] + '.' if f['pay_less_reopen_text'] else '')}",
        "Option move date: available. The user picks their payday and the SIP moves to 2 days after it.",
    ]
    if not f["pay_less_ok"] and f["pay_less_left"] == 0:
        lines.append("Option lower the amount for good: available, from the fund minimum. It stays until the user changes it.")
    return "\n".join(lines)
