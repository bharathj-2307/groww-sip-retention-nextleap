"""Date checks for every day from today to the end of 2028 (covers month ends, year end, leap February).

Run from mvp/:  python3 -m tests.test_dates
"""
from __future__ import annotations

import calendar
from datetime import date, timedelta

from core.sip import (SAMPLE_SIPS, MONTHS, facts, workdays_until, new_day_after_payday, next_on_new_day,
                      CHANGE_CUTOFF_WORKDAYS, CANCEL_NOTICE_DAYS, PAY_LESS_LIMIT, SIP_DAY_MAX)

PAYDAYS = [1, 5, 7, 10, 15, 20, 25, 26, 27, 28, 29, 30, 31]


def same_day_months_later(d: date, n: int, day: int) -> date:
    """Calendar answer: the same SIP day n months later, or the month's last day if it is shorter.

    Written separately from core.sip on purpose, so the test does not check the code against itself.
    """
    m = d.month - 1 + n
    y, m = d.year + m // 12, m % 12 + 1
    return date(y, m, min(day, calendar.monthrange(y, m)[1]))


def check_day(today: date) -> list[str]:
    errs = []
    for sip in SAMPLE_SIPS:
        f = facts(sip, today)
        nd, an, th = f["next_date"], f["after_next_date"], f["third_date"]
        tag = f"{today} case {sip.key}"
        sip_day = nd.day if sip.next_workday else sip.day
        if not nd > today:
            errs.append(f"{tag}: next date {nd} is not after today")
        if sip.next_workday:
            if nd.weekday() >= 5 or any((today + timedelta(days=k)).weekday() < 5 for k in range(1, (nd - today).days)):
                errs.append(f"{tag}: next date {nd} is not the next working day")
        else:
            if nd.day != sip.day or (nd - today).days > 31:
                errs.append(f"{tag}: next date {nd} is not the next {sip.day}th")
        if an != same_day_months_later(nd, 1, sip_day):
            errs.append(f"{tag}: after-next {an} should be {same_day_months_later(nd, 1, sip_day)}")
        if th != same_day_months_later(nd, 2, sip_day):
            errs.append(f"{tag}: third {th} should be {same_day_months_later(nd, 2, sip_day)}")
        close = workdays_until(today, nd) <= CHANGE_CUTOFF_WORKDAYS
        if f["cancel_may_debit"] != ((nd - today).days <= CANCEL_NOTICE_DAYS):
            errs.append(f"{tag}: cancel notice wrong")
        if sip.next_workday and not close:
            errs.append(f"{tag}: case 2 should always be too close")
        if close and sip.misses_in_row == 0 and not f["skip_ok"]:
            errs.append(f"{tag}: skip of the next month should be offered")
        if f["too_close"] != close:
            errs.append(f"{tag}: too_close wrong")
        t, ta = f["target_date"], f["target_after_date"]
        if (t, ta) != ((an, th) if close else (nd, an)):
            errs.append(f"{tag}: target dates wrong {t} {ta}")
        if f["target_month_text"] != MONTHS[t.month - 1] or f["target_after_month_text"] != MONTHS[ta.month - 1]:
            errs.append(f"{tag}: month names wrong")
        # pay less history and reopen date
        if sip.pay_less_months_ago:
            if f["pay_less_used"] != len(sip.pay_less_months_ago) or f["pay_less_left"] != max(0, PAY_LESS_LIMIT - f["pay_less_used"]):
                errs.append(f"{tag}: pay less count wrong")
            if f["pay_less_left"] == 0:
                first_use = same_day_months_later(nd, -max(sip.pay_less_months_ago), sip_day)
                if f["pay_less_reopen"] != same_day_months_later(first_use, 12, sip_day):
                    errs.append(f"{tag}: reopen {f['pay_less_reopen']} wrong")
                if not f["pay_less_reopen"] > today:
                    errs.append(f"{tag}: reopen {f['pay_less_reopen']} is not in the future")
        # move date: any SIP day the user picks must start on a valid date
        for new in range(1, SIP_DAY_MAX + 1):
            first = next_on_new_day(f, new)
            if first.day != new or workdays_until(today, first) <= CHANGE_CUTOFF_WORKDAYS or (close and first <= nd) \
                    or (first - today).days > 70:
                errs.append(f"{tag}: picked day {new} starts {first}")
        # move date: suggested day from the salary day
        for payday in PAYDAYS:
            new = new_day_after_payday(payday)
            if not 1 <= new <= SIP_DAY_MAX:
                errs.append(f"{tag}: payday {payday} gives SIP day {new}")
            gap = (new - payday) % 30 if new < payday else new - payday
            if not 2 <= gap <= 4:
                errs.append(f"{tag}: payday {payday} gives SIP day {new}, {gap} days later")
            first = next_on_new_day(f, new)
            if first.day != new:
                errs.append(f"{tag}: move to {new} starts {first}")
            if workdays_until(today, first) <= CHANGE_CUTOFF_WORKDAYS:
                errs.append(f"{tag}: move to {new} starts {first}, too soon")
            if close and first <= nd:
                errs.append(f"{tag}: move to {new} starts {first}, before the locked {nd} payment")
            if (first - today).days > 70:
                errs.append(f"{tag}: move to {new} starts {first}, too far away")
    return errs


def main() -> None:
    start, end = date.today(), date(2028, 12, 31)
    days, errs, d = 0, [], start
    while d <= end:
        errs += check_day(d)
        days += 1
        d += timedelta(days=1)
    print(f"Checked {days} days x {len(SAMPLE_SIPS)} cases x {len(PAYDAYS)} salary days and {SIP_DAY_MAX} picked SIP days.")
    print(f"Problems: {len(errs)}")
    for e in errs[:25]:
        print(" ", e)
    raise SystemExit(1 if errs else 0)


if __name__ == "__main__":
    main()
