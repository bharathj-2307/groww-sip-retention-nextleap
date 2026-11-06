"""Steady SIP: Short on Cash, Not on Plans.

A clickable MVP of a changed Groww SIP cancel flow, for a NextLeap case study.
Not a Groww product. Runs on sample SIPs only. No real user data.

Screens follow the approved wireframes (numbers 1-12 in comments).
"""
from __future__ import annotations

import html
import json
from datetime import date
from pathlib import Path

import streamlit as st

from core import ai, gate
from core.sip import (CANCEL_NOTICE_DAYS, SAMPLE_SIPS, SIPS_BY_KEY, MONTHS, facts, fmt_inr, fmt_short, fmt_date,
                      new_day_after_payday, next_on_new_day, pay_less_choices)

HELP_URL = "https://groww.in/help/mutual-funds/mf-sip"
HERE = Path(__file__).parent
GREEN, GREEN_DARK, GREEN_BG = "#0B7A5A", "#075940", "#E8F5F0"
INK, MUTED, LINE = "#1F2328", "#5A6170", "#E3E5E8"

st.set_page_config(page_title="Steady SIP", page_icon="🟢", layout="centered")

# ---------- style ----------
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html, body, [class*="css"], .stApp, button, input, textarea {{ font-family: Inter, system-ui, sans-serif !important; }}
.stApp {{ background: #F3F5F7; color: {INK}; }}
.stApp label, .stApp label p, .stApp [data-testid="stWidgetLabel"] p, .stApp [data-testid="stExpander"] summary p,
.stApp [data-testid="stMarkdownContainer"] p {{ color: {INK}; }}
.stApp [data-testid="stExpander"] details {{ background:#FFFFFF; }}
.stApp textarea, .stApp input {{ background:#FFFFFF !important; color:{INK} !important; }}
header[data-testid="stHeader"] {{ background: transparent; }}
.block-container {{ max-width: 460px !important; padding-top: 1.2rem; padding-bottom: 3rem; }}
.ss-guide-in {{ font-size:14px; line-height:21px; color:{INK}; }}
.ss-guide-in ol {{ margin:0 0 6px 0; padding-left:20px; }}
.ss-guide {{ background:#E8F5EF; border:1px solid #BFE3D3; border-radius:12px; padding:12px 16px; margin:4px 0 14px; font-size:14px; line-height:21px; color:{INK}; }}
.ss-guide ol {{ margin:6px 0 0 0; padding-left:20px; }}
.ss-guide li {{ margin:2px 0; }}
.ss-case {{ background:#FFFFFF; border-left:3px solid {GREEN}; border-radius:6px; padding:8px 12px; margin:2px 0 12px; font-size:14px; line-height:20px; color:{INK}; }}
.ss-step {{ font-size:14px; font-weight:600; color:{INK}; margin:0 0 8px; }}
.st-key-cases [data-testid="stHorizontalBlock"] {{ flex-wrap: nowrap !important; gap: 10px; }}
.st-key-cases [data-testid="stColumn"] {{ min-width: 0 !important; flex: 1 1 0 !important; width: auto !important; }}
.st-key-cases .stButton > button {{ width:100%; height:64px; justify-content:flex-start; text-align:left; border:1px solid #C9CDD2;
  border-radius:12px; background:#FFFFFF; padding:8px 12px; }}
.st-key-cases .stButton > button:hover {{ border-color:{GREEN}; color:{INK}; }}
.st-key-cases .stButton > button > div, .st-key-cases .stButton > button span[data-has-shortcut],
.st-key-cases .stButton > button [data-testid="stMarkdownContainer"] {{ width:100%; }}
.st-key-cases .stButton > button p {{ font-size:14px; line-height:19px; white-space: pre-line; text-align:left; color:{INK}; }}
.st-key-cases .stButton > button strong {{ font-size:12px; color:{MUTED}; font-weight:600; }}
.st-key-cases [class*="st-key-case_on"] .stButton > button {{ border:2px solid {GREEN}; background:{GREEN_BG}; }}
.st-key-cases [class*="st-key-case_on"] .stButton > button strong {{ color:{GREEN_DARK}; }}
.st-key-phone {{ background: #FFFFFF; border: 1px solid {LINE}; border-radius: 28px; padding: 18px 18px 20px;
  box-shadow: 0 6px 24px rgba(0,0,0,.06); color: {INK}; min-height: 760px; }}
.st-key-phone p, .st-key-phone span, .st-key-phone div {{ color: {INK}; }}
.ss-top {{ display:flex; align-items:center; gap:10px; font-size:16px; font-weight:600; margin: 0 0 6px; }}
.ss-h1 {{ margin: 6px 0 4px; font-size: 23px; line-height: 30px; font-weight: 700; color:{INK}; }}
.ss-sub {{ margin: 0 0 10px; font-size: 14px; line-height: 20px; color: {MUTED} !important; }}
.ss-muted {{ color: {MUTED} !important; font-size: 13px; line-height: 19px; }}
.ss-small {{ color: {MUTED} !important; font-size: 12px; line-height: 17px; }}
.ss-card {{ border: 1px solid {LINE}; border-radius: 12px; padding: 12px 14px; margin: 8px 0; }}
.ss-row {{ display:flex; justify-content:space-between; gap:12px; font-size:14px; margin: 6px 0; }}
.ss-row .k {{ color:{MUTED} !important; }} .ss-row .v {{ font-weight:600; text-align:right; }}
.ss-badge {{ display:inline-flex; align-items:center; gap:6px; background:{GREEN_BG}; border-radius:999px; padding:5px 12px;
  font-size:12px; font-weight:500; color:{GREEN_DARK} !important; }}
.ss-info {{ background:#EEF3FF; border:1px solid #D3DEFA; border-radius:10px; padding:8px 12px; font-size:13px; line-height:19px; color:{INK}; margin:8px 0 4px; }}
.ss-green {{ background:{GREEN_BG}; border-radius:12px; padding:12px 14px; font-size:14px; line-height:20px; color:{GREEN_DARK} !important; margin: 8px 0; }}
.ss-green * {{ color:{GREEN_DARK} !important; }}
.ss-grey {{ background:#F3F5F7; border-radius:12px; padding:12px 14px; font-size:14px; line-height:20px; margin: 8px 0; }}
.ss-warn {{ background:#FFF8E6; border-radius:12px; padding:10px 14px; font-size:13px; line-height:19px; margin: 8px 0; }}
.ss-new {{ font-size:11px; font-weight:600; color:#8A4B00 !important; background:#FFF1DC; border-radius:6px; padding:2px 6px; margin-left:6px; }}
.ss-h2 {{ font-size:15px; font-weight:600; margin: 12px 0 4px; }}
.ss-foot {{ border-top:1px solid {LINE}; margin-top: 14px; padding-top: 10px; }}
.ss-bubble-u {{ margin: 8px 0 4px auto; max-width: 85%; background:#F3F5F7; border-radius:14px; padding:9px 13px; font-size:14px; line-height:20px; width: fit-content; }}
.ss-bubble-a {{ margin: 4px 0 2px; max-width: 92%; border:1px solid {LINE}; border-radius:14px; padding:10px 13px; font-size:14px; line-height:21px; }}
.ss-check {{ font-size:12px; color:{GREEN_DARK} !important; margin: 2px 0 8px; }}
.ss-check-grey {{ font-size:12px; color:{MUTED} !important; margin: 2px 0 8px; }}
.ss-dim {{ background:#8C8F94; border-radius: 16px; padding: 14px; margin: -4px -4px 0; opacity:.9; }}
.ss-dim .t {{ color:#2b2d31 !important; font-weight:700; font-size:18px; margin-bottom:8px; }}
.ss-dim .c {{ border:1px solid #a9acb1; border-radius:10px; padding:9px 12px; margin:6px 0; color:#3a3d42 !important; font-size:14px; }}
.ss-sheet-title {{ text-align:center; font-size:19px; font-weight:700; margin: 10px 0 4px; }}
.ss-sheet-sub {{ text-align:center; color:{MUTED} !important; font-size:14px; margin: 0 0 12px; }}
.ss-icon {{ display:flex; justify-content:center; margin-top: 6px; }}
.ss-done-ic {{ width:72px; height:72px; border-radius:36px; background:{GREEN_BG}; display:flex; align-items:center; justify-content:center; margin: 40px auto 12px; }}
.ss-center {{ text-align:center; }}
a {{ color:{GREEN} !important; }}

/* buttons: default = white chip */
.st-key-phone .stButton > button {{ width:100%; min-height:48px; border:1px solid #C9CDD2; border-radius:12px; background:#FFFFFF;
  color:{INK}; justify-content:flex-start; text-align:left; padding: 8px 16px; font-size:15px; box-shadow:none; }}
.st-key-phone .stButton > button:hover {{ border-color:{GREEN}; color:{INK}; }}
.st-key-phone .stButton > button p {{ font-size:15px; white-space: pre-line; text-align:left; line-height: 21px; }}
/* option cards */
[class*="st-key-opt_"] .stButton > button {{ padding: 12px 14px; }}
[class*="st-key-opt_"] .stButton > button p {{ font-size:13px; color:{MUTED}; }}
[class*="st-key-opt_"] .stButton > button p strong {{ font-size:15px; color:{INK}; font-weight:600; }}
.st-key-opt_payless .stButton > button {{ border:2px solid {GREEN}; }}
[class*="st-key-opt_"] .stButton > button code {{ background:#FFF1DC; color:#8A4B00; font-family: inherit; font-size:11px;
  font-weight:700; border-radius:6px; padding:2px 7px; margin-left:4px; vertical-align: 2px; }}
/* hide Streamlit's "Press Enter to submit" hint and counter, which overlap the typed text */
[data-testid="InputInstructions"] {{ display:none !important; }}
/* green, not red, focus border on text boxes */
.stTextInput div:focus-within, .stTextArea div:focus-within, .stNumberInput div:focus-within {{ border-color:{GREEN} !important; }}
/* primary */
[class*="st-key-primary"] .stButton > button {{ background:{GREEN}; border:none; justify-content:center; min-height:52px; }}
[class*="st-key-primary"] .stButton > button p {{ color:#FFFFFF; font-weight:600; font-size:16px; text-align:center; }}
[class*="st-key-primary"] .stButton > button:hover {{ background:{GREEN_DARK}; }}
[class*="st-key-primary"] .stFormSubmitButton > button {{ background:{GREEN}; border:none; min-height:52px; border-radius:12px; }}
[class*="st-key-primary"] .stFormSubmitButton > button p {{ color:#FFFFFF; font-weight:600; font-size:16px; }}
/* text buttons */
[class*="st-key-link"] .stButton > button {{ border:none; background:transparent; justify-content:center; min-height:44px; }}
[class*="st-key-link"] .stButton > button p {{ color:{GREEN}; font-weight:600; text-align:center; }}
/* outlined green (Ask about your SIP) */
[class*="st-key-ask"] .stButton > button {{ border:1.5px solid {GREEN}; justify-content:center; }}
[class*="st-key-ask"] .stButton > button p {{ color:{GREEN}; font-weight:600; text-align:center; }}
/* grid choice buttons */
[class*="st-key-pick_"] .stButton > button {{ justify-content:center; padding: 4px 6px; }}
[class*="st-key-pick_"] .stButton > button p {{ text-align:center; }}
[class*="st-key-picked_"] .stButton > button {{ justify-content:center; border:2px solid {GREEN}; background:{GREEN_BG}; padding: 4px 6px; }}
[class*="st-key-picked_"] .stButton > button p {{ text-align:center; color:{GREEN_DARK}; font-weight:600; }}
/* locked option */
.ss-locked {{ border:1px dashed #C9CDD2; border-radius:12px; padding:12px 14px; background:#FAFAFB; margin: 0 0 8px; }}
/* back button */
[class*="st-key-back_"] .stButton > button {{ border:none; min-height:40px; width:auto; padding: 0 6px; font-size:20px; }}
/* suggested questions */
[class*="st-key-sugg_"] .stButton > button {{ border-radius:999px; min-height:38px; padding: 4px 12px; }}
[class*="st-key-sugg_"] .stButton > button p {{ font-size:13px; }}
.st-key-phone [data-testid="stTextArea"] textarea, .st-key-phone [data-testid="stTextInput"] input {{ border-radius:12px; font-size:15px; }}
.st-key-phone [data-testid="stForm"] {{ border:none; padding:0; }}
.st-key-sheet {{ border-top-left-radius: 18px; border-top-right-radius: 18px; background:#FFFFFF; box-shadow: 0 -6px 18px rgba(0,0,0,.10);
  padding: 8px 6px 4px; margin-top: -6px; }}

.st-key-phone [data-testid="stHorizontalBlock"] {{ flex-wrap: nowrap !important; gap: 10px; }}
.st-key-phone [data-testid="stColumn"] {{ min-width: 0 !important; flex: 1 1 0 !important; width: auto !important; }}
.stButton[class*="st-key-back_"] > button, [class*="st-key-back_"] button {{ border:none !important; min-height:40px; width:auto; padding: 0 8px 0 0; font-size:22px; justify-content:flex-start; }}
.st-key-topbar .ss-top {{ margin:0; }}
.st-key-phone .stButton > button > div, .st-key-phone .stButton > button span[data-has-shortcut],
.st-key-phone .stButton > button [data-testid="stMarkdownContainer"] {{ width:100%; }}
[class*="st-key-back_"] button {{ background: transparent !important; color: {INK} !important; }}
[class*="st-key-back_"] button p {{ color: {INK} !important; font-size: 22px !important; }}
.st-key-topbar {{ margin-bottom: 4px; }}
.st-key-sheet [class*="st-key-primary"] .stButton > button {{ background:#4FB28B; }}
</style>
""", unsafe_allow_html=True)


def btn(label: str, key: str, **kw) -> bool:
    kw.setdefault("width", "stretch")
    return st.button(label, key=key, **kw)


def H(s: str) -> None:
    st.markdown(s, unsafe_allow_html=True)


def esc(s: str) -> str:
    return html.escape(s or "")


# ---------- state ----------
S = st.session_state
S.setdefault("screen", "start")
S.setdefault("sip_key", "A")
S.setdefault("group", None)
S.setdefault("source", None)
S.setdefault("lang", "en")
S.setdefault("ai_sort", None)
S.setdefault("explain", None)
S.setdefault("chat", [])
S.setdefault("pick", None)
S.setdefault("result", None)
S.setdefault("saved", [])
S.setdefault("force_fail", False)
S.setdefault("prev", "start")


def go(screen: str) -> None:
    S.prev = S.screen
    S.screen = screen
    S.pick = None  # choices are per screen


def reset() -> None:
    for k in ("group", "source", "ai_sort", "explain", "pick", "result"):
        S[k] = None
    S.lang = "en"
    S.chat = []
    S.screen = "start"


F = facts(SIPS_BY_KEY[S.sip_key], date.today())

# ---------- outside the phone: what this is ----------
H(f"""<div style="margin-bottom:2px"><span style="font-size:22px;font-weight:700;color:{INK}">Steady SIP</span>
<span style="color:{MUTED};font-size:15px"> · Short on Cash, Not on Plans</span></div>
<div class="ss-small" style="margin-bottom:6px">A student prototype of Groww's Cancel SIP screen. Made-up data only. Do not enter real details.</div>""")
with st.expander("How to test (4 steps)"):
    H("""<div class="ss-guide-in"><ol><li>Pick a case. Start with Case 1.</li>
<li>Act as that person. Money is short and you just tapped Cancel SIP.</li>
<li>Choose what you would really do.</li>
<li>Try the other cases.</li></ol>
<div class="ss-muted">Why: many people cancel their SIP when money is short for a month. Steady SIP shows easier choices first.</div></div>""")

H('<div class="ss-step">1. Pick a case</div>')
with st.container(key="cases"):
    for row in (SAMPLE_SIPS[:2], SAMPLE_SIPS[2:]):
        for col, sip in zip(st.columns(2), row):
            n = SAMPLE_SIPS.index(sip) + 1
            with col, st.container(key=f"{'case_on' if sip.key == S.sip_key else 'case'}_{sip.key}"):
                if st.button(f"**Case {n}**\n{sip.label}", key=f"casebtn_{sip.key}", width="stretch") and sip.key != S.sip_key:
                    S.sip_key = sip.key
                    reset()
                    st.rerun()
_c = SIPS_BY_KEY[S.sip_key]
H(f'<div class="ss-case">{esc(_c.hint)}<br><span class="ss-muted"><b>Check:</b> {esc(_c.check)}</span></div>'
  f'<div class="ss-step">2. Act as this person on the phone below</div>')


# ---------- shared pieces ----------
def top(title: str, back_to: str | None = "start") -> None:
    with st.container(key="topbar", horizontal=True, vertical_alignment="center", gap="small"):
        if back_to and btn("←", key=f"back_{S.screen}", help="Back", width="content"):
            go(back_to)
            st.rerun()
        H(f'<div class="ss-top">{esc(title)}</div>')


def footer(extra: str = "") -> None:
    H(f'<div class="ss-foot"><div class="ss-small">This is not investment advice.{(" " + extra) if extra else ""}</div></div>')


def checks_badge(checks: list[dict]) -> None:
    H('<span class="ss-badge">🛡️ Written by AI · Checked: facts match, no advice</span>')
    with st.expander("See the 5 quality checks"):
        for c in checks:
            mark = "✅" if c["passed"] else "❌"
            H(f'<div class="ss-small">{mark} {esc(c["label"])}{(" · " + esc(c["detail"])) if c["detail"] else ""}</div>')


def save_reason(group: str) -> None:
    """Only the reason group is kept, never the words typed."""
    S.saved.append(group)


def route(group: str) -> None:
    S.group = group
    save_reason(group)
    if group in ("cash_short", "break"):
        open_options()
    elif group in ("stop", "returns"):
        go("popup_cancel")       # 10
    elif group == "withdraw":
        go("popup_withdraw")     # 10 (withdraw version)
    else:
        go("popup_general")      # 11


def open_options() -> None:
    """Run the AI explanation through the gate. Pass: screen 3/8/9. Fail: screen 12."""
    key = (S.sip_key, S.lang, S.group, S.force_fail)
    if not S.explain or S.explain.get("key") != key:
        with st.spinner("Checking your SIP"):
            r = ai.explain(F, S.lang, S.group or "cash_short")
        if "text" in r and r["text"]:
            checks = gate.check_text(r["text"], F, group=S.group or "cash_short")
        else:
            checks = [{"name": "facts", "label": "Facts match", "passed": False,
                       "detail": "The AI did not answer in time."}]
        if S.force_fail:
            checks = [dict(c) for c in checks]
            checks[0] = {**checks[0], "passed": False, "detail": "Failed on purpose by the reviewer switch."}
        S.explain = {"key": key, "text": r.get("text", ""), "checks": checks, "model": r.get("model")}
    go(F["screen"] if gate.passed(S.explain["checks"]) else "fallback")


# ---------- 1 and 2: what is happening ----------
def screen_start() -> None:
    top("Cancel SIP", back_to=None)
    H(f"""<div class="ss-card"><div style="font-size:14px;font-weight:600">{esc(F['fund'])}</div>
<div class="ss-muted">{F['amount_text']} every month · next on {fmt_date(F['next_date'])}</div></div>
<div class="ss-h1">Before you cancel, tell us what is happening</div>
<div class="ss-sub">We will show what each choice means for your SIP.</div>""")
    for label, group in ai.CHIPS.items():
        if btn(label, key=f"chip_{group}"):
            S.source, S.lang = "chip", "en"
            route(group)
            st.rerun()
    with st.form("typed", clear_on_submit=False, border=False):
        text = st.text_area("Or tell us in your own words (optional)", placeholder="Type in English or Hindi",
                            height=90, max_chars=400)
        with st.container(key="primary_continue"):
            sent = st.form_submit_button("Continue", width="stretch")
    H('<div class="ss-small">🎤 Voice input will come in a later version.</div>')
    if sent:
        if not text.strip():
            st.info("Tap a reason above or type a few words first.")
        else:
            with st.spinner("AI is reading your reply"):
                r = ai.classify(text.strip())
            g, conf = r.get("group", "other"), float(r.get("confidence", 0) or 0)
            ok = "error" not in r and gate.check_group(g, conf)["passed"]
            S.ai_sort = {"group": g, "confidence": conf, "passed": ok, "model": r.get("model"),
                         "error": r.get("error")}
            S.source = "typed"
            S.lang = r.get("language", "en") if ok else "en"
            route(g if ok else "other")   # unsure or error: general pop-up (11)
            st.rerun()
    footer("We save only the type of reason, not your words.")


# ---------- 3, 8, 9: facts and options ----------
def facts_card(rows: list[tuple[str, str]], para: str, title: str = "Where your SIP stands") -> None:
    body = "".join(f'<div class="ss-row"><span class="k">{esc(k)}</span><span class="v">{esc(v)}</span></div>' for k, v in rows)
    H(f'<div class="ss-card"><div style="font-size:15px;font-weight:600">{esc(title)}</div>{body}'
      f'<div class="ss-muted" style="margin-top:8px">{esc(para)}</div></div>')


def option(key: str, title: str, desc: str, new: bool = False) -> bool:
    label = f"**{title}**{'  `New`' if new else ''}\n{desc}"
    with st.container(key=f"opt_{key}"):
        return btn(label, key=f"optbtn_{key}")


def ask_and_cancel() -> None:
    with st.container(key="ask_btn"):
        if btn("💬  Ask about your SIP", key="askbtn"):
            go("ask")
            st.rerun()
    with st.container(key="link_cancel"):
        if btn("Cancel SIP anyway", key="cancel_anyway"):
            go("popup_cancel_confirm")
            st.rerun()


def screen_options() -> None:      # 3
    top("Your SIP options")
    checks_badge(S.explain["checks"])
    facts_card([("Invested so far", f"{F['invested_text']} in {F['months_old']} months"),
                ("Next instalment", f"{F['amount_text']} on {fmt_short(F['next_date'])}"),
                ("Missed in a row", f"{F['misses_in_row']} of {F['miss_limit']}")], S.explain["text"])
    H('<div class="ss-h2">If money is tight this month, you can:</div>')
    m, m2 = F["target_month_text"], F["target_after_month_text"]
    if F["pay_less_ok"] and option("payless", "Pay less this month",
                                   f"Pay any amount from {F['fund_min_text']} in {m}. It goes back to {F['amount_text']} in {m2} by itself.", new=True):
        go("payless"); st.rerun()
    if F["skip_ok"]:
        if option("skip", f"Skip {m}", f"Your SIP continues on {F['target_after_text']}."):
            go("popup_skip"); st.rerun()
    else:
        H(f'<div class="ss-locked"><div style="font-weight:600;font-size:15px;color:{MUTED}">Skip {m}</div>'
          f'<div class="ss-muted">{esc(F["skip_why"])}</div></div>')
    if option("move", "Move the date to after payday", "Pick a new date, such as a few days after your salary."):
        go("movedate"); st.rerun()
    ask_and_cancel()
    footer()


def screen_too_close() -> None:    # 8
    top("Your SIP options")
    checks_badge(S.explain["checks"])
    H(f'<div class="ss-grey">🕑 Your {F["amount_text"]} instalment is on {F["next_date_text"]}. It is within 2 working days, '
      f'so it can no longer be lowered, skipped or moved. Changes you make now start from {F["target_month_text"]}.</div>')
    nm = F["misses_in_row"] + 1
    facts_card([("Missed in a row after that", f"{nm} of {F['miss_limit']}")], S.explain["text"],
               title=f"If your balance is short on {F['next_date_text']}")
    H(f'<div class="ss-muted" style="margin:-2px 0 6px">Groww cancels a SIP only after {F["miss_limit"]} missed instalments in a row.</div>')
    m, m2 = F["target_month_text"], F["target_after_month_text"]
    H(f'<div class="ss-h2">You can set up {m} now:</div>')
    if F["pay_less_ok"] and option("payless", f"Pay less in {m}",
                                   f"Pay any amount from {F['fund_min_text']} on {F['target_text']}. It goes back to {F['amount_text']} in {m2} by itself."):
        go("payless"); st.rerun()
    if F["skip_ok"] and option("skip", f"Skip {m}",
                               f"Your SIP continues on {F['target_after_text']}. This counts as 1 missed of {F['miss_limit']}. "
                               f"If the {F['next_date_text']} payment also fails, it will be 2 missed in a row."):
        go("popup_skip"); st.rerun()
    if option("move", "Move the date to after payday", f"Pick a new date, such as a few days after your salary. Starts in {m}."):
        go("movedate"); st.rerun()
    ask_and_cancel()
    footer()


def screen_pay_less_used() -> None:  # 9
    top("Your SIP options")
    checks_badge(S.explain["checks"])
    used = ", ".join(F["pay_less_use_months"])
    facts_card([("Invested so far", f"{F['invested_text']} in {F['months_old']} months"),
                ("Next instalment", f"{F['amount_text']} on {fmt_short(F['next_date'])}"),
                ("Missed in a row", f"{F['misses_in_row']} of {F['miss_limit']}"),
                ("Pay less used", f"{F['pay_less_used']} of 2 ({used})")], S.explain["text"])
    m = F["target_month_text"]
    H('<div class="ss-h2">If money is tight this month, you can:</div>')
    H(f'<div class="ss-locked"><div style="font-weight:600;font-size:15px;color:{MUTED}">🔒 Pay less this month</div>'
      f'<div class="ss-muted">You have used this 2 times in the last 12 months. You can use it again from {F["pay_less_reopen_text"]}.</div></div>')
    if F["skip_ok"] and option("skip", f"Skip {m}",
                               f"Your SIP continues on {F['target_after_text']}. This counts as 1 missed of {F['miss_limit']}."):
        go("popup_skip"); st.rerun()
    if option("lower", "Lower your monthly amount",
              f"Set a new amount from {F['fund_min_text']}. It stays until you change it. You can raise it any time."):
        go("lower"); st.rerun()
    if option("move", "Move the date to after payday", "Pick a new date, such as a few days after your salary."):
        go("movedate"); st.rerun()
    ask_and_cancel()
    footer()


# ---------- 4: pay less this month ----------
def pick_grid(values: list, fmt, prefix: str, other: bool = True) -> None:
    items = list(values) + (["other"] if other else [])
    cols = st.columns(3)
    for i, v in enumerate(items):
        chosen = S.pick == v or (v == "other" and S.pick not in values and S.pick is not None)
        with cols[i % 3]:
            with st.container(key=f"{'picked' if chosen else 'pick'}_{prefix}_{i}"):
                if btn("Other" if v == "other" else fmt(v), key=f"{prefix}btn_{i}", width="stretch"):
                    S.pick = "other" if v == "other" else v
                    st.rerun()


def min_note() -> str:
    return (f'<div class="ss-info">ⓘ <b>Why {F["fund_min_text"]}?</b> It is the lowest SIP amount this fund allows. '
            f'Each fund sets its own minimum.</div>')


def screen_pay_less() -> None:
    top("Pay less this month", back_to=F["screen"])
    t, ta = F["target_text"], F["target_after_text"]
    m = F["target_month_text"]
    H(f'<div class="ss-h1" style="font-size:21px;line-height:28px">How much can you pay on {t}?</div>'
      f'<div class="ss-sub">Pick any amount from {F["fund_min_text"]} to {F["amount_text"]}.</div>'
      + min_note())
    left_after = F["pay_less_left"] - 1
    nth = "first" if F["pay_less_used"] == 0 else "second"
    more = (f"If {F['target_after_month_text']} is also tight, you can ask once more. " if left_after > 0 else "")
    H(f'<div class="ss-green">🔁 <b>For {m} only.</b> On {ta} your SIP goes back to {F["amount_text"]} by itself. '
      f'You do not need to do anything.<br><span style="display:block;margin-top:6px">{more}Pay less can be used 2 times in any 12 months. '
      f'This will be your {nth}.</span></div>')
    choices = pay_less_choices(F)
    if S.pick is None:
        S.pick = choices[min(1, len(choices) - 1)]
    pick_grid(choices, fmt_inr, "amt")
    amount = S.pick
    if S.pick == "other" or (isinstance(S.pick, int) and S.pick not in choices):
        amount = st.number_input(f"Amount from {F['fund_min_text']} to {fmt_inr(F['amount'] - 100)}",
                                 min_value=F["fund_min"], max_value=F["amount"] - 100, step=100,
                                 value=F["fund_min"], key="amt_other")
    amount = int(amount)
    H(f"""<div class="ss-card"><div style="font-size:15px;font-weight:600">What happens</div>
<div class="ss-row"><span class="k">{t}</span><span class="v">{fmt_inr(amount)}</span></div>
<div class="ss-row"><span class="k">From {ta}</span><span class="v">{F['amount_text']}, by itself</span></div>
<div class="ss-row"><span class="k">Missed in a row</span><span class="v">Still {F['misses_in_row']} of {F['miss_limit']}</span></div>
<div class="ss-muted" style="margin-top:6px">No instalment is missed, so your SIP stays active.</div></div>""")
    with st.container(key="primary_payless"):
        if btn(f"Pay {fmt_inr(amount)} in {m}", key="do_payless"):
            S.result = {"kind": "payless", "amount": amount}
            go("done"); st.rerun()
    with st.container(key="link_other_opts"):
        if btn("See other options", key="other_opts"):
            go(F["screen"]); st.rerun()
    footer()


# ---------- 5: move date ----------
def ordinal(n: int) -> str:
    return f"{n}{'th' if 11 <= n % 100 <= 13 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


def screen_move_date() -> None:
    top("Move the SIP date", back_to=F["screen"])
    H('<div class="ss-h1" style="font-size:21px;line-height:28px">Pick a new SIP date</div>'
      '<div class="ss-sub">Choose a day when the money is in your account.</div>'
      '<div class="ss-step" style="margin-top:12px">1. When does your salary usually come?</div>')
    days = [1, 5, 7, 10, 31]
    if S.pick is None or (S.pick not in days and S.pick != "other"):
        S.pick = 7
    pick_grid(days, lambda d: "Month end" if d == 31 else ordinal(d), "pay")
    payday = S.pick
    if S.pick == "other":
        payday = st.number_input("Salary day (1 to 31)", min_value=1, max_value=31, value=15, step=1, key="pay_other")
    suggested = new_day_after_payday(int(payday))
    H('<div class="ss-step" style="margin-top:8px">2. Your new SIP date</div>')
    new_day = st.selectbox("New SIP date", list(range(1, 29)), index=suggested - 1, format_func=ordinal,
                           key=f"sipday_{payday}", label_visibility="collapsed")
    H(f'<div class="ss-muted" style="margin:-6px 0 4px">Suggested: the {ordinal(suggested)}, a little after your salary. '
      f'You can pick any date from the 1st to the 28th.</div>')
    first = next_on_new_day(F, new_day)
    H(f"""<div class="ss-card"><div style="font-size:15px;font-weight:600">What happens</div>
<div class="ss-row"><span class="k">New SIP date</span><span class="v">{ordinal(new_day)} of every month</span></div>
<div class="ss-row"><span class="k">Next instalment</span><span class="v">{F['amount_text']} on {fmt_short(first)}</span></div>
<div class="ss-row"><span class="k">Amount</span><span class="v">Stays {F['amount_text']}</span></div>
<div class="ss-muted" style="margin-top:6px">We only use the days you pick. We do not read your bank account.</div></div>""")
    with st.container(key="primary_move"):
        if btn(f"Move SIP to the {ordinal(new_day)}", key="do_move"):
            S.result = {"kind": "move", "day": ordinal(new_day), "first": first}
            go("done"); st.rerun()
    with st.container(key="link_other_opts2"):
        if btn("See other options", key="other_opts2"):
            go(F["screen"]); st.rerun()
    footer()


# ---------- lower for good (from screen 9, Groww's existing amount change) ----------
def screen_lower() -> None:
    top("Lower your monthly amount", back_to=F["screen"])
    H(f'<div class="ss-h1" style="font-size:21px;line-height:28px">Pick a new monthly amount</div>'
      f'<div class="ss-sub">From {F["fund_min_text"]}. It stays until you change it. You can raise it any time.</div>'
      + min_note())
    choices = pay_less_choices(F)
    if S.pick is None or S.pick not in choices + ["other"]:
        S.pick = choices[-1]
    pick_grid(choices, fmt_inr, "low", other=False)
    with st.container(key="primary_lower"):
        if btn(f"Change to {fmt_inr(S.pick)} a month", key="do_lower"):
            S.result = {"kind": "lower", "amount": S.pick}
            go("done"); st.rerun()
    footer()


# ---------- 6: ask about your SIP ----------
SUGGESTED = ["If I pay less this month, will I lose anything?", "Can I skip again next month?", "What if a debit fails?"]


def ask(q: str) -> None:
    with st.spinner("Checking the answer"):
        r = ai.answer(q, F, S.lang)
    if "text" in r and r["text"]:
        checks = gate.check_text(r["text"], F, group=S.group or "cash_short", user_text=q)
    else:
        checks = [{"name": "facts", "label": "Facts match", "passed": False, "detail": "No answer in time."}]
    if S.force_fail:
        checks[0] = {**checks[0], "passed": False, "detail": "Failed on purpose by the reviewer switch."}
    S.chat.append({"q": q, "a": r.get("text", ""), "declined": r.get("declined", False), "checks": checks,
                   "small_talk": r.get("small_talk", False)})


def screen_ask() -> None:
    top("Ask about your SIP", back_to=F["screen"])
    if not S.chat:
        H('<div class="ss-muted">Ask anything about this SIP and your options. Answers use only Groww\'s SIP rules and this SIP.</div>')
    for t in S.chat:
        H(f'<div class="ss-bubble-u">{esc(t["q"])}</div>')
        if t.get("small_talk"):
            H(f'<div class="ss-bubble-a">{esc(t["a"])}</div><div style="height:8px"></div>')
        elif gate.passed(t["checks"]):
            H(f'<div class="ss-bubble-a">{esc(t["a"])}</div>')
            if t["declined"]:
                H(f'<div class="ss-check-grey">ⓘ Not answered by design. See <a href="{HELP_URL}" target="_blank">Groww\'s help page</a>.</div>')
            else:
                H('<div class="ss-check">🛡️ Checked: facts match · rules correct · no advice · calm</div>')
        else:
            failed = ", ".join(c["label"] for c in t["checks"] if not c["passed"])
            H(f'<div class="ss-bubble-a">We could not answer this clearly. Here is <a href="{HELP_URL}" target="_blank">Groww\'s help page</a>.</div>'
              f'<div class="ss-check-grey">Quality check failed ({esc(failed)}), so the AI answer was hidden.</div>')
    asked = {t["q"] for t in S.chat}
    for i, q in enumerate(SUGGESTED):
        if q not in asked:
            with st.container(key=f"sugg_{i}"):
                if btn(q, key=f"suggbtn_{i}"):
                    ask(q); st.rerun()
    with st.form("askform", clear_on_submit=True, border=False):
        q = st.text_input("Your question", placeholder="Ask in English or Hindi", max_chars=300)
        with st.container(key="primary_send"):
            sent = st.form_submit_button("Send", width="stretch")
    if sent and q.strip():
        ask(q.strip()); st.rerun()
    with st.container(key="link_return_opts"):
        if btn("Back to my options", key="return_opts"):
            go(F["screen"]); st.rerun()
    footer()


# ---------- 7: done ----------
def screen_done() -> None:
    r = S.result or {}
    k = r.get("kind")
    m, ta = F["target_month_text"], F["target_after_text"]
    if k == "payless":
        title = f"{m} set to {fmt_inr(r['amount'])}"
        left = F["pay_less_left"] - 1
        body = (f"Your SIP stays active. It goes back to {F['amount_text']} from {ta} by itself. "
                + (f"You can pay less {left} more time in the next 12 months." if left > 0 else
                   "You have now used pay less 2 times in the last 12 months."))
    elif k == "move":
        title = f"Your SIP moves to the {r['day']}"
        body = f"Your next instalment is {F['amount_text']} on {fmt_date(r['first'])}. The amount stays the same."
    elif k == "skip":
        title = f"{m} is skipped"
        body = (f"The {F['next_date_text']} payment still goes ahead. " if F["too_close"] else "") + \
               f"Your SIP continues on {ta}. This counts as 1 missed in a row."
    elif k == "lower":
        title = f"Your SIP is now {fmt_inr(r['amount'])} a month"
        body = "It stays at this amount until you change it. You can raise it any time from your SIP page."
    elif k == "cancelled":
        title = "SIP cancelled"
        body = (f"Your {F['amount_text']} instalment on {F['next_date_text']} may still be taken. Later instalments will stop. "
                if F["cancel_may_debit"] else "Future instalments are stopped. ") + f"Your {F['invested_text']} stays invested until you redeem it."
    elif k == "redeem":
        title = "Redeem opens next"
        body = ("In the Groww app, this button opens the Redeem page for this fund. "
                "Redeem is not part of this prototype. Your SIP has not been cancelled.")
    else:
        title = "Your SIP continues"
        body = "Nothing has changed."
    rows = "" if k in ("cancelled", "redeem") else (
        f'<div class="ss-card" style="text-align:left"><div class="ss-row"><span class="k">Invested so far</span><span class="v">{F["invested_text"]}</span></div>'
        f'<div class="ss-row"><span class="k">Missed in a row</span><span class="v">{F["misses_in_row"] + (1 if k == "skip" else 0)} of {F["miss_limit"]}</span></div></div>')
    H(f"""<div class="ss-done-ic"><span style="font-size:34px;color:{GREEN}">{"↗" if k == "redeem" else "✓"}</span></div>
<div class="ss-center"><div class="ss-h1">{esc(title)}</div><div class="ss-sub" style="font-size:15px;line-height:22px">{esc(body)}</div></div>{rows}""")
    with st.container(key="primary_done"):
        if btn("Done", key="donebtn"):
            reset(); st.rerun()
    group = (S.saved[-1] if S.saved else "none").replace("_", "-")
    H(f'<div class="ss-small ss-center">You can change this from your SIP page at any time.<br>'
      f'Saved for Groww: the reason type "{esc(group)}". Your words were not saved.</div>')


# ---------- 10, 11, 12 and Groww's other pop-ups ----------
def dim_bg() -> None:
    chips = "".join(f'<div class="c">{esc(c)}</div>' for c in list(ai.CHIPS)[:4])
    H(f'<div class="ss-dim"><div class="t">Before you cancel, tell us what is happening</div>{chips}</div>')


ICON_STOP = """<div class="ss-icon"><svg width="64" height="72" viewBox="0 0 64 72" aria-hidden="true"><rect x="10" y="6" width="44" height="44" rx="8" transform="rotate(45 32 28)" fill="#A8BEFF" stroke="#5B6CF0" stroke-width="3"/><circle cx="32" cy="28" r="12" fill="none" stroke="#fff" stroke-width="4"/><path d="M24 20l16 16" stroke="#fff" stroke-width="4"/><path d="M26 56h12v12l-6-5-6 5z" fill="#5B6CF0"/></svg></div>"""
ICON_WARN = """<div class="ss-icon"><svg width="64" height="56" viewBox="0 0 64 56" aria-hidden="true"><path d="M14 52L28 4h8l14 48z" fill="#A8BEFF"/><path d="M36 4l14 48h-8z" fill="#5B6CF0"/><text x="32" y="34" text-anchor="middle" font-size="18" font-weight="700" fill="#3DBE8B">!</text></svg></div>"""


def sheet(icon: str, title: str, sub: str, primary: tuple[str, str], secondary: tuple[str, str], note: str = "",
          extra_link: bool = False) -> None:
    dim_bg()
    with st.container(key="sheet"):
        if note:
            H(note)
        if primary[1] == "cancel" and F["cancel_may_debit"]:
            sub += (f'<div class="ss-info" style="text-align:left">ⓘ Your {F["amount_text"]} instalment on {F["next_date_text"]} '
                    f'is due within {CANCEL_NOTICE_DAYS} days. It may still be taken before the SIP stops.</div>')
        H(f'{icon}<div class="ss-sheet-title">{esc(title)}</div>' + (f'<div class="ss-sheet-sub">{sub}</div>' if sub else ""))
        if extra_link:
            with st.container(key="link_money_tight"):
                if btn("Is money tight this month? See your options", key="money_tight"):
                    S.group = "cash_short"
                    save_reason("cash_short")
                    open_options(); st.rerun()
        with st.container(key="primary_sheet"):
            if btn(primary[0], key="sheet_primary"):
                act(primary[1]); st.rerun()
        with st.container(key="link_sheet"):
            if btn(secondary[0], key="sheet_secondary"):
                act(secondary[1]); st.rerun()
    footer()


def act(what: str) -> None:
    if what == "cancel":
        S.result = {"kind": "cancelled"}; go("done")
    elif what == "continue":
        S.result = {"kind": "continue"}; go("done")
    elif what == "skip":
        S.result = {"kind": "skip"}; go("done")
    elif what == "cancel_confirm":
        go("popup_cancel_confirm")
    elif what == "redeem":
        S.result = {"kind": "redeem"}; go("done")


def screen_popup_cancel() -> None:       # 10: same pop-up and text as Groww today
    sheet(ICON_STOP, "Future instalments will be stopped", "Your invested amount stays in this fund until you redeem it.",
          ("Cancel SIP", "cancel"), ("Continue investing", "continue"))


def screen_popup_withdraw() -> None:     # 10, withdraw version
    sheet(ICON_STOP, "Your money won't be withdrawn by cancelling",
          "Only future instalments will be stopped. To withdraw your invested amount, redeem it separately.",
          ("Cancel SIP", "cancel"), ("Redeem investments", "redeem"))


def screen_popup_general() -> None:      # 11
    sheet(ICON_STOP, "Future instalments will be stopped", "Your invested amount stays in this fund until you redeem it.",
          ("Cancel SIP", "cancel"), ("Continue investing", "continue"), extra_link=True)


def screen_popup_cancel_confirm() -> None:
    sheet(ICON_STOP, "Future instalments will be stopped", "Your invested amount stays in this fund until you redeem it.",
          ("Cancel SIP", "cancel"), ("Continue investing", "continue"))


def groww_date(d: date) -> str:
    return f"{d.day:02d} {MONTHS[d.month - 1][:3]} '{str(d.year)[2:]}"


def screen_popup_skip() -> None:         # Groww's skip pop-up
    sheet(ICON_WARN, f"Are you sure you want to skip the {groww_date(F['target_date'])} instalment?",
          f'<span style="background:#FFF6DA;border-radius:10px;padding:8px 12px;display:inline-block">ⓘ Your next due date will be {groww_date(F["target_after_date"])}</span>',
          ("Skip instalment", "skip"), ("Cancel SIP anyway", "cancel_confirm"))


def screen_fallback() -> None:           # 12
    note = (f'<div class="ss-warn">We could not explain this clearly right now. Here are your basic options. '
            f'<a href="{HELP_URL}" target="_blank">Read Groww\'s help page on SIPs</a>.</div>')
    if F["skip_ok"]:
        sheet(ICON_WARN, f"Are you sure you want to skip the {groww_date(F['target_date'])} instalment?",
              f'<span style="background:#FFF6DA;border-radius:10px;padding:8px 12px;display:inline-block">ⓘ Your next due date will be {groww_date(F["target_after_date"])}</span>',
              ("Skip instalment", "skip"), ("Cancel SIP anyway", "cancel_confirm"), note=note)
    else:  # skip is not allowed here, so show Groww's general pop-up instead
        sheet(ICON_STOP, "Future instalments will be stopped", "Your invested amount stays in this fund until you redeem it.",
              ("Cancel SIP", "cancel"), ("Continue investing", "continue"), note=note)


SCREENS = {
    "start": screen_start, "options": screen_options, "options_too_close": screen_too_close,
    "options_pay_less_used": screen_pay_less_used, "payless": screen_pay_less, "movedate": screen_move_date,
    "lower": screen_lower, "ask": screen_ask, "done": screen_done, "popup_cancel": screen_popup_cancel,
    "popup_withdraw": screen_popup_withdraw, "popup_general": screen_popup_general,
    "popup_cancel_confirm": screen_popup_cancel_confirm, "popup_skip": screen_popup_skip, "fallback": screen_fallback,
}

with st.container(key="phone"):
    SCREENS.get(S.screen, screen_start)()

# ---------- outside the phone: for reviewers ----------
with st.expander("For reviewers: how the AI is checked"):
    H('<div class="ss-small">AI (Gemini) does three jobs: it sorts typed words into a reason group, '
      'writes the facts in plain words, and answers questions. Fixed rules supply every number and date. '
      'Every AI text passes 5 checks before it is shown: facts match, rules correct, no advice, calm tone, right group. '
      'If one fails, the user sees Groww\'s current pop-up and a help link.<br><br>'
      '<b>Time limits.</b> Skip and changes use Groww\'s rule: not for an instalment within 2 working days. '
      'For cancel, Groww\'s help pages say 3 working days or 7 days. So an instalment due within 7 days "may still be taken". '
      'A skip asked within 2 working days applies to the next instalment, as on Groww. '
      'Real limits vary by fund house, and Groww says some funds cannot be edited at all. '
      'A launch would read each fund\'s own limits.</div>')
    if S.ai_sort:
        a = S.ai_sort
        H(f'<div class="ss-small" style="margin-top:6px">Last typed reply: group <b>{esc(a["group"])}</b>, '
          f'confidence {a["confidence"]:.2f}, check {"passed" if a["passed"] else "failed: shown the general pop-up"}.</div>')
    S.force_fail = st.toggle("Make the next quality check fail (to see the fallback)", value=S.force_fail)
    res = HERE / "golden" / "results.json"
    if res.exists():
        try:
            s = json.loads(res.read_text())["summary"]
            H(f"""<div class="ss-small" style="margin-top:6px"><b>Golden set results</b> (run on {json.loads(res.read_text())['today']}):<br>
Right group: {s.get('group_accuracy_exact', 0):.0%} exact, {s.get('group_accuracy_acceptable', 0):.0%} acceptable, over {s.get('sort_items')} situations.<br>
Right screen after the check: {s.get('route_accuracy_after_gate', 0):.0%}. Money-short replies that got the options: {s.get('cash_short_recall', 0):.0%}.<br>
AI texts passing all 5 checks: {s.get('text_gate_pass_rate', 0):.0%} of {s.get('ai_texts')}.<br>
Questions answered or declined correctly: {s.get('question_behaviour_ok', 0):.0%}.<br>
Planted bad texts caught by the check: {s.get('gate_tests_correct')}.</div>""")
        except Exception:
            pass
