# Discovery engine

Reads public feedback about SIPs on Groww (Play Store, App Store, Reddit, TradingQ&A, YouTube), tags it with Gemini,
counts it, and ranks opportunity areas by reach, drop-off link and how fixable they are in the app.

- `collect/` pulls posts from each source into `data/raw/` (not stored in this repo).
- `tag/tag.py` first pass: relevant or not, 13 themes, stage, status, stated segment cues. `tag/extract.py` second pass: reasons, expectations, what people check, app area, outside action, unmet need.
- `analyze/` counts, drop-off links and `opportunities.py` (the ranking).
- `golden/` the hand-labelled validation set and scoring.
- `app/` the Streamlit app. It reads stored results from `app/data/` and makes no AI calls at run time.

Run the app: `cd discovery-engine/app && pip install -r requirements.txt && streamlit run app.py`.
Rebuild its data after re-running the analysis: `python build_app_data.py`.
