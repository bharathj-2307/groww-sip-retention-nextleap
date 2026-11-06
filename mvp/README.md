# Steady SIP: Short on Cash, Not on Plans

A clickable MVP of a changed Groww SIP cancel flow, built for a NextLeap case study.
It is not a Groww product. It runs on four sample SIPs. No real user data is used or stored.

## What it does

1. The user taps Cancel SIP and sees "Before you cancel, tell us what is happening". They tap a reason or type in English or Hindi.
2. Gemini sorts typed words into a group: short of money, short break, take money out, stop for good, returns, or other.
3. A user who is short of money sees the facts of their own SIP and three one-tap options: pay less this month, skip, or move the date to after payday. They can also ask questions about their SIP.
4. Everyone else sees Groww's current pop-up straight away.

Fixed rules supply every number and date (`core/sip.py`). AI only writes the words.
Every AI text passes 5 checks before it is shown (`core/gate.py`): facts match, rules correct, no advice, calm tone, right group.
If one check fails, the user sees Groww's current pop-up and a link to Groww's help page.

## Sample SIPs

| Sample | Shows |
|---|---|
| Normal month | Screen 3 with all three options |
| Debit is very close | Screen 8: the next debit is less than 2 working days away, so pay less and move date apply from next month |
| Pay less used twice | Screen 9: pay less is locked until a year after its first use |
| Missed 2 in a row | Skip is hidden, because a third miss would cancel the SIP |

## Golden set

`golden/golden_set.json` holds 30 situations to sort, 15 questions and 14 planted good or bad texts.
They are paraphrased from discovery engine posts and interview themes. Run from this folder:

```
python3 -m golden.run_eval
```

Results go to `golden/results.json`. The app shows the summary under "For reviewers".

## Run and deploy

```
pip install -r requirements.txt
GEMINI_API_KEY=... streamlit run app.py
```

On Streamlit Community Cloud, set the main file to `mvp/app.py`. Add the key under Settings, then Secrets:

```
GEMINI_API_KEY = "your key"
```

The key never goes in the repo.
