"""The three AI jobs: sort the reply, explain the facts, answer a question.

Fixed rules supply every fact. AI only handles language. Every AI output goes
through gate.py before a user sees it.
"""
from __future__ import annotations

import re

from .llm import chat, parse_json, LLMError
from .sip import MISS_LIMIT, facts_for_prompt

GROUPS = ["cash_short", "break", "withdraw", "stop", "returns", "other"]
CONFIDENCE_MIN = 0.7

# The screen each group leads to (wireframe numbers). The app and the golden-set eval both use this map.
GROUP_SCREEN = {
    "cash_short": "options",      # 3, 8 or 9: own-SIP facts and the gentle options
    "break": "options",
    "withdraw": "popup_withdraw",  # 10, withdraw version
    "stop": "popup_cancel",        # 10: Groww's current pop-up
    "returns": "popup_cancel",
    "other": "popup_general",      # 11: general pop-up with "Is money tight this month?"
}

# Chips map to a group with no AI call.
CHIPS = {
    "Money is tight this month": "cash_short",
    "Need a break for a month or two": "break",
    "Want to stop for good": "stop",
    "Not happy with returns": "returns",
    "Something else": "other",
}

CLASSIFY_SYSTEM = """You sort what a Groww user wrote when they tapped Cancel SIP.
They may write in English, Hindi or a mix (Hinglish). Pick exactly one group:

cash_short: short of money for now. Salary late, high bill, EMI, rent, job loss, medical cost, wedding cost, low bank balance, a debit failed for low balance, cannot pay this month or the next few months. They do not say they want their invested money back.
break: wants a pause of a month or a few months for a reason that is not money, or gives no reason.
withdraw: wants the money already invested back. Words like withdraw, redeem, take out, need my money back.
stop: wants to stop for good and money is not the reason. Moving abroad, goal done, does not want this fund any more, switching to another fund or app, closing the account.
returns: unhappy with returns, losses, red portfolio, market fall, thinks FD or other things are better.
other: anything else. App problems, autopay or mandate trouble, forgot to pay, duplicate SIP, confusion, questions, personal details, or text that makes no sense.

Rules:
- If money is short now AND they also mention returns, choose cash_short.
- If they need money now and ask to take out invested money, choose withdraw.
- Wanting to close, stop or band karna the SIP with no reason, or for private reasons, is stop. It is never break.
- break needs a clear wish to pause for a time and then continue.
- Give confidence from 0 to 1. Use below 0.7 when the text fits two groups about equally.
- Never repeat numbers or personal details from the text.
Reply with JSON only: {"group": "...", "confidence": 0.0, "language": "en|hi|mixed"}"""


def classify(text: str) -> dict:
    """Return {group, confidence, language, model} or {error}."""
    try:
        raw, model = chat(CLASSIFY_SYSTEM, f"User wrote:\n{text}", json_mode=True, temperature=0)
        data = parse_json(raw)
    except (LLMError, ValueError) as e:
        return {"error": str(e)}
    group = str(data.get("group", "")).strip().lower()
    try:
        conf = float(data.get("confidence", 0))
    except (TypeError, ValueError):
        conf = 0.0
    return {"group": group, "confidence": conf,
            "language": str(data.get("language", "en")), "model": model}


STYLE = """Write in very simple words for a first-time investor. Short sentences. Calm and kind.
No exclamation marks. No fear or urgency words.
Use only the facts given. Do not add any other number, date or rule.
Write amounts like ₹3,000 and dates like 5 December.
Never name or suggest any fund, stock or product. Never say whether returns will be good or bad.
Never tell the user what they should do. Only explain what each choice means.
Never call the money safe, secure or protected. Say it stays invested."""


def explain(f: dict, language: str = "en", group: str = "cash_short") -> dict:
    """Plain-words explanation of the user's own SIP before the options."""
    lang = "Hindi (Devanagari script, but keep digits like 3,000)" if language in ("hi", "mixed") else "English"
    situation = ("The user is short of money for now." if group == "cash_short"
                 else "The user wants a short break.")
    if f.get("too_close"):
        focus = (f"The {f['next_date_text']} instalment is too close to change. Say calmly: if the balance is short on that date "
                 "the payment will not go through, it counts as 1 missed, the SIP stays active and the invested money stays invested. "
                 f"Then say the user can set up {f['target_month_text']} now.")
    elif f.get("pay_less_left") == 0:
        focus = ("Say that the invested money stays invested whatever they choose. Say pay less has been used "
                 f"{f['pay_less_used']} times in the last 12 months and opens again on {f['pay_less_reopen_text']}. "
                 f"Say that a skip counts as 1 missed and the rule of {f['miss_limit']} missed in a row.")
    elif f.get("misses_in_row", 0) >= MISS_LIMIT - 1:
        focus = (f"Say that the invested money stays invested. Say calmly that they have missed {f['misses_in_row']} in a row and that "
                 "if the next one is also missed, Groww will cancel this SIP. Say the options on this screen keep it running.")
    else:
        focus = ("Say that the invested money stays invested whatever they choose, and that Groww cancels a SIP only "
                 f"after {f['miss_limit']} missed instalments in a row.")
    system = f"""You explain a user's own SIP facts before they choose what to do. {situation}
{STYLE}
Write 2 or 3 short sentences in {lang}. The screen already shows a table with the amounts and dates.
{focus}
Do not list or describe the options. The screen shows them.
Reply with JSON only: {{"text": "..."}}"""
    try:
        raw, model = chat(system, "Facts:\n" + facts_for_prompt(f), json_mode=True)
        text = str(parse_json(raw).get("text", "")).strip()
    except (LLMError, ValueError) as e:
        return {"error": str(e)}
    return {"text": text, "model": model}


# Greetings, thanks and goodbyes get a fixed friendly reply. No AI call is needed.
_SMALL_TALK = [
    (re.compile(r"^(?:hi+|hello+|hey+|hii+|namaste|namaskar|good (?:morning|afternoon|evening)|नमस्ते|नमस्कार|हेलो|हाय)(?=[\s!.,?]|$)[\s!.,?]*(?:there|team|groww)?[\s!.,?]*$", re.I),
     {"en": "Hello. Ask me anything about this SIP, such as what skipping or paying less means.",
      "hi": "नमस्ते। इस SIP के बारे में कुछ भी पूछें, जैसे स्किप करने या कम पैसे भरने का क्या मतलब है।"}),
    (re.compile(r"^(?:thanks?|thank you|thank u|thx|ty|ok(?:ay)? thanks?|thanks a lot|thank you so much|great,? thanks?|dhanyavaad|dhanyawad|shukriya|धन्यवाद|शुक्रिया)(?=[\s!.,]|$)[\s!.,]*(?:so much|a lot)?[\s!.,]*$", re.I),
     {"en": "You are welcome. Ask another question any time, or go back to your options.",
      "hi": "आपका स्वागत है। कोई और सवाल हो तो पूछें, या अपने विकल्पों पर वापस जाएं।"}),
    (re.compile(r"^(?:ok(?:ay)?|okk+|fine|got it|cool|bye|goodbye|see you|theek hai|ठीक है|अलविदा)(?=[\s!.,]|$)[\s!.,]*$", re.I),
     {"en": "Sure. Ask another question any time, or go back to your options.",
      "hi": "ठीक है। कोई और सवाल हो तो पूछें, या अपने विकल्पों पर वापस जाएं।"}),
]


def small_talk(text: str) -> str | None:
    """Fixed reply for greetings, thanks and goodbyes, in the user's script. None if it is a real question."""
    t = text.strip()
    hindi = bool(re.search(r"[\u0900-\u097F]", t))
    for pat, replies in _SMALL_TALK:
        if pat.match(t):
            return replies["hi" if hindi else "en"]
    return None


def answer(question: str, f: dict, language: str = "en") -> dict:
    """Short factual answer to a follow-up question about this SIP."""
    fixed = small_talk(question)
    if fixed:
        return {"text": fixed, "declined": False, "small_talk": True, "model": None}
    system = f"""You answer a Groww user's question about their own SIP. Speak as Groww ("we").
{STYLE}
Answer in 1 to 3 short sentences, in the same language and script as the question.

Answer with facts when the question is about what a choice does: skip, pay less this month,
move date, cancel, missing instalments, or what happens to invested money. If they ask whether
a choice affects returns, say plainly how much less is invested that month, that the money already
invested stays invested, and that nobody can predict returns. That is a fact, not advice.

If the facts say an instalment is too close to change, and the question is about skipping, lowering or moving
a payment, first say that this instalment cannot be changed and still goes ahead. Then say what can be done from
the next one.

Decline only when they ask which fund to pick, whether they should stop or continue, what the market
or returns will do, or to check account details. Then start with: "We cannot suggest funds or what to do.
This is not investment advice." You may add one relevant fact from the list. Set declined to true.
If the facts do not cover the question, say "We are not sure about this. Please see Groww's help pages."
and set declined to true.
If the message is only a greeting, thanks or small talk, reply in one friendly sentence and invite a
question about this SIP. Set declined to false.
If the question has an account number, PAN or other personal detail, do not repeat it or use it.
Say we cannot look up account details here. Set declined to true.
Reply with JSON only: {{"answer": "...", "declined": true|false}}"""
    try:
        raw, model = chat(system, "Facts:\n" + facts_for_prompt(f) + f"\n\nQuestion:\n{question}",
                          json_mode=True)
        data = parse_json(raw)
    except (LLMError, ValueError) as e:
        return {"error": str(e)}
    return {"text": str(data.get("answer", "")).strip(),
            "declined": bool(data.get("declined", False)), "model": model}
