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
| Case 1: Never missed a payment | Screen 3 with all three options |
| Case 2: Payment is 1 or 2 days away | Screen 8: the next payment is within 2 working days, so it goes ahead. Skip, pay less and move date apply from next month |
| Case 3: Already paid less twice | Screen 9: pay less is locked until a year after its first use |
| Case 4: Missed last 2 payments | Skip is hidden, because a third miss would cancel the SIP |

## Golden set

`golden/golden_set.json` holds 30 situations to sort, 18 questions and 23 planted good or bad texts.
They are paraphrased from discovery engine posts and interview themes. Run from this folder:

```
python3 -m golden.run_eval
```

Results go to `golden/results.json`. The app shows the summary under "For reviewers".

`golden/holdout_set.json` is a fresh set of 20 situations, 10 questions and 8 planted texts.
Its expected answers were committed before the first run. Run it with `python3 -m golden.run_eval --holdout`.
The first run is kept in `golden/holdout_results_before_fixes.json`. The run after fixes is in `golden/holdout_results.json`.

Date rules are checked for every day from today to the end of 2028, for all 4 cases and 13 salary days
(month ends, year end and the leap February included):

```
python3 -m tests.test_dates
```

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
