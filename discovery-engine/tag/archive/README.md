# Earlier prompt versions

These scripts are kept only to show how the prompts changed after the golden set checks. They are not run.

| File | Replaced by | What changed |
|---|---|---|
| `tag_v1.py` | `../tag.py` | First tagging prompt. |
| `tag_v2.py` | `../tag.py` | v2: praise and complaints count as relevant, "asking others" includes posts that ask for advice, stage rules. v3 (current) adds the status rule. |
| `extract_v1.py` | `../extract.py` | First second-pass prompt. v2 (current) adds the drop reason, failed instalment, app area and need rules. |

The current scripts share one Gemini client, `../gemini_batch.py`.
