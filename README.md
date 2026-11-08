# Groww SIP retention (NextLeap graduation project)

A Growth PM case study. The goal is to keep more first-time SIP investors on Groww active 12 months after their first SIP.
Active means at least one successful instalment in the last 30 days.

This is a student project. It is not a Groww product and is not investment advice.

## What is in this repo

| Folder | What it is | Live link |
|---|---|---|
| [`discovery-engine/`](discovery-engine/) | AI discovery engine. It reads public posts about SIPs on Groww, tags them with Gemini, and ranks opportunity areas. | [Open the engine](https://groww-sip-retention-ai-build-engine.streamlit.app/) |
| [`mvp/`](mvp/) | Steady SIP, the MVP. A changed Cancel SIP flow for people who are short of money in a SIP month. It is built around an eval-gated AI feature. | [Open the MVP](https://groww-steady-sip.streamlit.app/) |

## How the parts connect

1. **Discovery engine.** It read 7,386 public posts from the Play Store, App Store, Reddit, TradingQ&A and YouTube. It found 4,487 real experiences and ranked the problems linked to stopping a SIP.
2. **Segment and problem.** Interviews and a survey confirmed the focus: salaried first-time investors in year one of their first SIP who are short of money in a SIP month.
3. **Steady SIP.** When such a user taps Cancel, they see the facts of their own SIP and three gentle options: pay less this month, skip, or move the date. AI reads what they type and writes plain words. Fixed rules supply every number and date.
4. **AI quality.** Every AI text passes 5 checks before it is shown. If one fails, the user sees Groww's current pop-up and a help link. The AI is scored on a golden set and a fresh holdout set.

## Run it locally

Discovery engine app:

```
cd discovery-engine/app
pip install -r requirements.txt
streamlit run app.py
```

Steady SIP:

```
cd mvp
pip install -r requirements.txt
GEMINI_API_KEY=... streamlit run app.py
python3 -m tests.test_dates      # date rules
python3 -m golden.run_eval       # AI quality on the golden set
```

Each folder's README has more detail.

## Data and privacy

- Raw posts, API keys, interview notes and survey answers are not stored in this repo.
- The MVP runs on four made-up sample SIPs. It does not ask for account numbers or PAN.
- The API key is read from the environment or Streamlit secrets. It is never committed.
